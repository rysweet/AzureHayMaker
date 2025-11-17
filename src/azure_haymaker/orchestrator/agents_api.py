"""Agents API endpoints for HayMaker orchestrator."""

import json
import logging
import os
from datetime import datetime

import azure.functions as func
from azure.cosmos import CosmosClient
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
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

    timestamp: str
    level: str
    message: str
    agent_id: str
    source: str = "agent"


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


async def query_logs_from_cosmosdb(
    agent_id: str,
    tail: int = 100,
    since_timestamp: str | None = None,
) -> list[LogEntry]:
    """Query logs from Cosmos DB.

    Args:
        agent_id: Agent ID to filter logs
        tail: Number of recent entries to return (default: 100)
        since_timestamp: Optional ISO 8601 timestamp to get logs after

    Returns:
        List of log entries, sorted by timestamp (newest first)
    """
    logs = []

    try:
        # Initialize Cosmos DB client
        cosmos_endpoint = os.getenv("COSMOSDB_ENDPOINT")
        if not cosmos_endpoint:
            logger.error("COSMOSDB_ENDPOINT not configured")
            return logs

        credential = DefaultAzureCredential()
        cosmos_client = CosmosClient(cosmos_endpoint, credential)
        database = cosmos_client.get_database_client("haymaker")
        container = database.get_container_client("agent-logs")

        # Build query
        if since_timestamp:
            query = """
                SELECT * FROM c
                WHERE c.agent_id = @agent_id
                AND c.timestamp > @since_timestamp
                ORDER BY c.timestamp DESC
            """
            parameters = [
                {"name": "@agent_id", "value": agent_id},
                {"name": "@since_timestamp", "value": since_timestamp},
            ]
        else:
            query = """
                SELECT TOP @limit * FROM c
                WHERE c.agent_id = @agent_id
                ORDER BY c.timestamp DESC
            """
            parameters = [
                {"name": "@agent_id", "value": agent_id},
                {"name": "@limit", "value": tail},
            ]

        # Execute query
        items = list(
            container.query_items(
                query=query,
                parameters=parameters,
                partition_key=agent_id,
                enable_cross_partition_query=False,
            )
        )

        # Convert to LogEntry objects
        for item in items:
            log_entry = LogEntry(
                timestamp=item.get("timestamp", ""),
                level=item.get("level", "INFO"),
                message=item.get("message", ""),
                agent_id=item.get("agent_id", ""),
                source=item.get("source", "agent"),
            )
            logs.append(log_entry)

        logger.info(f"Retrieved {len(logs)} logs for agent {agent_id}")

    except Exception as e:
        logger.error(f"Error querying logs from Cosmos DB: {e}")
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
        since: ISO 8601 timestamp to get logs after (for --follow mode)

    Response:
        200 OK: {
            "logs": [
                {
                    "timestamp": str (ISO 8601),
                    "level": str,
                    "message": str,
                    "agent_id": str,
                    "source": str
                }
            ]
        }

        404 Not Found: Agent not found
        500 Internal Server Error: Server error

    Example:
        GET /api/v1/agents/agent-123/logs
        GET /api/v1/agents/agent-123/logs?tail=50
        GET /api/v1/agents/agent-123/logs?since=2025-11-17T12:00:00Z
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
        tail = int(req.params.get("tail", "100"))
        since_timestamp = req.params.get("since")

        # Query logs from Cosmos DB
        logs = await query_logs_from_cosmosdb(
            agent_id=agent_id, tail=tail, since_timestamp=since_timestamp
        )

        # Format response
        response_data = {
            "logs": [
                {
                    "timestamp": log.timestamp,
                    "level": log.level,
                    "message": log.message,
                    "agent_id": log.agent_id,
                    "source": log.source,
                }
                for log in logs
            ]
        }

        return func.HttpResponse(
            body=json.dumps(response_data), status_code=200, mimetype="application/json"
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
