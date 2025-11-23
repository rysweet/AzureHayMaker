# Azure Functions App Structure

## Overview

The `src/function_app.py` file contains all 17 Azure Functions for the HayMaker orchestrator. This monolithic pattern ensures 100% reliable function discovery by Azure Functions V4 runtime.

## Function Inventory

### Total: 17 Functions

1. **Timer Trigger** (1 function)
   - `haymaker_timer` - Scheduled execution (4x daily)

2. **Orchestrator** (1 function)
   - `orchestrate_haymaker_run` - Main workflow coordinator

3. **Activity Functions** (8 functions)
   - `validate_environment_activity` - Verify credentials and prerequisites
   - `select_scenarios_activity` - Random scenario selection
   - `create_service_principal_activity` - SP creation for scenarios
   - `deploy_container_app_activity` - Container Apps deployment
   - `check_agent_status_activity` - Monitor running agents
   - `verify_cleanup_activity` - Verify resource cleanup
   - `force_cleanup_activity` - Force delete remaining resources
   - `generate_report_activity` - Generate execution reports

4. **HTTP API Functions** (7 functions)
   - `execute_scenario` - POST /api/execute
   - `get_execution_status` - GET /api/executions/{execution_id}
   - `list_agents` - GET /api/agents
   - `get_agent_logs` - GET /api/agents/{agent_id}/logs
   - `get_metrics` - GET /api/metrics
   - `list_resources` - GET /api/resources
   - `get_resource` - GET /api/resources/{resource_id}

## HTTP API Routes

| Method | Route | Function | Purpose |
|--------|-------|----------|---------|
| POST | `/api/execute` | `execute_scenario` | Submit on-demand execution request |
| GET | `/api/executions/{execution_id}` | `get_execution_status` | Query execution status |
| GET | `/api/agents` | `list_agents` | List all agents with optional filters |
| GET | `/api/agents/{agent_id}/logs` | `get_agent_logs` | Get agent logs |
| GET | `/api/metrics` | `get_metrics` | Get aggregated execution metrics |
| GET | `/api/resources` | `list_resources` | List all managed resources |
| GET | `/api/resources/{resource_id}` | `get_resource` | Get specific resource details |

## Implementation Pattern

All functions follow the **monolithic pattern** for Azure Functions V4:

```python
# Single FunctionApp instance
app = func.FunctionApp()

# All decorators in function_app.py
@app.route(route="execute", methods=["POST"])
async def execute_scenario(req: func.HttpRequest) -> func.HttpResponse:
    # Import dependencies inside function body
    from azure_haymaker.orchestrator.config import load_config
    from azure_haymaker.models.execution import ExecutionRequest

    # Implementation logic
    ...
```

### Key Principles

1. **Single FunctionApp Instance**: One `app = func.FunctionApp()` at module level
2. **All Decorators Here**: Every `@app.*` decorator must be in this file
3. **Internal Imports**: Import dependencies inside function bodies for isolation
4. **No Separate App Instances**: Never create `app = func.FunctionApp()` elsewhere

## Why Monolithic?

Azure Functions V4 discovers functions by:
1. Loading `function_app.py` module
2. Finding the `app` instance
3. Introspecting all `@app.*` decorated functions

If decorators are in separate files, they won't be discovered because:
- Azure doesn't scan other modules
- Import statements don't register functions with the app instance
- The runtime only sees decorators in the entry point module

## Testing

Run the discovery test to verify all functions:

```bash
python tests/test_function_discovery.py
```

Expected output:
```
✅ All 17 functions discovered successfully!
✅ All 7 HTTP API routes defined correctly!
```

## Deployment

When deploying to Azure:

1. Functions are automatically discovered from `function_app.py`
2. No `function.json` files needed (Python V2 model)
3. All 17 functions appear in Azure Portal
4. HTTP triggers are accessible at `/api/{route}`

## File Structure

```
src/
├── function_app.py          # 17 Azure Functions (2154 lines)
└── azure_haymaker/
    └── orchestrator/
        ├── config.py        # Configuration loading
        ├── execute_api.py   # Original execute/status implementations
        ├── agents_api.py    # Original agents implementations
        ├── metrics_api.py   # Original metrics implementation
        ├── resources_api.py # Original resources implementations
        └── ...              # Other helper modules
```

## Migration Status

**COMPLETED**: All HTTP API functions have been migrated from separate API files into `function_app.py`:

- ✅ `execute_scenario` (from `execute_api.py`)
- ✅ `get_execution_status` (from `execute_api.py`)
- ✅ `list_agents` (from `agents_api.py`)
- ✅ `get_agent_logs` (from `agents_api.py`)
- ✅ `get_metrics` (from `metrics_api.py`)
- ✅ `list_resources` (from `resources_api.py`)
- ✅ `get_resource` (from `resources_api.py`)

The original API files (`*_api.py`) can be kept for reference or removed - they are no longer used by Azure Functions runtime.
