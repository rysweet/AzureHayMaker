"""Agents API endpoints for HayMaker orchestrator."""

import logging
from datetime import datetime

import azure.functions as func
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient
from pydantic import BaseModel

app = func.FunctionApp()
logger = logging.getLogger(__name__)


def sanitize_odata_value(value: str) -> str:
    """Sanitize input for OData query filters to prevent injection attacks.

    Args:
        value: Input string to sanitize

    Returns:
        Sanitized string safe for use in OData filters
    """
    # Convert to string and escape single quotes by doubling them (OData standard)
    return str(value).replace("'", "''")


class AgentInfo(BaseModel):
    """Agent information."""

    agent_id: str
    scenario: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    progress: str | None = None
    error: str | None = None


class LogEntry(BaseModel):
    """Log entry."""

    timestamp: datetime
    level: str
    message: str
    agent_id: str
    scenario: str | None = None


async def query_agents_from_table(
    table_client,
    status_filter: str | None = None,
    limit: int = 100,
) -> list[AgentInfo]:
    """Query agents from Table Storage.

    Args:
        table_client: Table client
        status_filter: Optional status filter (running, completed, failed)
        limit: Maximum number of results

    Returns:
        List of agent information
    """
    agents = []

    try:
        # Build query filter
        query_filter = None
        if status_filter:
            query_filter = f"status eq '{sanitize_odata_value(status_filter)}'"

        # Query table
        entities = table_client.query_entities(
            query_filter=query_filter,
            select=[
                "agent_id",
                "scenario",
                "status",
                "started_at",
                "completed_at",
                "progress",
                "error",
            ],
        )

        # Convert to AgentInfo models
        for entity in entities:
            if len(agents) >= limit:
                break

            try:
                agent = AgentInfo(
                    agent_id=entity.get("agent_id", entity.get("RowKey", "unknown")),
                    scenario=entity.get("scenario", "unknown"),
                    status=entity.get("status", "unknown"),
                    started_at=entity.get("started_at", datetime.now()),
                    completed_at=entity.get("completed_at"),
                    progress=entity.get("progress"),
                    error=entity.get("error"),
                )
                agents.append(agent)
            except Exception as e:
                logger.warning(f"Error parsing agent entity: {e}")
                continue

    except Exception as e:
        logger.error(f"Error querying agents from table: {e}")
        raise

    return agents


async def query_logs_from_servicebus(
    servicebus_client: ServiceBusClient,
    topic_name: str,
    subscription_name: str,
    agent_id: str,
    tail: int = 100,
) -> list[LogEntry]:
    """Query logs from Service Bus.

    Note: This is a simplified implementation. In production, logs should be
    stored in a persistent store (Cosmos DB, Blob Storage) for querying.

    Args:
        servicebus_client: Service Bus client
        topic_name: Topic name
        subscription_name: Subscription name for the agent
        agent_id: Agent ID to filter logs
        tail: Number of recent entries to return

    Returns:
        List of log entries
    """
    logs = []

    try:
        # In production, query logs from persistent storage (Cosmos DB, Log Analytics)
        # For now, return empty list as Service Bus doesn't support querying
        # This would need to be implemented with a proper log storage solution

        logger.info(f"Log query for agent {agent_id} (returning empty - needs log storage)")

    except Exception as e:
        logger.error(f"Error querying logs: {e}")
        raise

    return logs


@app.route(route="agents", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def list_agents(req: func.HttpRequest) -> func.HttpResponse:
    """List all agents.

    Query Parameters:
        status: Optional status filter (running, completed, failed)
        limit: Maximum number of results (default: 100)

    Response:
        200 OK: {
            "agents": [
                {
                    "agent_id": str,
                    "scenario": str,
                    "status": str,
                    "started_at": str (ISO 8601),
                    "completed_at": str (ISO 8601) | null,
                    "progress": str | null,
                    "error": str | null
                }
            ]
        }

        500 Internal Server Error: Server error

    Example:
        GET /api/v1/agents
        GET /api/v1/agents?status=running
        GET /api/v1/agents?limit=50
    """
    try:
        # Parse query parameters
        status_filter = req.params.get("status")
        limit = int(req.params.get("limit", "100"))

        # Get Table Storage configuration
        import os

        table_account_name = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
        table_name = os.getenv("AGENTS_TABLE_NAME", "agents")

        if not table_account_name:
            logger.error("TABLE_STORAGE_ACCOUNT_NAME not configured")
            return func.HttpResponse(
                body='{"error": "Agents storage not configured"}',
                status_code=500,
                mimetype="application/json",
            )

        # Create Table Storage client (using managed identity)
        credential = DefaultAzureCredential()
        table_service_client = TableServiceClient(
            endpoint=f"https://{table_account_name}.table.core.windows.net",
            credential=credential,
        )
        table_client = table_service_client.get_table_client(table_name)

        # Query agents
        agents = await query_agents_from_table(
            table_client,
            status_filter=status_filter,
            limit=limit,
        )

        # Build response
        response = {"agents": [agent.model_dump(mode="json") for agent in agents]}

        return func.HttpResponse(
            body=str(response),
            status_code=200,
            mimetype="application/json",
        )

    except ValueError as e:
        # Log detailed error internally
        logger.warning(f"Invalid parameter in list_agents: {e}")
        return func.HttpResponse(
            body='{"error": {"code": "INVALID_PARAMETER", "message": "Invalid request parameter"}}',
            status_code=400,
            mimetype="application/json",
        )
    except Exception:
        # Log detailed error internally but return generic message
        logger.exception("Error listing agents")
        return func.HttpResponse(
            body='{"error": {"code": "INTERNAL_ERROR", "message": "Failed to list agents"}}',
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="agents/{agent_id}/logs", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def get_agent_logs(req: func.HttpRequest) -> func.HttpResponse:
    """Get logs for an agent.

    Path Parameters:
        agent_id: Agent ID

    Query Parameters:
        tail: Number of recent log entries (default: 100)
        follow: Whether to stream logs (not implemented via HTTP)

    Response:
        200 OK: {
            "logs": [
                {
                    "timestamp": str (ISO 8601),
                    "level": str,
                    "message": str,
                    "agent_id": str,
                    "scenario": str | null
                }
            ]
        }

        404 Not Found: Agent not found
        500 Internal Server Error: Server error

    Example:
        GET /api/v1/agents/agent-123/logs
        GET /api/v1/agents/agent-123/logs?tail=50
    """
    try:
        # Parse path parameter
        agent_id = req.route_params.get("agent_id")

        if not agent_id:
            return func.HttpResponse(
                body='{"error": "agent_id is required"}',
                status_code=400,
                mimetype="application/json",
            )

        # Parse query parameters
        # TODO: Implement log tailing and following once log storage is added
        # tail = int(req.params.get("tail", "100"))
        # follow = req.params.get("follow", "false").lower() == "true"

        # Get Service Bus configuration
        import os

        servicebus_namespace = os.getenv("SERVICE_BUS_NAMESPACE")
        # topic_name = os.getenv("SERVICE_BUS_TOPIC", "agent-logs")

        if not servicebus_namespace:
            logger.error("SERVICE_BUS_NAMESPACE not configured")
            return func.HttpResponse(
                body='{"error": "Log storage not configured"}',
                status_code=500,
                mimetype="application/json",
            )

        # Note: In production, logs should be queried from persistent storage
        # (Cosmos DB, Log Analytics, Blob Storage) not Service Bus
        # Service Bus is for real-time streaming, not historical queries

        # For now, return placeholder response
        logs = []

        # Build response
        response = {
            "logs": [log.model_dump(mode="json") for log in logs],
            "note": "Log storage implementation pending. Logs should be queried from Log Analytics or Cosmos DB.",
        }

        return func.HttpResponse(
            body=str(response),
            status_code=200,
            mimetype="application/json",
        )

    except ValueError as e:
        # Log detailed error internally
        logger.warning(f"Invalid parameter in get_agent_logs: {e}")
        return func.HttpResponse(
            body='{"error": {"code": "INVALID_PARAMETER", "message": "Invalid request parameter"}}',
            status_code=400,
            mimetype="application/json",
        )
    except Exception:
        # Log detailed error internally but return generic message
        logger.exception("Error retrieving agent logs")
        return func.HttpResponse(
            body='{"error": {"code": "INTERNAL_ERROR", "message": "Failed to retrieve agent logs"}}',
            status_code=500,
            mimetype="application/json",
        )
