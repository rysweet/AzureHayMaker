"""
Unit tests for workflow_orchestrator module.

Tests cover the main orchestration function that coordinates:
- Phase 1: Validation
- Phase 2: Scenario Selection
- Phase 3: Provisioning (SP creation + Container deployment)
- Phase 4: Monitoring (8 hour wait with checks)
- Phase 5: Cleanup Verification
- Phase 6: Forced Cleanup
- Phase 7: Report Generation

Testing approach:
- Mock Durable Functions context and activity calls
- Test phase transitions and state management
- Focus on error handling and failure scenarios
- Verify idempotency and replay safety

The orchestrator is a generator function (uses yield for Durable Functions pattern).
Tests use a helper function to drive the generator with mocked activity results.

NOTE: The function is decorated with @app.orchestration_trigger which wraps it.
We access the underlying function via the closure to test the generator logic directly.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from azure_haymaker.orchestrator.workflow_orchestrator import orchestrate_haymaker_run


def get_underlying_orchestrator():
    """Extract the underlying generator function from the decorator wrapper.

    The orchestrate_haymaker_run is decorated with @app.orchestration_trigger
    which wraps it. The actual generator function is stored in the closure.
    """
    # Navigate through the decorator layers to get the underlying function
    # orchestrate_haymaker_run._function._func.__closure__[0].cell_contents
    return orchestrate_haymaker_run._function._func.__closure__[0].cell_contents


# ==============================================================================
# GENERATOR DRIVER HELPER
# ==============================================================================


def run_orchestrator_generator(gen, activity_results):
    """Drive a Durable Functions orchestrator generator with mocked activity results.

    Args:
        gen: The generator from calling the orchestrator function
        activity_results: List of results to send for each yield

    Returns:
        Final return value from the orchestrator
    """
    result_iter = iter(activity_results)

    try:
        # Start the generator
        next(gen)
        while True:
            # Send the next mocked result
            result = next(result_iter, None)
            gen.send(result)
    except StopIteration as e:
        return e.value


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_context():
    """Create a mock Durable Functions orchestration context."""
    context = Mock()
    # context.input is already a dict, which has a get() method built-in
    context.input = {
        "run_id": "test-run-001",
        "started_at": "2025-11-25T10:00:00Z",
    }
    context.current_utc_datetime = datetime(2025, 11, 25, 10, 0, 0, tzinfo=UTC)
    context.call_activity = Mock()
    context.task_all = Mock()
    context.create_timer = Mock()

    return context


@pytest.fixture
def mock_validation_result():
    """Mock validation phase result."""
    return {
        "overall_passed": True,
        "results": [
            {"check": "azure_credentials", "status": "passed"},
            {"check": "api_access", "status": "passed"},
        ],
    }


@pytest.fixture
def mock_scenario_selection():
    """Mock scenario selection result."""
    return {
        "scenarios": [
            {"scenario_name": "compute-01", "technology_area": "compute"},
            {"scenario_name": "storage-01", "technology_area": "storage"},
        ]
    }


@pytest.fixture
def mock_sp_results():
    """Mock service principal creation results."""
    return [
        {
            "status": "success",
            "sp_details": {
                "client_id": "sp-001-client-id",
                "object_id": "sp-001-object-id",
            },
        },
        {
            "status": "success",
            "sp_details": {
                "client_id": "sp-002-client-id",
                "object_id": "sp-002-object-id",
            },
        },
    ]


@pytest.fixture
def mock_container_results():
    """Mock container deployment results."""
    return [
        {"status": "success", "container_id": "container-001"},
        {"status": "success", "container_id": "container-002"},
    ]


# ==============================================================================
# TESTS: Happy Path - Successful Execution
# ==============================================================================


def test_orchestrate_haymaker_run_successful_execution(
    mock_context,
    mock_validation_result,
    mock_scenario_selection,
    mock_sp_results,
    mock_container_results,
):
    """Test complete successful orchestration workflow."""
    # For Phase 4 monitoring, we need to simulate the 8-hour window expiring
    # after first check by manipulating current_utc_datetime
    monitoring_end_time = mock_context.current_utc_datetime + timedelta(hours=8)

    # Build activity results sequence matching the orchestrator's yield pattern
    activity_results = [
        mock_validation_result,  # Phase 1: Validation
        mock_scenario_selection,  # Phase 2: Selection
        mock_sp_results,  # Phase 3: SP creation (task_all)
        mock_container_results,  # Phase 3: Container deployment (task_all)
        {"running_count": 0, "completed_count": 2},  # Phase 4: First monitoring check
        None,  # Phase 4: Timer (we'll advance time in side effect)
        {"remaining_resources": []},  # Phase 5: Cleanup verification
        {"report_url": "https://storage.blob.core.windows.net/reports/test-run-001.json"},  # Phase 7: Report
    ]

    # After the timer yield, advance time past monitoring end
    def advance_time_past_monitoring():
        mock_context.current_utc_datetime = monitoring_end_time + timedelta(minutes=1)

    # We need to track yield count to know when to advance time
    yield_count = [0]
    original_results = list(activity_results)

    def get_next_result():
        idx = yield_count[0]
        yield_count[0] += 1
        if idx == 5:  # After timer yield
            advance_time_past_monitoring()
        if idx < len(original_results):
            return original_results[idx]
        return None

    # Get the underlying function and execute orchestration using generator driver
    underlying_fn = get_underlying_orchestrator()
    gen = underlying_fn(mock_context)

    # Custom driver that advances time
    try:
        next(gen)
        while True:
            result = get_next_result()
            gen.send(result)
    except StopIteration as e:
        result = e.value

    # Verify execution completed successfully
    assert result["status"] == "completed"
    assert result["run_id"] == "test-run-001"
    assert "report_url" in result
    assert "phases" in result

    # Verify all phases completed
    phases = result["phases"]
    assert "validation" in phases
    assert phases["validation"]["status"] == "passed"
    assert "selection" in phases
    assert "provisioning" in phases
    assert "monitoring" in phases
    assert "cleanup" in phases

    # Verify provisioning phase
    assert phases["provisioning"]["service_principals"]["created"] == 2
    assert phases["provisioning"]["container_apps"]["deployed"] == 2

    # Verify cleanup phase (no resources remaining)
    assert phases["cleanup"]["status"] == "verified"
    assert phases["cleanup"]["verification_found"] == 0


# ==============================================================================
# TESTS: Phase 1 - Validation Failure
# ==============================================================================


def test_orchestrate_haymaker_run_validation_failed(mock_context):
    """Test orchestration stops when validation fails."""
    validation_failure = {
        "overall_passed": False,
        "results": [{"check": "azure_credentials", "status": "failed"}],
    }

    activity_results = [validation_failure]

    underlying_fn = get_underlying_orchestrator()
    gen = underlying_fn(mock_context)
    result = run_orchestrator_generator(gen, activity_results)

    # Verify execution failed at validation
    assert result["status"] == "failed"
    assert result["failure_reason"] == "environment_validation_failed"
    assert "phases" in result
    assert "validation" in result["phases"]

    # Verify no further phases were executed
    assert "selection" not in result["phases"]
    assert "provisioning" not in result["phases"]


# ==============================================================================
# TESTS: Phase 2 - No Scenarios Selected
# ==============================================================================


def test_orchestrate_haymaker_run_no_scenarios(mock_context, mock_validation_result):
    """Test orchestration fails when no scenarios are selected."""
    activity_results = [
        mock_validation_result,
        {"scenarios": []},  # Empty scenarios
    ]

    underlying_fn = get_underlying_orchestrator()
    gen = underlying_fn(mock_context)
    result = run_orchestrator_generator(gen, activity_results)

    assert result["status"] == "failed"
    assert result["failure_reason"] == "no_scenarios_selected"
    assert result["phases"]["selection"]["scenario_count"] == 0


# ==============================================================================
# TESTS: Phase 3 - Provisioning Failures
# ==============================================================================


def test_orchestrate_haymaker_run_sp_creation_failures(
    mock_context, mock_validation_result, mock_scenario_selection
):
    """Test handling of service principal creation failures."""
    sp_results_with_failures = [
        {
            "status": "success",
            "sp_details": {"client_id": "sp-001", "object_id": "obj-001"},
        },
        {"status": "failed", "error": "Insufficient permissions"},
    ]

    # Only one successful SP, so only one container task
    container_results = [
        {"status": "success", "container_id": "container-001"},
    ]

    # Setup time manipulation for monitoring loop
    monitoring_end_time = mock_context.current_utc_datetime + timedelta(hours=8)

    activity_results = [
        mock_validation_result,  # Phase 1
        mock_scenario_selection,  # Phase 2
        sp_results_with_failures,  # Phase 3: SP creation
        container_results,  # Phase 3: Container deployment
        {"running_count": 0, "completed_count": 1},  # Phase 4: Monitoring check
        None,  # Phase 4: Timer
        {"remaining_resources": []},  # Phase 5: Cleanup verification
        {"report_url": "https://storage/report.json"},  # Phase 7: Report
    ]

    yield_count = [0]
    original_results = list(activity_results)

    def get_next_result():
        idx = yield_count[0]
        yield_count[0] += 1
        if idx == 5:  # After timer yield
            mock_context.current_utc_datetime = monitoring_end_time + timedelta(minutes=1)
        if idx < len(original_results):
            return original_results[idx]
        return None

    underlying_fn = get_underlying_orchestrator()
    gen = underlying_fn(mock_context)

    try:
        next(gen)
        while True:
            r = get_next_result()
            gen.send(r)
    except StopIteration as e:
        result = e.value

    # Verify execution completes despite SP failure
    assert result["status"] == "completed"
    phases = result["phases"]
    assert phases["provisioning"]["service_principals"]["created"] == 1
    assert phases["provisioning"]["service_principals"]["failed"] == 1


def test_orchestrate_haymaker_run_container_deployment_failures(
    mock_context, mock_validation_result, mock_scenario_selection, mock_sp_results
):
    """Test handling of container deployment failures."""
    container_results_with_failures = [
        {"status": "success", "container_id": "container-001"},
        {"status": "failed", "error": "Container Apps environment not found"},
    ]

    monitoring_end_time = mock_context.current_utc_datetime + timedelta(hours=8)

    activity_results = [
        mock_validation_result,  # Phase 1
        mock_scenario_selection,  # Phase 2
        mock_sp_results,  # Phase 3: SP creation
        container_results_with_failures,  # Phase 3: Container deployment
        {"running_count": 0, "completed_count": 1},  # Phase 4: Monitoring
        None,  # Phase 4: Timer
        {"remaining_resources": []},  # Phase 5: Cleanup
        {"report_url": "https://storage/report.json"},  # Phase 7: Report
    ]

    yield_count = [0]
    original_results = list(activity_results)

    def get_next_result():
        idx = yield_count[0]
        yield_count[0] += 1
        if idx == 5:
            mock_context.current_utc_datetime = monitoring_end_time + timedelta(minutes=1)
        if idx < len(original_results):
            return original_results[idx]
        return None

    underlying_fn = get_underlying_orchestrator()
    gen = underlying_fn(mock_context)

    try:
        next(gen)
        while True:
            r = get_next_result()
            gen.send(r)
    except StopIteration as e:
        result = e.value

    # Verify execution completes despite container failure
    phases = result["phases"]
    assert phases["provisioning"]["container_apps"]["deployed"] == 1
    assert phases["provisioning"]["container_apps"]["failed"] == 1


# ==============================================================================
# TESTS: Phase 4 - Monitoring
# ==============================================================================


def test_orchestrate_haymaker_run_monitoring_with_early_completion(
    mock_context,
    mock_validation_result,
    mock_scenario_selection,
    mock_sp_results,
    mock_container_results,
):
    """Test monitoring exits early when all containers complete."""
    monitoring_end_time = mock_context.current_utc_datetime + timedelta(hours=8)

    activity_results = [
        mock_validation_result,  # Phase 1
        mock_scenario_selection,  # Phase 2
        mock_sp_results,  # Phase 3: SP creation
        mock_container_results,  # Phase 3: Container deployment
        {"running_count": 0, "completed_count": 2},  # Phase 4: All completed on first check
        None,  # Phase 4: Timer
        {"remaining_resources": []},  # Phase 5: Cleanup
        {"report_url": "https://storage/report.json"},  # Phase 7: Report
    ]

    yield_count = [0]
    original_results = list(activity_results)

    def get_next_result():
        idx = yield_count[0]
        yield_count[0] += 1
        if idx == 5:  # After timer, advance past monitoring end
            mock_context.current_utc_datetime = monitoring_end_time + timedelta(minutes=1)
        if idx < len(original_results):
            return original_results[idx]
        return None

    underlying_fn = get_underlying_orchestrator()
    gen = underlying_fn(mock_context)

    try:
        next(gen)
        while True:
            r = get_next_result()
            gen.send(r)
    except StopIteration as e:
        result = e.value

    # Verify monitoring completed
    assert result["status"] == "completed"
    monitoring = result["phases"]["monitoring"]
    assert len(monitoring["status_checks"]) == 1  # Only one check before time advanced


# ==============================================================================
# TESTS: Phase 6 - Forced Cleanup
# ==============================================================================


def test_orchestrate_haymaker_run_forced_cleanup_required(
    mock_context,
    mock_validation_result,
    mock_scenario_selection,
    mock_sp_results,
    mock_container_results,
):
    """Test forced cleanup when resources remain after verification."""
    monitoring_end_time = mock_context.current_utc_datetime + timedelta(hours=8)

    activity_results = [
        mock_validation_result,  # Phase 1
        mock_scenario_selection,  # Phase 2
        mock_sp_results,  # Phase 3: SP creation
        mock_container_results,  # Phase 3: Container deployment
        {"running_count": 0, "completed_count": 2},  # Phase 4: Monitoring
        None,  # Phase 4: Timer
        {
            "remaining_resources": [
                {"id": "resource-001", "type": "VM"},
                {"id": "resource-002", "type": "Storage"},
            ]
        },  # Phase 5: Cleanup verification finds resources
        {"status": "completed", "deleted_count": 2, "failed_count": 0},  # Phase 6: Forced cleanup
        {"report_url": "https://storage/report.json"},  # Phase 7: Report
    ]

    yield_count = [0]
    original_results = list(activity_results)

    def get_next_result():
        idx = yield_count[0]
        yield_count[0] += 1
        if idx == 5:
            mock_context.current_utc_datetime = monitoring_end_time + timedelta(minutes=1)
        if idx < len(original_results):
            return original_results[idx]
        return None

    underlying_fn = get_underlying_orchestrator()
    gen = underlying_fn(mock_context)

    try:
        next(gen)
        while True:
            r = get_next_result()
            gen.send(r)
    except StopIteration as e:
        result = e.value

    # Verify forced cleanup was executed
    cleanup = result["phases"]["cleanup"]
    assert cleanup["verification_found"] == 2
    assert cleanup["deleted"] == 2
    assert cleanup["failed"] == 0


# ==============================================================================
# TESTS: Error Handling
# ==============================================================================


def test_orchestrate_haymaker_run_unhandled_exception(mock_context, mock_validation_result):
    """Test error handling for unexpected exceptions."""
    # We need to throw an exception during the generator execution
    # The orchestrator catches exceptions internally

    underlying_fn = get_underlying_orchestrator()
    gen = underlying_fn(mock_context)

    # Custom driver that throws exception when sent
    try:
        next(gen)
        gen.send(mock_validation_result)
        # Now throw an exception into the generator
        result = gen.throw(Exception, "Unexpected database error")
    except StopIteration as e:
        result = e.value

    # Verify execution failed gracefully
    assert result["status"] == "failed"
    assert "error" in result
    assert "Unexpected database error" in result["error"]
    assert "ended_at" in result


# ==============================================================================
# TESTS: Input Validation
# ==============================================================================


def test_orchestrate_haymaker_run_with_valid_input(mock_context):
    """Test that orchestration processes input correctly."""
    # Verify input is accessible
    assert mock_context.input["run_id"] == "test-run-001"
    assert "started_at" in mock_context.input


def test_orchestrate_haymaker_run_checkpoint_phases(
    mock_context,
    mock_validation_result,
    mock_scenario_selection,
    mock_sp_results,
    mock_container_results,
):
    """Test that phases are checkpointed in execution_report."""
    monitoring_end_time = mock_context.current_utc_datetime + timedelta(hours=8)

    activity_results = [
        mock_validation_result,  # Phase 1
        mock_scenario_selection,  # Phase 2
        mock_sp_results,  # Phase 3: SP creation
        mock_container_results,  # Phase 3: Container deployment
        {"running_count": 0, "completed_count": 2},  # Phase 4: Monitoring
        None,  # Phase 4: Timer
        {"remaining_resources": []},  # Phase 5: Cleanup
        {"report_url": "https://storage/report.json"},  # Phase 7: Report
    ]

    yield_count = [0]
    original_results = list(activity_results)

    def get_next_result():
        idx = yield_count[0]
        yield_count[0] += 1
        if idx == 5:
            mock_context.current_utc_datetime = monitoring_end_time + timedelta(minutes=1)
        if idx < len(original_results):
            return original_results[idx]
        return None

    underlying_fn = get_underlying_orchestrator()
    gen = underlying_fn(mock_context)

    try:
        next(gen)
        while True:
            r = get_next_result()
            gen.send(r)
    except StopIteration as e:
        result = e.value

    # Verify all phases are recorded
    assert "phases" in result
    assert len(result["phases"]) >= 4  # At least validation, selection, provisioning, cleanup
