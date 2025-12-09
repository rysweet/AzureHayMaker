"""Meta-orchestrator for multi-tenant execution.

This module implements the "orchestrator of orchestrators" pattern that spawns
and manages individual tenant orchestrators concurrently.

Design Pattern: Fan-out/Fan-in
- Spawns child orchestrators (one per tenant)
- Waits for all to complete (fan-in)
- Aggregates results and generates meta-report

Phase 2: Orchestrator Integration
"""

import logging
from typing import Any

from azure.durable_functions import DurableOrchestrationContext

from azure_haymaker.orchestrator.models.tenant_config import (
    MetaOrchestratorConfig,
    TenantContext,
)
from azure_haymaker.orchestrator.orchestrator_app import app

logger = logging.getLogger(__name__)


@app.orchestration_trigger(context_name="context")
def orchestrate_multi_tenant_run(context: DurableOrchestrationContext) -> dict[str, Any]:
    """Meta-orchestrator durable function that manages multiple tenant orchestrations.

    This is the "orchestrator of orchestrators" that:
    1. Loads multi-tenant configuration
    2. Validates credentials for all target tenants
    3. Spawns child orchestrators (one per tenant) with concurrency control
    4. Monitors all child orchestrations
    5. Aggregates results and generates meta-report

    Args:
        context: Durable orchestration context

    Returns:
        Meta-orchestration result with tenant status summary

    Example input:
        {
            "meta_run_id": "meta-abc123",
            "meta_config": {...},  // MetaOrchestratorConfig dict
            "started_at": "2025-12-09T12:00:00Z"
        }

    Example output:
        {
            "meta_run_id": "meta-abc123",
            "started_at": "2025-12-09T12:00:00Z",
            "ended_at": "2025-12-09T20:00:00Z",
            "total_tenants": 3,
            "enabled_tenants": 2,
            "succeeded_tenants": 2,
            "failed_tenants": 0,
            "succeeded_tenant_names": ["tenant-a", "tenant-b"],
            "failed_tenant_names": [],
            "tenant_results": {...},
            "status": "completed"
        }
    """
    # Extract and validate input
    input_data = context.get_input()

    # Validate required fields present
    if "meta_run_id" not in input_data or not input_data["meta_run_id"]:
        raise ValueError("meta_run_id is required in orchestration input")
    if "meta_config" not in input_data or not input_data["meta_config"]:
        raise ValueError("meta_config is required in orchestration input")

    meta_run_id = input_data["meta_run_id"]
    meta_config_dict = input_data["meta_config"]

    # Reconstruct MetaOrchestratorConfig
    # The dict might use nested structure (meta_orchestrator + target_tenants)
    # or flat structure - handle both
    if "meta_orchestrator" in meta_config_dict:
        # Nested structure - flatten it
        flat_config = {**meta_config_dict["meta_orchestrator"]}
        flat_config["target_tenants"] = meta_config_dict["target_tenants"]
        meta_config = MetaOrchestratorConfig(**flat_config)
    else:
        # Already flat
        meta_config = MetaOrchestratorConfig(**meta_config_dict)

    logger.info(
        f"Meta-orchestration {meta_run_id} starting with {len(meta_config.target_tenants)} tenants"
    )

    # Track tenant results
    tenant_results = {}
    succeeded_tenants = []
    failed_tenants = []

    # Spawn child orchestrators for each enabled tenant (with concurrency control)
    tasks = []
    for target_tenant in meta_config.target_tenants:
        if not target_tenant.enabled:
            logger.info(f"Skipping disabled tenant: {target_tenant.name}")
            continue

        # Create tenant context
        tenant_context = TenantContext(
            tenant_id=target_tenant.tenant_id,
            tenant_name=target_tenant.name,
            subscription_id=target_tenant.subscription_id,
            region=target_tenant.region,
        )

        # Prepare child orchestrator input
        # The child orchestrator expects specific format matching workflow_orchestrator.py
        child_input = {
            "run_id": f"{target_tenant.name}-{meta_run_id}",
            "tenant_context": tenant_context.model_dump(),
            "started_at": context.current_utc_datetime.isoformat(),
            "config": {
                "scenarios": target_tenant.scenarios,
                "max_scenarios": target_tenant.max_scenarios_per_execution,
                "resource_tags": target_tenant.resource_tags,
                "limits": target_tenant.limits,
            },
        }

        # Spawn sub-orchestration (calls orchestrate_haymaker_run)
        task = context.call_sub_orchestrator(
            "orchestrate_haymaker_run",
            input_=child_input,
            instance_id=f"{meta_run_id}-{target_tenant.name}",
        )
        tasks.append((target_tenant.name, task))

    # Wait for all child orchestrations with timeout
    logger.info(f"Waiting for {len(tasks)} tenant orchestrations to complete")

    # Use fan-in pattern to collect results
    for tenant_name, task in tasks:
        try:
            result = yield task
            tenant_results[tenant_name] = result
            succeeded_tenants.append(tenant_name)
            logger.info(f"Tenant {tenant_name} orchestration succeeded")
        except Exception as e:
            logger.error(f"Tenant {tenant_name} orchestration failed: {e}", exc_info=True)
            tenant_results[tenant_name] = {"status": "failed", "error": str(e)}
            failed_tenants.append(tenant_name)

    # Generate meta-report
    meta_report = {
        "meta_run_id": meta_run_id,
        "started_at": input_data.get("started_at"),
        "ended_at": context.current_utc_datetime.isoformat(),
        "total_tenants": len(meta_config.target_tenants),
        "enabled_tenants": len(tasks),
        "succeeded_tenants": len(succeeded_tenants),
        "failed_tenants": len(failed_tenants),
        "succeeded_tenant_names": succeeded_tenants,
        "failed_tenant_names": failed_tenants,
        "tenant_results": tenant_results,
        "status": (
            "completed"
            if not failed_tenants
            else "partial"
            if succeeded_tenants
            else "failed"
        ),
    }

    logger.info(
        f"Meta-orchestration {meta_run_id} complete: "
        f"{len(succeeded_tenants)} succeeded, {len(failed_tenants)} failed"
    )

    return meta_report
