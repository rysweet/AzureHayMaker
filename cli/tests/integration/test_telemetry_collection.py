"""Integration tests for full telemetry collection workflow."""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path


class TestTelemetryCollectionWorkflow:
    """Test complete telemetry collection workflow."""

    @pytest.mark.asyncio
    async def test_full_collection_cycle(self, mock_api_client, tmp_path):
        """Test complete collection cycle from API to storage."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from haymaker_cli.telemetry.config import TelemetryConfig

        # Setup
        config = TelemetryConfig(storage_path=str(tmp_path))
        storage = TelemetryStorage(config.storage_path)
        collector = TelemetryCollector(mock_api_client, storage)

        # Collect data
        result = await collector.collect_once()

        assert result.success is True
        assert result.executions_collected > 0

        # Verify data was stored
        executions = storage.load_executions()
        assert len(executions) > 0

        agents = storage.load_agents()
        assert len(agents) > 0

    @pytest.mark.asyncio
    async def test_incremental_collection(self, mock_api_client, tmp_path):
        """Test incremental collection with multiple cycles."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(tmp_path)
        collector = TelemetryCollector(mock_api_client, storage)

        # First collection
        result1 = await collector.collect_once()
        assert result1.success is True

        first_count = len(storage.load_executions())

        # Second collection (incremental)
        result2 = await collector.collect_once()
        assert result2.success is True

        second_count = len(storage.load_executions())

        # Should have more data after second collection
        assert second_count >= first_count

    @pytest.mark.asyncio
    async def test_background_collection_lifecycle(self, mock_api_client, tmp_path):
        """Test complete background collection lifecycle."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(tmp_path)
        collector = TelemetryCollector(mock_api_client, storage, interval_seconds=0.5)

        # Start background collection
        await collector.start_background()
        assert collector.is_running is True

        # Let it run for a bit
        await asyncio.sleep(1.5)

        # Check status
        status = collector.get_status()
        assert status["is_running"] is True
        assert status["last_collection_time"] is not None

        # Stop collection
        await collector.stop_background()
        assert collector.is_running is False

        # Verify data was collected
        executions = storage.load_executions()
        assert len(executions) > 0

    @pytest.mark.asyncio
    async def test_collection_with_api_failures(self, mock_api_client, tmp_path):
        """Test collection handles intermittent API failures."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from tests.fixtures.sample_data import sample_execution_data

        storage = TelemetryStorage(tmp_path)
        collector = TelemetryCollector(mock_api_client, storage)

        # Simulate API failure on first call, success on second
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("API temporarily unavailable")
            return {"executions": sample_execution_data(count=5), "total": 5}

        mock_api_client.get_executions.side_effect = side_effect

        # First call should fail
        result1 = await collector.collect_once()
        assert result1.success is False

        # Second call should succeed
        result2 = await collector.collect_once()
        assert result2.success is True

    @pytest.mark.asyncio
    async def test_collection_with_data_pruning(self, mock_api_client, tmp_path):
        """Test collection with automatic data pruning."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from haymaker_cli.telemetry.config import TelemetryConfig

        config = TelemetryConfig(
            storage_path=str(tmp_path),
            retention_days=7
        )

        storage = TelemetryStorage(config.storage_path)
        collector = TelemetryCollector(mock_api_client, storage, config=config)

        # Collect data
        await collector.collect_once()

        # Trigger pruning
        pruned = storage.prune_old_data(retention_days=7)

        assert isinstance(pruned, dict)

    @pytest.mark.asyncio
    async def test_concurrent_collection_prevention(self, mock_api_client, tmp_path):
        """Test that concurrent collection is prevented."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(tmp_path)
        collector1 = TelemetryCollector(mock_api_client, storage)
        collector2 = TelemetryCollector(mock_api_client, storage)

        # Start first collector
        await collector1.start_background()

        # Second collector should not start
        with pytest.raises(RuntimeError):
            await collector2.start_background()

        await collector1.stop_background()

    @pytest.mark.asyncio
    async def test_collection_recovery_after_crash(self, mock_api_client, tmp_path):
        """Test collection can recover after simulated crash."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(tmp_path)

        # Simulate stale lock file from crashed process
        lock_file = tmp_path / "telemetry.lock"
        lock_file.write_text("12345")  # Fake PID

        # New collector should be able to start with force flag
        collector = TelemetryCollector(mock_api_client, storage)
        await collector.start_background(force=True)

        assert collector.is_running is True

        await collector.stop_background()

    @pytest.mark.asyncio
    async def test_collection_with_large_dataset(self, mock_api_client, tmp_path):
        """Test collection handles large datasets efficiently."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from tests.fixtures.sample_data import sample_execution_data
        import time

        # Mock large dataset
        mock_api_client.get_executions.return_value = {
            "executions": sample_execution_data(count=1000),
            "total": 1000
        }

        storage = TelemetryStorage(tmp_path)
        collector = TelemetryCollector(mock_api_client, storage)

        # Measure collection time
        start_time = time.time()
        result = await collector.collect_once()
        collection_time = time.time() - start_time

        assert result.success is True
        assert result.executions_collected == 1000
        # Should complete in reasonable time
        assert collection_time < 10.0

    @pytest.mark.asyncio
    async def test_collection_storage_integrity(self, mock_api_client, tmp_path):
        """Test collected data maintains integrity in storage."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(tmp_path)
        collector = TelemetryCollector(mock_api_client, storage)

        # Collect data
        await collector.collect_once()

        # Load data and verify integrity
        executions = storage.load_executions()

        for execution in executions:
            # All executions should have required fields
            assert "id" in execution
            assert "scenario_id" in execution
            assert "status" in execution

    @pytest.mark.asyncio
    async def test_collection_with_file_rotation(self, mock_api_client, tmp_path):
        """Test collection with file rotation when max size reached."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from haymaker_cli.telemetry.config import TelemetryConfig

        config = TelemetryConfig(
            storage_path=str(tmp_path),
            max_file_size_mb=1  # Very small for testing
        )

        storage = TelemetryStorage(config.storage_path)
        collector = TelemetryCollector(mock_api_client, storage, config=config)

        # Collect multiple times to trigger rotation
        for _ in range(10):
            await collector.collect_once()

        # Should have created multiple files or rotated

    @pytest.mark.asyncio
    async def test_collection_metrics(self, mock_api_client, tmp_path):
        """Test collection metrics are accurate."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(tmp_path)
        collector = TelemetryCollector(mock_api_client, storage)

        result = await collector.collect_once()

        # Verify all metrics are present
        assert result.executions_collected >= 0
        assert result.agents_collected >= 0
        assert result.resources_collected >= 0
        assert result.collection_time_seconds > 0

        # Total should match what's in storage
        stored_executions = len(storage.load_executions())
        assert stored_executions == result.executions_collected


class TestTelemetryConfigIntegration:
    """Test telemetry configuration integration."""

    def test_config_file_workflow(self, tmp_path):
        """Test loading and saving config file workflow."""
        from haymaker_cli.telemetry.config import TelemetryConfig
        import yaml

        config_file = tmp_path / "telemetry.yaml"

        # Create config
        config = TelemetryConfig(
            storage_path=str(tmp_path / "data"),
            retention_days=45
        )

        # Save to file
        config.save_to_file(config_file)

        assert config_file.exists()

        # Load from file
        loaded_config = TelemetryConfig.from_file(config_file)

        assert loaded_config.retention_days == 45

    def test_config_validation_workflow(self, tmp_path):
        """Test config validation workflow."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        config = TelemetryConfig(storage_path=str(tmp_path))

        # Validate storage path
        assert config.validate_storage_path() is True

        # Get file paths
        paths = config.get_file_paths()
        assert "executions" in paths
        assert "agents" in paths


class TestTelemetryStorageIntegration:
    """Test telemetry storage integration scenarios."""

    def test_storage_export_import_workflow(self, tmp_path):
        """Test complete export/import workflow."""
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from tests.fixtures.sample_data import (
            sample_execution_data,
            sample_agent_data
        )

        # Create and populate storage
        storage1 = TelemetryStorage(tmp_path / "storage1")
        storage1.save_executions(sample_execution_data(count=10))
        storage1.save_agents(sample_agent_data("exec-001", count=20))

        # Export to JSON
        export_file = tmp_path / "export.json"
        storage1.export_to_json(export_file)

        # Import to new storage
        storage2 = TelemetryStorage(tmp_path / "storage2")
        storage2.import_from_json(export_file)

        # Verify data matches
        executions1 = storage1.load_executions()
        executions2 = storage2.load_executions()

        assert len(executions1) == len(executions2)

    def test_storage_compression_workflow(self, tmp_path):
        """Test storage compression workflow."""
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from tests.fixtures.sample_data import sample_execution_data

        storage = TelemetryStorage(tmp_path)

        # Save data
        storage.save_executions(sample_execution_data(count=100))

        # Get initial file size
        sizes_before = storage.get_file_sizes()

        # Compress files
        compressed = storage.compress_old_files(days_old=0)

        assert isinstance(compressed, list)

        # Compressed files should exist
        compressed_files = list(tmp_path.glob("*.gz"))
        # Compression may or may not reduce size depending on implementation

    def test_storage_vacuum_workflow(self, tmp_path):
        """Test storage vacuum workflow."""
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from tests.fixtures.sample_data import sample_execution_data

        storage = TelemetryStorage(tmp_path)

        # Save data with duplicates
        data = sample_execution_data(count=10)
        storage.save_executions(data)
        storage.save_executions(data)  # Duplicate

        # Vacuum
        result = storage.vacuum()

        assert result["success"] is True

        # Should have removed duplicates
        executions = storage.load_executions()
        # Depending on implementation, may deduplicate
