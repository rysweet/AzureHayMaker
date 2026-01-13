// Key Vault Module
// Purpose: Secure storage for secrets and credentials

@description('Key Vault name (globally unique)')
@minLength(3)
@maxLength(24)
param keyVaultName string

@description('Azure region')
param location string = resourceGroup().location

@description('Resource tags')
param tags object = {}

@description('Azure AD tenant ID')
param tenantId string

@description('Object IDs with full access (admins)')
param adminObjectIds array = []

@description('Enable soft delete')
param enableSoftDelete bool = true

@description('Soft delete retention days (minimum 30 days recommended for production)')
@minValue(7)
@maxValue(90)
param softDeleteRetentionInDays int = 30

@description('Enable purge protection')
param enablePurgeProtection bool = true

@description('Allow public network access (set to false for production)')
param publicNetworkAccess bool = false

@description('Allowed IP addresses for Key Vault access')
param allowedIpAddresses array = []

@description('Allowed VNet subnet resource IDs')
param allowedSubnetIds array = []

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enablePurgeProtection: enablePurgeProtection ? true : null
    enableRbacAuthorization: true
    publicNetworkAccess: publicNetworkAccess ? 'Enabled' : 'Disabled'
    networkAcls: {
      bypass: 'AzureServices'
      // For dev/staging: Allow all when public access enabled (GitHub Actions needs access)
      // For prod: Deny all except specific IPs/VNets
      defaultAction: publicNetworkAccess ? 'Allow' : 'Deny'
      ipRules: [for ip in allowedIpAddresses: {
        value: ip
      }]
      virtualNetworkRules: [for subnetId in allowedSubnetIds: {
        id: subnetId
        ignoreMissingVnetServiceEndpoint: false
      }]
    }
  }
}

// Note: Role assignments managed at subscription level to avoid deployment conflicts
// GitHub Actions SP has subscription-level "Key Vault Secrets Officer" role
// Manual grant: az role assignment create --assignee <sp-id> --role "Key Vault Secrets Officer" --scope /subscriptions/<sub-id>

// Outputs
output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
