# Workflow Orchestrator Refactoring

## Overview

The `orchestrate_haymaker_run()` function has been refactored from a monolithic 295-line function into a modular architecture with 10 helper functions, each under 50 lines of code.

## Refactored Architecture

### Main Orchestration Function

**Function**: `orchestrate_haymaker_run(context: Any) -> Any`
**Size**: ~50 LOC (reduced from 295 LOC)
**Responsibility**: High-level orchestration of all 7 workflow phases

The main function now serves as a clean orchestrator that delegates each phase to specialized helper functions:

```python
@app.orchestration_trigger(context_name="context")
def orchestrate_haymaker_run(context: Any) -> Any:
    """Main orchestration function - coordinates 7 phases."""
    run_id = context.input.get("run_id")
    started_at = context.input.get("started_at")

    execution_report = _initialize_execution_report(run_id, started_at)

    try:
        # Phase 1: Validation
        validation_result, passed = yield from _execute_validation_phase(context, run_id, execution_report)
        if not passed:
            return execution_report

        # Phase 2: Selection
        selection_result = yield from _execute_selection_phase(context, run_id, execution_report)
        if not selection_result["scenarios"]:
            return execution_report

        # Phase 3: Provisioning
        provisioning_result = yield from _execute_provisioning_phase(
            context, run_id, selection_result["scenarios"], execution_report
        )

        # Phase 4: Monitoring
        yield from _execute_monitoring_phase(
            context, run_id, provisioning_result["successful_containers"], execution_report
        )

        # Phase 5-6: Cleanup
        yield from _execute_cleanup_phases(
            context, run_id, selection_result["scenarios"],
            provisioning_result["successful_sps"], execution_report
        )

        # Phase 7: Reporting
        report_url = yield from _execute_reporting_phase(
            context, run_id, execution_report, selection_result["scenarios"],
            provisioning_result["sp_count"], provisioning_result["container_count"]
        )

        execution_report["status"] = "completed"
        execution_report["report_url"] = report_url
        return execution_report

    except Exception as e:
        return _handle_orchestration_error(context, run_id, execution_report, e)
```

### Helper Functions

#### 1. Initialization

**Function**: `_initialize_execution_report(run_id: str, started_at: str) -> dict[str, Any]`
**Size**: 11 LOC
**Responsibility**: Create initial execution report structure

#### 2. Phase 1 - Validation

**Function**: `_execute_validation_phase(context, run_id: str, execution_report: dict) -> tuple[dict, bool]`
**Size**: 29 LOC
**Responsibility**: Execute environment validation and update execution report
**Returns**: (validation_result, passed: bool)

#### 3. Phase 2 - Selection

**Function**: `_execute_selection_phase(context, run_id: str, execution_report: dict) -> dict[str, Any]`
**Size**: 25 LOC
**Responsibility**: Select scenarios for execution
**Returns**: selection_result with scenarios list

#### 4. Phase 3 - Provisioning (Multi-Function)

**Main Function**: `_execute_provisioning_phase(...) -> dict[str, Any]`
**Size**: 20 LOC
**Responsibility**: Orchestrate SP creation and container deployment

**Sub-Function 1**: `_create_service_principals(context, run_id, scenarios) -> list[dict]`
**Size**: 30 LOC
**Responsibility**: Create all service principals in parallel
**Returns**: List of SP creation results

**Sub-Function 2**: `_deploy_containers(context, run_id, scenarios, sp_results) -> list[dict]`
**Size**: 30 LOC
**Responsibility**: Deploy Container Apps in parallel (only for successful SPs)
**Returns**: List of container deployment results

#### 5. Phase 4 - Monitoring

**Function**: `_execute_monitoring_phase(context, run_id, successful_containers, execution_report)`
**Size**: 38 LOC
**Responsibility**: 8-hour monitoring with periodic status checks (every 15 minutes)

#### 6. Phase 5-6 - Cleanup

**Function**: `_execute_cleanup_phases(context, run_id, scenarios, successful_sps, execution_report)`
**Size**: 45 LOC
**Responsibility**: Verify cleanup completion and force cleanup if resources remain

#### 7. Phase 7 - Reporting

**Function**: `_execute_reporting_phase(context, run_id, execution_report, scenarios, sp_count, container_count) -> str`
**Size**: 19 LOC
**Responsibility**: Generate final execution report
**Returns**: report_url string

#### 8. Error Handling

**Function**: `_handle_orchestration_error(context, run_id, execution_report, error) -> dict[str, Any]`
**Size**: 6 LOC
**Responsibility**: Handle orchestration errors and update execution report
**Returns**: Updated execution_report with error details

## Key Design Decisions

### 1. Generator Pattern Preservation

All helper functions that call Azure Durable Functions activities are implemented as generators (use `yield from`):

```python
def _execute_validation_phase(context, run_id, execution_report):
    """Generator function that yields activity results."""
    validation_result = yield context.call_activity("validate_environment_activity", None)
    # ... process result
    return (validation_result, overall_passed)
```

### 2. Phase Isolation

Each phase is completely independent and can be:
- Tested separately with mocked activities
- Modified without affecting other phases
- Understood in isolation

### 3. Type Hints

Full type hints added for all parameters and return values:

```python
def _initialize_execution_report(run_id: str, started_at: str) -> dict[str, Any]:
    """Initialize execution report structure."""
    ...
```

### 4. Error Propagation

Errors bubble up to the main function for centralized error handling:

```python
try:
    # All phases
    ...
except Exception as e:
    return _handle_orchestration_error(context, run_id, execution_report, e)
```

### 5. Dictionary Safety

Safe dictionary access patterns used throughout:

```python
if "phases" not in execution_report:
    execution_report["phases"] = {}
phases = execution_report["phases"]
```

## Benefits

### Readability

- Main function is now ~50 LOC and reads like a workflow diagram
- Each helper function has a single, clear responsibility
- Function names clearly describe their purpose

### Maintainability

- Changes to one phase don't affect others
- Helper functions can be tested independently
- Easier to debug issues in specific phases

### Testability

- Each helper function can be unit tested with mocked activities
- Integration tests cover full orchestration flow
- Edge cases can be tested at the appropriate level

### Philosophy Compliance

- ✅ **Ruthless Simplicity**: Each function does one thing
- ✅ **Modular Design**: Clear module boundaries (phases as modules)
- ✅ **Zero-BS Implementation**: No stubs, all functions work
- ✅ **<50 LOC per function**: All helper functions comply

## Testing Strategy

### Unit Tests

Each helper function has dedicated unit tests:

```python
def test_initialize_execution_report():
    """Test execution report initialization."""
    result = _initialize_execution_report("run-123", "2024-01-19T00:00:00Z")
    assert result["run_id"] == "run-123"
    assert result["status"] == "in_progress"

def test_execute_validation_phase_success(mock_context):
    """Test validation phase with successful validation."""
    # Mock context.call_activity
    # Test validation result processing
    ...
```

### Integration Tests

Full orchestration flow tested with all phases:

```python
def test_full_orchestration_happy_path():
    """Test complete orchestration with all phases succeeding."""
    # Use orchestrator_generator_wrapper
    # Mock all activity calls
    # Verify execution report structure
    ...
```

### Edge Case Tests

- Empty scenario selection
- Partial provisioning failures
- Cleanup with remaining resources
- Error handling at each phase

## Migration Guide

### For Developers

The refactored code maintains 100% backward compatibility:

- Same function signature: `orchestrate_haymaker_run(context: Any) -> Any`
- Same return structure: execution_report dict
- Same activity function calls
- Same error handling behavior

### For Operators

No operational changes required:

- Same Durable Functions orchestration
- Same monitoring and logging
- Same checkpoint/replay behavior
- Same activity invocations

## Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Main function LOC | 295 | ~50 | -83% |
| Largest function LOC | 295 | 45 | -85% |
| Functions > 50 LOC | 1 | 0 | ✅ Compliant |
| Helper functions | 0 | 10 | Better modularity |
| Testable units | 1 | 11 | +1000% |

## Related

- Issue: #272
- Quality Audit: docs/QUALITY_AUDIT_2026-01-17.md
- Original file: src/azure_haymaker/orchestrator/workflow_orchestrator.py
- Tests: tests/unit/test_workflow_orchestrator.py
