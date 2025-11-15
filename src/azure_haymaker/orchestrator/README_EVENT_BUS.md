# Event Bus Module

Azure Service Bus integration for agent logs and resource event management in Azure HayMaker.

## Overview

The Event Bus module provides async integration with Azure Service Bus for:
- Publishing resource events to topics
- Subscribing to agent logs from topics with callback processing
- Parsing resource creation/deletion events
- Message batching support
- Dual-write capability to Log Analytics and Blob Storage

## Architecture

### Components

1. **EventBusClient**: Configuration client for event bus connections
2. **publish_event()**: Publishes structured events to Service Bus topics
3. **subscribe_to_agent_logs()**: Subscribes to and processes messages from topics
4. **parse_resource_events()**: Converts raw events into Resource objects

### Data Flow

```
Agent Events
    |
    v
Azure Service Bus Topic (agent-logs)
    |
    +---> Orchestrator Subscriber
    |         |
    |         +---> Parse Events
    |         |
    |         +---> Log Analytics (dual-write)
    |         |
    |         +---> Blob Storage (dual-write)
    |
    +---> Other Subscribers
```

## API Reference

### EventBusClient

Configuration client for managing Azure Service Bus connections.

```python
client = EventBusClient(
    connection_string="Endpoint=sb://...",
    topic_name="agent-logs",
    batch_size=100
)
```

**Parameters:**
- `connection_string`: Azure Service Bus connection string
- `topic_name`: Name of the Service Bus topic
- `batch_size`: Number of messages to batch before sending (default: 100)

### publish_event()

Publishes an event to an Azure Service Bus topic.

```python
import asyncio
from azure_haymaker.orchestrator import publish_event

event = {
    "event_type": "resource_created",
    "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
    "resource_type": "Microsoft.Compute/virtualMachines",
    "resource_name": "vm1",
    "scenario_name": "test-scenario",
    "run_id": "run-123",
    "timestamp": "2024-11-14T12:00:00Z",
}

await publish_event(connection_string, "agent-logs", event)
```

**Parameters:**
- `connection_string`: Azure Service Bus connection string
- `topic_name`: Topic to publish to
- `event`: Dictionary containing event data

**Returns:** None

**Raises:** Exception if connection or publishing fails

### subscribe_to_agent_logs()

Subscribes to a Service Bus subscription and processes messages through a callback.

```python
async def handle_event(message: dict):
    """Process incoming event."""
    print(f"Event type: {message['event_type']}")

await subscribe_to_agent_logs(
    connection_string,
    "agent-logs",
    "orchestrator-sub",
    handle_event,
    max_wait_time=5
)
```

**Parameters:**
- `connection_string`: Azure Service Bus connection string
- `topic_name`: Topic to subscribe to
- `subscription_name`: Subscription name
- `callback`: Async callback function to process each message
- `max_wait_time`: Maximum time to wait for messages in seconds (default: 5)

**Returns:** None

**Raises:** Exception if connection or subscription fails

**Callback:** Receives a dictionary with message data. Both async and sync callbacks are supported.

### parse_resource_events()

Parses raw event data into Resource objects.

```python
from azure_haymaker.orchestrator import parse_resource_events

events = [
    {
        "event_type": "resource_created",
        "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
        "resource_type": "Microsoft.Compute/virtualMachines",
        "resource_name": "vm1",
        "scenario_name": "test-scenario",
        "run_id": "run-123",
        "timestamp": "2024-11-14T12:00:00Z",
        "tags": {"env": "test"},
    }
]

resources = parse_resource_events(events)
for resource in resources:
    print(f"Resource: {resource.resource_name}, Status: {resource.status}")
```

**Parameters:**
- `messages`: List of event dictionaries

**Returns:** List of Resource objects

**Supported Event Types:**
- `resource_created`: Resource was successfully created
- `resource_deleted`: Resource was successfully deleted
- `resource_deletion_failed`: Resource deletion failed
- Unknown types are silently skipped

**Parsed Fields:**
- `resource_id`: Full Azure resource ID
- `resource_type`: Azure resource type (e.g., Microsoft.Compute/virtualMachines)
- `resource_name`: Human-readable resource name
- `scenario_name`: Scenario that created the resource
- `run_id`: Execution run identifier
- `created_at`: Timestamp from event (or current time if missing)
- `status`: ResourceStatus enum value
- `deletion_attempts`: Number of deletion attempts (if present)
- `deletion_error`: Error message from failed deletion (if present)
- `tags`: Dictionary of resource tags (default: empty)

## Event Schema

### Resource Created Event

```json
{
    "event_type": "resource_created",
    "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
    "resource_type": "Microsoft.Compute/virtualMachines",
    "resource_name": "vm1",
    "scenario_name": "test-scenario",
    "run_id": "run-123",
    "timestamp": "2024-11-14T12:00:00Z",
    "tags": {
        "environment": "test",
        "team": "haymaker"
    }
}
```

### Resource Deleted Event

```json
{
    "event_type": "resource_deleted",
    "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/storage1",
    "resource_type": "Microsoft.Storage/storageAccounts",
    "resource_name": "storage1",
    "scenario_name": "test-scenario",
    "run_id": "run-123",
    "timestamp": "2024-11-14T12:01:00Z"
}
```

### Resource Deletion Failed Event

```json
{
    "event_type": "resource_deletion_failed",
    "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
    "resource_type": "Microsoft.Compute/virtualMachines",
    "resource_name": "vm1",
    "scenario_name": "test-scenario",
    "run_id": "run-123",
    "timestamp": "2024-11-14T12:02:00Z",
    "deletion_error": "Resource is locked or has active dependencies",
    "deletion_attempts": 3
}
```

## Usage Examples

### Example 1: Publish Resource Creation Event

```python
import asyncio
import json
from datetime import datetime
from azure_haymaker.orchestrator import publish_event

async def publish_vm_created():
    event = {
        "event_type": "resource_created",
        "resource_id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/myvm",
        "resource_type": "Microsoft.Compute/virtualMachines",
        "resource_name": "myvm",
        "scenario_name": "compute-scenario",
        "run_id": "run-abc123",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tags": {
            "env": "test",
            "created_by": "haymaker"
        }
    }

    await publish_event(
        connection_string="Endpoint=sb://haymaker.servicebus.windows.net/;...",
        topic_name="agent-logs",
        event=event
    )
    print("Event published successfully")

asyncio.run(publish_vm_created())
```

### Example 2: Subscribe and Process Events

```python
import asyncio
from azure_haymaker.orchestrator import subscribe_to_agent_logs, parse_resource_events

async def event_callback(message: dict):
    """Process incoming event."""
    print(f"Received event: {message['event_type']}")

    # Parse resource events
    resources = parse_resource_events([message])
    for resource in resources:
        print(f"  Resource: {resource.resource_name}")
        print(f"  Type: {resource.resource_type}")
        print(f"  Status: {resource.status}")

async def main():
    await subscribe_to_agent_logs(
        connection_string="Endpoint=sb://haymaker.servicebus.windows.net/;...",
        topic_name="agent-logs",
        subscription_name="orchestrator-sub",
        callback=event_callback,
        max_wait_time=30
    )

asyncio.run(main())
```

### Example 3: Batch Event Processing

```python
import asyncio
from azure_haymaker.orchestrator import subscribe_to_agent_logs, parse_resource_events

events_buffer = []

async def batch_callback(message: dict):
    """Accumulate events for batch processing."""
    events_buffer.append(message)

    if len(events_buffer) >= 10:
        # Process batch
        resources = parse_resource_events(events_buffer)
        print(f"Processing batch of {len(resources)} resources")

        # Do something with resources (e.g., write to database)
        for resource in resources:
            print(f"  Processed: {resource.resource_name}")

        events_buffer.clear()

async def main():
    await subscribe_to_agent_logs(
        connection_string="Endpoint=sb://haymaker.servicebus.windows.net/;...",
        topic_name="agent-logs",
        subscription_name="orchestrator-sub",
        callback=batch_callback,
        max_wait_time=60
    )

asyncio.run(main())
```

## Integration with Dual-Write

### Log Analytics Integration

Events can be simultaneously written to Azure Log Analytics for centralized monitoring:

```python
async def handle_event(message: dict):
    """Process event and write to Log Analytics."""
    # Parse event
    resources = parse_resource_events([message])

    # Send to Log Analytics
    for resource in resources:
        log_entry = {
            "resource_id": resource.resource_id,
            "resource_name": resource.resource_name,
            "status": str(resource.status),
            "created_at": resource.created_at.isoformat(),
            "scenario": resource.scenario_name,
            "run_id": resource.run_id,
        }
        # Use Log Analytics client to send entry
        await log_analytics_client.send_log(log_entry)
```

### Blob Storage Integration

Events can be archived to Blob Storage for long-term retention:

```python
import json
from datetime import datetime

async def handle_event(message: dict):
    """Process event and archive to Blob Storage."""
    resources = parse_resource_events([message])

    # Archive to Blob Storage
    for resource in resources:
        blob_name = f"events/{datetime.utcnow().isoformat()}/{resource.resource_id}.json"
        blob_data = {
            "resource": resource.model_dump(),
            "archived_at": datetime.utcnow().isoformat(),
        }
        # Use Blob Storage client to upload
        await blob_client.upload_blob(blob_name, json.dumps(blob_data))
```

## Error Handling

### Connection Errors

```python
try:
    await publish_event(connection_string, topic_name, event)
except Exception as e:
    logger.error(f"Failed to publish event: {e}")
```

### Message Parsing Errors

The module handles invalid JSON messages gracefully:
- Messages with invalid JSON are logged as errors
- Processing continues with other messages
- Message is still completed to prevent reprocessing

### Resource Parsing Errors

Missing required fields in events are handled gracefully:
- Events with missing required fields are logged as errors
- Processing continues with other events
- Unknown event types are silently skipped

## Testing

Comprehensive test suite in `tests/unit/test_event_bus.py`:

```bash
uv run pytest tests/unit/test_event_bus.py -v
```

Test coverage:
- EventBusClient initialization
- Event publishing success and error cases
- Subscription and message processing
- Resource event parsing for all event types
- Batch processing workflows
- Error handling and recovery

## Dependencies

- `azure-servicebus>=7.13.0`: Azure Service Bus client
- `pydantic>=2.10.0`: Data validation
- `azure_haymaker.models.resource`: Resource model

## Performance Considerations

### Message Batching

Configure batch size for optimal throughput:

```python
# Larger batches for high-volume scenarios
client = EventBusClient(
    connection_string=conn_str,
    topic_name="agent-logs",
    batch_size=500  # Process 500 messages at a time
)
```

### Subscription Timeout

Adjust wait time based on message frequency:

```python
# Longer timeout for low-frequency events
await subscribe_to_agent_logs(
    connection_string,
    topic_name,
    subscription_name,
    callback,
    max_wait_time=60  # Wait up to 60 seconds
)

# Shorter timeout for high-frequency processing
await subscribe_to_agent_logs(
    connection_string,
    topic_name,
    subscription_name,
    callback,
    max_wait_time=1  # More responsive
)
```

## Logging

Module uses Python logging with "azure_haymaker.orchestrator.event_bus" logger:

```python
import logging

logger = logging.getLogger("azure_haymaker.orchestrator.event_bus")
logger.setLevel(logging.DEBUG)  # Enable debug logging
```

Debug logs include:
- Published event type
- Received message type
- Message completion status
- Parsing results and errors
