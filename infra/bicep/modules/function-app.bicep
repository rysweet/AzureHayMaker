// Function App Module
// Purpose: Azure Functions hosting for orchestrator

@description('Function App name')
param functionAppName string

@description('Azure region')
param location string = resourceGroup().location

@description('Resource tags')
param tags object = {}

@description('App Service Plan name')
param appServicePlanName string

@description('Storage account connection string')
@secure()
param storageConnectionString string

@description('Application Insights connection string')
@secure()
param appInsightsConnectionString string

@description('Key Vault URI for secret references')
param keyVaultUri string

@description('Service Bus connection string')
@secure()
param serviceBusConnectionString string

@description('Cosmos DB connection string')
@secure()
param cosmosDbConnectionString string

@description('Azure tenant ID')
param tenantId string

@description('Azure subscription ID')
param subscriptionId string

@description('Azure client ID (managed identity)')
param clientId string

@description('Environment name (dev/staging/prod)')
param environment string

@description('Python version')
param pythonVersion string = '3.13'

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  tags: tags
  sku: {
    name: environment == 'prod' ? 'EP1' : 'B1' // Elastic Premium for prod, Basic for dev/staging (avoids quota issues)
    tier: environment == 'prod' ? 'ElasticPremium' : 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${functionAppName}-insights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Request_Source: 'rest'
    WorkspaceResourceId: null
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    clientAffinityEnabled: false
    siteConfig: {
      linuxFxVersion: 'PYTHON|${pythonVersion}'
      appSettings: [
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'AzureWebJobsStorage'
          value: storageConnectionString
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'AZURE_FUNCTIONS_ENVIRONMENT'
          value: environment
        }
        // Azure Identity
        {
          name: 'AZURE_TENANT_ID'
          value: tenantId
        }
        {
          name: 'AZURE_SUBSCRIPTION_ID'
          value: subscriptionId
        }
        {
          name: 'AZURE_CLIENT_ID'
          value: clientId
        }
        // Key Vault
        {
          name: 'KEY_VAULT_URL'
          value: keyVaultUri
        }
        // Service Bus
        {
          name: 'ServiceBusConnection'
          value: serviceBusConnectionString
        }
        // Cosmos DB
        {
          name: 'CosmosDbConnection'
          value: cosmosDbConnectionString
        }
        // Storage accounts
        {
          name: 'STORAGE_ACCOUNT_NAME'
          value: split(split(storageConnectionString, ';')[1], '=')[1]
        }
        {
          name: 'TABLE_STORAGE_ACCOUNT_NAME'
          value: split(split(storageConnectionString, ';')[1], '=')[1]
        }
        // Secrets from Key Vault (referenced)
        {
          name: 'MAIN_SP_CLIENT_SECRET'
          value: '@Microsoft.KeyVault(VaultName=${split(keyVaultUri, '.')[0]};SecretName=main-sp-client-secret)'
        }
        {
          name: 'ANTHROPIC_API_KEY'
          value: '@Microsoft.KeyVault(VaultName=${split(keyVaultUri, '.')[0]};SecretName=anthropic-api-key)'
        }
        {
          name: 'LOG_ANALYTICS_WORKSPACE_KEY'
          value: '@Microsoft.KeyVault(VaultName=${split(keyVaultUri, '.')[0]};SecretName=log-analytics-workspace-key)'
        }
      ]
      cors: {
        allowedOrigins: [
          'https://portal.azure.com'
        ]
      }
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
  }
}

// Outputs
output functionAppId string = functionApp.id
output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output principalId string = functionApp.identity.principalId
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output appInsightsConnectionString string = appInsights.properties.ConnectionString
