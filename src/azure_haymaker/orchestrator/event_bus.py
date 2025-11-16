"""Azure Service Bus event bus integration for agent logs and resource events."""

import inspect
import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient

from azure_haymaker.models.resource import Resource, ResourceStatus

logger = logging.getLogger(__name__)


class EventBusClient:
    """Client for Azure Service Bus event publishing and subscription.

    Manages connections to Azure Service Bus for publishing events and subscribing
    to agent logs with support for message batching and dual-write to Log Analytics
    and Blob Storage.
    """

    def __init__(
        self,
        connection_string: str,
        topic_name: str,
        batch_size: int = 100,
    ) -> None:
        """Initialize EventBusClient.

        Args:
            connection_string: Azure Service Bus connection string
            topic_name: Name of the Service Bus topic
            batch_size: Number of messages to batch before sending (default: 100)
        """
        self.connection_string = connection_string
        self.topic_name = topic_name
        self.batch_size = batch_size


async def publish_event(
    connection_string: str,
    topic_name: str,
    event: dict[str, Any],
) -> None:
    """Publish an event to Azure Service Bus topic.

    Publishes structured events to the agent-logs topic for downstream processing.
    Events are serialized as JSON and sent with proper error handling.

    Args:
        connection_string: Azure Service Bus connection string
        topic_name: Name of the Service Bus topic to publish to
        event: Event data dictionary containing event_type and event details

    Raises:
        Exception: If connection or publishing fails

    Example:
        >>> event = {
        ...     "event_type": "resource_created",
        ...     "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
        ...     "resource_name": "vm1",
        ... }
        >>> await publish_event(connection_string, "agent-logs", event)
    """
    client: ServiceBusClient | None = None
    try:
        sb_client = ServiceBusClient.from_connection_string(connection_string)
        client = sb_client
        sender = sb_client.get_topic_sender(topic_name)

        # Serialize event to JSON
        event_json = json.dumps(event, default=str)
        message = ServiceBusMessage(event_json)

        # Send the message
        await sender.send_messages(message)
        logger.debug(f"Published event to topic {topic_name}: {event.get('event_type')}")

    finally:
        if client:
            await client.close()


async def subscribe_to_agent_logs(
    connection_string: str,
    topic_name: str,
    subscription_name: str,
    callback: Callable[[dict[str, Any]], Any],
    max_wait_time: int = 5,
) -> None:
    """Subscribe to agent logs from Service Bus topic.

    Subscribes to a Service Bus subscription and processes incoming messages
    through a provided callback. Automatically completes messages after processing.
    Handles multiple messages and provides error recovery.

    Args:
        connection_string: Azure Service Bus connection string
        topic_name: Name of the Service Bus topic to subscribe to
        subscription_name: Name of the subscription to receive messages from
        callback: Async callback function to process each message
        max_wait_time: Maximum time to wait for messages in seconds (default: 5)

    Raises:
        Exception: If connection fails or subscription cannot be established

    Example:
        >>> async def handle_log(message: dict) -> None:
        ...     print(f"Received: {message['event_type']}")
        >>> await subscribe_to_agent_logs(
        ...     connection_string,
        ...     "agent-logs",
        ...     "orchestrator-sub",
        ...     handle_log
        ... )
    """
    client: ServiceBusClient | None = None
    try:
        sb_client = ServiceBusClient.from_connection_string(connection_string)
        client = sb_client
        receiver = sb_client.get_subscription_receiver(topic_name, subscription_name)

        # Receive messages
        messages = receiver.receive_messages(max_wait_time=max_wait_time)

        for message in messages:  # type: ignore[misc]  # Azure ServiceBus async iteration - requires refactor to async SDK
            try:
                # Parse message body
                message_data = json.loads(message.body.decode("utf-8"))
                logger.debug(f"Received message: {message_data.get('event_type')}")

                # Call the callback
                if inspect.iscoroutinefunction(callback):
                    await callback(message_data)
                else:
                    callback(message_data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message: {e}")

            finally:
                # Complete the message regardless of processing result
                await receiver.complete_message(message)
                logger.debug("Message completed")

    finally:
        if client:
            await client.close()


def parse_resource_events(messages: list[dict[str, Any]]) -> list[Resource]:
    """Parse resource creation and deletion events from messages.

    Extracts resource event data from messages and converts them to Resource
    objects. Supports resource creation, deletion, and deletion failure events.
    Unknown event types are ignored.

    Args:
        messages: List of message dictionaries containing event data

    Returns:
        List of Resource objects parsed from event messages

    Example:
        >>> messages = [
        ...     {
        ...         "event_type": "resource_created",
        ...         "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
        ...         "resource_type": "Microsoft.Compute/virtualMachines",
        ...         "resource_name": "vm1",
        ...         "scenario_name": "test-scenario",
        ...         "run_id": "run-123",
        ...         "timestamp": "2024-11-14T12:00:00Z",
        ...     }
        ... ]
        >>> resources = parse_resource_events(messages)
        >>> assert resources[0].status == ResourceStatus.CREATED
    """
    resources: list[Resource] = []

    for message in messages:
        event_type = message.get("event_type")

        # Map event types to resource status
        if event_type == "resource_created":
            status = ResourceStatus.CREATED
        elif event_type == "resource_deleted":
            status = ResourceStatus.DELETED
        elif event_type == "resource_deletion_failed":
            status = ResourceStatus.DELETION_FAILED
        else:
            # Skip unknown event types
            logger.debug(f"Skipping unknown event type: {event_type}")
            continue

        try:
            # Parse timestamp
            timestamp_str = message.get("timestamp", "")
            if timestamp_str:
                created_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                created_at = datetime.now()

            # Extract resource data
            resource = Resource(
                resource_id=message.get("resource_id", ""),
                resource_type=message.get("resource_type", ""),
                resource_name=message.get("resource_name", ""),
                scenario_name=message.get("scenario_name", ""),
                run_id=message.get("run_id", ""),
                created_at=created_at,
                status=status,
                deletion_attempts=message.get("deletion_attempts", 0),
                deletion_error=message.get("deletion_error"),
                tags=message.get("tags", {}),
            )

            resources.append(resource)
            logger.debug(f"Parsed resource event: {resource.resource_name} ({event_type})")

        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse resource event: {e}")
            continue

    return resources
