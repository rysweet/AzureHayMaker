"""Unit tests for telemetry storage."""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path

from tests.fixtures.sample_data import (
    sample_execution_data,
    sample_agent_data,
    sample_resource_data
)


class TestTelemetryStorage:
    """Test TelemetryStorage class."""

    def test_storage_initialization(self, telemetry_storage_dir):
        """Test TelemetryStorage initializes correctly."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        assert storage.storage_path == telemetry_storage_dir
        assert storage.storage_path.exists()

    def test_storage_creates_directory(self, tmp_path):
        """Test TelemetryStorage creates directory if not exists."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        new_dir = tmp_path / "new_telemetry"
        assert not new_dir.exists()

        storage = TelemetryStorage(new_dir)

        assert new_dir.exists()

    def test_storage_save_executions(self, telemetry_storage_dir):
        """Test TelemetryStorage saves execution records."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        executions = sample_execution_data(count=5)

        storage.save_executions(executions)

        executions_file = telemetry_storage_dir / "executions.jsonl"
        assert executions_file.exists()

        with open(executions_file) as f:
            lines = f.readlines()
            assert len(lines) == 5

    def test_storage_load_executions(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage loads execution records."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        executions = storage.load_executions()

        assert len(executions) == 10  # From fixture
        assert executions[0]["id"] == "exec-001"

    def test_storage_load_executions_with_filter(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage filters executions by criteria."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        # Filter by status
        completed = storage.load_executions(filters={"status": "completed"})
        assert all(e["status"] == "completed" for e in completed)

        # Filter by scenario
        scenario_1 = storage.load_executions(filters={"scenario_id": "scenario-1"})
        assert all(e["scenario_id"] == "scenario-1" for e in scenario_1)

    def test_storage_load_executions_date_range(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage filters executions by date range."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()

        executions = storage.load_executions(
            filters={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        assert len(executions) > 0

    def test_storage_save_agents(self, telemetry_storage_dir):
        """Test TelemetryStorage saves agent records."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        agents = sample_agent_data("exec-001", count=10)

        storage.save_agents(agents)

        agents_file = telemetry_storage_dir / "agents.jsonl"
        assert agents_file.exists()

        with open(agents_file) as f:
            lines = f.readlines()
            assert len(lines) == 10

    def test_storage_load_agents(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage loads agent records."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        agents = storage.load_agents()

        assert len(agents) == 20  # From fixture
        assert agents[0]["execution_id"] == "exec-001"

    def test_storage_load_agents_by_execution(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage filters agents by execution ID."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        agents = storage.load_agents(filters={"execution_id": "exec-001"})

        assert len(agents) > 0
        assert all(a["execution_id"] == "exec-001" for a in agents)

    def test_storage_save_resources(self, telemetry_storage_dir):
        """Test TelemetryStorage saves resource records."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        resources = sample_resource_data("exec-001", count=15)

        storage.save_resources(resources)

        resources_file = telemetry_storage_dir / "resources.jsonl"
        assert resources_file.exists()

        with open(resources_file) as f:
            lines = f.readlines()
            assert len(lines) == 15

    def test_storage_load_resources(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage loads resource records."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        resources = storage.load_resources()

        assert len(resources) == 30  # From fixture

    def test_storage_append_mode(self, telemetry_storage_dir):
        """Test TelemetryStorage appends to existing files."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        # Save first batch
        executions_1 = sample_execution_data(count=5)
        storage.save_executions(executions_1)

        # Save second batch
        executions_2 = sample_execution_data(count=3)
        storage.save_executions(executions_2)

        # Load all
        all_executions = storage.load_executions()
        assert len(all_executions) == 8

    def test_storage_handles_corrupted_lines(self, telemetry_storage_dir, corrupted_telemetry_file):
        """Test TelemetryStorage handles corrupted JSON lines gracefully."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        # Should skip corrupted lines and load valid ones
        executions = storage.load_executions()

        assert len(executions) == 2  # Only valid lines

    def test_storage_empty_file(self, telemetry_storage_dir):
        """Test TelemetryStorage handles empty files."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        executions = storage.load_executions()

        assert executions == []

    def test_storage_nonexistent_file(self, telemetry_storage_dir):
        """Test TelemetryStorage handles nonexistent files."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        executions = storage.load_executions()

        assert executions == []

    def test_storage_get_date_range(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage returns date range of stored data."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        date_range = storage.get_date_range()

        assert "earliest" in date_range
        assert "latest" in date_range
        assert date_range["earliest"] is not None
        assert date_range["latest"] is not None

    def test_storage_get_last_sync_time(self, telemetry_storage_dir):
        """Test TelemetryStorage tracks last sync timestamp."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        # First sync - should be None
        last_sync = storage.get_last_sync_time()
        assert last_sync is None

        # Update sync time
        now = datetime.utcnow()
        storage.set_last_sync_time(now)

        # Retrieve sync time
        last_sync = storage.get_last_sync_time()
        assert last_sync is not None
        assert isinstance(last_sync, datetime)

    def test_storage_prune_old_data(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage prunes data older than retention period."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        # Prune data older than 7 days
        retention_days = 7
        pruned_count = storage.prune_old_data(retention_days)

        assert isinstance(pruned_count, dict)
        assert "executions" in pruned_count
        assert "agents" in pruned_count
        assert "resources" in pruned_count

    def test_storage_get_file_size(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage reports file sizes."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        file_sizes = storage.get_file_sizes()

        assert "executions" in file_sizes
        assert "agents" in file_sizes
        assert "resources" in file_sizes
        assert file_sizes["executions"] > 0

    def test_storage_compress_files(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage compresses old files."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        compressed = storage.compress_old_files(days_old=0)

        assert isinstance(compressed, list)
        # Should create .gz files

    def test_storage_vacuum(self, telemetry_storage_dir, sample_telemetry_files):
        """Test TelemetryStorage vacuum operation (optimize storage)."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        # Vacuum should remove duplicates and compact files
        result = storage.vacuum()

        assert result["success"] is True
        assert "records_removed" in result

    def test_storage_export_to_json(self, telemetry_storage_dir, sample_telemetry_files, tmp_path):
        """Test TelemetryStorage exports data to JSON file."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        export_file = tmp_path / "export.json"
        storage.export_to_json(export_file)

        assert export_file.exists()

        with open(export_file) as f:
            data = json.load(f)
            assert "executions" in data
            assert len(data["executions"]) > 0

    def test_storage_import_from_json(self, telemetry_storage_dir, tmp_path):
        """Test TelemetryStorage imports data from JSON file."""
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Create export file
        export_data = {
            "executions": sample_execution_data(count=5),
            "agents": sample_agent_data("exec-001", count=10),
            "resources": sample_resource_data("exec-001", count=15)
        }

        export_file = tmp_path / "import.json"
        with open(export_file, "w") as f:
            json.dump(export_data, f)

        # Import
        storage = TelemetryStorage(telemetry_storage_dir)
        storage.import_from_json(export_file)

        # Verify
        executions = storage.load_executions()
        assert len(executions) == 5
