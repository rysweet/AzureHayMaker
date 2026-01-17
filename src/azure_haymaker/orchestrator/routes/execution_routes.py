"""Execution management route handlers.

Single Responsibility: Execution lifecycle management.

Public API:
    router: FastAPI router with execution endpoints
    list_executions: GET /executions - List all executions
    get_execution: GET /executions/{id} - Get execution details
    get_execution_cost: GET /executions/{id}/cost - Get execution cost
    execute: POST /execute - Trigger manual execution
    validate: POST /validate - Validate environment
    list_scenarios: GET /scenarios - List available scenarios
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from azure_haymaker.orchestrator.auth import require_auth
from azure_haymaker.orchestrator.config import load_config
from azure_haymaker.orchestrator.cost_query import CostSummary, get_cost_summary
from azure_haymaker.orchestrator.scenario_selector import select_scenarios
from azure_haymaker.orchestrator.validation import validate_environment
from azure_haymaker.tracing import TraceContext, get_tracer
from azure_haymaker.tracing.instrumentation import add_span_attributes

logger = logging.getLogger(__name__)

router = APIRouter(tags=["executions"])

# Auth dependency type alias
AuthDep = Annotated[dict, Depends(require_auth)]

# Reference to executions dict (injected by main app)
executions: dict[str, dict[str, Any]] = {}

# Reference to run_orchestration function (injected by main app)
_run_orchestration_fn = None


def set_executions_ref(exec_dict: dict[str, dict[str, Any]]) -> None:
    """Set reference to executions dictionary from main app."""
    global executions
    executions = exec_dict


def set_run_orchestration_fn(fn) -> None:
    """Set reference to run_orchestration function from main app."""
    global _run_orchestration_fn
    _run_orchestration_fn = fn


@router.get("/executions")
async def list_executions(_: AuthDep):
    """List all executions. Requires authentication."""
    return {"executions": list(executions.values())}


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, _: AuthDep):
    """Get execution details. Requires authentication."""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    return executions[execution_id]


@router.get("/executions/{run_id}/cost", response_model=CostSummary)
async def get_execution_cost(run_id: str, _: AuthDep):
    """Get cost summary for an execution run.

    Queries Azure Cost Management for costs associated with this run,
    filtered by AzureHayMaker-managed=true and RunId={run_id} tags.

    Note: Azure Cost Management has approximately 24 hours delay before
    cost data becomes available. Recent runs may return empty or partial data.

    Args:
        run_id: Execution run ID

    Returns:
        CostSummary with cost breakdown by resource type and scenario

    Raises:
        HTTPException 404: If run_id is not found in executions
        HTTPException 500: If cost query fails
    """
    if run_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")

    try:
        config = await load_config()
        cost_summary = await get_cost_summary(
            subscription_id=config.target_subscription_id,
            run_id=run_id,
        )
        return cost_summary
    except Exception as e:
        logger.error(f"Failed to get cost summary for run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query costs: {str(e)}",
        ) from e


@router.post("/execute")
async def execute(_: AuthDep, request: dict[str, Any] | None = None):
    """Manually trigger an orchestration run. Requires authentication."""
    run_id = str(uuid4())
    skip_validation = request.get("skip_validation", False) if request else False
    logger.info(f"Manual execution triggered: run_id={run_id}, skip_validation={skip_validation}")

    tracer = get_tracer(__name__)
    with tracer.start_as_current_span(
        "execute-orchestration",
        attributes={
            "haymaker.run_id": run_id,
            "haymaker.skip_validation": skip_validation,
        },
    ) as span:
        trace_ctx = TraceContext.create_new(run_id=run_id)
        add_span_attributes(span, **{"haymaker.trace_id": trace_ctx.trace_id})

        if _run_orchestration_fn:
            asyncio.create_task(
                _run_orchestration_fn(
                    run_id, skip_validation=skip_validation, trace_context=trace_ctx
                )
            )
        else:
            logger.error("run_orchestration function not configured")

        return {
            "execution_id": run_id,
            "status": "started",
            "started_at": datetime.now(UTC).isoformat(),
            "trace_id": trace_ctx.trace_id,
        }


@router.post("/validate")
async def validate(_: AuthDep):
    """Validate environment configuration. Requires authentication."""
    try:
        config = await load_config()
        result = await validate_environment(config)
        return {
            "overall_passed": result.overall_passed,
            "results": [r.model_dump() for r in result.results],
        }
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/scenarios")
async def list_scenarios(_: AuthDep):
    """List available scenarios (small simulation size). Requires authentication."""
    try:
        from azure_haymaker.models.config import SimulationSize

        scenarios = select_scenarios(SimulationSize.SMALL)
        return {
            "scenarios": [
                {
                    "scenario_name": s.scenario_name,
                    "technology_area": s.technology_area,
                    "scenario_doc_path": s.scenario_doc_path,
                }
                for s in scenarios
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list scenarios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


__all__ = [
    "router",
    "list_executions",
    "get_execution",
    "get_execution_cost",
    "execute",
    "validate",
    "list_scenarios",
    "set_executions_ref",
    "set_run_orchestration_fn",
]
