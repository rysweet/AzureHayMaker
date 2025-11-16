// Azure HayMaker Infrastructure - Main Template
// Purpose: Orchestrates deployment of all Azure resources for HayMaker orchestrator

targetScope = 'subscription'

// Parameters
@description('Environment name (dev, staging, prod)')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environment string

@description('Azure region for all resources')
param location string = 'eastus'

@description('Naming prefix for all resources')
@minLength(3)
@maxLength(10)
param namingPrefix string = 'haymaker'

@description('Azure AD tenant ID')
param tenantId string = tenant().tenantId

@description('Azure subscription ID')
param subscriptionId string = subscription().subscriptionId

@description('Admin object IDs for Key Vault access')
param adminObjectIds array = []

@description('Client ID for GitHub OIDC authentication')
param githubOidcClientId string = ''

// Variables
@description('Deployment timestamp for unique resource names')
param deploymentTimestamp string = utcNow('yyyyMMddHHmmss')

var uniqueSuffix = uniqueString(subscription().id, namingPrefix, environment, deploymentTimestamp)
var resourceGroupName = '${namingPrefix}-${environment}-${take(uniqueSuffix, 6)}-rg'
var commonTags = {
  Environment: environment
  ManagedBy: 'Bicep'
  Project: 'AzureHayMaker'
  DeployedBy: 'GitHubActions'
}

// Resource names with environment suffix and unique identifiers for globally unique resources
var logAnalyticsName = '${namingPrefix}-${environment}-logs'
var storageAccountName = toLower('${namingPrefix}${environment}${take(uniqueSuffix, 6)}')
var serviceBusName = '${namingPrefix}-${environment}-${take(uniqueSuffix, 6)}-bus'
var keyVaultName = '${namingPrefix}-${environment}-${take(uniqueSuffix, 6)}-kv'
var cosmosDbName = '${namingPrefix}-${environment}-${take(uniqueSuffix, 6)}-cosmos'
var containerAppsEnvName = '${namingPrefix}-${environment}-cae'
var containerRegistryName = toLower('${namingPrefix}${environment}${take(uniqueSuffix, 6)}acr')
var functionAppName = '${namingPrefix}-${environment}-${take(uniqueSuffix, 6)}-func'
var appServicePlanName = '${namingPrefix}-${environment}-plan'

// Resource Group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: commonTags
}

// Log Analytics Workspace
module logAnalytics 'modules/log-analytics.bicep' = {
  scope: resourceGroup
  name: 'logAnalytics-${uniqueSuffix}'
  params: {
    workspaceName: logAnalyticsName
    location: location
    tags: commonTags
    retentionInDays: environment == 'prod' ? 90 : 30
    sku: 'PerGB2018'
  }
}

// Storage Account
module storage 'modules/storage.bicep' = {
  scope: resourceGroup
  name: 'storage-${uniqueSuffix}'
  params: {
    storageAccountName: storageAccountName
    location: location
    tags: commonTags
    sku: environment == 'prod' ? 'Standard_GRS' : 'Standard_LRS'
    enableVersioning: environment == 'prod'
    retentionDays: environment == 'prod' ? 30 : 7
  }
}

// Service Bus
module serviceBus 'modules/servicebus.bicep' = {
  scope: resourceGroup
  name: 'serviceBus-${uniqueSuffix}'
  params: {
    namespaceName: serviceBusName
    location: location
    tags: commonTags
    sku: environment == 'prod' ? 'Standard' : 'Standard'
    topicName: 'agent-logs'
    queueName: 'execution-requests'
  }
}

// Key Vault
module keyVault 'modules/keyvault.bicep' = {
  scope: resourceGroup
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
  }
}

// Cosmos DB
module cosmosDb 'modules/cosmosdb.bicep' = {
  scope: resourceGroup
  name: 'cosmosDb-${uniqueSuffix}'
  params: {
    accountName: cosmosDbName
    location: location
    tags: commonTags
    databaseName: 'haymaker'
    metricsContainerName: 'metrics'
    runsContainerName: 'runs'
    throughput: environment == 'prod' ? 400 : 0 // Serverless for dev/staging
  }
}

// Container Apps Environment
module containerAppsEnv 'modules/container-apps-env.bicep' = {
  scope: resourceGroup
  name: 'containerAppsEnv-${uniqueSuffix}'
  params: {
    environmentName: containerAppsEnvName
    location: location
    tags: commonTags
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    logAnalyticsSharedKey: logAnalytics.outputs.primarySharedKey
  }
}

// Container Registry
module containerRegistry 'modules/container-registry.bicep' = {
  scope: resourceGroup
  name: 'containerRegistry-${uniqueSuffix}'
  params: {
    registryName: containerRegistryName
    location: location
    tags: commonTags
    sku: 'Standard'  // Basic SKU not supported in some subscriptions
    adminUserEnabled: true
  }
}

// Function App (depends on most other resources)
module functionApp 'modules/function-app.bicep' = {
  scope: resourceGroup
  name: 'functionApp-${uniqueSuffix}'
  params: {
    functionAppName: functionAppName
    appServicePlanName: appServicePlanName
    location: location
    tags: commonTags
    storageConnectionString: storage.outputs.connectionString
    appInsightsConnectionString: logAnalytics.outputs.workspaceId
    keyVaultUri: keyVault.outputs.keyVaultUri
    serviceBusConnectionString: serviceBus.outputs.connectionString
    cosmosDbConnectionString: cosmosDb.outputs.connectionString
    tenantId: tenantId
    subscriptionId: subscriptionId
    clientId: githubOidcClientId
    environment: environment
    pythonVersion: '3.13'
  }
}

// Grant Function App access to Key Vault (via module to match scope)
module functionAppKeyVaultRole 'modules/role-assignment.bicep' = {
  scope: resourceGroup
  name: 'functionAppKeyVaultRole-${uniqueSuffix}'
  params: {
    principalId: functionApp.outputs.principalId
    roleDefinitionId: '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App access to Storage (via module to match scope)
module functionAppStorageRole 'modules/role-assignment.bicep' = {
  scope: resourceGroup
  name: 'functionAppStorageRole-${uniqueSuffix}'
  params: {
    principalId: functionApp.outputs.principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App access to Cosmos DB (via module to match scope)
module functionAppCosmosRole 'modules/role-assignment.bicep' = {
  scope: resourceGroup
  name: 'functionAppCosmosRole-${uniqueSuffix}'
  params: {
    principalId: functionApp.outputs.principalId
    roleDefinitionId: '00000000-0000-0000-0000-000000000002' // Cosmos DB Built-in Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output resourceGroupName string = resourceGroup.name
output location string = location
output environment string = environment

// Infrastructure outputs
output logAnalyticsWorkspaceId string = logAnalytics.outputs.workspaceId
output logAnalyticsCustomerId string = logAnalytics.outputs.customerId
output storageAccountName string = storage.outputs.storageAccountName
output serviceBusNamespace string = serviceBus.outputs.namespaceName
output keyVaultName string = keyVault.outputs.keyVaultName
output keyVaultUri string = keyVault.outputs.keyVaultUri
output cosmosDbEndpoint string = cosmosDb.outputs.endpoint
output cosmosDbDatabaseName string = cosmosDb.outputs.databaseName
output containerAppsEnvironmentName string = containerAppsEnv.outputs.environmentName
output containerRegistryName string = containerRegistry.outputs.registryName
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer

// Function App outputs
output functionAppName string = functionApp.outputs.functionAppName
output functionAppUrl string = functionApp.outputs.functionAppUrl
output functionAppPrincipalId string = functionApp.outputs.principalId
