using '../main-vm.bicep'

param environment = 'dev'
param adminObjectIds = ['42d7dce2-072a-4ff4-9c3c-11474f4fc7df']
param githubOidcClientId = '7fc87f52-c911-49ce-b64f-e4f22fa7c8b0'

// SECURITY: Load SSH public key from local file (NEVER commit SSH keys to version control)
// For local dev: Place your SSH public key in infra/secrets/haymaker_vm.pub
// For production: Use GitHub Secrets, Key Vault, or environment variable override
// See: infra/secrets/README.md
param sshPublicKey = loadTextContent('../../secrets/haymaker_vm.pub')
