# Cross-Tenant Orchestration - Developer Quick Reference

**Last Updated**: 2025-12-09

---

## Quick Start: Using Tenant-Aware Activities

### Single-Tenant Mode (Default - No Changes Required)

All existing code continues to work without modification:

```python
# Existing single-tenant code (unchanged)
from azure_haymaker.orchestrator.sp_manager import create_service_principal
from azure_haymaker.orchestrator.execution_tracker import ExecutionTracker
from azure_haymaker.orchestrator.container_deployer import ContainerDeployer

# Create SP in infrastructure tenant
sp_details = await create_service_principal(
    scenario_name="my-scenario",
    subscription_id="sub-123",
    roles=["Contributor"],
    key_vault_client=kv_client
    # No tenant_context = single-tenant mode
)

# Track execution without tenant isolation
tracker = ExecutionTracker(table_client)
execution_id = await tracker.create_execution(scenarios=["scenario-01"])

# Deploy to infrastructure tenant
deployer = ContainerDeployer(config)
container_id = await deployer.deploy(scenario, sp_details)
```

---

## Cross-Tenant Mode (New Capability)

### Step 1: Get Tenant Credentials

```python
from azure_haymaker.orchestrator.tenant_auth import TenantCredentialManager

# Initialize credential manager with Key Vault client
credential_manager = TenantCredentialManager(kv_client)

# Retrieve tenant credentials from Key Vault
# Expects secrets: {tenant-name}-client-id, {tenant-name}-client-secret, etc.
tenant_cred = await credential_manager.get_tenant_credential("tenant-alpha")
```

### Step 2: Build Tenant Context

```python
tenant_context = {
    "tenant_id": tenant_cred.tenant_id,           # Target tenant UUID
    "tenant_name": "tenant-alpha",                 # Human-readable name
    "subscription_id": tenant_cred.subscription_id,  # Target subscription UUID
    "region": "eastus",                            # Azure region
    "resource_group_name": "rg-tenant-alpha",     # Optional: Override RG name
    "credential": tenant_cred                      # TenantCredential object
}
```

### Step 3: Use Tenant-Aware Activities

#### Create Service Principal in Target Tenant

```python
from azure_haymaker.orchestrator.sp_manager import create_service_principal

sp_details = await create_service_principal(
    scenario_name="my-scenario",
    subscription_id=tenant_context["subscription_id"],  # Target subscription
    roles=["Contributor"],
    key_vault_client=kv_client,
    tenant_context=tenant_context  # 👈 Cross-tenant mode
)

# SP is created in tenant-alpha, NOT infrastructure tenant
# Secret stored in Key Vault with name: scenario-sp-my-scenario-secret
```

#### Track Execution with Tenant Isolation

```python
from azure_haymaker.orchestrator.execution_tracker import ExecutionTracker

tracker = ExecutionTracker(
    table_client,
    tenant_context=tenant_context  # 👈 Enable tenant isolation
)

execution_id = await tracker.create_execution(
    scenarios=["scenario-01"],
    duration_hours=2
)

# Data stored with tenant-prefixed partition key:
# PartitionKey = "{tenant_id}#{execution_id}"
# tenant_id field automatically injected
```

#### Deploy Container to Target Tenant

```python
from azure_haymaker.orchestrator.container_deployer import ContainerDeployer

deployer = ContainerDeployer(
    config,
    tenant_context=tenant_context  # 👈 Deploy to target tenant
)

container_id = await deployer.deploy(scenario, sp_details)

# Container deployed to:
# - Subscription: tenant_context["subscription_id"]
# - Resource Group: tenant_context["resource_group_name"]
# - Using: tenant_context["credential"] for authentication
```

---

## API Reference

### `sp_manager.py`

#### `create_service_principal()`

```python
async def create_service_principal(
    scenario_name: str,
    subscription_id: str,
    roles: list[str],
    key_vault_client: SecretClient,
    secret_validity_days: int = 30,
    tenant_context: dict | None = None  # 👈 NEW
) -> ServicePrincipalDetails
```

**Parameters**:
- `tenant_context` (optional): Tenant context dict with credentials
  - If `None`: Creates SP in infrastructure tenant (single-tenant mode)
  - If provided: Creates SP in target tenant (cross-tenant mode)

#### `delete_service_principal()`

```python
async def delete_service_principal(
    sp_name: str,
    key_vault_client: SecretClient,
    tenant_context: dict | None = None  # 👈 NEW
) -> None
```

**Parameters**:
- `tenant_context` (optional): Same as above

#### `rotate_service_principal_secret()`

```python
async def rotate_service_principal_secret(
    sp_name: str,
    key_vault_client: SecretClient,
    secret_validity_days: int = 30,
    remove_old_secrets: bool = True,
    tenant_context: dict | None = None  # 👈 NEW
) -> ServicePrincipalDetails
```

**Parameters**:
- `tenant_context` (optional): Same as above

---

### `execution_tracker.py`

#### `ExecutionTracker.__init__()`

```python
class ExecutionTracker:
    def __init__(
        self,
        table_client: TableClient,
        tenant_context: dict | None = None  # 👈 NEW
    )
```

**Parameters**:
- `tenant_context` (optional): Tenant context dict
  - If `None`: Uses standard table storage (single-tenant mode)
  - If provided: Wraps client with `TenantAwareTableClient` for tenant isolation

**Behavior Changes with `tenant_context`**:
- PartitionKey format: `{tenant_id}#{base_key}`
- Automatic `tenant_id` field injection
- Query filtering by tenant prefix

---

### `container_deployer.py`

#### `ContainerDeployer.__init__()`

```python
class ContainerDeployer:
    def __init__(
        self,
        config: OrchestratorConfig,
        tenant_context: dict | None = None  # 👈 NEW
    )
```

**Parameters**:
- `tenant_context` (optional): Tenant context dict with target deployment info
  - If `None`: Deploys to config subscription/RG (single-tenant mode)
  - If provided: Deploys to target tenant subscription/RG (cross-tenant mode)

**Overrides with `tenant_context`**:
- `subscription_id`: Uses `tenant_context["subscription_id"]`
- `resource_group_name`: Uses `tenant_context["resource_group_name"]`
- Credentials: Uses `tenant_context["credential"]` for authentication

---

## Tenant Context Structure

### Required Fields

```python
{
    "tenant_id": str,           # Target tenant UUID (validated format)
    "tenant_name": str,          # Human-readable tenant name
    "subscription_id": str,      # Target subscription UUID (validated format)
    "region": str,               # Azure region (e.g., "eastus")
    "credential": TenantCredential  # Tenant service principal credentials
}
```

### Optional Fields

```python
{
    "resource_group_name": str,  # Override resource group name for deployment
    # Additional tenant-specific config can be added here
}
```

---

## Credential Management

### Storing Tenant Credentials in Key Vault

```python
from azure_haymaker.orchestrator.tenant_auth import TenantCredentialManager

credential_manager = TenantCredentialManager(kv_client)

await credential_manager.store_tenant_credentials(
    tenant_name="tenant-alpha",
    client_id="client-id-123",
    client_secret="client-secret-456",
    tenant_id="11111111-1111-1111-1111-111111111111",
    subscription_id="22222222-2222-2222-2222-222222222222"
)

# Creates 4 secrets in Key Vault:
# - tenant-alpha-client-id
# - tenant-alpha-client-secret
# - tenant-alpha-tenant-id
# - tenant-alpha-subscription-id
```

### Retrieving Tenant Credentials

```python
# Get credentials for a tenant
tenant_cred = await credential_manager.get_tenant_credential("tenant-alpha")

# Access fields (client_secret is masked in logs via SecretStr)
print(tenant_cred.client_id)        # "client-id-123"
print(tenant_cred.tenant_id)        # "11111111-..."
print(tenant_cred.subscription_id)  # "22222222-..."

# Get secret value (only when needed for authentication)
secret = tenant_cred.client_secret.get_secret_value()
```

### Listing All Tenants

```python
# Get all tenant names with credentials in Key Vault
tenant_names = await credential_manager.get_all_tenant_names()
# Returns: ["tenant-alpha", "tenant-beta", ...]
```

---

## Storage Isolation

### Single-Tenant Mode

Without `tenant_context`:

```python
tracker = ExecutionTracker(table_client)  # No tenant_context
```

**Storage Pattern**:
- PartitionKey: `execution_id` (e.g., `"exec-20251209-abc123"`)
- RowKey: Timestamp (e.g., `"2025-12-09T10:30:00.000000Z"`)
- No tenant_id field

### Cross-Tenant Mode

With `tenant_context`:

```python
tracker = ExecutionTracker(table_client, tenant_context=tenant_context)
```

**Storage Pattern**:
- PartitionKey: `{tenant_id}#{execution_id}` (e.g., `"11111111-1111-1111-1111-111111111111#exec-20251209-abc123"`)
- RowKey: Timestamp (e.g., `"2025-12-09T10:30:00.000000Z"`)
- tenant_id field: `"11111111-1111-1111-1111-111111111111"` (injected automatically)

**Query Filtering**:
All queries automatically filtered by tenant prefix:
```python
# User code
entities = await tracker.query_entities("Status eq 'running'")

# Actual query executed by TenantAwareTableClient
# "PartitionKey ge '11111111-..#' and PartitionKey lt '11111111-...$' and (Status eq 'running')"
```

---

## Common Patterns

### Pattern 1: Iterate Over All Tenants

```python
from azure_haymaker.orchestrator.tenant_auth import TenantCredentialManager

credential_manager = TenantCredentialManager(kv_client)
tenant_names = await credential_manager.get_all_tenant_names()

for tenant_name in tenant_names:
    # Get credentials
    tenant_cred = await credential_manager.get_tenant_credential(tenant_name)

    # Build tenant context
    tenant_context = {
        "tenant_id": tenant_cred.tenant_id,
        "tenant_name": tenant_name,
        "subscription_id": tenant_cred.subscription_id,
        "region": "eastus",
        "credential": tenant_cred
    }

    # Execute scenario in target tenant
    sp_details = await create_service_principal(
        scenario_name="scenario-01",
        subscription_id=tenant_context["subscription_id"],
        roles=["Contributor"],
        key_vault_client=kv_client,
        tenant_context=tenant_context
    )

    # Continue with deployment...
```

### Pattern 2: Conditional Cross-Tenant Logic

```python
async def execute_scenario(
    scenario_name: str,
    config: dict,
    tenant_name: str | None = None  # None = single-tenant
):
    """Execute scenario in single-tenant or cross-tenant mode."""

    # Build tenant context only if tenant_name provided
    tenant_context = None
    if tenant_name:
        credential_manager = TenantCredentialManager(kv_client)
        tenant_cred = await credential_manager.get_tenant_credential(tenant_name)
        tenant_context = {
            "tenant_id": tenant_cred.tenant_id,
            "tenant_name": tenant_name,
            "subscription_id": tenant_cred.subscription_id,
            "region": config["region"],
            "credential": tenant_cred
        }

    # Activities automatically use correct mode based on tenant_context
    sp_details = await create_service_principal(
        scenario_name=scenario_name,
        subscription_id=tenant_context["subscription_id"] if tenant_context else config["subscription_id"],
        roles=["Contributor"],
        key_vault_client=kv_client,
        tenant_context=tenant_context  # None = single-tenant, dict = cross-tenant
    )

    tracker = ExecutionTracker(table_client, tenant_context=tenant_context)
    deployer = ContainerDeployer(orchestrator_config, tenant_context=tenant_context)

    # Execute workflow...
```

---

## Migration Guide

### Existing Single-Tenant Code → Support Cross-Tenant

**Before**:
```python
async def provision_scenario(scenario_name: str):
    # Hardcoded infrastructure tenant
    sp_details = await create_service_principal(
        scenario_name=scenario_name,
        subscription_id="infra-sub-123",
        roles=["Contributor"],
        key_vault_client=kv_client
    )

    tracker = ExecutionTracker(table_client)
    deployer = ContainerDeployer(config)
```

**After** (supports both modes):
```python
async def provision_scenario(
    scenario_name: str,
    tenant_context: dict | None = None  # 👈 Add optional parameter
):
    # Extract subscription_id from tenant_context or use default
    subscription_id = (
        tenant_context["subscription_id"]
        if tenant_context
        else "infra-sub-123"
    )

    # Pass tenant_context to all activities
    sp_details = await create_service_principal(
        scenario_name=scenario_name,
        subscription_id=subscription_id,
        roles=["Contributor"],
        key_vault_client=kv_client,
        tenant_context=tenant_context  # 👈 Pass through
    )

    tracker = ExecutionTracker(table_client, tenant_context=tenant_context)  # 👈 Pass through
    deployer = ContainerDeployer(config, tenant_context=tenant_context)  # 👈 Pass through
```

---

## Troubleshooting

### Issue: SP Creation Fails in Target Tenant

**Symptom**: `ServicePrincipalError: Graph API error`

**Diagnosis**:
1. Verify tenant credentials in Key Vault:
   ```python
   cred = await credential_manager.get_tenant_credential("tenant-alpha")
   print(cred)  # Should show valid tenant_id, client_id, subscription_id
   ```

2. Validate tenant access:
   ```python
   is_valid = await credential_manager.validate_tenant_access("tenant-alpha")
   assert is_valid, "Tenant credentials invalid"
   ```

3. Check SP permissions in target tenant:
   - Requires `Application.ReadWrite.All` in Microsoft Graph
   - Requires `RoleAssignment` permissions in target subscription

---

### Issue: Data Not Isolated Between Tenants

**Symptom**: Queries return data from other tenants

**Diagnosis**:
1. Verify tenant_context passed to ExecutionTracker:
   ```python
   tracker = ExecutionTracker(table_client, tenant_context=tenant_context)
   assert tracker.tenant_context is not None  # Should have context
   ```

2. Check partition key format in storage:
   ```python
   # Should be: "{tenant_id}#{execution_id}"
   # NOT: "{execution_id}"
   ```

3. Verify TenantAwareTableClient wrapping:
   ```python
   from azure_haymaker.orchestrator.services.tenant_storage import TenantAwareTableClient
   assert isinstance(tracker.table, TenantAwareTableClient)
   ```

---

### Issue: Container Deployment Goes to Wrong Subscription

**Symptom**: Container deployed to infrastructure tenant, not target tenant

**Diagnosis**:
1. Verify tenant_context passed to ContainerDeployer:
   ```python
   deployer = ContainerDeployer(config, tenant_context=tenant_context)
   assert deployer.tenant_context is not None
   assert deployer.subscription_id == tenant_context["subscription_id"]
   ```

2. Check credential extraction in deploy():
   ```python
   # Should log: "Using target tenant credentials"
   # NOT: "Using infrastructure tenant credentials"
   ```

---

## Testing

### Unit Testing with Tenant Context

```python
import pytest
from azure_haymaker.orchestrator.tenant_auth import TenantCredential
from pydantic import SecretStr

@pytest.fixture
def mock_tenant_context():
    """Create mock tenant context for testing."""
    return {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "tenant_name": "tenant-alpha",
        "subscription_id": "22222222-2222-2222-2222-222222222222",
        "region": "eastus",
        "credential": TenantCredential(
            client_id="client-id-123",
            client_secret=SecretStr("client-secret-456"),
            tenant_id="11111111-1111-1111-1111-111111111111",
            subscription_id="22222222-2222-2222-2222-222222222222"
        )
    }

async def test_cross_tenant_sp_creation(mock_tenant_context):
    """Test SP creation in target tenant."""
    # Mock Graph API, Key Vault, etc.
    with patch(...):
        sp_details = await create_service_principal(
            scenario_name="test-scenario",
            subscription_id=mock_tenant_context["subscription_id"],
            roles=["Contributor"],
            key_vault_client=mock_kv_client,
            tenant_context=mock_tenant_context
        )

    assert sp_details.client_id is not None
    # Verify SP created in target tenant, not infrastructure tenant
```

---

## Best Practices

### 1. Always Validate Tenant Context

```python
def validate_tenant_context(tenant_context: dict | None) -> None:
    """Validate tenant context structure before use."""
    if tenant_context is None:
        return  # Single-tenant mode, no validation needed

    required_fields = ["tenant_id", "tenant_name", "subscription_id", "region", "credential"]
    for field in required_fields:
        if field not in tenant_context:
            raise ValueError(f"Missing required field in tenant_context: {field}")

    # Validate UUID format
    from uuid import UUID
    try:
        UUID(tenant_context["tenant_id"])
        UUID(tenant_context["subscription_id"])
    except ValueError as e:
        raise ValueError(f"Invalid UUID format in tenant_context: {e}")
```

### 2. Use Credential Manager for All Tenant Credentials

Don't hardcode credentials:
```python
# ❌ BAD
tenant_context = {
    "tenant_id": "hardcoded-id",
    "credential": {"client_secret": "hardcoded-secret"}  # Insecure
}

# ✅ GOOD
credential_manager = TenantCredentialManager(kv_client)
tenant_cred = await credential_manager.get_tenant_credential("tenant-alpha")
tenant_context = {
    "tenant_id": tenant_cred.tenant_id,
    "credential": tenant_cred  # SecretStr protects secret
}
```

### 3. Pass Tenant Context Through All Layers

Maintain tenant context throughout call stack:
```python
async def execute_workflow(tenant_context: dict | None = None):
    # Layer 1: Workflow
    await provision_resources(tenant_context=tenant_context)

async def provision_resources(tenant_context: dict | None = None):
    # Layer 2: Provisioning
    sp_details = await create_service_principal(..., tenant_context=tenant_context)
    await deploy_container(..., tenant_context=tenant_context)

# ❌ DON'T lose tenant_context in intermediate layers
```

---

## Summary

**Key Takeaways**:

1. **Zero Breaking Changes**: All existing single-tenant code works unchanged
2. **Opt-In Cross-Tenant**: Pass `tenant_context` parameter to enable cross-tenant mode
3. **Consistent Pattern**: Same tenant_context structure across all activities
4. **Secure by Default**: Use `TenantCredentialManager` for credential retrieval
5. **Automatic Isolation**: Storage automatically partitioned by tenant_id

**When to Use Cross-Tenant Mode**:
- Managing multiple Azure tenants from single orchestrator
- Deploying scenarios to customer tenants
- Multi-tenant SaaS deployments
- Testing scenarios in isolated tenant sandboxes

**When to Use Single-Tenant Mode**:
- Single customer deployment
- All resources in same tenant/subscription
- Legacy deployments (no migration needed)
