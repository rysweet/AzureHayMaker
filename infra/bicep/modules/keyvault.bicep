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

@description('Soft delete retention days')
@minValue(7)
@maxValue(90)
param softDeleteRetentionInDays int = 7

@description('Enable purge protection')
param enablePurgeProtection bool = false

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
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

// Grant admin access via RBAC (Key Vault Administrator role)
resource adminRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for objectId in adminObjectIds: {
  name: guid(keyVault.id, objectId, 'KeyVaultAdministrator')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '00482a5a-887f-4fb3-b363-3b7fe8e74483') // Key Vault Administrator
    principalId: objectId
    principalType: 'ServicePrincipal'
  }
}]

// Outputs
output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
