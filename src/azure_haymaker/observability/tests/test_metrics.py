"""Tests for Application Insights custom metrics.

Testing pyramid:
- 60% Unit tests (fast, mocked)
- 30% Integration tests (meter verification)
- 10% E2E tests (App Insights connection)
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# UNIT TESTS (60%) - Fast, heavily mocked
# =============================================================================


class TestMetricsClient:
    """Unit tests for MetricsClient."""

    def test_singleton_pattern(self):
        """Verify MetricsClient follows singleton pattern."""
        from azure_haymaker.observability.metrics import get_metrics_client

        client1 = get_metrics_client()
        client2 = get_metrics_client()

        assert client1 is client2, "get_metrics_client should return same instance"

    def test_initialization_with_connection_string(self):
        """Verify MetricsClient initializes with connection string."""
        from azure_haymaker.observability.metrics import MetricsClient

        conn_string = "InstrumentationKey=test-key;IngestionEndpoint=https://test.monitor.azure.com"

        with patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": conn_string}):
            client = MetricsClient()

            assert client.is_enabled is True
            assert client._connection_string == conn_string

    def test_initialization_without_connection_string(self):
        """Verify MetricsClient gracefully handles missing connection string."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(os.environ, {}, clear=True):
            client = MetricsClient()

            assert client.is_enabled is False
            assert client._connection_string is None

    def test_record_execution_duration_success(self):
        """Verify execution duration metric is recorded correctly."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            # Mock the meter and histogram
            mock_histogram = MagicMock()
            client._execution_duration_histogram = mock_histogram

            client.record_execution_duration(
                run_id="test-run", duration_seconds=123.45, status="success"
            )

            mock_histogram.record.assert_called_once_with(
                123.45, attributes={"run_id": "test-run", "status": "success"}
            )

    def test_record_execution_duration_disabled(self):
        """Verify execution duration metric no-op when disabled."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(os.environ, {}, clear=True):
            client = MetricsClient()

            # Should not raise exception
            client.record_execution_duration(
                run_id="test-run", duration_seconds=123.45, status="success"
            )

    def test_increment_scenarios_executed(self):
        """Verify scenarios executed counter is incremented."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            mock_counter = MagicMock()
            client._scenarios_executed_counter = mock_counter

            client.increment_scenarios_executed(run_id="test-run", scenario_type="compute-vm")

            mock_counter.add.assert_called_once_with(
                1, attributes={"run_id": "test-run", "scenario_type": "compute-vm"}
            )

    def test_increment_scenarios_executed_custom_count(self):
        """Verify scenarios executed counter handles custom counts."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            mock_counter = MagicMock()
            client._scenarios_executed_counter = mock_counter

            client.increment_scenarios_executed(
                run_id="test-run", scenario_type="compute-vm", count=5
            )

            mock_counter.add.assert_called_once_with(
                5, attributes={"run_id": "test-run", "scenario_type": "compute-vm"}
            )

    def test_record_cleanup_success_true(self):
        """Verify cleanup success metric recorded as 1."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            mock_gauge = MagicMock()
            client._cleanup_success_gauge = mock_gauge

            client.record_cleanup_success(
                run_id="test-run", success=True, cleanup_phase="resources"
            )

            mock_gauge.set.assert_called_once_with(
                1, attributes={"run_id": "test-run", "cleanup_phase": "resources"}
            )

    def test_record_cleanup_success_false(self):
        """Verify cleanup failure metric recorded as 0."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            mock_gauge = MagicMock()
            client._cleanup_success_gauge = mock_gauge

            client.record_cleanup_success(run_id="test-run", success=False, cleanup_phase="storage")

            mock_gauge.set.assert_called_once_with(
                0, attributes={"run_id": "test-run", "cleanup_phase": "storage"}
            )

    def test_increment_resources_created(self):
        """Verify resources created counter is incremented."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            mock_counter = MagicMock()
            client._resources_created_counter = mock_counter

            client.increment_resources_created(run_id="test-run", resource_type="vm", count=3)

            mock_counter.add.assert_called_once_with(
                3, attributes={"run_id": "test-run", "resource_type": "vm"}
            )

    def test_increment_resources_created_default_count(self):
        """Verify resources created counter defaults to 1."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            mock_counter = MagicMock()
            client._resources_created_counter = mock_counter

            client.increment_resources_created(run_id="test-run", resource_type="storage")

            mock_counter.add.assert_called_once_with(
                1, attributes={"run_id": "test-run", "resource_type": "storage"}
            )


# =============================================================================
# INTEGRATION TESTS (30%) - Multiple components
# =============================================================================


class TestMetricsIntegration:
    """Integration tests for metrics with OpenTelemetry."""

    @patch("azure_haymaker.observability.metrics.configure_azure_monitor")
    @patch("azure_haymaker.observability.metrics.get_meter_provider")
    def test_full_initialization_workflow(self, mock_get_meter_provider, mock_configure_azure):
        """Verify full initialization workflow with Azure Monitor."""
        from azure_haymaker.observability.metrics import MetricsClient

        mock_meter = MagicMock()
        mock_meter_provider = MagicMock()
        mock_meter_provider.get_meter.return_value = mock_meter
        mock_get_meter_provider.return_value = mock_meter_provider

        conn_string = "InstrumentationKey=test-key"

        with patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": conn_string}):
            MetricsClient()

            # Verify Azure Monitor was configured
            mock_configure_azure.assert_called_once_with(connection_string=conn_string)

            # Verify meter provider was obtained
            mock_get_meter_provider.assert_called_once()

            # Verify meter was created
            mock_meter_provider.get_meter.assert_called_once_with("azure_haymaker.observability")

    @patch("azure_haymaker.observability.metrics.get_meter_provider")
    def test_meter_instrument_creation(self, mock_get_meter_provider):
        """Verify all metric instruments are created."""
        from azure_haymaker.observability.metrics import MetricsClient

        mock_meter = MagicMock()
        mock_meter_provider = MagicMock()
        mock_meter_provider.get_meter.return_value = mock_meter
        mock_get_meter_provider.return_value = mock_meter_provider

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            MetricsClient()

            # Verify histogram created for execution duration
            assert mock_meter.create_histogram.called
            histogram_calls = list(mock_meter.create_histogram.call_args_list)
            assert any("execution.duration_seconds" in str(call) for call in histogram_calls)

            # Verify counters created
            assert mock_meter.create_counter.called
            counter_calls = list(mock_meter.create_counter.call_args_list)
            assert any("scenarios.executed_count" in str(call) for call in counter_calls)
            assert any("resources.created_count" in str(call) for call in counter_calls)

            # Verify gauge created
            assert mock_meter.create_up_down_counter.called or mock_meter.create_gauge.called

    def test_multiple_metrics_recorded_in_sequence(self):
        """Verify multiple metrics can be recorded in sequence."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            # Mock all instruments
            client._execution_duration_histogram = MagicMock()
            client._scenarios_executed_counter = MagicMock()
            client._cleanup_success_gauge = MagicMock()
            client._resources_created_counter = MagicMock()

            # Record multiple metrics
            client.record_execution_duration("run-1", 100.0, "success")
            client.increment_scenarios_executed("run-1", "compute")
            client.record_cleanup_success("run-1", True, "resources")
            client.increment_resources_created("run-1", "vm", 2)

            # Verify all were called
            assert client._execution_duration_histogram.record.called
            assert client._scenarios_executed_counter.add.called
            assert client._cleanup_success_gauge.set.called
            assert client._resources_created_counter.add.called


# =============================================================================
# E2E TESTS (10%) - Complete workflows
# =============================================================================


class TestMetricsEndToEnd:
    """End-to-end tests for complete metric workflows."""

    @patch("azure_haymaker.observability.metrics.configure_azure_monitor")
    @patch("azure_haymaker.observability.metrics.get_meter_provider")
    def test_complete_orchestration_workflow(self, mock_get_meter_provider, mock_configure_azure):
        """Verify complete orchestration workflow emits all expected metrics."""
        from azure_haymaker.observability.metrics import get_metrics_client

        mock_meter = MagicMock()
        mock_meter_provider = MagicMock()
        mock_meter_provider.get_meter.return_value = mock_meter
        mock_get_meter_provider.return_value = mock_meter_provider

        # Mock meter instruments
        mock_histogram = MagicMock()
        mock_counter = MagicMock()
        mock_gauge = MagicMock()

        mock_meter.create_histogram.return_value = mock_histogram
        mock_meter.create_counter.return_value = mock_counter
        mock_meter.create_up_down_counter.return_value = mock_gauge

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            # Simulate orchestration workflow
            metrics = get_metrics_client()

            run_id = "orchestration-run-123"

            # 1. Execute scenarios
            metrics.increment_scenarios_executed(run_id, "compute-vm", count=2)
            metrics.increment_scenarios_executed(run_id, "storage-blob", count=1)

            # 2. Track resources
            metrics.increment_resources_created(run_id, "vm", count=2)
            metrics.increment_resources_created(run_id, "storage", count=1)

            # 3. Cleanup phase
            metrics.record_cleanup_success(run_id, True, "resources")

            # 4. Record total duration
            metrics.record_execution_duration(run_id, 350.5, "success")

            # Verify all metrics recorded
            assert mock_counter.add.call_count >= 4  # 2 scenarios + 2 resources
            assert mock_gauge.set.call_count >= 1  # 1 cleanup
            assert mock_histogram.record.call_count >= 1  # 1 duration

    @patch("azure_haymaker.observability.metrics.configure_azure_monitor")
    def test_graceful_degradation_on_azure_monitor_failure(self, mock_configure_azure):
        """Verify graceful degradation if Azure Monitor configuration fails."""
        from azure_haymaker.observability.metrics import MetricsClient

        mock_configure_azure.side_effect = Exception("Azure Monitor unavailable")

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            # Should not raise exception
            client = MetricsClient()

            # Should gracefully handle metric recording
            client.record_execution_duration("test-run", 100.0, "success")
            client.increment_scenarios_executed("test-run", "compute")


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestMetricsErrorHandling:
    """Tests for error handling and edge cases."""

    def test_negative_duration_handled(self):
        """Verify negative duration is rejected or handled."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()
            client._execution_duration_histogram = MagicMock()

            with pytest.raises(ValueError, match="duration.*negative"):
                client.record_execution_duration("test-run", -10.0, "success")

    def test_empty_run_id_handled(self):
        """Verify empty run_id is rejected."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            with pytest.raises(ValueError, match="run_id.*empty"):
                client.record_execution_duration("", 100.0, "success")

    def test_invalid_status_handled(self):
        """Verify invalid status values are rejected."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            with pytest.raises(ValueError, match="status.*invalid"):
                client.record_execution_duration("test-run", 100.0, "invalid-status")

    def test_negative_resource_count_handled(self):
        """Verify negative resource count is rejected."""
        from azure_haymaker.observability.metrics import MetricsClient

        with patch.dict(
            os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test"}
        ):
            client = MetricsClient()

            with pytest.raises(ValueError, match="count.*negative"):
                client.increment_resources_created("test-run", "vm", count=-5)
