"""Metrics API endpoint for HayMaker orchestrator."""

import logging
from datetime import datetime, timedelta, timezone

import azure.functions as func
from azure.cosmos import CosmosClient
from pydantic import BaseModel, Field

app = func.FunctionApp()
logger = logging.getLogger(__name__)


class ScenarioMetrics(BaseModel):
    """Per-scenario metrics."""

    scenario_name: str
    run_count: int
    success_count: int
    fail_count: int
    avg_duration_hours: float | None = None


class MetricsSummary(BaseModel):
    """Metrics summary response."""

    total_executions: int
    active_agents: int
    total_resources: int
    last_execution: datetime | None = None
    success_rate: float
    period: str = "7d"
    scenarios: list[ScenarioMetrics] = Field(default_factory=list)


def parse_period(period: str) -> timedelta:
    """Parse period string to timedelta.

    Args:
        period: Period string (7d, 30d, 90d)

    Returns:
        Timedelta representing the period

    Raises:
        ValueError: If period format is invalid
    """
    if period.endswith("d"):
        days = int(period[:-1])
        return timedelta(days=days)
    else:
        raise ValueError(f"Invalid period format: {period}. Must be like '7d', '30d', '90d'")


async def query_cosmos_metrics(
    cosmos_client: CosmosClient,
    database_name: str,
    container_name: str,
    start_time: datetime,
    scenario_filter: str | None = None,
) -> dict:
    """Query metrics from Cosmos DB.

    Args:
        cosmos_client: Cosmos DB client
        database_name: Database name
        container_name: Container name
        start_time: Start time for query
        scenario_filter: Optional scenario name filter

    Returns:
        Dictionary with aggregated metrics
    """
    database = cosmos_client.get_database_client(database_name)
    container = database.get_container_client(container_name)

    # Build query
    query = """
        SELECT
            c.scenario_name,
            c.status,
            c.started_at,
            c.completed_at,
            c.execution_id
        FROM c
        WHERE c.started_at >= @start_time
    """

    params = [{"name": "@start_time", "value": start_time.isoformat()}]

    if scenario_filter:
        query += " AND c.scenario_name = @scenario"
        params.append({"name": "@scenario", "value": scenario_filter})

    # Execute query
    items = list(
        container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        )
    )

    # Aggregate metrics
    scenario_stats: dict[str, dict] = {}
    total_executions = len(items)
    success_count = 0
    last_execution = None

    for item in items:
        scenario_name = item.get("scenario_name", "unknown")
        status = item.get("status", "unknown")
        started_at = item.get("started_at")
        completed_at = item.get("completed_at")

        # Track scenario stats
        if scenario_name not in scenario_stats:
            scenario_stats[scenario_name] = {
                "run_count": 0,
                "success_count": 0,
                "fail_count": 0,
                "total_duration": 0,
                "duration_count": 0,
            }

        stats = scenario_stats[scenario_name]
        stats["run_count"] += 1

        if status == "completed":
            stats["success_count"] += 1
            success_count += 1
        elif status == "failed":
            stats["fail_count"] += 1

        # Calculate duration
        if started_at and completed_at:
            try:
                start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                duration = (end - start).total_seconds() / 3600  # hours
                stats["total_duration"] += duration
                stats["duration_count"] += 1
            except (ValueError, AttributeError):
                pass

        # Track latest execution
        if started_at:
            try:
                execution_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                if last_execution is None or execution_time > last_execution:
                    last_execution = execution_time
            except (ValueError, AttributeError):
                pass

    # Build scenario metrics
    scenario_metrics = []
    for scenario_name, stats in scenario_stats.items():
        avg_duration = None
        if stats["duration_count"] > 0:
            avg_duration = stats["total_duration"] / stats["duration_count"]

        scenario_metrics.append(
            ScenarioMetrics(
                scenario_name=scenario_name,
                run_count=stats["run_count"],
                success_count=stats["success_count"],
                fail_count=stats["fail_count"],
                avg_duration_hours=avg_duration,
            )
        )

    # Sort by run count (descending)
    scenario_metrics.sort(key=lambda x: x.run_count, reverse=True)

    # Calculate success rate
    success_rate = success_count / total_executions if total_executions > 0 else 0.0

    return {
        "total_executions": total_executions,
        "success_count": success_count,
        "success_rate": success_rate,
        "last_execution": last_execution,
        "scenario_metrics": scenario_metrics,
    }


@app.route(route="metrics", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def get_metrics(req: func.HttpRequest) -> func.HttpResponse:
    """Get aggregated execution metrics.

    Query Parameters:
        period: Time period (7d, 30d, 90d) - default: 7d
        scenario: Optional scenario name filter

    Response:
        200 OK: {
            "total_executions": int,
            "active_agents": int,
            "total_resources": int,
            "last_execution": str (ISO 8601) | null,
            "success_rate": float,
            "period": str,
            "scenarios": [
                {
                    "scenario_name": str,
                    "run_count": int,
                    "success_count": int,
                    "fail_count": int,
                    "avg_duration_hours": float | null
                }
            ]
        }

        400 Bad Request: Invalid query parameters
        500 Internal Server Error: Server error

    Example:
        GET /api/v1/metrics?period=30d
        GET /api/v1/metrics?period=7d&scenario=compute-01
    """
    try:
        # Parse query parameters
        period = req.params.get("period", "7d")
        scenario_filter = req.params.get("scenario")

        # Validate period
        try:
            period_delta = parse_period(period)
        except ValueError as e:
            return func.HttpResponse(
                body=str(e),
                status_code=400,
                mimetype="application/json",
            )

        # Calculate start time
        start_time = datetime.now(timezone.utc) - period_delta

        # Get Cosmos DB configuration from environment
        import os

        cosmos_endpoint = os.getenv("COSMOSDB_ENDPOINT")
        cosmos_database = os.getenv("COSMOSDB_DATABASE", "haymaker")
        cosmos_container = os.getenv("COSMOSDB_METRICS_CONTAINER", "execution_metrics")

        if not cosmos_endpoint:
            logger.error("COSMOSDB_ENDPOINT not configured")
            return func.HttpResponse(
                body='{"error": "Metrics database not configured"}',
                status_code=500,
                mimetype="application/json",
            )

        # Create Cosmos DB client (using managed identity)
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        cosmos_client = CosmosClient(cosmos_endpoint, credential)

        # Query metrics
        metrics_data = await query_cosmos_metrics(
            cosmos_client,
            cosmos_database,
            cosmos_container,
            start_time,
            scenario_filter,
        )

        # Get active agents count (query from Table Storage or return 0)
        active_agents = 0
        total_resources = 0

        # Build response
        summary = MetricsSummary(
            total_executions=metrics_data["total_executions"],
            active_agents=active_agents,
            total_resources=total_resources,
            last_execution=metrics_data["last_execution"],
            success_rate=metrics_data["success_rate"],
            period=period,
            scenarios=metrics_data["scenario_metrics"],
        )

        return func.HttpResponse(
            body=summary.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.exception("Error retrieving metrics")
        return func.HttpResponse(
            body=f'{{"error": "{str(e)}"}}',
            status_code=500,
            mimetype="application/json",
        )
