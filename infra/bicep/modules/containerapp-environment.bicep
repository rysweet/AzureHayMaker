// Container Apps Environment Module
// Purpose: Managed environment with E16 workload profile (128GB RAM)

@description('Environment name')
param environmentName string

@description('Azure region')
param location string = resourceGroup().location

@description('Resource tags')
param tags object = {}

@description('Log Analytics workspace resource ID')
param logAnalyticsWorkspaceId string

@description('Workload profiles (E16 for 128GB RAM)')
param workloadProfiles array = [
  {
    name: 'E16'
    workloadProfileType: 'E16'
    minimumCount: 1
    maximumCount: 3
  }
]

// Container Apps Environment with E16 workload profile
resource environment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
    workloadProfiles: workloadProfiles
    zoneRedundant: false // Single zone for dev, can enable for prod
  }
}

// Outputs
output environmentId string = environment.id
output environmentName string = environment.name
output defaultDomain string = environment.properties.defaultDomain
