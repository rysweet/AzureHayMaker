"""Analytics and metrics route handlers.

Single Responsibility: Analytics aggregation and metrics endpoints.

Public API:
    router: FastAPI router with analytics endpoints
    metrics: GET /metrics - Get execution metrics
    get_analytics: GET /analytics - Get analytics summary
"""

import json
import logging
import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from azure.data.tables import TableServiceClient
from fastapi import APIRouter, Depends, HTTPException, Query

from azure_haymaker.models.execution import (
    AnalyticsSummary,
    ExecutionCounts,
    ScenarioStats,
)
from azure_haymaker.orchestrator.auth import require_auth
from azure_haymaker.utils.credentials import get_credential

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])

# Auth dependency type alias
AuthDep = Annotated[dict, Depends(require_auth)]

# Reference to executions dict (injected by main app)
executions: dict[str, dict[str, Any]] = {}


def set_executions_ref(exec_dict: dict[str, dict[str, Any]]) -> None:
    """Set reference to executions dictionary from main app."""
    global executions
    executions = exec_dict


@router.get("/metrics")
async def metrics(_: AuthDep):
    """Get execution metrics. Requires authentication."""
    total_execs = len(executions)
    completed = len([e for e in executions.values() if e["status"] == "completed"])

    return {
        "total_executions": total_execs,
        "active_agents": len([e for e in executions.values() if e["status"] == "running"]),
        "total_resources": 0,
        "success_rate": (completed / total_execs) if total_execs > 0 else 0.0,
        "last_execution": None,
        "period": "7d",
    }


@router.get("/analytics", response_model=AnalyticsSummary)
async def get_analytics(
    _: AuthDep,
    period: Literal["7d", "30d", "90d"] = Query(
        default="30d",
        description="Time period for analytics (7d, 30d, or 90d)",
    ),
) -> AnalyticsSummary:
    """Get analytics summary for the dashboard. Requires authentication.

    Queries Table Storage for execution history and aggregates statistics
    for the specified time period.

    Args:
        period: Time period to analyze (7d, 30d, or 90d)

    Returns:
        AnalyticsSummary with execution counts, success rate, and top scenarios
    """
    try:
        period_days = {"7d": 7, "30d": 30, "90d": 90}[period]
        cutoff_date = datetime.now(UTC) - timedelta(days=period_days)

        table_storage_account = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
        if not table_storage_account:
            logger.warning("TABLE_STORAGE_ACCOUNT_NAME not set, returning empty analytics")
            return AnalyticsSummary(
                period=period,
                executions=ExecutionCounts(total=0, succeeded=0, failed=0),
                success_rate=0.0,
                avg_duration_hours=0.0,
                top_scenarios=[],
            )

        credential = get_credential()
        table_service = TableServiceClient(
            endpoint=f"https://{table_storage_account}.table.core.windows.net",
            credential=credential,
        )
        table_client = table_service.get_table_client("ExecutionRuns")

        cutoff_iso = cutoff_date.isoformat()
        query_filter = f"CreatedAt ge datetime'{cutoff_iso}'"

        total_executions = 0
        succeeded_executions = 0
        failed_executions = 0
        total_duration_hours = 0.0
        duration_count = 0
        scenario_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"count": 0, "succeeded": 0, "failed": 0}
        )

        seen_execution_ids: set[str] = set()

        try:
            entities = table_client.query_entities(query_filter=query_filter)
            for entity in entities:
                execution_id = entity.get("PartitionKey", "")

                if execution_id in seen_execution_ids:
                    continue
                seen_execution_ids.add(execution_id)

                total_executions += 1

                status = entity.get("Status", "")
                if status in ("completed", "COMPLETED"):
                    succeeded_executions += 1
                elif status in ("failed", "FAILED", "error", "ERROR"):
                    failed_executions += 1

                created_at_str = entity.get("CreatedAt")
                completed_at_str = entity.get("CompletedAt")
                if created_at_str and completed_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        completed_at = datetime.fromisoformat(
                            completed_at_str.replace("Z", "+00:00")
                        )
                        duration = (completed_at - created_at).total_seconds() / 3600
                        if duration > 0:
                            total_duration_hours += duration
                            duration_count += 1
                    except (ValueError, TypeError) as e:
                        logger.debug(
                            f"Failed to parse timestamps for execution {execution_id}: {e}"
                        )

                scenarios_json = entity.get("Scenarios", "[]")
                try:
                    scenarios = json.loads(scenarios_json)
                    for scenario_name in scenarios:
                        scenario_stats[scenario_name]["count"] += 1
                        if status in ("completed", "COMPLETED"):
                            scenario_stats[scenario_name]["succeeded"] += 1
                        elif status in ("failed", "FAILED", "error", "ERROR"):
                            scenario_stats[scenario_name]["failed"] += 1
                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug(
                        f"Failed to parse scenarios JSON for execution {execution_id}: {e}"
                    )

        except Exception as e:
            logger.warning(f"Failed to query Table Storage: {e}")
            return AnalyticsSummary(
                period=period,
                executions=ExecutionCounts(total=0, succeeded=0, failed=0),
                success_rate=0.0,
                avg_duration_hours=0.0,
                top_scenarios=[],
            )

        success_rate = succeeded_executions / total_executions if total_executions > 0 else 0.0
        avg_duration = total_duration_hours / duration_count if duration_count > 0 else 0.0

        top_scenarios = sorted(
            [
                ScenarioStats(
                    name=name,
                    count=stats["count"],
                    success_rate=(
                        stats["succeeded"] / stats["count"] if stats["count"] > 0 else 0.0
                    ),
                )
                for name, stats in scenario_stats.items()
            ],
            key=lambda s: s.count,
            reverse=True,
        )[:10]

        return AnalyticsSummary(
            period=period,
            executions=ExecutionCounts(
                total=total_executions,
                succeeded=succeeded_executions,
                failed=failed_executions,
            ),
            success_rate=round(success_rate, 4),
            avg_duration_hours=round(avg_duration, 2),
            top_scenarios=top_scenarios,
        )

    except Exception as e:
        logger.error(f"Failed to get analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


__all__ = [
    "router",
    "metrics",
    "get_analytics",
    "set_executions_ref",
]
