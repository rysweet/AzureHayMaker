# Infrastructure Secrets

This directory stores sensitive files that should NEVER be committed to version control.

## SSH Keys for VM Deployment

### Local Development

For local deployments, place your SSH public key here:

```bash
# Generate a new SSH key pair (if needed)
ssh-keygen -t rsa -b 4096 -C "haymaker-orchestrator" -f ~/.ssh/haymaker_id_rsa

# Copy public key to secrets directory
cp ~/.ssh/haymaker_id_rsa.pub infra/secrets/haymaker_vm.pub
```

The `vm-dev.bicepparam` file references this path using `loadTextContent()`:

```bicep
param sshPublicKey = loadTextContent('../secrets/haymaker_vm.pub')
```

### Production Deployments

**NEVER** use local files for production. Use one of these secure methods:

#### Option 1: GitHub Secrets (Recommended for CI/CD)

```bash
# In GitHub Actions workflow
az deployment group create \
  --resource-group haymaker-prod-rg \
  --template-file infra/bicep/main-vm.bicep \
  --parameters infra/bicep/parameters/vm-prod.bicepparam \
  --parameters sshPublicKey="${{ secrets.VM_SSH_PUBLIC_KEY }}"
```

#### Option 2: Azure Key Vault

```bash
# Store SSH key in Key Vault
az keyvault secret set \
  --vault-name haymaker-prod-kv \
  --name vm-ssh-public-key \
  --file ~/.ssh/haymaker_id_rsa.pub

# Reference in deployment
az deployment group create \
  --resource-group haymaker-prod-rg \
  --template-file infra/bicep/main-vm.bicep \
  --parameters infra/bicep/parameters/vm-prod.bicepparam \
  --parameters sshPublicKey="$(az keyvault secret show --vault-name haymaker-prod-kv --name vm-ssh-public-key --query value -o tsv)"
```

#### Option 3: Environment Variable

```bash
# Set environment variable
export HAYMAKER_SSH_PUBLIC_KEY=$(cat ~/.ssh/haymaker_id_rsa.pub)

# Deploy with parameter override
az deployment group create \
  --resource-group haymaker-prod-rg \
  --template-file infra/bicep/main-vm.bicep \
  --parameters infra/bicep/parameters/vm-prod.bicepparam \
  --parameters sshPublicKey="$HAYMAKER_SSH_PUBLIC_KEY"
```

## Security Checklist

- [ ] Never commit `.pub`, `.pem`, or `.key` files to version control
- [ ] Never hardcode SSH keys in `.bicepparam` files
- [ ] Use GitHub Secrets or Key Vault for production
- [ ] Rotate SSH keys regularly (every 90 days)
- [ ] Use different keys for different environments
- [ ] Restrict SSH access with network security groups

## Directory Structure

```
infra/secrets/
├── README.md                  # This file (safe to commit)
├── haymaker_vm.pub            # SSH public key for dev VM (GITIGNORED)
├── haymaker_vm_staging.pub    # SSH public key for staging VM (GITIGNORED)
└── haymaker_vm_prod.pub       # SSH public key for prod VM (GITIGNORED)
```

**IMPORTANT**: Only `README.md` should be committed. All other files are automatically ignored by `.gitignore`.
