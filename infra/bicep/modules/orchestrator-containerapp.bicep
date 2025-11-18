// Orchestrator Container App Module
// Purpose: Run orchestrator with 128GB RAM using E16 workload profile + KEDA CRON scheduling

@description('Container App name')
param containerAppName string

@description('Azure region')
param location string = resourceGroup().location

@description('Resource tags')
param tags object = {}

@description('Container Apps Environment resource ID')
param environmentId string

@description('Container image')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Container registry server')
param containerRegistry string = ''

@description('Environment name (dev/staging/prod)')
param environment string

@description('Key Vault URI')
param keyVaultUri string

@description('Service Bus namespace')
param serviceBusNamespace string

@description('Storage account name')
param storageAccountName string

@description('Cosmos DB endpoint')
param cosmosDbEndpoint string = ''

@description('Tenant ID')
param tenantId string

@description('Subscription ID')
param subscriptionId string

@description('Client ID')
param clientId string

@description('Simulation size')
param simulationSize string = 'small'

@description('Log Analytics workspace ID')
param logAnalyticsWorkspaceId string

// Container App for Orchestrator with 128GB RAM
resource orchestratorApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: environmentId
    workloadProfileName: 'E16' // 128GB RAM, 16 vCPU - Captain's specification!
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: []
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: containerRegistry != '' ? [
        {
          server: containerRegistry
          identity: 'system'
        }
      ] : []
    }
    template: {
      scale: {
        minReplicas: 0 // Scale to zero when not running
        maxReplicas: 1 // Single instance for orchestrator
        rules: [
          {
            name: 'cron-schedule'
            custom: {
              type: 'cron'
              metadata: {
                timezone: 'UTC'
                start: '0 0,6,12,18 * * *' // 4x daily: 00:00, 06:00, 12:00, 18:00 UTC
                end: '0 1,7,13,19 * * *'   // End 1 hour later
                desiredReplicas: '1'
              }
            }
          }
          {
            name: 'startup-trigger'
            custom: {
              type: 'cron'
              metadata: {
                timezone: 'UTC'
                start: '@reboot' // Run on startup
                desiredReplicas: '1'
              }
            }
          }
        ]
      }
      containers: [
        {
          name: 'orchestrator'
          image: containerImage
          resources: {
            cpu: json('16')     // 16 vCPU
            memory: '128Gi'     // 128GB RAM - Captain's preferred!
          }
          env: [
            // Azure Configuration
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
              name: 'SERVICE_BUS_NAMESPACE'
              value: serviceBusNamespace
            }
            {
              name: 'SERVICE_BUS_TOPIC'
              value: 'agent-logs'
            }
            // Storage
            {
              name: 'STORAGE_ACCOUNT_NAME'
              value: storageAccountName
            }
            {
              name: 'TABLE_STORAGE_ACCOUNT_NAME'
              value: storageAccountName
            }
            // Cosmos DB (optional)
            {
              name: 'COSMOSDB_ENDPOINT'
              value: cosmosDbEndpoint
            }
            {
              name: 'COSMOSDB_DATABASE'
              value: 'haymaker'
            }
            // Container Configuration
            {
              name: 'CONTAINER_REGISTRY'
              value: containerRegistry
            }
            {
              name: 'CONTAINER_IMAGE'
              value: 'azure-haymaker-agent:latest'
            }
            // Orchestrator Settings
            {
              name: 'SIMULATION_SIZE'
              value: simulationSize
            }
            {
              name: 'LOG_ANALYTICS_WORKSPACE_ID'
              value: logAnalyticsWorkspaceId
            }
            {
              name: 'RESOURCE_GROUP_NAME'
              value: resourceGroup().name
            }
            // Node.js Memory Configuration for any Node.js components
            {
              name: 'NODE_OPTIONS'
              value: '--max-old-space-size=32768' // 32GB heap for Node.js
            }
          ]
        }
      ]
    }
  }
}

// Outputs
output containerAppId string = orchestratorApp.id
output containerAppName string = orchestratorApp.name
output principalId string = orchestratorApp.identity.principalId
output fqdn string = orchestratorApp.properties.configuration.ingress.fqdn
