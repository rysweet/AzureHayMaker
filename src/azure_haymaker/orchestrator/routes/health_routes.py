"""Health and status route handlers.

Single Responsibility: Server health, status, and infrastructure queries.

Public API:
    router: FastAPI router with health endpoints
    health: GET / - Health check (unauthenticated)
    status: GET /status - Orchestrator status (authenticated)
    list_resources: GET /resources - List HayMaker-managed resources
    list_agents: GET /agents - List agent executions
"""

import logging
import os
from datetime import UTC, datetime
from typing import Annotated, Any

from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from fastapi import APIRouter, Depends, HTTPException, Query

from azure_haymaker.orchestrator.auth import require_auth
from azure_haymaker.orchestrator.cleanup import query_managed_resources
from azure_haymaker.orchestrator.config import load_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Auth dependency type alias
AuthDep = Annotated[dict, Depends(require_auth)]

# Reference to executions dict (injected by main app)
executions: dict[str, dict[str, Any]] = {}


def set_executions_ref(exec_dict: dict[str, dict[str, Any]]) -> None:
    """Set reference to executions dictionary from main app."""
    global executions
    executions = exec_dict


@router.get("/")
async def health():
    """Health check endpoint (unauthenticated).

    Returns basic health status for load balancer probes.
    """
    return {
        "status": "healthy",
        "service": "azure-haymaker-orchestrator",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/status")
async def status(_: AuthDep):
    """Get orchestrator status. Requires authentication.

    Returns current orchestrator status including active execution count.
    """
    running = [e for e in executions.values() if e["status"] == "running"]
    return {
        "status": "running" if running else "idle",
        "service": "azure-haymaker-orchestrator",
        "timestamp": datetime.now(UTC).isoformat(),
        "executions_active": len(running),
        "executions_total": len(executions),
    }


@router.get("/resources")
async def list_resources(
    _: AuthDep,
    execution_id: str | None = Query(None, description="Filter by execution ID"),
    scenario: str | None = Query(None, description="Filter by scenario name"),
    status: str | None = Query(None, description="Filter by status (created/deleted)"),
    limit: int = Query(100, description="Maximum number of results"),
):
    """List all HayMaker-managed resources in the tenant. Requires authentication.

    Queries Azure Resource Graph for all resources tagged with AzureHayMaker-managed=true.

    Args:
        execution_id: Optional filter by execution ID
        scenario: Optional filter by scenario name
        status: Optional filter by status
        limit: Maximum results (default 100)

    Returns:
        List of resources with metadata
    """
    try:
        config = await load_config()
        # query_managed_resources requires non-None run_id, skip if None
        if not execution_id:
            return {"resources": [], "count": 0}

        resources = await query_managed_resources(
            subscription_id=config.target_subscription_id,
            run_id=execution_id,
        )

        # Apply filters
        filtered_resources = resources
        if scenario:
            filtered_resources = [
                r for r in filtered_resources if scenario.lower() in r.resource_name.lower()
            ]

        # Limit results
        filtered_resources = filtered_resources[:limit]

        def parse_resource_id(resource_id: str) -> tuple[str, str]:
            """Extract resource group from Azure resource ID."""
            parts = resource_id.split("/")
            rg_idx = parts.index("resourceGroups") + 1 if "resourceGroups" in parts else -1
            rg = parts[rg_idx] if rg_idx > 0 and rg_idx < len(parts) else "unknown"
            return rg, ""

        return {
            "resources": [
                {
                    "id": r.resource_id,
                    "name": r.resource_name,
                    "type": r.resource_type,
                    "resourceGroup": parse_resource_id(r.resource_id)[0],
                    "location": parse_resource_id(r.resource_id)[1],
                    "tags": r.tags,
                }
                for r in filtered_resources
            ],
            "count": len(filtered_resources),
            "total_found": len(resources),
        }
    except Exception as e:
        logger.error(f"Failed to list resources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/agents")
async def list_agents(
    _: AuthDep,
    status: str | None = Query(None, description="Filter by status (running/completed/failed)"),
    limit: int = Query(100, description="Maximum number of results"),
):
    """List all agents. Requires authentication.

    Queries Table Storage for agent execution information.

    Args:
        status: Optional status filter
        limit: Maximum results (default 100)

    Returns:
        List of agents with metadata
    """
    try:
        from azure_haymaker.orchestrator.agents_api import query_agents_from_table

        table_account_name = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
        table_name = os.getenv("AGENTS_TABLE_NAME", "agents")

        if not table_account_name:
            raise HTTPException(
                status_code=500,
                detail="Agents storage not configured. Set TABLE_STORAGE_ACCOUNT_NAME.",
            )

        credential = DefaultAzureCredential()
        table_service_client = TableServiceClient(
            endpoint=f"https://{table_account_name}.table.core.windows.net",
            credential=credential,
        )
        table_client = table_service_client.get_table_client(table_name)

        agents = await query_agents_from_table(
            table_client,
            status_filter=status,
            limit=limit,
        )

        return {
            "agents": [agent.model_dump(mode="json") for agent in agents],
            "count": len(agents),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


__all__ = [
    "router",
    "health",
    "status",
    "list_resources",
    "list_agents",
    "set_executions_ref",
]
