"""Unit tests for event bus and Azure Service Bus integration."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.servicebus import ServiceBusMessage

from azure_haymaker.models.resource import ResourceStatus
from azure_haymaker.orchestrator.event_bus import (
    EventBusClient,
    parse_resource_events,
    publish_event,
    subscribe_to_agent_logs,
)


class TestEventBusClientInitialization:
    """Tests for EventBusClient initialization."""

    def test_event_bus_client_init(self) -> None:
        """Test EventBusClient initialization with connection string."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"

        client = EventBusClient(connection_string, topic_name)

        assert client.connection_string == connection_string
        assert client.topic_name == topic_name

    def test_event_bus_client_custom_batch_size(self) -> None:
        """Test EventBusClient with custom batch size."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"
        batch_size = 50

        client = EventBusClient(connection_string, topic_name, batch_size=batch_size)

        assert client.batch_size == batch_size

    def test_event_bus_client_default_batch_size(self) -> None:
        """Test EventBusClient uses default batch size."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"

        client = EventBusClient(connection_string, topic_name)

        assert client.batch_size == 100


class TestPublishEvent:
    """Tests for publish_event function."""

    @pytest.mark.asyncio
    async def test_publish_event_success(self) -> None:
        """Test successful event publishing."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"

        event_data = {
            "event_type": "resource_created",
            "resource_id": "/subscriptions/123/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
            "timestamp": "2024-11-14T12:00:00Z",
        }

        with patch("azure_haymaker.orchestrator.event_bus.ServiceBusClient") as mock_client_class:
            mock_client = MagicMock()
            mock_sender = MagicMock()
            mock_client_class.from_connection_string.return_value = mock_client
            mock_client.get_topic_sender.return_value = mock_sender
            mock_client.close = AsyncMock()
            mock_sender.send_messages = AsyncMock()

            await publish_event(connection_string, topic_name, event_data)

            mock_client_class.from_connection_string.assert_called_once_with(connection_string)
            mock_client.get_topic_sender.assert_called_once_with(topic_name)
            mock_sender.send_messages.assert_called_once()
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_event_with_json_serialization(self) -> None:
        """Test event publishing with JSON serialization."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"

        event_data = {
            "event_type": "resource_created",
            "details": {"nested": "value"},
        }

        with patch("azure_haymaker.orchestrator.event_bus.ServiceBusClient") as mock_client_class:
            mock_client = MagicMock()
            mock_sender = MagicMock()
            mock_client_class.from_connection_string.return_value = mock_client
            mock_client.get_topic_sender.return_value = mock_sender
            mock_client.close = AsyncMock()
            mock_sender.send_messages = AsyncMock()

            await publish_event(connection_string, topic_name, event_data)

            # Verify message was sent with JSON body
            call_args = mock_sender.send_messages.call_args
            assert call_args is not None
            message = call_args[0][0]
            assert isinstance(message, ServiceBusMessage)

    @pytest.mark.asyncio
    async def test_publish_event_handles_connection_error(self) -> None:
        """Test event publishing handles connection errors gracefully."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"

        event_data = {"event_type": "test"}

        with patch("azure_haymaker.orchestrator.event_bus.ServiceBusClient") as mock_client_class:
            mock_client_class.from_connection_string.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                await publish_event(connection_string, topic_name, event_data)


class TestSubscribeToAgentLogs:
    """Tests for subscribe_to_agent_logs function."""

    @pytest.mark.asyncio
    async def test_subscribe_to_agent_logs_success(self) -> None:
        """Test successful subscription to agent logs."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"
        subscription_name = "orchestrator-sub"

        callback = AsyncMock()

        with patch("azure_haymaker.orchestrator.event_bus.ServiceBusClient") as mock_client_class:
            mock_client = MagicMock()
            mock_receiver = MagicMock()
            mock_message = MagicMock()
            mock_message.body = b'{"event_type": "test"}'
            mock_receiver.receive_messages.return_value = [mock_message]
            mock_receiver.complete_message = AsyncMock()
            mock_client.close = AsyncMock()

            mock_client_class.from_connection_string.return_value = mock_client
            mock_client.get_subscription_receiver.return_value = mock_receiver

            await subscribe_to_agent_logs(
                connection_string, topic_name, subscription_name, callback, max_wait_time=1
            )

            mock_client_class.from_connection_string.assert_called_once_with(connection_string)
            mock_client.get_subscription_receiver.assert_called_once_with(
                topic_name, subscription_name
            )
            callback.assert_called()

    @pytest.mark.asyncio
    async def test_subscribe_to_agent_logs_with_multiple_messages(self) -> None:
        """Test subscription handles multiple messages."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"
        subscription_name = "orchestrator-sub"

        callback = AsyncMock()

        with patch("azure_haymaker.orchestrator.event_bus.ServiceBusClient") as mock_client_class:
            mock_client = MagicMock()
            mock_receiver = MagicMock()
            mock_message1 = MagicMock()
            mock_message1.body = b'{"event_type": "event1"}'
            mock_message2 = MagicMock()
            mock_message2.body = b'{"event_type": "event2"}'
            mock_receiver.receive_messages.return_value = [mock_message1, mock_message2]
            mock_receiver.complete_message = AsyncMock()
            mock_client.close = AsyncMock()

            mock_client_class.from_connection_string.return_value = mock_client
            mock_client.get_subscription_receiver.return_value = mock_receiver

            await subscribe_to_agent_logs(
                connection_string, topic_name, subscription_name, callback, max_wait_time=1
            )

            assert callback.call_count == 2

    @pytest.mark.asyncio
    async def test_subscribe_to_agent_logs_complete_message(self) -> None:
        """Test subscription completes messages after processing."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"
        subscription_name = "orchestrator-sub"

        callback = AsyncMock()

        with patch("azure_haymaker.orchestrator.event_bus.ServiceBusClient") as mock_client_class:
            mock_client = MagicMock()
            mock_receiver = MagicMock()
            mock_message = MagicMock()
            mock_message.body = b'{"event_type": "test"}'
            mock_receiver.receive_messages.return_value = [mock_message]
            mock_receiver.complete_message = AsyncMock()
            mock_client.close = AsyncMock()

            mock_client_class.from_connection_string.return_value = mock_client
            mock_client.get_subscription_receiver.return_value = mock_receiver

            await subscribe_to_agent_logs(
                connection_string, topic_name, subscription_name, callback, max_wait_time=1
            )

            mock_receiver.complete_message.assert_called()

    @pytest.mark.asyncio
    async def test_subscribe_to_agent_logs_handles_parsing_error(self) -> None:
        """Test subscription handles invalid message formats."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"
        subscription_name = "orchestrator-sub"

        callback = AsyncMock()

        with patch("azure_haymaker.orchestrator.event_bus.ServiceBusClient") as mock_client_class:
            mock_client = MagicMock()
            mock_receiver = MagicMock()
            mock_message = MagicMock()
            mock_message.body = b"invalid json{{"
            mock_receiver.receive_messages.return_value = [mock_message]
            mock_receiver.complete_message = AsyncMock()
            mock_client.close = AsyncMock()

            mock_client_class.from_connection_string.return_value = mock_client
            mock_client.get_subscription_receiver.return_value = mock_receiver

            await subscribe_to_agent_logs(
                connection_string, topic_name, subscription_name, callback, max_wait_time=1
            )

            # Should complete message even on parsing error
            mock_receiver.complete_message.assert_called()


class TestParseResourceEvents:
    """Tests for parse_resource_events function."""

    def test_parse_resource_events_single_creation(self) -> None:
        """Test parsing a single resource creation event."""
        messages = [
            {
                "event_type": "resource_created",
                "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "resource_name": "vm1",
                "scenario_name": "test-scenario",
                "run_id": "run-123",
                "timestamp": "2024-11-14T12:00:00Z",
            }
        ]

        resources = parse_resource_events(messages)

        assert len(resources) == 1
        assert (
            resources[0].resource_id
            == "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1"
        )
        assert resources[0].resource_name == "vm1"
        assert resources[0].status == ResourceStatus.CREATED

    def test_parse_resource_events_multiple_types(self) -> None:
        """Test parsing multiple event types."""
        messages = [
            {
                "event_type": "resource_created",
                "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "resource_name": "vm1",
                "scenario_name": "test-scenario",
                "run_id": "run-123",
                "timestamp": "2024-11-14T12:00:00Z",
            },
            {
                "event_type": "resource_deleted",
                "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/storage1",
                "resource_type": "Microsoft.Storage/storageAccounts",
                "resource_name": "storage1",
                "scenario_name": "test-scenario",
                "run_id": "run-123",
                "timestamp": "2024-11-14T12:01:00Z",
            },
        ]

        resources = parse_resource_events(messages)

        assert len(resources) == 2
        assert resources[0].status == ResourceStatus.CREATED
        assert resources[1].status == ResourceStatus.DELETED

    def test_parse_resource_events_with_tags(self) -> None:
        """Test parsing events with resource tags."""
        messages = [
            {
                "event_type": "resource_created",
                "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "resource_name": "vm1",
                "scenario_name": "test-scenario",
                "run_id": "run-123",
                "timestamp": "2024-11-14T12:00:00Z",
                "tags": {"environment": "test", "team": "haymaker"},
            }
        ]

        resources = parse_resource_events(messages)

        assert len(resources) == 1
        assert resources[0].tags == {"environment": "test", "team": "haymaker"}

    def test_parse_resource_events_deletion_with_error(self) -> None:
        """Test parsing deletion events with error information."""
        messages = [
            {
                "event_type": "resource_deletion_failed",
                "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "resource_name": "vm1",
                "scenario_name": "test-scenario",
                "run_id": "run-123",
                "timestamp": "2024-11-14T12:00:00Z",
                "deletion_error": "Resource is locked",
                "deletion_attempts": 3,
            }
        ]

        resources = parse_resource_events(messages)

        assert len(resources) == 1
        assert resources[0].status == ResourceStatus.DELETION_FAILED
        assert resources[0].deletion_error == "Resource is locked"
        assert resources[0].deletion_attempts == 3

    def test_parse_resource_events_empty_list(self) -> None:
        """Test parsing empty message list."""
        messages: list[dict[str, Any]] = []

        resources = parse_resource_events(messages)

        assert len(resources) == 0

    def test_parse_resource_events_ignores_unknown_event_types(self) -> None:
        """Test that unknown event types are skipped."""
        messages = [
            {
                "event_type": "resource_created",
                "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "resource_name": "vm1",
                "scenario_name": "test-scenario",
                "run_id": "run-123",
                "timestamp": "2024-11-14T12:00:00Z",
            },
            {
                "event_type": "unknown_event_type",
                "data": "some data",
            },
        ]

        resources = parse_resource_events(messages)

        assert len(resources) == 1

    def test_parse_resource_events_preserves_timestamps(self) -> None:
        """Test that timestamps are correctly parsed."""
        timestamp_str = "2024-11-14T12:00:00Z"
        messages = [
            {
                "event_type": "resource_created",
                "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "resource_name": "vm1",
                "scenario_name": "test-scenario",
                "run_id": "run-123",
                "timestamp": timestamp_str,
            }
        ]

        resources = parse_resource_events(messages)

        assert len(resources) == 1
        assert resources[0].created_at is not None


class TestEventBusIntegration:
    """Integration tests for event bus functionality."""

    @pytest.mark.asyncio
    async def test_publish_and_parse_event_workflow(self) -> None:
        """Test complete workflow of publishing and parsing events."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"

        event_data = {
            "event_type": "resource_created",
            "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
            "resource_type": "Microsoft.Compute/virtualMachines",
            "resource_name": "vm1",
            "scenario_name": "test-scenario",
            "run_id": "run-123",
            "timestamp": "2024-11-14T12:00:00Z",
        }

        # Publish event
        with patch("azure_haymaker.orchestrator.event_bus.ServiceBusClient") as mock_client_class:
            mock_client = MagicMock()
            mock_sender = MagicMock()
            mock_client_class.from_connection_string.return_value = mock_client
            mock_client.get_topic_sender.return_value = mock_sender
            mock_client.close = AsyncMock()
            mock_sender.send_messages = AsyncMock()

            await publish_event(connection_string, topic_name, event_data)

            mock_sender.send_messages.assert_called_once()

        # Parse event
        resources = parse_resource_events([event_data])

        assert len(resources) == 1
        assert resources[0].resource_name == "vm1"

    @pytest.mark.asyncio
    async def test_subscription_with_batch_processing(self) -> None:
        """Test batch processing of messages through subscription."""
        connection_string = "Endpoint=sb://haymaker.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test"
        topic_name = "agent-logs"
        subscription_name = "orchestrator-sub"

        collected_messages: list[dict[str, Any]] = []

        async def batch_callback(message_data: dict[str, Any]) -> None:
            collected_messages.append(message_data)

        with patch("azure_haymaker.orchestrator.event_bus.ServiceBusClient") as mock_client_class:
            mock_client = MagicMock()
            mock_receiver = MagicMock()
            mock_message1 = MagicMock()
            mock_message1.body = b'{"event_type": "event1", "resource_id": "id1"}'
            mock_message2 = MagicMock()
            mock_message2.body = b'{"event_type": "event2", "resource_id": "id2"}'
            mock_receiver.receive_messages.return_value = [mock_message1, mock_message2]
            mock_receiver.complete_message = AsyncMock()
            mock_client.close = AsyncMock()

            mock_client_class.from_connection_string.return_value = mock_client
            mock_client.get_subscription_receiver.return_value = mock_receiver

            await subscribe_to_agent_logs(
                connection_string,
                topic_name,
                subscription_name,
                batch_callback,
                max_wait_time=1,
            )

            assert len(collected_messages) == 2
            assert collected_messages[0]["resource_id"] == "id1"
            assert collected_messages[1]["resource_id"] == "id2"
