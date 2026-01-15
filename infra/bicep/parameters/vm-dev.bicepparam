using '../main-vm.bicep'

param environment = 'dev'
param adminObjectIds = ['42d7dce2-072a-4ff4-9c3c-11474f4fc7df']
param githubOidcClientId = '7fc87f52-c911-49ce-b64f-e4f22fa7c8b0'
// SSH key must be provided via environment variable SSH_PUBLIC_KEY at deployment time
// Do NOT hardcode SSH keys in version control
// Example: az deployment group create ... --parameters sshPublicKey="$SSH_PUBLIC_KEY"
param sshPublicKey = ''
