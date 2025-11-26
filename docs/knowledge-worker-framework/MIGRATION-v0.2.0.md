# Migration Guide: v0.1.x → v0.2.0

## Overview

Version 0.2.0 introduces **BREAKING CHANGES** to the Knowledge Worker framework. This guide helps you migrate from v0.1.x to v0.2.0.

**Key Changes:**
- Removed simulation mode (`live_mode` flag)
- Made `graph_client` a **required** parameter
- System now **always** operates with real M365 operations
- Added automatic E5 license assignment

## What Changed

### Breaking Change 1: Orchestrator Constructor

**Before (v0.1.x):**
```python
# graph_client was optional
orchestrator = KnowledgeWorkerOrchestrator()

# or with credentials
orchestrator = KnowledgeWorkerOrchestrator(graph_client)
```

**After (v0.2.0):**
```python
# graph_client is REQUIRED
from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient

credential = ClientSecretCredential(
    tenant_id=os.getenv("KW_TENANT_ID"),
    client_id=os.getenv("KW_APP_ID"),
    client_secret=os.getenv("KW_CLIENT_SECRET"),
)
graph_client = GraphServiceClient(credential)

# REQUIRED parameter
orchestrator = KnowledgeWorkerOrchestrator(graph_client)
```

**Error if not provided:**
```
ValueError: graph_client is required. Knowledge Worker orchestrator
operates only with real M365 operations. Ensure credentials are
configured: KW_TENANT_ID, KW_APP_ID, KW_CLIENT_SECRET
```

### Breaking Change 2: DeploymentConfig

**Before (v0.1.x):**
```python
config = DeploymentConfig(
    name="test-deployment",
    total_workers=10,
    live_mode=True,  # Flag to enable real M365
    tenant_domain="test.onmicrosoft.com",
)
```

**After (v0.2.0):**
```python
config = DeploymentConfig(
    name="test-deployment",
    total_workers=10,
    # live_mode removed - always live
    tenant_domain="test.onmicrosoft.com",
)
```

**No simulation mode exists** - all operations use real M365.

### Breaking Change 3: CLI Commands

**Before (v0.1.x):**
```bash
# Could run without credentials (simulation mode)
haymaker kw deploy --workers 5
```

**After (v0.2.0):**
```bash
# Requires credentials
export KW_TENANT_ID="your-tenant-id"
export KW_APP_ID="your-app-id"
export KW_CLIENT_SECRET="your-client-secret"

haymaker kw deploy --workers 5
```

**Error if credentials missing:**
```
Error: Missing M365 credentials
Set KW_APP_ID, KW_CLIENT_SECRET, and KW_TENANT_ID environment variables
```

## Migration Steps

### Step 1: Update Dependencies

```bash
# Update to v0.2.0
pip install --upgrade azure-haymaker==0.2.0

# Or with uv
uv pip install --upgrade azure-haymaker==0.2.0
```

### Step 2: Set Up M365 Credentials

#### Option A: Environment Variables (Development)

```bash
# Create .env file
cat > .env << EOF
KW_TENANT_ID=c7674d41-af6c-46f5-89a5-d41495d2151e
KW_APP_ID=e2c7f4c6-00d7-4f62-9bb1-84b877fb5d7e
KW_CLIENT_SECRET=your-client-secret-here
EOF

# Set restrictive permissions
chmod 600 .env

# Load in shell
source .env
```

#### Option B: Azure Key Vault (Production)

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

vault_url = "https://your-vault.vault.azure.net/"
credential = DefaultAzureCredential()
client = SecretClient(vault_url=vault_url, credential=credential)

tenant_id = client.get_secret("kw-tenant-id").value
client_id = client.get_secret("kw-app-id").value
client_secret = client.get_secret("kw-client-secret").value
```

See [SECURITY.md](./SECURITY.md) for complete Key Vault setup.

### Step 3: Update Your Code

#### Pattern 1: Simple Orchestrator Usage

**Before:**
```python
from azure_haymaker.knowledge_worker import KnowledgeWorkerOrchestrator, DeploymentConfig

orchestrator = KnowledgeWorkerOrchestrator()
config = DeploymentConfig(name="test", live_mode=True)
run_id = orchestrator.create_deployment(config)
```

**After:**
```python
import os
from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient
from azure_haymaker.knowledge_worker import KnowledgeWorkerOrchestrator, DeploymentConfig

# Create Graph client
credential = ClientSecretCredential(
    tenant_id=os.getenv("KW_TENANT_ID"),
    client_id=os.getenv("KW_APP_ID"),
    client_secret=os.getenv("KW_CLIENT_SECRET"),
)
graph_client = GraphServiceClient(credential)

# Pass to orchestrator (REQUIRED)
orchestrator = KnowledgeWorkerOrchestrator(graph_client)
config = DeploymentConfig(name="test")  # No live_mode
run_id = orchestrator.create_deployment(config)
```

#### Pattern 2: With Key Vault

**Before:**
```python
orchestrator = KnowledgeWorkerOrchestrator()
# ... rest of code
```

**After:**
```python
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from msgraph.graph_service_client import GraphServiceClient
from azure_haymaker.knowledge_worker import KnowledgeWorkerOrchestrator

# Load credentials from Key Vault
vault_url = "https://haymaker-prod.vault.azure.net/"
kv_credential = DefaultAzureCredential()
kv_client = SecretClient(vault_url=vault_url, credential=kv_credential)

tenant_id = kv_client.get_secret("kw-tenant-id").value
client_id = kv_client.get_secret("kw-app-id").value
client_secret = kv_client.get_secret("kw-client-secret").value

# Create Graph client
graph_credential = ClientSecretCredential(
    tenant_id=tenant_id,
    client_id=client_id,
    client_secret=client_secret,
)
graph_client = GraphServiceClient(graph_credential)

# Pass to orchestrator
orchestrator = KnowledgeWorkerOrchestrator(graph_client)
```

#### Pattern 3: CLI Scripts

**Before:**
```bash
#!/bin/bash
haymaker kw deploy --workers 10
```

**After:**
```bash
#!/bin/bash

# Load credentials
export KW_TENANT_ID="$(az keyvault secret show --vault-name haymaker-kw --name kw-tenant-id --query value -o tsv)"
export KW_APP_ID="$(az keyvault secret show --vault-name haymaker-kw --name kw-app-id --query value -o tsv)"
export KW_CLIENT_SECRET="$(az keyvault secret show --vault-name haymaker-kw --name kw-client-secret --query value -o tsv)"

# Deploy
haymaker kw deploy --workers 10
```

### Step 4: Update Tests

**Before:**
```python
def test_orchestrator_creation():
    orchestrator = KnowledgeWorkerOrchestrator()
    assert orchestrator is not None
```

**After:**
```python
from unittest.mock import Mock

def test_orchestrator_creation():
    mock_client = Mock()
    orchestrator = KnowledgeWorkerOrchestrator(mock_client)
    assert orchestrator._graph_client == mock_client

def test_orchestrator_requires_client():
    with pytest.raises(ValueError, match="graph_client is required"):
        KnowledgeWorkerOrchestrator(None)
```

### Step 5: Verify Migration

Run these checks to ensure migration succeeded:

```bash
# 1. Check credentials are set
env | grep KW_

# 2. Test Graph API connectivity
haymaker kw e2e-test

# 3. Run unit tests
pytest tests/unit/test_knowledge_worker.py

# 4. Try a small deployment
haymaker kw deploy --workers 1 --dry-run
```

## Rollback Strategy

If you need to rollback to v0.1.x:

```bash
# Downgrade package
pip install azure-haymaker==0.1.3

# Restore old code patterns
git revert <migration-commit>

# Simulation mode will work again
orchestrator = KnowledgeWorkerOrchestrator()  # No credentials needed
```

**Note:** Once users are provisioned in v0.2.0 (with E5 licenses), they remain in your tenant. Clean them up manually if rolling back.

## Troubleshooting

### Error: "graph_client is required"

**Cause:** Not passing GraphServiceClient to orchestrator

**Fix:**
```python
from msgraph.graph_service_client import GraphServiceClient
from azure.identity import ClientSecretCredential

credential = ClientSecretCredential(...)
graph_client = GraphServiceClient(credential)
orchestrator = KnowledgeWorkerOrchestrator(graph_client)  # Pass here
```

### Error: "Missing M365 credentials"

**Cause:** Environment variables not set

**Fix:**
```bash
export KW_TENANT_ID="your-tenant-id"
export KW_APP_ID="your-app-id"
export KW_CLIENT_SECRET="your-client-secret"
```

### Error: "Authorization_RequestDenied"

**Cause:** Application doesn't have required Graph API permissions

**Fix:**
```bash
APP_ID="your-app-id"
GRAPH_API="00000003-0000-0000-c000-000000000000"

# Add permissions
az ad app permission add --id $APP_ID --api $GRAPH_API \
  --api-permissions 741f803b-c850-494e-b5df-cde7c675a1ca=Role

# Grant admin consent
az ad app permission admin-consent --id $APP_ID
```

See [SECURITY.md](./SECURITY.md#microsoft-graph-api-permissions) for complete permission setup.

### Error: "No licenses available"

**Cause:** Tenant doesn't have enough E5 licenses

**Check available licenses:**
```python
skus = await graph_client.subscribed_skus.get()
for sku in skus.value:
    if "E5" in sku.sku_part_number:
        print(f"Total: {sku.prepaid_units.enabled}, Available: {sku.prepaid_units.enabled - sku.consumed_units}")
```

**Solutions:**
- Purchase more E5 licenses
- Clean up unused Knowledge Worker accounts
- Use a test tenant with developer licenses

## New Features in v0.2.0

### Automatic License Assignment

Users are now automatically assigned Microsoft 365 E5 licenses:

```python
# Happens automatically in provision_worker()
identity = await user_manager.provision_worker(...)
# User now has E5 license and mailbox access
```

**Benefits:**
- No manual license assignment needed
- Users can send/receive email immediately
- Calendar operations work out of the box

### Improved Error Messages

Errors now include actionable guidance:

```
ValueError: graph_client is required. Knowledge Worker orchestrator
operates only with real M365 operations. Ensure credentials are
configured: KW_TENANT_ID, KW_APP_ID, KW_CLIENT_SECRET
```

### Simplified Architecture

- Single code path (no simulation vs. live branching)
- Easier to understand and maintain
- Reduced complexity by ~40%

## FAQ

### Q: Why was simulation mode removed?

**A:** Simulation mode added complexity without value. Real M365 testing requires real operations. If you need isolated testing, use a dedicated test tenant.

### Q: Can I still test without a tenant?

**A:** No. The Knowledge Worker framework requires a real M365 tenant. Use a developer tenant (free with M365 Developer Program).

### Q: What's the cost impact?

**A:** E5 licenses cost ~$57/user/month. Budget accordingly:
- 10 workers = ~$570/month
- 50 workers = ~$2,850/month
- 300 workers = ~$17,100/month

Use auto-cleanup to minimize costs.

### Q: Is this a major version bump?

**A:** Yes. This should be v0.2.0 (not v0.1.4) due to breaking changes.

### Q: Do I need to clean up old deployments?

**A:** Yes, if you used v0.1.x in simulation mode. Old "deployments" were local only and require no cleanup. New v0.2.0 deployments create real Entra users that need cleanup.

## Support

For migration help:
- GitHub Issues: https://github.com/rysweet/AzureHayMaker/issues
- Documentation: https://github.com/rysweet/AzureHayMaker/tree/main/docs/knowledge-worker-framework
- Security Guide: [SECURITY.md](./SECURITY.md)

## Version Compatibility

| Version | Simulation Mode | graph_client | License Assignment |
|---------|----------------|--------------|-------------------|
| v0.1.x  | ✓ Yes          | Optional     | ✗ No              |
| v0.2.0+ | ✗ No           | **Required** | ✓ Yes             |

Migration effort: ~30 minutes per codebase
