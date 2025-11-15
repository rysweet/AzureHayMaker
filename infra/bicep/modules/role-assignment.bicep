// Role Assignment Module
// Purpose: Assign RBAC role to a principal

@description('Principal ID (object ID)')
param principalId string

@description('Role definition ID (GUID)')
param roleDefinitionId string

@description('Principal type')
@allowed([
  'ServicePrincipal'
  'User'
  'Group'
])
param principalType string = 'ServicePrincipal'

// Role Assignment
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, principalId, roleDefinitionId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
    principalId: principalId
    principalType: principalType
  }
}

// Outputs
output roleAssignmentId string = roleAssignment.id
output roleAssignmentName string = roleAssignment.name
