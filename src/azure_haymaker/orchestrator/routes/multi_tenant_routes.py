"""Multi-tenant execution route handlers.

Single Responsibility: Multi-tenant parallel execution orchestration.

Public API:
    router: FastAPI router with multi-tenant endpoints
    execute_multi_tenant: POST /execute/multi-tenant - Execute across tenants
    get_multi_tenant_execution: GET /executions/{id}/tenants - Get status
    list_multi_tenant_executions: GET /meta-executions - List all
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from azure_haymaker.models.execution import (
    MultiTenantExecutionRequest,
    MultiTenantExecutionResponse,
    TenantExecutionDetail,
    TenantExecutionStatusEnum,
)
from azure_haymaker.orchestrator.auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["multi-tenant"])

# Auth dependency type alias
AuthDep = Annotated[dict, Depends(require_auth)]

# Track multi-tenant meta-executions
meta_executions: dict[str, MultiTenantExecutionResponse] = {}

# Reference to run_orchestration function (injected by main app)
_run_orchestration_fn = None


def set_meta_executions_ref(meta_dict: dict[str, MultiTenantExecutionResponse]) -> None:
    """Set reference to meta_executions dictionary from main app."""
    global meta_executions
    meta_executions = meta_dict


def set_run_orchestration_fn(fn) -> None:
    """Set reference to run_orchestration function from main app."""
    global _run_orchestration_fn
    _run_orchestration_fn = fn


@router.post("/execute/multi-tenant", response_model=MultiTenantExecutionResponse, status_code=202)
async def execute_multi_tenant(_: AuthDep, request: MultiTenantExecutionRequest):
    """Execute orchestration across multiple tenants in parallel.

    This endpoint starts a meta-execution that runs orchestration for each
    specified tenant. Execution happens in parallel (up to max_parallelism).

    Requires authentication. Tenant IDs must exist in the tenant registry
    (loaded from Key Vault).

    Args:
        request: MultiTenantExecutionRequest with tenant IDs and parameters

    Returns:
        MultiTenantExecutionResponse with meta_execution_id and initial status

    Raises:
        HTTPException 400: If no valid tenants found
        HTTPException 500: If execution fails to start
    """
    from azure_haymaker.orchestrator.config import load_config_with_tenants
    from azure_haymaker.orchestrator.meta_orchestrator import (
        FailureMode,
        MetaExecutionRequest,
        MetaOrchestrator,
    )

    try:
        config = await load_config_with_tenants()

        if not config.has_multi_tenant_registry:
            raise HTTPException(
                status_code=400,
                detail="Multi-tenant registry is empty. Configure tenants in Key Vault first.",
            )

        internal_request = MetaExecutionRequest(
            tenant_ids=request.tenant_ids,
            scenarios=request.scenarios,
            scenario_count=request.scenario_count,
            duration_hours=request.duration_hours,
            max_parallelism=request.max_parallelism,
            failure_mode=FailureMode(request.failure_mode.value),
            skip_validation=request.skip_validation,
            tags=request.tags,
        )

        valid_tenants, invalid_ids = MetaOrchestrator.validate_tenants(config, request.tenant_ids)

        if not valid_tenants:
            raise HTTPException(
                status_code=400, detail=f"No valid tenants found. Invalid/disabled: {invalid_ids}"
            )

        meta_execution_id = str(uuid4())
        started_at = datetime.now(UTC)

        initial_statuses = [
            TenantExecutionDetail(
                tenant_id=t.tenant_id,
                tenant_display_name=t.display_name,
                status=TenantExecutionStatusEnum.PENDING,
            )
            for t in valid_tenants
        ]

        for invalid_id in invalid_ids:
            initial_statuses.append(
                TenantExecutionDetail(
                    tenant_id=invalid_id,
                    status=TenantExecutionStatusEnum.SKIPPED,
                    error_message="Tenant not found or disabled in registry",
                )
            )

        response = MultiTenantExecutionResponse(
            meta_execution_id=meta_execution_id,
            status="running",
            started_at=started_at,
            total_tenants=len(request.tenant_ids),
            skipped_count=len(invalid_ids),
            tenant_statuses=initial_statuses,
            failure_mode=request.failure_mode,
        )

        meta_executions[meta_execution_id] = response

        async def run_meta_execution():
            try:
                result = await MetaOrchestrator.execute(
                    config=config,
                    request=internal_request,
                    run_orchestration_fn=_run_orchestration_fn,
                )

                final_statuses = [
                    TenantExecutionDetail(
                        tenant_id=s.tenant_id,
                        tenant_display_name=s.tenant_display_name,
                        status=TenantExecutionStatusEnum(s.state.value),
                        execution_id=s.execution_id,
                        started_at=s.started_at,
                        completed_at=s.completed_at,
                        error_message=s.error_message,
                        scenarios_completed=s.scenarios_completed,
                        scenarios_failed=s.scenarios_failed,
                    )
                    for s in result.tenant_statuses
                ]

                meta_executions[meta_execution_id] = MultiTenantExecutionResponse(
                    meta_execution_id=result.meta_execution_id,
                    status="completed" if result.all_succeeded else "completed_with_failures",
                    started_at=result.started_at,
                    completed_at=result.completed_at,
                    total_tenants=result.total_tenants,
                    succeeded_count=result.succeeded_count,
                    failed_count=result.failed_count,
                    skipped_count=result.skipped_count,
                    tenant_statuses=final_statuses,
                    failure_mode=request.failure_mode,
                    aborted_early=result.aborted_early,
                )

            except Exception as e:
                logger.error(f"Meta-execution {meta_execution_id} failed: {e}", exc_info=True)
                meta_executions[meta_execution_id].status = "failed"

        asyncio.create_task(run_meta_execution())

        logger.info(
            f"Started multi-tenant execution {meta_execution_id} for {len(valid_tenants)} tenants"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start multi-tenant execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to start multi-tenant execution: {str(e)}"
        ) from e


@router.get("/executions/{meta_execution_id}/tenants", response_model=MultiTenantExecutionResponse)
async def get_multi_tenant_execution(meta_execution_id: str, _: AuthDep):
    """Get status of a multi-tenant execution.

    Returns the current status of all tenant executions within a meta-execution.

    Args:
        meta_execution_id: The meta-execution ID returned from POST /api/execute/multi-tenant

    Returns:
        MultiTenantExecutionResponse with current status of all tenants

    Raises:
        HTTPException 404: If meta_execution_id not found
    """
    if meta_execution_id not in meta_executions:
        raise HTTPException(
            status_code=404, detail=f"Multi-tenant execution not found: {meta_execution_id}"
        )

    return meta_executions[meta_execution_id]


@router.get("/meta-executions", response_model=list[MultiTenantExecutionResponse])
async def list_multi_tenant_executions(_: AuthDep):
    """List all multi-tenant executions.

    Returns:
        List of all meta-executions with their current status
    """
    return list(meta_executions.values())


__all__ = [
    "router",
    "execute_multi_tenant",
    "get_multi_tenant_execution",
    "list_multi_tenant_executions",
    "meta_executions",
    "set_meta_executions_ref",
    "set_run_orchestration_fn",
]
