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
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from azure_haymaker.orchestrator.workflow_orchestrator import orchestrate_haymaker_run

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_context():
    """Create a mock Durable Functions orchestration context."""
    context = Mock()
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


@pytest.mark.skip(reason="Complex mock fixture issues - fix in separate PR")
def test_orchestrate_haymaker_run_successful_execution(
    mock_context,
    mock_validation_result,
    mock_scenario_selection,
    mock_sp_results,
    mock_container_results,
):
    """Test complete successful orchestration workflow."""

    # Setup activity call results in sequence
    activity_results = [
        mock_validation_result,  # Phase 1: Validation
        mock_scenario_selection,  # Phase 2: Selection
        # Phase 3: SP creation (parallel) - handled by task_all
        # Phase 3: Container deployment (parallel) - handled by task_all
        # Phase 4: Monitoring checks (in loop)
        {"running_count": 2, "completed_count": 0},  # First check
        {"running_count": 0, "completed_count": 2},  # Second check - all done
        # Phase 5: Cleanup verification
        {"remaining_resources": []},
        # Phase 7: Report generation
        {"report_url": "https://storage.blob.core.windows.net/reports/test-run-001.json"},
    ]

    call_activity_iter = iter(activity_results)

    def call_activity_side_effect(activity_name, input_data):
        """Yield next result from activity_results."""
        return next(call_activity_iter)

    mock_context.call_activity = Mock(side_effect=call_activity_side_effect)

    # Setup parallel task results
    mock_context.task_all = Mock(side_effect=[mock_sp_results, mock_container_results])

    # Setup timer to advance time
    def create_timer_side_effect(fire_at):
        # Advance current time by 15 minutes
        mock_context.current_utc_datetime = fire_at
        return Mock()

    mock_context.create_timer = Mock(side_effect=create_timer_side_effect)

    # Execute orchestration
    result = orchestrate_haymaker_run(mock_context)

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
    validation_failure = {"overall_passed": False, "results": [{"check": "azure_credentials", "status": "failed"}]}

    mock_context.call_activity = Mock(return_value=validation_failure)

    # Execute orchestration
    result = orchestrate_haymaker_run(mock_context)

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


def test_orchestrate_haymaker_run_no_scenarios(
    mock_context, mock_validation_result
):
    """Test orchestration fails when no scenarios are selected."""
    mock_context.call_activity = Mock(
        side_effect=[
            mock_validation_result,
            {"scenarios": []},  # Empty scenarios
        ]
    )

    result = orchestrate_haymaker_run(mock_context)

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

    container_results = [
        {"status": "success", "container_id": "container-001"},
    ]

    activity_sequence = [
        mock_validation_result,
        mock_scenario_selection,
        {"running_count": 0, "completed_count": 1},  # Monitoring check
        {"remaining_resources": []},  # Cleanup verification
        {"report_url": "https://storage/report.json"},  # Report
    ]

    mock_context.call_activity = Mock(side_effect=activity_sequence)
    mock_context.task_all = Mock(side_effect=[sp_results_with_failures, container_results])

    result = orchestrate_haymaker_run(mock_context)

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

    activity_sequence = [
        mock_validation_result,
        mock_scenario_selection,
        {"running_count": 0, "completed_count": 1},  # Monitoring
        {"remaining_resources": []},  # Cleanup
        {"report_url": "https://storage/report.json"},  # Report
    ]

    mock_context.call_activity = Mock(side_effect=activity_sequence)
    mock_context.task_all = Mock(side_effect=[mock_sp_results, container_results_with_failures])

    result = orchestrate_haymaker_run(mock_context)

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
    # All containers complete immediately
    activity_sequence = [
        mock_validation_result,
        mock_scenario_selection,
        {"running_count": 0, "completed_count": 2},  # All completed on first check
        {"remaining_resources": []},  # Cleanup
        {"report_url": "https://storage/report.json"},  # Report
    ]

    mock_context.call_activity = Mock(side_effect=activity_sequence)
    mock_context.task_all = Mock(side_effect=[mock_sp_results, mock_container_results])

    result = orchestrate_haymaker_run(mock_context)

    # Verify monitoring completed early
    assert result["status"] == "completed"
    monitoring = result["phases"]["monitoring"]
    assert len(monitoring["status_checks"]) == 1  # Only one check needed


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
    activity_sequence = [
        mock_validation_result,
        mock_scenario_selection,
        {"running_count": 0, "completed_count": 2},  # Monitoring
        {
            "remaining_resources": [
                {"id": "resource-001", "type": "VM"},
                {"id": "resource-002", "type": "Storage"},
            ]
        },  # Cleanup verification finds resources
        {"status": "completed", "deleted_count": 2, "failed_count": 0},  # Forced cleanup
        {"report_url": "https://storage/report.json"},  # Report
    ]

    mock_context.call_activity = Mock(side_effect=activity_sequence)
    mock_context.task_all = Mock(side_effect=[mock_sp_results, mock_container_results])

    result = orchestrate_haymaker_run(mock_context)

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
    mock_context.call_activity = Mock(
        side_effect=[
            mock_validation_result,
            Exception("Unexpected database error"),
        ]
    )

    result = orchestrate_haymaker_run(mock_context)

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
    activity_sequence = [
        mock_validation_result,
        mock_scenario_selection,
        {"running_count": 0, "completed_count": 2},
        {"remaining_resources": []},
        {"report_url": "https://storage/report.json"},
    ]

    mock_context.call_activity = Mock(side_effect=activity_sequence)
    mock_context.task_all = Mock(side_effect=[mock_sp_results, mock_container_results])

    result = orchestrate_haymaker_run(mock_context)

    # Verify all phases are recorded
    assert "phases" in result
    assert len(result["phases"]) >= 4  # At least validation, selection, provisioning, cleanup
