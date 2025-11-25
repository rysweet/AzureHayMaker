"""Unit tests for workflow_orchestrator.py - 7-phase orchestration logic.

Tests cover:
- Phase 1: Validation - environment validation and early exit on failure
- Phase 2: Scenario Selection - selection and empty scenarios handling
- Phase 3: Provisioning - parallel SP creation and container deployment
- Phase 4: Monitoring - 8-hour monitoring loop with periodic checks
- Phase 5: Cleanup Verification - remaining resources detection
- Phase 6: Forced Cleanup - conditional cleanup when resources remain
- Phase 7: Reporting - report generation and final status

Uses Azure Durable Functions testing utilities (orchestrator_generator_wrapper).

Issue: #79 - Add Test Coverage for Workflow Orchestrator
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from azure.durable_functions.models import TaskBase
from azure.durable_functions.testing import orchestrator_generator_wrapper

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def run_id() -> str:
    """Generate unique run ID for tests."""
    return str(uuid4())


@pytest.fixture
def started_at() -> str:
    """Return ISO timestamp for test start."""
    return datetime.now(UTC).isoformat()


@pytest.fixture
def mock_validation_success() -> dict[str, Any]:
    """Successful validation result."""
    return {
        "overall_passed": True,
        "results": [
            {"check_name": "azure_credentials", "passed": True},
            {"check_name": "anthropic_api", "passed": True},
            {"check_name": "key_vault", "passed": True},
        ],
    }


@pytest.fixture
def mock_validation_failure() -> dict[str, Any]:
    """Failed validation result."""
    return {
        "overall_passed": False,
        "results": [
            {"check_name": "azure_credentials", "passed": False, "error": "Invalid credentials"},
            {"check_name": "anthropic_api", "passed": True},
        ],
    }


@pytest.fixture
def mock_scenarios() -> dict[str, Any]:
    """Mock scenario selection result."""
    return {
        "scenarios": [
            {
                "scenario_name": "scenario-1",
                "technology_area": "AI & ML",
                "scenario_doc_path": "docs/scenarios/scenario-1.md",
                "agent_path": "src/agents/scenario_1.py",
            },
            {
                "scenario_name": "scenario-2",
                "technology_area": "Security",
                "scenario_doc_path": "docs/scenarios/scenario-2.md",
                "agent_path": "src/agents/scenario_2.py",
            },
        ]
    }


@pytest.fixture
def mock_sp_results() -> list[dict[str, Any]]:
    """Mock service principal creation results."""
    return [
        {
            "status": "success",
            "sp_details": {
                "sp_name": "AzureHayMaker-scenario-1-admin",
                "client_id": "client-1",
                "principal_id": "principal-1",
                "secret_reference": "scenario-sp-scenario-1-secret",
            },
        },
        {
            "status": "success",
            "sp_details": {
                "sp_name": "AzureHayMaker-scenario-2-admin",
                "client_id": "client-2",
                "principal_id": "principal-2",
                "secret_reference": "scenario-sp-scenario-2-secret",
            },
        },
    ]


@pytest.fixture
def mock_container_results(run_id: str) -> list[dict[str, Any]]:
    """Mock container deployment results."""
    return [
        {
            "status": "success",
            "container_id": f"/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/container-{run_id}-1",
        },
        {
            "status": "success",
            "container_id": f"/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/containerApps/container-{run_id}-2",
        },
    ]


# =============================================================================
# MOCK CONTEXT FACTORY
# =============================================================================


def create_mock_task(result: Any) -> TaskBase:
    """Create a mock TaskBase with a result."""
    task = MagicMock(spec=TaskBase)
    task.result = result
    return task


def create_mock_context(
    run_id: str,
    started_at: str,
    activity_results: dict[str, Any],
) -> MagicMock:
    """Create a mock DurableOrchestrationContext.

    Args:
        run_id: The run ID for this orchestration
        started_at: ISO timestamp for when the run started
        activity_results: Dictionary mapping activity names to their results

    Returns:
        Mock context that simulates DurableOrchestrationContext behavior
    """
    context = MagicMock()
    context.input = {"run_id": run_id, "started_at": started_at}

    # Track current time for timer simulation
    current_time = datetime.now(UTC)

    context.current_utc_datetime = property(lambda self: current_time)

    # Track call counts for activities called multiple times
    call_counts: dict[str, int] = {}

    def mock_call_activity(activity_name: str, params: Any = None) -> TaskBase:
        """Mock call_activity that returns TaskBase with configured result."""
        if activity_name not in call_counts:
            call_counts[activity_name] = 0

        result = activity_results.get(activity_name, {"status": "success"})

        # Handle sequence of results
        if isinstance(result, list):
            idx = call_counts[activity_name]
            call_counts[activity_name] = idx + 1
            if idx < len(result):
                return create_mock_task(result[idx])
            return create_mock_task(result[-1])

        call_counts[activity_name] += 1
        return create_mock_task(result)

    context.call_activity = Mock(side_effect=mock_call_activity)

    def mock_task_all(tasks: list[TaskBase]) -> TaskBase:
        """Mock task_all that returns TaskBase with list of results."""
        results = [t.result for t in tasks]
        return create_mock_task(results)

    context.task_all = Mock(side_effect=mock_task_all)

    def mock_create_timer(fire_at: datetime) -> TaskBase:
        """Mock create_timer that advances time."""
        nonlocal current_time
        current_time = fire_at
        return create_mock_task(None)

    context.create_timer = Mock(side_effect=mock_create_timer)

    # Make current_utc_datetime a property that returns current_time
    type(context).current_utc_datetime = property(lambda self: current_time)

    return context


def run_orchestration(
    run_id: str,
    started_at: str,
    activity_results: dict[str, Any],
) -> dict[str, Any]:
    """Run the workflow orchestrator with mocked context.

    Args:
        run_id: Unique run identifier
        started_at: ISO timestamp for run start
        activity_results: Dictionary mapping activity names to results

    Returns:
        The execution report dictionary returned by the orchestrator
    """
    from azure_haymaker.orchestrator.workflow_orchestrator import orchestrate_haymaker_run

    # Get the underlying orchestrator function from the decorated function
    # The decorator wraps the function, we need to access the original
    func = orchestrate_haymaker_run.build().get_user_function()
    orchestrator_func = func.orchestrator_function

    # Create mock context
    context = create_mock_context(run_id, started_at, activity_results)

    # Create generator from orchestrator function
    generator = orchestrator_func(context)

    # Use the Azure testing utility to run the generator
    values = list(orchestrator_generator_wrapper(generator))

    # The last value is the return value
    if values:
        return values[-1]
    return {}


# =============================================================================
# PHASE 1: VALIDATION TESTS
# =============================================================================


class TestPhase1Validation:
    """Tests for Phase 1: Environment Validation."""

    def test_validation_failure_stops_workflow(
        self,
        run_id: str,
        started_at: str,
        mock_validation_failure: dict[str, Any],
    ):
        """Test that validation failure stops the workflow immediately."""
        activity_results = {
            "validate_environment_activity": mock_validation_failure,
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert result["status"] == "failed"
        assert result["failure_reason"] == "environment_validation_failed"
        # Should not proceed to Phase 2
        assert "selection" not in result.get("phases", {})

    def test_validation_success_records_results(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that validation phase records check results on success."""
        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": []},
            "generate_report_activity": {"report_url": "https://test.blob.core.windows.net/reports/test.json", "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert result["status"] == "completed"
        validation_phase = result["phases"]["validation"]
        assert validation_phase["status"] == "passed"
        assert "checks" in validation_phase
        assert len(validation_phase["checks"]) == 3


# =============================================================================
# PHASE 2: SCENARIO SELECTION TESTS
# =============================================================================


class TestPhase2ScenarioSelection:
    """Tests for Phase 2: Scenario Selection."""

    def test_no_scenarios_selected_fails_workflow(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
    ):
        """Test that workflow fails when no scenarios are selected."""
        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": {"scenarios": []},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert result["status"] == "failed"
        assert result["failure_reason"] == "no_scenarios_selected"

    def test_scenario_selection_records_count(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that scenario selection records the count and names."""
        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": []},
            "generate_report_activity": {"report_url": "https://test.blob.core.windows.net/reports/test.json", "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        selection_phase = result["phases"]["selection"]
        assert selection_phase["status"] == "completed"
        assert selection_phase["scenario_count"] == 2
        assert "scenario-1" in selection_phase["scenarios"]
        assert "scenario-2" in selection_phase["scenarios"]


# =============================================================================
# PHASE 3: PROVISIONING TESTS
# =============================================================================


class TestPhase3Provisioning:
    """Tests for Phase 3: Service Principal Creation and Container Deployment."""

    def test_provisioning_records_sp_and_container_counts(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that provisioning records SP and container counts."""
        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": []},
            "generate_report_activity": {"report_url": "https://test.blob.core.windows.net/reports/test.json", "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        provisioning_phase = result["phases"]["provisioning"]
        assert provisioning_phase["status"] == "completed"
        assert provisioning_phase["service_principals"]["requested"] == 2
        assert "container_apps" in provisioning_phase

    def test_sp_failure_continues_with_successful_sps(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that workflow continues with successful SPs when some fail."""
        sp_results_mixed = [
            {
                "status": "success",
                "sp_details": {
                    "sp_name": "AzureHayMaker-scenario-1-admin",
                    "client_id": "client-1",
                    "principal_id": "principal-1",
                    "secret_reference": "secret-1",
                },
            },
            {
                "status": "failed",
                "error": "SP creation failed",
            },
        ]

        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": sp_results_mixed,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 1, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": []},
            "generate_report_activity": {"report_url": "https://test.blob.core.windows.net/reports/test.json", "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert result["status"] == "completed"
        provisioning_phase = result["phases"]["provisioning"]
        assert provisioning_phase["service_principals"]["failed"] >= 0


# =============================================================================
# PHASE 4: MONITORING TESTS
# =============================================================================


class TestPhase4Monitoring:
    """Tests for Phase 4: 8-hour Monitoring Loop."""

    def test_monitoring_records_status_checks(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that monitoring records periodic status checks."""
        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": []},
            "generate_report_activity": {"report_url": "https://test.blob.core.windows.net/reports/test.json", "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert result["status"] == "completed"
        monitoring_phase = result["phases"]["monitoring"]
        assert "status_checks" in monitoring_phase


# =============================================================================
# PHASE 5 & 6: CLEANUP TESTS
# =============================================================================


class TestPhase5And6Cleanup:
    """Tests for Phase 5: Cleanup Verification and Phase 6: Forced Cleanup."""

    def test_no_remaining_resources_skips_forced_cleanup(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that forced cleanup is skipped when no resources remain."""
        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": []},
            "generate_report_activity": {"report_url": "https://test.blob.core.windows.net/reports/test.json", "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        cleanup_phase = result["phases"]["cleanup"]
        assert cleanup_phase["status"] == "verified"
        assert cleanup_phase["verification_found"] == 0
        assert cleanup_phase["deleted"] == 0

    def test_remaining_resources_triggers_forced_cleanup(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that remaining resources trigger forced cleanup."""
        remaining_resources = [
            {"resource_id": "/subscriptions/sub/resourceGroups/rg1", "resource_type": "Microsoft.Resources/resourceGroups"},
            {"resource_id": "/subscriptions/sub/resourceGroups/rg2", "resource_type": "Microsoft.Resources/resourceGroups"},
        ]

        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": remaining_resources},
            "force_cleanup_activity": {"status": "completed", "deleted_count": 2, "failed_count": 0},
            "generate_report_activity": {"report_url": "https://test.blob.core.windows.net/reports/test.json", "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        cleanup_phase = result["phases"]["cleanup"]
        assert cleanup_phase["status"] == "completed"
        assert cleanup_phase["verification_found"] == 2
        assert cleanup_phase["deleted"] == 2
        assert cleanup_phase["failed"] == 0

    def test_partial_cleanup_failure_recorded(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that partial cleanup failures are recorded."""
        remaining_resources = [
            {"resource_id": "/subscriptions/sub/resourceGroups/rg1", "resource_type": "Microsoft.Resources/resourceGroups"},
        ]

        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": remaining_resources},
            "force_cleanup_activity": {"status": "partial_failure", "deleted_count": 0, "failed_count": 1},
            "generate_report_activity": {"report_url": "https://test.blob.core.windows.net/reports/test.json", "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        cleanup_phase = result["phases"]["cleanup"]
        assert cleanup_phase["status"] == "partial_failure"
        assert cleanup_phase["failed"] == 1


# =============================================================================
# PHASE 7: REPORTING TESTS
# =============================================================================


class TestPhase7Reporting:
    """Tests for Phase 7: Report Generation."""

    def test_report_url_included_in_result(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that report URL is included in final result."""
        expected_url = "https://teststorage.blob.core.windows.net/execution-reports/test-run/report.json"

        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": []},
            "generate_report_activity": {"report_url": expected_url, "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert result["status"] == "completed"
        assert result["report_url"] == expected_url

    def test_ended_at_timestamp_included(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that ended_at timestamp is included in final result."""
        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": []},
            "generate_report_activity": {"report_url": "https://test.blob.core.windows.net/reports/test.json", "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert "ended_at" in result
        # Should be a valid ISO timestamp
        datetime.fromisoformat(result["ended_at"].replace("Z", "+00:00"))


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling and recovery."""

    def test_execution_report_initialized_correctly(
        self,
        run_id: str,
        started_at: str,
    ):
        """Test that execution report is initialized with correct fields."""
        activity_results = {
            "validate_environment_activity": {"overall_passed": False, "results": []},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert "run_id" in result
        assert "started_at" in result
        assert "status" in result
        assert "phases" in result
        assert result["run_id"] == run_id
        assert result["started_at"] == started_at


# =============================================================================
# STATE MANAGEMENT TESTS
# =============================================================================


class TestStateManagement:
    """Tests for state management across phases."""

    def test_phases_dict_persists_across_phases(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test that phases dictionary persists and accumulates data."""
        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": []},
            "generate_report_activity": {"report_url": "https://test.blob.core.windows.net/reports/test.json", "report_id": run_id},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        phases = result["phases"]
        assert "validation" in phases
        assert "selection" in phases
        assert "provisioning" in phases
        assert "monitoring" in phases
        assert "cleanup" in phases

    def test_run_id_propagated_throughout_orchestration(
        self,
        run_id: str,
        started_at: str,
    ):
        """Test that run_id from input is used throughout orchestration."""
        activity_results = {
            "validate_environment_activity": {"overall_passed": False, "results": []},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert result["run_id"] == run_id


# =============================================================================
# FULL WORKFLOW INTEGRATION TESTS
# =============================================================================


class TestFullWorkflowIntegration:
    """Integration tests for complete workflow execution."""

    def test_successful_full_workflow(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test a complete successful workflow from start to finish."""
        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": []},
            "generate_report_activity": {
                "report_url": "https://teststorage.blob.core.windows.net/execution-reports/test-run/report.json",
                "report_id": run_id,
            },
        }

        result = run_orchestration(run_id, started_at, activity_results)

        # Verify successful completion
        assert result["status"] == "completed"
        assert result["run_id"] == run_id
        assert "report_url" in result
        assert "ended_at" in result

        # Verify all phases completed
        phases = result["phases"]
        assert phases["validation"]["status"] == "passed"
        assert phases["selection"]["status"] == "completed"
        assert phases["provisioning"]["status"] == "completed"
        assert "status_checks" in phases["monitoring"]
        assert phases["cleanup"]["status"] == "verified"

    def test_workflow_with_forced_cleanup(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
        mock_scenarios: dict[str, Any],
        mock_sp_results: list[dict[str, Any]],
        mock_container_results: list[dict[str, Any]],
    ):
        """Test workflow that requires forced cleanup."""
        remaining_resources = [
            {"resource_id": "/subscriptions/sub/resourceGroups/rg1", "resource_type": "Microsoft.Resources/resourceGroups"},
        ]

        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": mock_scenarios,
            "create_service_principal_activity": mock_sp_results,
            "deploy_container_app_activity": mock_container_results,
            "check_agent_status_activity": {"running_count": 2, "completed_count": 0, "failed_count": 0},
            "verify_cleanup_activity": {"remaining_resources": remaining_resources},
            "force_cleanup_activity": {"status": "completed", "deleted_count": 1, "failed_count": 0},
            "generate_report_activity": {
                "report_url": "https://teststorage.blob.core.windows.net/execution-reports/test-run/report.json",
                "report_id": run_id,
            },
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert result["status"] == "completed"
        assert result["phases"]["cleanup"]["status"] == "completed"
        assert result["phases"]["cleanup"]["deleted"] == 1

    def test_workflow_early_exit_on_validation_failure(
        self,
        run_id: str,
        started_at: str,
        mock_validation_failure: dict[str, Any],
    ):
        """Test that workflow exits early when validation fails."""
        activity_results = {
            "validate_environment_activity": mock_validation_failure,
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert result["status"] == "failed"
        assert result["failure_reason"] == "environment_validation_failed"
        assert "validation" in result["phases"]
        # Other phases should not exist
        assert "selection" not in result["phases"]
        assert "provisioning" not in result["phases"]

    def test_workflow_early_exit_on_no_scenarios(
        self,
        run_id: str,
        started_at: str,
        mock_validation_success: dict[str, Any],
    ):
        """Test that workflow exits early when no scenarios are selected."""
        activity_results = {
            "validate_environment_activity": mock_validation_success,
            "select_scenarios_activity": {"scenarios": []},
        }

        result = run_orchestration(run_id, started_at, activity_results)

        assert result["status"] == "failed"
        assert result["failure_reason"] == "no_scenarios_selected"
        assert "selection" in result["phases"]
        # Provisioning should not exist
        assert "provisioning" not in result["phases"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
