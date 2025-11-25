using '../main-vm.bicep'

param environment = 'dev'
param adminObjectIds = ['42d7dce2-072a-4ff4-9c3c-11474f4fc7df']
param githubOidcClientId = '7fc87f52-c911-49ce-b64f-e4f22fa7c8b0'
// SSH key for VM access - use file reference to avoid escaping issues
param sshPublicKey = loadTextContent('~/.ssh/haymaker-orchestrator-key.pub')
