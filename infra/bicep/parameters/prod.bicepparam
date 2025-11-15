// Production Environment Parameters
using '../main.bicep'

param environment = 'prod'
param location = 'eastus'
param namingPrefix = 'haymaker'

// Admin object IDs will be injected by workflow
param adminObjectIds = []

// GitHub OIDC client ID will be injected by workflow
param githubOidcClientId = ''
