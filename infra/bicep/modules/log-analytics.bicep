// Log Analytics Workspace Module
// Purpose: Centralized logging and monitoring for all Azure HayMaker resources

@description('Workspace name')
param workspaceName string

@description('Azure region')
param location string = resourceGroup().location

@description('Resource tags')
param tags object = {}

@description('Retention in days (30-730)')
@minValue(30)
@maxValue(730)
param retentionInDays int = 30

@description('Workspace SKU')
@allowed([
  'PerGB2018'
  'Free'
  'Standalone'
  'PerNode'
  'Premium'
])
param sku string = 'PerGB2018'

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: sku
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Outputs
output workspaceId string = logAnalyticsWorkspace.id
output workspaceName string = logAnalyticsWorkspace.name
output customerId string = logAnalyticsWorkspace.properties.customerId
output primarySharedKey string = logAnalyticsWorkspace.listKeys().primarySharedKey
