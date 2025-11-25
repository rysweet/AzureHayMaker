// Azure HayMaker Infrastructure - Main Template
// Purpose: Orchestrates deployment of all Azure resources for HayMaker orchestrator
//
// NOTE: Deploy to existing resource group. Create RG first:
// az group create --name haymaker-<env>-rg --location <region>

targetScope = 'resourceGroup'

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

// Resource Group should be created before deploying this template
// Example: az group create --name haymaker-dev-rg --location westus2

// Log Analytics Workspace
module logAnalytics 'modules/log-analytics.bicep' = {
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
    publicNetworkAccess: environment != 'prod'  // Enable public access for dev/staging (GitHub Actions needs it)
  }
}

// Cosmos DB
// Cosmos DB (Optional for dev - region capacity limitations)
module cosmosDb 'modules/cosmosdb.bicep' = if (environment != 'dev') {
  name: 'cosmosDb-${uniqueSuffix}'
  params: {
    accountName: cosmosDbName
    location: location
    tags: commonTags
    databaseName: 'haymaker'
    metricsContainerName: 'metrics'
    runsContainerName: 'runs'
    throughput: environment == 'prod' ? 400 : 0 // Serverless for staging
  }
}

// Container Apps Environment
module containerAppsEnv 'modules/container-apps-env.bicep' = {
  name: 'containerAppsEnv-${uniqueSuffix}'
  params: {
    environmentName: containerAppsEnvName
    location: location
    tags: commonTags
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    logAnalyticsSharedKey: logAnalytics.outputs.primarySharedKey
  }
}

// Container Registry (Optional for dev - SKU limitations in some subscriptions)
module containerRegistry 'modules/container-registry.bicep' = if (environment != 'dev') {
  name: 'containerRegistry-${uniqueSuffix}'
  params: {
    registryName: containerRegistryName
    location: location
    tags: commonTags
    sku: 'Premium'
    adminUserEnabled: false
  }
}

// Function App (depends on most other resources)
module functionApp 'modules/function-app.bicep' = {
  name: 'functionApp-${uniqueSuffix}'
  params: {
    functionAppName: functionAppName
    appServicePlanName: appServicePlanName
    location: location
    tags: commonTags
    // SECURITY: Using managed identity instead of connection strings
    storageAccountName: storage.outputs.storageAccountName
    appInsightsConnectionString: logAnalytics.outputs.workspaceId
    keyVaultUri: keyVault.outputs.keyVaultUri
    // SECURITY: Removed connection strings - use Managed Identity instead
    tenantId: tenantId
    subscriptionId: subscriptionId
    clientId: githubOidcClientId
    environment: environment
    pythonVersion: '3.13'
    // Additional parameters for orchestrator configuration
    serviceBusNamespace: serviceBus.outputs.namespaceName
    containerRegistryLoginServer: environment != 'dev' ? containerRegistry.outputs.loginServer : ''
    containerImage: 'azure-haymaker-agent:latest'
    simulationSize: 'small'
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    resourceGroupName: resourceGroup().name
  }
}

// Grant Function App access to Key Vault (via module to match scope)
module functionAppKeyVaultRole 'modules/role-assignment.bicep' = {
  name: 'functionAppKeyVaultRole-${uniqueSuffix}'
  params: {
    principalId: functionApp.outputs.principalId
    roleDefinitionId: '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App access to Storage (via module to match scope)
module functionAppStorageRole 'modules/role-assignment.bicep' = {
  name: 'functionAppStorageRole-${uniqueSuffix}'
  params: {
    principalId: functionApp.outputs.principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App access to Storage Tables (via module to match scope)
module functionAppStorageTableRole 'modules/role-assignment.bicep' = {
  name: 'functionAppStorageTableRole-${uniqueSuffix}'
  params: {
    principalId: functionApp.outputs.principalId
    roleDefinitionId: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3' // Storage Table Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App access to Storage Queue (via module to match scope)
module functionAppStorageQueueRole 'modules/role-assignment.bicep' = {
  name: 'functionAppStorageQueueRole-${uniqueSuffix}'
  params: {
    principalId: functionApp.outputs.principalId
    roleDefinitionId: '974c5e8b-45b9-4653-ba55-5f855dd0fb88' // Storage Queue Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App access to Service Bus (via module to match scope)
module functionAppServiceBusRole 'modules/role-assignment.bicep' = {
  name: 'functionAppServiceBusRole-${uniqueSuffix}'
  params: {
    principalId: functionApp.outputs.principalId
    roleDefinitionId: '090c5cfd-751d-490a-894a-3ce6f1109419' // Azure Service Bus Data Owner
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App access to ACR (via module to match scope) - only if ACR is deployed
module functionAppAcrRole 'modules/role-assignment.bicep' = if (environment != 'dev') {
  name: 'functionAppAcrRole-${uniqueSuffix}'
  params: {
    principalId: functionApp.outputs.principalId
    roleDefinitionId: '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App access to Cosmos DB (via module to match scope) - only if Cosmos DB is deployed
module functionAppCosmosRole 'modules/role-assignment.bicep' = if (environment != 'dev') {
  name: 'functionAppCosmosRole-${uniqueSuffix}'
  params: {
    principalId: functionApp.outputs.principalId
    roleDefinitionId: '00000000-0000-0000-0000-000000000002' // Cosmos DB Built-in Data Contributor
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output resourceGroupName string = resourceGroup().name
output location string = resourceGroup().location
output environment string = environment

// Infrastructure outputs
output logAnalyticsWorkspaceId string = logAnalytics.outputs.workspaceId
output logAnalyticsCustomerId string = logAnalytics.outputs.customerId
output storageAccountName string = storage.outputs.storageAccountName
output serviceBusNamespace string = serviceBus.outputs.namespaceName
output keyVaultName string = keyVault.outputs.keyVaultName
output keyVaultUri string = keyVault.outputs.keyVaultUri
output cosmosDbEndpoint string = environment != 'dev' ? cosmosDb.outputs.endpoint : ''
output cosmosDbDatabaseName string = environment != 'dev' ? cosmosDb.outputs.databaseName : ''
output containerAppsEnvironmentName string = containerAppsEnv.outputs.environmentName
output containerRegistryName string = environment != 'dev' ? containerRegistry.outputs.registryName : ''
output containerRegistryLoginServer string = environment != 'dev' ? containerRegistry.outputs.loginServer : ''

// Function App outputs
output functionAppName string = functionApp.outputs.functionAppName
output functionAppUrl string = functionApp.outputs.functionAppUrl
output functionAppPrincipalId string = functionApp.outputs.principalId
