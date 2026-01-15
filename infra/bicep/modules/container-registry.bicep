// Container Registry Module
// Purpose: Private registry for agent container images

@description('Container Registry name (globally unique)')
@minLength(5)
@maxLength(50)
param registryName string

@description('Azure region')
param location string = resourceGroup().location

@description('Resource tags')
param tags object = {}

@description('Registry SKU')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param sku string = 'Premium'

@description('Enable admin user (disabled by default for security - use managed identities instead)')
param adminUserEnabled bool = false

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: adminUserEnabled
    publicNetworkAccess: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
    policies: {
      quarantinePolicy: {
        status: 'disabled'
      }
      retentionPolicy: {
        status: 'enabled'
        days: 7
      }
      trustPolicy: {
        status: 'disabled'
      }
    }
    encryption: {
      status: 'disabled'
    }
    dataEndpointEnabled: false
  }
}

// Outputs
// SECURITY: Do NOT output credentials - use managed identities for authentication
output registryId string = containerRegistry.id
output registryName string = containerRegistry.name
output loginServer string = containerRegistry.properties.loginServer
