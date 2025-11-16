// Development Environment Parameters
using '../main.bicep'

param environment = 'dev'
param location = 'westus2'  // Changed from eastus - better quota availability
param namingPrefix = 'haymaker'

// Admin object IDs will be injected by workflow
param adminObjectIds = []

// GitHub OIDC client ID will be injected by workflow
param githubOidcClientId = ''
