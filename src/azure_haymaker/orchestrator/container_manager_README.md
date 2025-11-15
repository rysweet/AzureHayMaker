# Container Manager for Azure HayMaker

## Overview

The Container Manager module manages the complete lifecycle of Container Apps deployed on Azure for scenario execution. It enforces mandatory security requirements including VNet integration, implements Key Vault credential references for service principal credentials, and enforces strict resource configurations (64GB RAM, 2 CPU minimum).

**Location**: `src/azure_haymaker/orchestrator/container_manager.py`

## Module Philosophy

This module adheres to the Zero-BS Philosophy:
- **No stubs or placeholders**: Every function is fully functional
- **Fail fast on invalid input**: Validation happens immediately, not at deployment time
- **Mandatory security**: VNet integration is not optional—it's required by security review
- **Self-contained**: All configuration and credential handling is within this module

## Core Components

### ContainerManager Class

Main class for managing Container App operations. Use this for object-oriented patterns or dependency injection.

```python
from azure_haymaker.orchestrator.container_manager import ContainerManager
from azure_haymaker.models.config import OrchestratorConfig

# Initialize manager
manager = ContainerManager(config=orchestrator_config)

# Deploy container app
resource_id = await manager.deploy(scenario=scenario_metadata, sp=service_principal)

# Monitor status
status = await manager.get_status(app_name="scenario-name-agent")

# Delete when done
deleted = await manager.delete(app_name="scenario-name-agent")
```

### Standalone Functions

Async functions for direct use without class instantiation:

```python
from azure_haymaker.orchestrator.container_manager import (
    deploy_container_app,
    get_container_status,
    delete_container_app,
)

# Deploy
resource_id = await deploy_container_app(
    scenario=scenario_metadata,
    sp=service_principal,
    config=orchestrator_config,
)

# Get status
status = await get_container_status(
    app_name="scenario-name-agent",
    resource_group_name="azure-haymaker-rg",
    subscription_id="00000000-0000-0000-0000-000000000000",
)

# Delete
deleted = await delete_container_app(
    app_name="scenario-name-agent",
    resource_group_name="azure-haymaker-rg",
    subscription_id="00000000-0000-0000-0000-000000000000",
)
```

## Security Features

### VNet Integration (Mandatory)

All containers are deployed with VNet integration as required by security review. This ensures:
- Private network isolation
- No public endpoints exposed
- Secure communication within organization network

**Configuration:**
```python
config = OrchestratorConfig(
    vnet_integration_enabled=True,           # Required, not optional
    vnet_resource_group="network-rg",        # Required if enabled
    vnet_name="azure-haymaker-vnet",         # Required if enabled
    subnet_name="container-subnet",          # Required if enabled
)
```

**Validation:**
The ContainerManager will raise `ValueError` if VNet is enabled but resource group, VNet name, or subnet name is missing.

### Key Vault Credential References

Service principal credentials and secrets are passed via Key Vault references, not as environment variables. This ensures:
- Credentials are never stored in container configuration
- Azure Managed Identity handles access to Key Vault
- Automatic credential rotation is supported
- Secrets are encrypted at rest and in transit

**Environment Variables (via Key Vault):**
- `AZURE_CLIENT_SECRET` → references `sp-client-secret` in Key Vault
- `ANTHROPIC_API_KEY` → references `anthropic-api-key` in Key Vault

**Implementation:**
```python
# Credentials passed via Key Vault references, not direct values
env_vars = [
    {
        "name": "AZURE_CLIENT_SECRET",
        "secretRef": "sp-client-secret",  # References Key Vault
    },
    {
        "name": "ANTHROPIC_API_KEY",
        "secretRef": "anthropic-api-key",  # References Key Vault
    },
]
```

## Resource Configuration

### Minimum Resource Requirements

Containers are enforced to have minimum resources:
- **Memory**: 64GB (enforced at creation)
- **CPU**: 2 cores (enforced at creation)

**Validation:**
```python
# These will raise ValueError
config.container_memory_gb = 32  # Too low
config.container_cpu_cores = 1   # Too low

manager = ContainerManager(config)  # Raises ValueError
```

## Container App Naming

Container apps are named based on scenario names with automatic sanitization:

**Naming Convention**: `{sanitized-scenario-name}-agent`

**Sanitization Rules:**
1. Convert to lowercase
2. Replace underscores with hyphens
3. Remove invalid characters
4. Append `-agent` suffix
5. Limit to 63 characters (Azure Container App limit)

**Examples:**
```python
manager._generate_app_name("MyScenario")           # "myscenario-agent"
manager._generate_app_name("my_scenario_v2")      # "my-scenario-v2-agent"
manager._generate_app_name("scenario-with-api")   # "scenario-with-api-agent"
```

## API Reference

### ContainerManager Class

#### `__init__(config: OrchestratorConfig)`

Initialize the ContainerManager.

**Raises:**
- `ValueError`: If memory < 64GB or CPU < 2
- `ValueError`: If VNet enabled but config missing required fields

#### `async deploy(scenario: ScenarioMetadata, sp: ServicePrincipalDetails) -> str`

Deploy a container app for scenario execution.

**Args:**
- `scenario`: Scenario metadata (must have valid scenario_name)
- `sp`: Service principal details (must have valid client_id)

**Returns:**
- Resource ID of deployed container app (string)

**Raises:**
- `ValueError`: If scenario_name or sp.client_id is missing
- `ContainerAppError`: If deployment fails for any reason

**Environment Variables Set in Container:**
- `AZURE_CLIENT_ID`: Set to SP client ID (plaintext)
- `AZURE_TENANT_ID`: Set to tenant ID (plaintext)
- `AZURE_SUBSCRIPTION_ID`: Set to subscription ID (plaintext)
- `AZURE_CLIENT_SECRET`: References Key Vault secret (not plaintext)
- `KEY_VAULT_URL`: Set to Key Vault URL (plaintext)
- `ANTHROPIC_API_KEY`: References Key Vault secret (not plaintext)

#### `async get_status(app_name: str) -> str`

Get current status of a deployed container app.

**Args:**
- `app_name`: Container app name

**Returns:**
- Status string: "Running", "Provisioning", "Failed", etc.

**Raises:**
- `ValueError`: If app_name is empty
- `ContainerAppError`: If status check fails

#### `async delete(app_name: str) -> bool`

Delete a container app.

**Args:**
- `app_name`: Container app name

**Returns:**
- `True` if deleted successfully
- `False` if app not found (not an error)

**Raises:**
- `ValueError`: If app_name is empty
- `ContainerAppError`: If deletion fails for reasons other than not found

### Standalone Functions

#### `async deploy_container_app(scenario: ScenarioMetadata, sp: ServicePrincipalDetails, config: OrchestratorConfig) -> str`

Deploy a container app (equivalent to `ContainerManager.deploy()` but without class instantiation).

#### `async get_container_status(app_name: str, resource_group_name: str, subscription_id: str) -> str`

Get container status (equivalent to `ContainerManager.get_status()` but standalone).

#### `async delete_container_app(app_name: str, resource_group_name: str, subscription_id: str) -> bool`

Delete container app (equivalent to `ContainerManager.delete()` but standalone).

## Error Handling

### ContainerAppError

Custom exception for all container manager errors:

```python
from azure_haymaker.orchestrator.container_manager import ContainerAppError

try:
    resource_id = await deploy_container_app(...)
except ContainerAppError as e:
    print(f"Deployment failed: {e}")
    # Handle deployment failure
```

## Usage Examples

### Basic Deployment Workflow

```python
from azure_haymaker.orchestrator.container_manager import ContainerManager
from azure_haymaker.models.config import OrchestratorConfig
from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.models.service_principal import ServicePrincipalDetails

# Load configuration
config = await load_orchestrator_config()

# Create manager
manager = ContainerManager(config=config)

# Create scenario metadata
scenario = ScenarioMetadata(
    scenario_name="ai-ml-scenario-1",
    scenario_doc_path="gs://bucket/scenario.md",
    agent_path="gs://bucket/agent.py",
    technology_area="AI/ML",
)

# Get service principal for scenario
sp = ServicePrincipalDetails(
    sp_name="AzureHayMaker-ai-ml-scenario-1-admin",
    client_id="12345678-1234-1234-1234-123456789abc",
    principal_id="87654321-4321-4321-4321-cba987654321",
    secret_reference="scenario-sp-ai-ml-scenario-1-secret",
    created_at=datetime.now(timezone.utc).isoformat(),
    scenario_name="ai-ml-scenario-1",
)

# Deploy container app
resource_id = await manager.deploy(scenario=scenario, sp=sp)
print(f"Deployed: {resource_id}")

# Wait and check status
await asyncio.sleep(10)
status = await manager.get_status(app_name="ai-ml-scenario-1-agent")
print(f"Status: {status}")

# Clean up (during shutdown)
deleted = await manager.delete(app_name="ai-ml-scenario-1-agent")
print(f"Deleted: {deleted}")
```

### Error Handling

```python
from azure_haymaker.orchestrator.container_manager import (
    deploy_container_app,
    ContainerAppError,
)

try:
    resource_id = await deploy_container_app(
        scenario=scenario,
        sp=service_principal,
        config=config,
    )
    print(f"Deployed: {resource_id}")
except ValueError as e:
    # Input validation error (scenario or SP invalid)
    print(f"Invalid input: {e}")
except ContainerAppError as e:
    # Azure operation failed
    print(f"Deployment failed: {e}")
```

## Testing

The module includes comprehensive test coverage with 25 tests verifying:
- Container Manager initialization with valid/invalid configs
- Resource constraint enforcement (64GB, 2 CPU)
- VNet integration validation
- Container name generation and sanitization
- Container configuration building
- Key Vault secret references
- Environment variable setup
- Input validation for all functions
- Error handling and edge cases

**Run tests:**
```bash
pytest tests/unit/test_container_manager.py -v
```

**Test file**: `tests/unit/test_container_manager.py`

## Design Decisions

### Lazy Import of Azure SDK

The Container Apps SDK is imported inside methods (lazy import) to avoid dependency issues during testing. This allows tests to run without the azure-mgmt-appcontainers package installed.

```python
# Inside deploy() method:
from azure.mgmt.appcontainers import ContainerAppsAPIClient

client = ContainerAppsAPIClient(
    credential=credential,
    subscription_id=subscription_id,
)
```

### Dictionary-Based Configuration

Container configuration is built using dictionaries instead of model objects. This provides:
- Flexibility for Azure API changes
- Easier testing without Azure SDK models
- Clear visibility into configuration structure

### No External State

ContainerManager does not maintain state about deployed apps. Each operation:
- Creates fresh Azure SDK clients
- Authenticates using DefaultAzureCredential
- Performs atomic operations
- Returns results without caching

## Dependencies

- `azure-identity`: For DefaultAzureCredential authentication
- `azure-mgmt-appcontainers`: For Container Apps API (lazy import)
- `azure-core`: For exceptions and types

## Future Enhancements

1. **Monitoring Integration**: Add telemetry and logging to Application Insights
2. **Auto-scaling**: Add support for container app scaling policies
3. **Resource Limits Override**: Allow fine-grained resource configuration per scenario
4. **Health Checks**: Implement health probes and restart policies
5. **Configuration Validation**: Pre-deployment validation of container images

## Troubleshooting

### "Container app not found" when checking status

**Cause**: Container app either failed to deploy or was already deleted
**Fix**: Check deployment logs and verify app was successfully created

### "VNet integration enabled but vnet_resource_group not provided"

**Cause**: VNet is enabled in config but required fields are missing
**Fix**: Provide vnet_resource_group, vnet_name, and subnet_name in config

### "Container memory must be at least 64GB"

**Cause**: Config specifies less than 64GB memory
**Fix**: Update config to use 64GB or higher

## References

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure Container Apps CLI Reference](https://learn.microsoft.com/cli/azure/containerapp)
- [Python Azure SDK for Container Apps](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/containerregistry/azure-mgmt-containerregistry)
