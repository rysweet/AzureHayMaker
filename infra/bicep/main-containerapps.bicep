// Azure HayMaker - Container Apps Architecture
// Orchestrator on Container Apps with E16 workload profile (128GB RAM)
// All automation via GitOps - Captain's requirement

targetScope = 'resourceGroup'

@description('Environment name (dev/staging/prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Admin object IDs for Key Vault access')
param adminObjectIds array

@description('GitHub OIDC client ID')
param githubOidcClientId string

@description('Orchestrator container image')
param orchestratorImage string = 'haymakerorchacr.azurecr.io/haymaker-orchestrator:latest'

@description('Agent container image')
param agentImage string = 'azure-haymaker-agent:latest'

@description('Simulation size')
param simulationSize string = 'small'

// Common tags
var commonTags = {
  Environment: environment
  Project: 'AzureHayMaker'
  ManagedBy: 'Bicep'
  DeployedBy: 'GitHubActions'
  Architecture: 'ContainerApps'
}

// Generate unique suffix
var uniqueSuffix = uniqueString(resourceGroup().id, environment)

// Resource names (keep under 32 chars for Container Apps)
var containerAppEnvName = 'haymaker-${environment}-${uniqueSuffix}-cae'
var orchestratorAppName = 'orch-${environment}-${substring(uniqueSuffix, 0, 10)}' // <32 chars
var keyVaultName = 'haymaker-${environment}-${substring(uniqueSuffix, 0, 6)}-kv'
var serviceBusName = 'haymaker-${environment}-${uniqueSuffix}-bus'
var storageName = 'haymaker${environment}${substring(uniqueSuffix, 0, 8)}'

// Tenant and subscription
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
    publicNetworkAccess: true // Allow for GitHub Actions + Container Apps
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

// Container Registry for orchestrator images
module containerRegistry 'modules/container-registry.bicep' = {
  name: 'acr-${uniqueSuffix}'
  params: {
    registryName: 'haymakerorchacr'
    location: location
    tags: commonTags
    sku: 'Basic' // Basic for dev, can upgrade for prod
    adminUserEnabled: true
  }
}

// Container Apps Environment with E16 workload profile
module containerAppsEnv 'modules/containerapp-environment.bicep' = {
  name: 'containerAppsEnv-${uniqueSuffix}'
  params: {
    environmentName: containerAppEnvName
    location: location
    tags: commonTags
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    // E16 workload profile: 128GB RAM, 16 vCPU (same for dev and prod per Captain)
    workloadProfiles: [
      {
        name: 'E16'
        workloadProfileType: 'E16'
        minimumCount: 1
        maximumCount: environment == 'prod' ? 3 : 1
      }
    ]
  }
}

// Orchestrator Container App with 128GB RAM
module orchestrator 'modules/orchestrator-containerapp.bicep' = {
  name: 'orchestrator-${uniqueSuffix}'
  params: {
    containerAppName: orchestratorAppName
    location: location
    tags: commonTags
    environmentId: containerAppsEnv.outputs.environmentId
    containerImage: orchestratorImage
    containerRegistry: containerRegistry.outputs.loginServer // Use ACR for orchestrator images
    environment: environment
    keyVaultUri: keyVault.outputs.keyVaultUri
    serviceBusNamespace: serviceBus.outputs.namespaceName
    storageAccountName: storage.outputs.storageAccountName
    cosmosDbEndpoint: ''
    tenantId: tenantId
    subscriptionId: subscriptionId
    clientId: githubOidcClientId
    simulationSize: simulationSize
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
  }
}

// Grant Orchestrator access to Key Vault
module orchestratorKeyVaultRole 'modules/role-assignment.bicep' = {
  name: 'orchestratorKeyVaultRole-${uniqueSuffix}'
  params: {
    principalId: orchestrator.outputs.principalId
    roleDefinitionId: '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
  }
}

// Grant Orchestrator access to ACR (AcrPull)
resource orchestratorAcrRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.outputs.registryId, orchestrator.outputs.principalId, 'AcrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: orchestrator.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output containerAppEnvName string = containerAppsEnv.outputs.environmentName
output orchestratorName string = orchestrator.outputs.containerAppName
output orchestratorFqdn string = orchestrator.outputs.fqdn
output keyVaultName string = keyVault.outputs.keyVaultName
output serviceBusName string = serviceBus.outputs.namespaceName
output storageName string = storage.outputs.storageAccountName
