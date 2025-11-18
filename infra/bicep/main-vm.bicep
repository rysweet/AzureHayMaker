// Azure HayMaker Infrastructure - VM-Based Orchestrator
// Replaces Function App with VM for 64GB+ RAM requirement

targetScope = 'resourceGroup'

@description('Environment name (dev/staging/prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Admin object IDs for Key Vault access')
param adminObjectIds array

@description('GitHub OIDC client ID for federated identity')
param githubOidcClientId string

@description('SSH public key for VM access')
@secure()
param sshPublicKey string

// Common tags
var commonTags = {
  Environment: environment
  Project: 'AzureHayMaker'
  ManagedBy: 'Bicep'
  DeployedBy: 'GitHubActions'
}

// Generate unique suffix
var uniqueSuffix = uniqueString(resourceGroup().id, environment)

// Resource names
var vmName = 'haymaker-${environment}-${uniqueSuffix}-vm'
var keyVaultName = 'haymaker-${environment}-${substring(uniqueSuffix, 0, 6)}-kv'
var serviceBusName = 'haymaker-${environment}-${uniqueSuffix}-bus'
var storageName = 'haymaker${environment}${substring(uniqueSuffix, 0, 8)}'

// Tenant and subscription info
var tenantId = tenant().tenantId
var subscriptionId = subscription().subscriptionId

// Storage Account
module storage 'modules/storage.bicep' = {
  name: 'storage-${uniqueSuffix}'
  params: {
    storageAccountName: storageName
    location: location
    tags: commonTags
  }
}

// Key Vault
module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVault-${uniqueSuffix}'
  params: {
    keyVaultName: keyVaultName
    location: location
    tags: commonTags
    tenantId: tenantId
    adminObjectIds: adminObjectIds
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: environment == 'prod'
    publicNetworkAccess: true  // Allow all for GitHub Actions + VM access
  }
}

// Service Bus
module serviceBus 'modules/servicebus.bicep' = {
  name: 'serviceBus-${uniqueSuffix}'
  params: {
    namespaceName: serviceBusName
    location: location
    tags: commonTags
    sku: environment == 'prod' ? 'Premium' : 'Standard'
  }
}

// Log Analytics
module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'logAnalytics-${uniqueSuffix}'
  params: {
    workspaceName: 'haymaker-${environment}-${uniqueSuffix}-logs'
    location: location
    tags: commonTags
    sku: 'PerGB2018'
    retentionInDays: environment == 'prod' ? 90 : 30
  }
}

// Orchestrator VM with 64GB RAM
module orchestratorVM 'modules/orchestrator-vm.bicep' = {
  name: 'orchestratorVM-${uniqueSuffix}'
  params: {
    vmName: vmName
    location: location
    tags: commonTags
    sshPublicKey: sshPublicKey
    vmSize: 'Standard_E8s_v3' // 64GB RAM - EXACTLY what captain ordered!
    environment: environment
    keyVaultUri: keyVault.outputs.keyVaultUri
  }
}

// Grant VM access to Key Vault
module vmKeyVaultRole 'modules/role-assignment.bicep' = {
  name: 'vmKeyVaultRole-${uniqueSuffix}'
  params: {
    principalId: orchestratorVM.outputs.principalId
    roleDefinitionId: '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
  }
}

// Outputs
output vmName string = orchestratorVM.outputs.vmName
output vmPublicIP string = orchestratorVM.outputs.publicIPAddress
output vmFQDN string = orchestratorVM.outputs.fqdn
output keyVaultName string = keyVault.outputs.keyVaultName
output serviceBusName string = serviceBus.outputs.namespaceName
output storageName string = storage.outputs.storageAccountName
