"""Unit tests for scenario models."""

from datetime import UTC, datetime

from azure_haymaker.models.scenario import (
    ScenarioMetadata,
    ScenarioStatus,
)


class TestScenarioStatus:
    """Tests for ScenarioStatus enum."""

    def test_scenario_status_values(self) -> None:
        """Test that scenario status enum has expected values."""
        assert ScenarioStatus.PENDING == "pending"
        assert ScenarioStatus.RUNNING == "running"
        assert ScenarioStatus.COMPLETED == "completed"
        assert ScenarioStatus.FAILED == "failed"
        assert ScenarioStatus.CLEANUP_COMPLETE == "cleanup_complete"


class TestScenarioMetadata:
    """Tests for ScenarioMetadata model."""

    def test_scenario_metadata_valid(self) -> None:
        """Test valid scenario metadata creation."""
        metadata = ScenarioMetadata(
            scenario_name="ai-ml-01-cognitive-services-vision",
            scenario_doc_path="scenarios/ai-ml/01-cognitive-services-vision.md",
            agent_path="agents/ai_ml_cognitive_services_vision.py",
            technology_area="AI/ML",
        )

        assert metadata.scenario_name == "ai-ml-01-cognitive-services-vision"
        assert metadata.technology_area == "AI/ML"
        assert metadata.status == ScenarioStatus.PENDING
        assert metadata.started_at is None
        assert metadata.ended_at is None

    def test_scenario_metadata_with_status(self) -> None:
        """Test scenario metadata with custom status."""
        now = datetime.now(UTC)
        metadata = ScenarioMetadata(
            scenario_name="networking-02-vnet-peering",
            scenario_doc_path="scenarios/networking/02-vnet-peering.md",
            agent_path="agents/networking_vnet_peering.py",
            technology_area="Networking",
            status=ScenarioStatus.RUNNING,
            started_at=now,
        )

        assert metadata.status == ScenarioStatus.RUNNING
        assert metadata.started_at == now

    def test_scenario_duration_property(self) -> None:
        """Test duration calculation."""
        start = datetime(2025, 11, 14, 12, 0, 0, tzinfo=UTC)
        end = datetime(2025, 11, 14, 20, 0, 0, tzinfo=UTC)

        metadata = ScenarioMetadata(
            scenario_name="storage-01-blob-storage",
            scenario_doc_path="scenarios/storage/01-blob-storage.md",
            agent_path="agents/storage_blob.py",
            technology_area="Storage",
            status=ScenarioStatus.COMPLETED,
            started_at=start,
            ended_at=end,
        )

        assert metadata.duration_seconds == 8 * 3600  # 8 hours

    def test_scenario_duration_none_when_not_ended(self) -> None:
        """Test that duration is None when scenario hasn't ended."""
        metadata = ScenarioMetadata(
            scenario_name="compute-01-vm",
            scenario_doc_path="scenarios/compute/01-vm.md",
            agent_path="agents/compute_vm.py",
            technology_area="Compute",
            status=ScenarioStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

        assert metadata.duration_seconds is None

    def test_scenario_update_status(self) -> None:
        """Test updating scenario status."""
        metadata = ScenarioMetadata(
            scenario_name="database-01-sql",
            scenario_doc_path="scenarios/database/01-sql.md",
            agent_path="agents/database_sql.py",
            technology_area="Database",
        )

        # Start the scenario
        start_time = datetime.now(UTC)
        metadata.status = ScenarioStatus.RUNNING
        metadata.started_at = start_time

        assert metadata.status == ScenarioStatus.RUNNING
        assert metadata.started_at == start_time

        # Complete the scenario
        end_time = datetime.now(UTC)
        metadata.status = ScenarioStatus.COMPLETED
        metadata.ended_at = end_time

        assert metadata.status == ScenarioStatus.COMPLETED
        assert metadata.ended_at == end_time
