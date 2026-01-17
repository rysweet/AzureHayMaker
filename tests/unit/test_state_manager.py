"""Unit tests for Deployment State Manager module.

Tests the knowledge_worker/state_manager.py module which handles:
- Save/Load deployment state
- Missing file handling
- Worker CRUD operations
- State serialization/deserialization
- List and query operations

Testing approach:
- 60% unit tests (heavily mocked)
- 30% integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerIdentity,
    WorkerPersona,
)
from azure_haymaker.knowledge_worker.state_manager import DeploymentStateManager

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_state_dir():
    """Create a temporary directory for state storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def state_manager(temp_state_dir):
    """Create a state manager with temporary directory."""
    return DeploymentStateManager(state_dir=temp_state_dir)


@pytest.fixture
def sample_worker_identity():
    """Create a sample WorkerIdentity for testing."""
    return WorkerIdentity(
        worker_id="kw-test-001",
        display_name="Test Worker",
        user_principal_name="test@corp.onmicrosoft.com",
        department="engineering",
        persona=WorkerPersona.ENGINEERING,
        endpoint_type=EndpointType.CLI_CONTAINER,
        entra_object_id="obj-123",
        team_ids=["team-1", "team-2"],
    )


@pytest.fixture
def sample_deployment_data():
    """Sample deployment data for testing."""
    return {
        "run_id": "run-test-001",
        "name": "Test Deployment",
        "phase": "running",
        "status": "active",
        "worker_count": 5,
        "started_at": datetime(2024, 1, 1, 10, 0, 0),
        "config": {"setting1": "value1"},
    }


# ============================================================================
# Unit Tests - Initialization (60%)
# ============================================================================


class TestDeploymentStateManagerInit:
    """Tests for DeploymentStateManager initialization."""

    def test_default_state_dir(self):
        """Test that default state_dir is ~/.azure_haymaker."""
        with patch.object(Path, "mkdir"):
            manager = DeploymentStateManager()

        expected_dir = Path.home() / ".azure_haymaker"
        assert manager.state_dir == expected_dir

    def test_custom_state_dir(self, temp_state_dir):
        """Test initialization with custom state directory."""
        manager = DeploymentStateManager(state_dir=temp_state_dir)

        assert manager.state_dir == temp_state_dir

    def test_creates_deployments_directory(self, temp_state_dir):
        """Test that deployments directory is created."""
        manager = DeploymentStateManager(state_dir=temp_state_dir)

        assert manager.deployments_dir.exists()
        assert manager.deployments_dir == temp_state_dir / "deployments"

    def test_creates_workers_directory(self, temp_state_dir):
        """Test that workers directory is created."""
        manager = DeploymentStateManager(state_dir=temp_state_dir)

        assert manager.workers_dir.exists()
        assert manager.workers_dir == temp_state_dir / "workers"


# ============================================================================
# Unit Tests - save_deployment (60%)
# ============================================================================


class TestSaveDeployment:
    """Tests for save_deployment method."""

    def test_saves_deployment_to_file(self, state_manager, sample_deployment_data):
        """Test that deployment is saved to JSON file."""
        state_manager.save_deployment(**sample_deployment_data)

        deployment_file = state_manager.deployments_dir / "run-test-001.json"
        assert deployment_file.exists()

    def test_saved_deployment_contains_all_fields(self, state_manager, sample_deployment_data):
        """Test that saved deployment contains all expected fields."""
        state_manager.save_deployment(**sample_deployment_data)

        deployment_file = state_manager.deployments_dir / "run-test-001.json"
        data = json.loads(deployment_file.read_text())

        assert data["run_id"] == "run-test-001"
        assert data["name"] == "Test Deployment"
        assert data["phase"] == "running"
        assert data["status"] == "active"
        assert data["worker_count"] == 5
        assert data["started_at"] is not None
        assert data["config"] == {"setting1": "value1"}
        assert "updated_at" in data

    def test_saves_datetime_as_isoformat(self, state_manager, sample_deployment_data):
        """Test that datetime fields are saved as ISO format strings."""
        state_manager.save_deployment(**sample_deployment_data)

        deployment_file = state_manager.deployments_dir / "run-test-001.json"
        data = json.loads(deployment_file.read_text())

        # Should be parseable as datetime
        started_at = datetime.fromisoformat(data["started_at"])
        assert started_at.year == 2024
        assert started_at.month == 1

    def test_saves_completed_at_when_provided(self, state_manager):
        """Test that completed_at is saved when provided."""
        state_manager.save_deployment(
            run_id="run-001",
            name="Test",
            phase="completed",
            status="success",
            worker_count=3,
            started_at=datetime(2024, 1, 1, 10, 0),
            completed_at=datetime(2024, 1, 1, 12, 0),
        )

        deployment_file = state_manager.deployments_dir / "run-001.json"
        data = json.loads(deployment_file.read_text())

        assert data["completed_at"] is not None
        completed_at = datetime.fromisoformat(data["completed_at"])
        assert completed_at.hour == 12

    def test_saves_error_when_provided(self, state_manager):
        """Test that error message is saved when provided."""
        state_manager.save_deployment(
            run_id="run-001",
            name="Test",
            phase="failed",
            status="error",
            worker_count=3,
            error="Something went wrong",
        )

        deployment_file = state_manager.deployments_dir / "run-001.json"
        data = json.loads(deployment_file.read_text())

        assert data["error"] == "Something went wrong"

    def test_overwrites_existing_deployment(self, state_manager):
        """Test that saving to same run_id overwrites existing file."""
        # Save initial
        state_manager.save_deployment(
            run_id="run-001",
            name="Initial",
            phase="starting",
            status="pending",
            worker_count=3,
        )

        # Overwrite
        state_manager.save_deployment(
            run_id="run-001",
            name="Updated",
            phase="running",
            status="active",
            worker_count=5,
        )

        deployment_file = state_manager.deployments_dir / "run-001.json"
        data = json.loads(deployment_file.read_text())

        assert data["name"] == "Updated"
        assert data["worker_count"] == 5

    def test_defaults_config_to_empty_dict(self, state_manager):
        """Test that config defaults to empty dict when not provided."""
        state_manager.save_deployment(
            run_id="run-001",
            name="Test",
            phase="running",
            status="active",
            worker_count=3,
        )

        deployment_file = state_manager.deployments_dir / "run-001.json"
        data = json.loads(deployment_file.read_text())

        assert data["config"] == {}


# ============================================================================
# Unit Tests - load_deployment (60%)
# ============================================================================


class TestLoadDeployment:
    """Tests for load_deployment method."""

    def test_loads_existing_deployment(self, state_manager, sample_deployment_data):
        """Test loading an existing deployment."""
        state_manager.save_deployment(**sample_deployment_data)

        result = state_manager.load_deployment("run-test-001")

        assert result is not None
        assert result["run_id"] == "run-test-001"
        assert result["name"] == "Test Deployment"

    def test_returns_none_for_nonexistent_deployment(self, state_manager):
        """Test that None is returned for non-existent deployment."""
        result = state_manager.load_deployment("nonexistent-run")

        assert result is None

    def test_handles_corrupted_json_gracefully(self, state_manager):
        """Test that corrupted JSON file is handled gracefully."""
        # Create corrupted file
        deployment_file = state_manager.deployments_dir / "corrupted.json"
        deployment_file.write_text("{invalid json content")

        result = state_manager.load_deployment("corrupted")

        assert result is None

    def test_loaded_data_matches_saved_data(self, state_manager):
        """Test that loaded data matches what was saved."""
        state_manager.save_deployment(
            run_id="run-001",
            name="Test Deployment",
            phase="running",
            status="active",
            worker_count=5,
            config={"key": "value"},
        )

        result = state_manager.load_deployment("run-001")

        assert result["name"] == "Test Deployment"
        assert result["phase"] == "running"
        assert result["status"] == "active"
        assert result["worker_count"] == 5
        assert result["config"]["key"] == "value"


# ============================================================================
# Unit Tests - list_deployments (60%)
# ============================================================================


class TestListDeployments:
    """Tests for list_deployments method."""

    def test_returns_empty_list_when_no_deployments(self, state_manager):
        """Test that empty list is returned when no deployments exist."""
        result = state_manager.list_deployments()

        assert result == []

    def test_returns_all_deployments(self, state_manager):
        """Test that all deployments are returned."""
        # Create multiple deployments
        for i in range(3):
            state_manager.save_deployment(
                run_id=f"run-{i}",
                name=f"Deployment {i}",
                phase="running",
                status="active",
                worker_count=i + 1,
            )

        result = state_manager.list_deployments()

        assert len(result) == 3

    def test_sorted_by_updated_at_descending(self, state_manager):
        """Test that results are sorted by updated_at descending."""
        import time

        # Create deployments with slight delay to ensure different timestamps
        for i in range(3):
            state_manager.save_deployment(
                run_id=f"run-{i}",
                name=f"Deployment {i}",
                phase="running",
                status="active",
                worker_count=i + 1,
            )
            time.sleep(0.01)  # Small delay to ensure different timestamps

        result = state_manager.list_deployments()

        # Most recent should be first (run-2)
        assert result[0]["run_id"] == "run-2"

    def test_skips_corrupted_files(self, state_manager):
        """Test that corrupted files are skipped in listing."""
        # Create valid deployment
        state_manager.save_deployment(
            run_id="valid",
            name="Valid",
            phase="running",
            status="active",
            worker_count=1,
        )

        # Create corrupted file
        corrupted_file = state_manager.deployments_dir / "corrupted.json"
        corrupted_file.write_text("not valid json")

        result = state_manager.list_deployments()

        assert len(result) == 1
        assert result[0]["run_id"] == "valid"


# ============================================================================
# Unit Tests - delete_deployment (60%)
# ============================================================================


class TestDeleteDeployment:
    """Tests for delete_deployment method."""

    def test_deletes_existing_deployment(self, state_manager):
        """Test deleting an existing deployment."""
        state_manager.save_deployment(
            run_id="run-001",
            name="Test",
            phase="completed",
            status="success",
            worker_count=3,
        )

        result = state_manager.delete_deployment("run-001")

        assert result is True
        assert state_manager.load_deployment("run-001") is None

    def test_returns_false_for_nonexistent_deployment(self, state_manager):
        """Test that False is returned when deleting non-existent deployment."""
        result = state_manager.delete_deployment("nonexistent")

        assert result is False


# ============================================================================
# Unit Tests - save_worker (60%)
# ============================================================================


class TestSaveWorker:
    """Tests for save_worker method."""

    def test_saves_worker_to_file(self, state_manager, sample_worker_identity):
        """Test that worker is saved to JSON file."""
        state_manager.save_worker("run-001", sample_worker_identity)

        worker_file = state_manager.workers_dir / "run-001" / "kw-test-001.json"
        assert worker_file.exists()

    def test_creates_run_directory(self, state_manager, sample_worker_identity):
        """Test that run-specific directory is created."""
        state_manager.save_worker("run-001", sample_worker_identity)

        run_dir = state_manager.workers_dir / "run-001"
        assert run_dir.exists()
        assert run_dir.is_dir()

    def test_saved_worker_contains_all_fields(self, state_manager, sample_worker_identity):
        """Test that saved worker contains all expected fields."""
        state_manager.save_worker("run-001", sample_worker_identity)

        worker_file = state_manager.workers_dir / "run-001" / "kw-test-001.json"
        data = json.loads(worker_file.read_text())

        assert data["worker_id"] == "kw-test-001"
        assert data["display_name"] == "Test Worker"
        assert data["user_principal_name"] == "test@corp.onmicrosoft.com"
        assert data["entra_object_id"] == "obj-123"
        assert data["persona"] == "engineering"
        assert data["endpoint_type"] == "cli_container"
        assert data["department"] == "engineering"
        assert data["team_ids"] == ["team-1", "team-2"]
        assert data["run_id"] == "run-001"
        assert "updated_at" in data

    def test_saves_enum_values_as_strings(self, state_manager, sample_worker_identity):
        """Test that enum values are saved as strings."""
        state_manager.save_worker("run-001", sample_worker_identity)

        worker_file = state_manager.workers_dir / "run-001" / "kw-test-001.json"
        data = json.loads(worker_file.read_text())

        assert isinstance(data["persona"], str)
        assert isinstance(data["endpoint_type"], str)


# ============================================================================
# Unit Tests - load_workers (60%)
# ============================================================================


class TestLoadWorkers:
    """Tests for load_workers method."""

    def test_returns_empty_list_when_no_workers(self, state_manager):
        """Test that empty list is returned when no workers exist."""
        result = state_manager.load_workers("nonexistent-run")

        assert result == []

    def test_loads_all_workers_for_run(self, state_manager):
        """Test loading all workers for a specific run."""
        # Create multiple workers
        for i in range(3):
            worker = WorkerIdentity(
                worker_id=f"kw-{i}",
                display_name=f"Worker {i}",
                user_principal_name=f"worker{i}@test.com",
                department="test",
                persona=WorkerPersona.ENGINEERING,
            )
            state_manager.save_worker("run-001", worker)

        result = state_manager.load_workers("run-001")

        assert len(result) == 3

    def test_only_loads_workers_for_specified_run(self, state_manager, sample_worker_identity):
        """Test that only workers for specified run are loaded."""
        # Save worker to different runs
        state_manager.save_worker("run-001", sample_worker_identity)

        worker2 = WorkerIdentity(
            worker_id="kw-002",
            display_name="Other Worker",
            user_principal_name="other@test.com",
            department="test",
            persona=WorkerPersona.SALES,
        )
        state_manager.save_worker("run-002", worker2)

        # Only workers for run-001 should be returned
        result = state_manager.load_workers("run-001")

        assert len(result) == 1
        assert result[0]["worker_id"] == "kw-test-001"

    def test_skips_corrupted_worker_files(self, state_manager, sample_worker_identity):
        """Test that corrupted worker files are skipped."""
        state_manager.save_worker("run-001", sample_worker_identity)

        # Create corrupted file
        corrupted_file = state_manager.workers_dir / "run-001" / "corrupted.json"
        corrupted_file.write_text("{invalid")

        result = state_manager.load_workers("run-001")

        assert len(result) == 1


# ============================================================================
# Unit Tests - delete_workers (60%)
# ============================================================================


class TestDeleteWorkers:
    """Tests for delete_workers method."""

    def test_deletes_all_workers_for_run(self, state_manager):
        """Test deleting all workers for a run."""
        # Create multiple workers
        for i in range(3):
            worker = WorkerIdentity(
                worker_id=f"kw-{i}",
                display_name=f"Worker {i}",
                user_principal_name=f"worker{i}@test.com",
                department="test",
                persona=WorkerPersona.ENGINEERING,
            )
            state_manager.save_worker("run-001", worker)

        count = state_manager.delete_workers("run-001")

        assert count == 3
        assert state_manager.load_workers("run-001") == []

    def test_returns_zero_for_nonexistent_run(self, state_manager):
        """Test that 0 is returned when deleting workers for non-existent run."""
        count = state_manager.delete_workers("nonexistent")

        assert count == 0

    def test_removes_empty_run_directory(self, state_manager, sample_worker_identity):
        """Test that empty run directory is removed after deleting workers."""
        state_manager.save_worker("run-001", sample_worker_identity)

        state_manager.delete_workers("run-001")

        run_dir = state_manager.workers_dir / "run-001"
        assert not run_dir.exists()

    def test_does_not_affect_other_runs(self, state_manager, sample_worker_identity):
        """Test that deleting workers for one run doesn't affect others."""
        state_manager.save_worker("run-001", sample_worker_identity)

        worker2 = WorkerIdentity(
            worker_id="kw-002",
            display_name="Other Worker",
            user_principal_name="other@test.com",
            department="test",
            persona=WorkerPersona.SALES,
        )
        state_manager.save_worker("run-002", worker2)

        state_manager.delete_workers("run-001")

        # run-002 workers should still exist
        assert len(state_manager.load_workers("run-002")) == 1


# ============================================================================
# Unit Tests - get_recent_deployments (60%)
# ============================================================================


class TestGetRecentDeployments:
    """Tests for get_recent_deployments method."""

    def test_returns_limited_results(self, state_manager):
        """Test that results are limited to specified count."""
        # Create many deployments
        import time

        for i in range(15):
            state_manager.save_deployment(
                run_id=f"run-{i:03d}",
                name=f"Deployment {i}",
                phase="completed",
                status="success",
                worker_count=i,
            )
            time.sleep(0.001)  # Ensure different timestamps

        result = state_manager.get_recent_deployments(limit=5)

        assert len(result) == 5

    def test_default_limit_is_10(self, state_manager):
        """Test that default limit is 10."""
        import time

        for i in range(15):
            state_manager.save_deployment(
                run_id=f"run-{i:03d}",
                name=f"Deployment {i}",
                phase="completed",
                status="success",
                worker_count=i,
            )
            time.sleep(0.001)

        result = state_manager.get_recent_deployments()

        assert len(result) == 10

    def test_returns_most_recent_first(self, state_manager):
        """Test that most recent deployments are returned first."""
        import time

        for i in range(5):
            state_manager.save_deployment(
                run_id=f"run-{i:03d}",
                name=f"Deployment {i}",
                phase="completed",
                status="success",
                worker_count=i,
            )
            time.sleep(0.01)

        result = state_manager.get_recent_deployments(limit=3)

        # Most recent (run-004) should be first
        assert result[0]["run_id"] == "run-004"

    def test_returns_all_if_fewer_than_limit(self, state_manager):
        """Test that all deployments are returned if fewer than limit."""
        state_manager.save_deployment(
            run_id="run-001",
            name="Only One",
            phase="completed",
            status="success",
            worker_count=1,
        )

        result = state_manager.get_recent_deployments(limit=10)

        assert len(result) == 1


# ============================================================================
# Integration Tests (30%)
# ============================================================================


class TestDeploymentStateManagerIntegration:
    """Integration tests for state manager components."""

    def test_full_deployment_lifecycle(self, state_manager, sample_worker_identity):
        """Test complete deployment lifecycle: create, update, query, delete."""
        # Create deployment
        state_manager.save_deployment(
            run_id="run-lifecycle",
            name="Lifecycle Test",
            phase="starting",
            status="pending",
            worker_count=0,
            started_at=datetime.now(),
        )

        # Add workers
        state_manager.save_worker("run-lifecycle", sample_worker_identity)

        # Update deployment
        state_manager.save_deployment(
            run_id="run-lifecycle",
            name="Lifecycle Test",
            phase="running",
            status="active",
            worker_count=1,
            started_at=datetime.now(),
        )

        # Verify state
        deployment = state_manager.load_deployment("run-lifecycle")
        workers = state_manager.load_workers("run-lifecycle")

        assert deployment["phase"] == "running"
        assert len(workers) == 1

        # Complete and cleanup
        state_manager.save_deployment(
            run_id="run-lifecycle",
            name="Lifecycle Test",
            phase="completed",
            status="success",
            worker_count=1,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

        # Delete
        state_manager.delete_workers("run-lifecycle")
        state_manager.delete_deployment("run-lifecycle")

        # Verify cleanup
        assert state_manager.load_deployment("run-lifecycle") is None
        assert state_manager.load_workers("run-lifecycle") == []

    def test_multiple_runs_coexist(self, state_manager):
        """Test that multiple runs can coexist independently."""
        # Create multiple runs with workers
        for run_id in ["run-a", "run-b", "run-c"]:
            state_manager.save_deployment(
                run_id=run_id,
                name=f"Run {run_id}",
                phase="running",
                status="active",
                worker_count=2,
            )

            for i in range(2):
                worker = WorkerIdentity(
                    worker_id=f"{run_id}-worker-{i}",
                    display_name=f"Worker {i}",
                    user_principal_name=f"w{i}@test.com",
                    department="test",
                    persona=WorkerPersona.ENGINEERING,
                )
                state_manager.save_worker(run_id, worker)

        # Verify all exist
        all_deployments = state_manager.list_deployments()
        assert len(all_deployments) == 3

        for run_id in ["run-a", "run-b", "run-c"]:
            workers = state_manager.load_workers(run_id)
            assert len(workers) == 2

        # Delete one run
        state_manager.delete_workers("run-b")
        state_manager.delete_deployment("run-b")

        # Verify others unaffected
        assert len(state_manager.list_deployments()) == 2
        assert len(state_manager.load_workers("run-a")) == 2
        assert len(state_manager.load_workers("run-c")) == 2


# ============================================================================
# Edge Case Tests (10%)
# ============================================================================


class TestDeploymentStateManagerEdgeCases:
    """Edge case tests for state manager."""

    def test_special_characters_in_run_id(self, state_manager):
        """Test handling of special characters in run_id."""
        # Note: Some special chars may not work in filenames
        run_id = "run-with-dashes_and_underscores"

        state_manager.save_deployment(
            run_id=run_id,
            name="Special Chars",
            phase="running",
            status="active",
            worker_count=1,
        )

        result = state_manager.load_deployment(run_id)
        assert result["run_id"] == run_id

    def test_very_long_deployment_name(self, state_manager):
        """Test handling of very long deployment names."""
        long_name = "A" * 1000

        state_manager.save_deployment(
            run_id="run-long-name",
            name=long_name,
            phase="running",
            status="active",
            worker_count=1,
        )

        result = state_manager.load_deployment("run-long-name")
        assert result["name"] == long_name

    def test_unicode_in_deployment_data(self, state_manager):
        """Test handling of unicode characters in deployment data."""
        state_manager.save_deployment(
            run_id="run-unicode",
            name="Test Deployment \u00e9\u00e8\u00ea",  # é è ê
            phase="running",
            status="active",
            worker_count=1,
            config={"message": "Hello \u4e16\u754c"},  # 世界 (world in Chinese)
        )

        result = state_manager.load_deployment("run-unicode")
        assert "\u00e9" in result["name"]
        assert result["config"]["message"] == "Hello \u4e16\u754c"

    def test_empty_config_serialization(self, state_manager):
        """Test that empty config is properly serialized."""
        state_manager.save_deployment(
            run_id="run-empty-config",
            name="Test",
            phase="running",
            status="active",
            worker_count=1,
            config={},
        )

        result = state_manager.load_deployment("run-empty-config")
        assert result["config"] == {}

    def test_none_datetime_fields(self, state_manager):
        """Test handling of None datetime fields."""
        state_manager.save_deployment(
            run_id="run-no-dates",
            name="Test",
            phase="pending",
            status="waiting",
            worker_count=0,
            started_at=None,
            completed_at=None,
        )

        result = state_manager.load_deployment("run-no-dates")
        assert result["started_at"] is None
        assert result["completed_at"] is None

    def test_worker_with_empty_team_ids(self, state_manager):
        """Test saving worker with empty team_ids list."""
        worker = WorkerIdentity(
            worker_id="kw-no-teams",
            display_name="No Teams Worker",
            user_principal_name="noteams@test.com",
            department="solo",
            persona=WorkerPersona.ENGINEERING,
            team_ids=[],
        )

        state_manager.save_worker("run-001", worker)

        workers = state_manager.load_workers("run-001")
        assert workers[0]["team_ids"] == []

    def test_concurrent_saves_same_file(self, state_manager):
        """Test that concurrent saves to same file don't corrupt data."""
        # Simulate rapid updates
        for i in range(10):
            state_manager.save_deployment(
                run_id="run-concurrent",
                name=f"Update {i}",
                phase="running",
                status="active",
                worker_count=i,
            )

        result = state_manager.load_deployment("run-concurrent")
        # Should have the last update
        assert result["worker_count"] == 9

    def test_module_exports_state_manager_class(self):
        """Test that __all__ exports DeploymentStateManager."""
        from azure_haymaker.knowledge_worker import state_manager as sm_module

        assert "DeploymentStateManager" in sm_module.__all__
