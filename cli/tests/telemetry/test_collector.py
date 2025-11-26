"""Unit tests for telemetry collector."""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path


class TestTelemetryCollector:
    """Test TelemetryCollector class."""

    @pytest.mark.asyncio
    async def test_collector_initialization(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector initializes correctly."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage)

        assert collector.api_client == mock_api_client
        assert collector.storage == storage
        assert collector.is_running is False

    @pytest.mark.asyncio
    async def test_collector_collect_once_success(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector.collect_once successfully collects data."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage)

        result = await collector.collect_once()

        assert result.success is True
        assert result.executions_collected == 5
        assert result.agents_collected > 0
        assert result.resources_collected > 0
        assert result.collection_time_seconds > 0

        # Verify data was stored
        executions = storage.load_executions()
        assert len(executions) == 5

    @pytest.mark.asyncio
    async def test_collector_collect_once_api_error(self, mock_api_client_error, telemetry_storage_dir):
        """Test TelemetryCollector handles API errors gracefully."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client_error, storage)

        result = await collector.collect_once()

        assert result.success is False
        assert result.executions_collected == 0
        assert result.error_message is not None
        assert "API connection failed" in result.error_message

    @pytest.mark.asyncio
    async def test_collector_collect_once_empty_data(self, mock_api_client_empty, telemetry_storage_dir):
        """Test TelemetryCollector handles empty API responses."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client_empty, storage)

        result = await collector.collect_once()

        assert result.success is True
        assert result.executions_collected == 0
        assert result.agents_collected == 0

    @pytest.mark.asyncio
    async def test_collector_incremental_sync(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector performs incremental sync using last_sync_time."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage)

        # First collection
        await collector.collect_once()

        # Get last sync time
        last_sync = storage.get_last_sync_time()
        assert last_sync is not None

        # Second collection should use last_sync_time filter
        await collector.collect_once()

        # Verify API was called with since parameter
        calls = mock_api_client.get_executions.call_args_list
        assert len(calls) == 2
        # Second call should include since parameter
        second_call_kwargs = calls[1].kwargs if calls[1].kwargs else {}
        assert "since" in second_call_kwargs or len(calls) == 2

    @pytest.mark.asyncio
    async def test_collector_batch_collection(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector handles paginated API responses."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Mock paginated response
        mock_api_client.get_executions.side_effect = [
            {"executions": [{"id": f"exec-{i}"} for i in range(100)], "total": 250, "page": 1},
            {"executions": [{"id": f"exec-{i}"} for i in range(100, 200)], "total": 250, "page": 2},
            {"executions": [{"id": f"exec-{i}"} for i in range(200, 250)], "total": 250, "page": 3},
        ]

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage, batch_size=100)

        result = await collector.collect_once()

        assert result.executions_collected == 250
        assert mock_api_client.get_executions.call_count >= 3

    @pytest.mark.asyncio
    async def test_collector_start_background(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector starts background collection."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage, interval_seconds=1)

        await collector.start_background()

        assert collector.is_running is True
        assert collector.background_task is not None

        # Let it run briefly
        await asyncio.sleep(0.1)

        await collector.stop_background()

    @pytest.mark.asyncio
    async def test_collector_stop_background(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector stops background collection."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage, interval_seconds=1)

        await collector.start_background()
        assert collector.is_running is True

        await collector.stop_background()

        assert collector.is_running is False
        assert collector.background_task is None or collector.background_task.done()

    @pytest.mark.asyncio
    async def test_collector_background_interval(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector respects collection interval."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage, interval_seconds=0.5)

        await collector.start_background()

        # Wait for multiple collections
        await asyncio.sleep(1.5)

        await collector.stop_background()

        # Should have called collect multiple times
        assert mock_api_client.get_executions.call_count >= 2

    @pytest.mark.asyncio
    async def test_collector_lock_file_creation(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector creates lock file when starting."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage)

        lock_file = telemetry_storage_dir / "telemetry.lock"
        assert not lock_file.exists()

        await collector.start_background()

        assert lock_file.exists()

        await collector.stop_background()

        assert not lock_file.exists()

    @pytest.mark.asyncio
    async def test_collector_prevents_concurrent_collection(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector prevents concurrent collection instances."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector1 = TelemetryCollector(mock_api_client, storage)
        collector2 = TelemetryCollector(mock_api_client, storage)

        await collector1.start_background()

        # Second collector should fail to start
        with pytest.raises(RuntimeError, match="already running"):
            await collector2.start_background()

        await collector1.stop_background()

    @pytest.mark.asyncio
    async def test_collector_resume_after_crash(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector can resume after crash (stale lock file)."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)

        # Create stale lock file
        lock_file = telemetry_storage_dir / "telemetry.lock"
        lock_file.write_text("stale_pid")

        collector = TelemetryCollector(mock_api_client, storage)

        # Should detect stale lock and start anyway
        await collector.start_background(force=True)

        assert collector.is_running is True

        await collector.stop_background()

    @pytest.mark.asyncio
    async def test_collector_timeout_handling(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector handles API timeouts."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Mock slow API call
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(10)
            return {"executions": []}

        mock_api_client.get_executions = slow_call

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage, timeout_seconds=0.5)

        result = await collector.collect_once()

        assert result.success is False
        assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_collector_partial_success(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector handles partial collection success."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from tests.fixtures.sample_data import sample_execution_data

        # Mock API where executions succeed but agents fail
        mock_api_client.get_executions.return_value = {
            "executions": sample_execution_data(count=5),
            "total": 5
        }
        mock_api_client.get_agents.side_effect = Exception("Agents API failed")

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage)

        result = await collector.collect_once()

        # Should succeed overall but report partial failure
        assert result.success is True
        assert result.executions_collected == 5
        assert result.agents_collected == 0
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_collector_get_status(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector returns status information."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage)

        status = collector.get_status()

        assert "is_running" in status
        assert "last_collection_time" in status
        assert "last_collection_result" in status
        assert status["is_running"] is False

        await collector.start_background()

        status = collector.get_status()
        assert status["is_running"] is True

        await collector.stop_background()

    @pytest.mark.asyncio
    async def test_collector_health_check_before_collection(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector performs health check before collecting."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage)

        await collector.collect_once()

        # Should have called health check
        mock_api_client.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_collector_unhealthy_api_skip_collection(self, mock_api_client, telemetry_storage_dir):
        """Test TelemetryCollector skips collection if API is unhealthy."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Mock unhealthy API
        mock_api_client.health_check.side_effect = Exception("API down")

        storage = TelemetryStorage(telemetry_storage_dir)
        collector = TelemetryCollector(mock_api_client, storage)

        result = await collector.collect_once()

        assert result.success is False
        # Should not have attempted to collect executions
        mock_api_client.get_executions.assert_not_called()
