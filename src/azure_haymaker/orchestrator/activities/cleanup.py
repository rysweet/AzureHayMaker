"""Cleanup activities for Azure HayMaker orchestrator.

This module contains activity functions for verifying and forcing cleanup
of Azure resources and service principals.

Activities:
- verify_cleanup_activity: Verifies resources have been deleted
- force_cleanup_activity: Force-deletes remaining resources and SPs

Design Pattern: Activity Functions
- Stateless operations
- Can be retried
- Return structured results
"""

import logging
from datetime import UTC, datetime
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from azure_haymaker.models.service_principal import ServicePrincipalDetails as SPDetailsModel
from azure_haymaker.orchestrator.cleanup import force_delete_resources, query_managed_resources
from azure_haymaker.orchestrator.config import load_config
from azure_haymaker.orchestrator.orchestrator_app import app

logger = logging.getLogger(__name__)


@app.activity_trigger(input_name="params")
async def verify_cleanup_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Verify cleanup of resources.

    Queries Azure Resource Graph for resources tagged as AzureHayMaker-managed
    and verifies they have been deleted.

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - scenarios: List of scenario names

    Returns:
        Dictionary with remaining resources:
        {
            "remaining_resources": [
                {
                    "resource_id": str,
                    "resource_type": str,
                    "scenario_name": str
                }
            ]
        }
    """
    try:
        run_id = params.get("run_id")
        scenarios = params.get("scenarios", [])

        logger.info(f"Activity: verify_cleanup - Checking {len(scenarios)} scenarios")

        config = await load_config()
        # Ensure run_id is not None
        if not run_id:
            raise ValueError("run_id is required for cleanup verification")

        remaining_resources = await query_managed_resources(
            subscription_id=config.target_subscription_id,
            run_id=run_id,
        )

        logger.info(
            f"Activity: verify_cleanup - Found {len(remaining_resources)} remaining resources"
        )
        return {
            "remaining_resources": [
                {
                    "resource_id": r.resource_id,
                    "resource_type": r.resource_type,
                    "scenario_name": r.tags.get("Scenario", "unknown") if r.tags else "unknown",
                }
                for r in remaining_resources
            ],
        }
    except Exception as e:
        logger.error(f"Activity: verify_cleanup - Failed: {str(e)}", exc_info=True)
        return {
            "remaining_resources": [],
        }


@app.activity_trigger(input_name="params")
async def force_cleanup_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Force cleanup of remaining resources and service principals.

    Deletes all resources tagged as AzureHayMaker-managed for the run,
    with retry logic for dependencies. Also deletes service principals.

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - scenarios: List of scenario names
            - sp_details: List of service principal details

    Returns:
        Dictionary with cleanup results:
        {
            "status": "completed" | "partial_failure" | "failed",
            "deleted_count": int,
            "failed_count": int,
            "sp_deleted_count": int
        }
    """
    try:
        run_id = params.get("run_id")
        scenarios = params.get("scenarios", [])
        sp_details_list = params.get("sp_details", [])

        logger.info(
            f"Activity: force_cleanup - "
            f"run_id={run_id}, "
            f"scenarios={len(scenarios)}, "
            f"sps={len(sp_details_list)}"
        )

        config = await load_config()

        # Ensure run_id is not None
        if not run_id:
            raise ValueError("run_id is required for forced cleanup")

        # Query for resources to delete
        remaining_resources = await query_managed_resources(
            subscription_id=config.target_subscription_id,
            run_id=run_id,
        )

        # Create Key Vault client for SP secret deletion
        credential = DefaultAzureCredential()
        key_vault_client = SecretClient(vault_url=config.key_vault_url, credential=credential)

        # Convert sp_details dicts to ServicePrincipalDetails objects
        sp_details_objs = []
        for sp in sp_details_list:
            if not isinstance(sp, dict):
                continue
            created_at_str = sp.get("created_at")
            if created_at_str and isinstance(created_at_str, str):
                created_at_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            else:
                created_at_dt = datetime.now(UTC)

            sp_details_objs.append(
                SPDetailsModel(
                    sp_name=sp.get("sp_name", ""),
                    client_id=sp.get("client_id", ""),
                    principal_id=sp.get("principal_id", ""),
                    secret_reference=sp.get("secret_reference", ""),
                    created_at=created_at_dt,
                    scenario_name=sp.get("scenario_name", "unknown"),
                )
            )

        cleanup_report = await force_delete_resources(
            resources=remaining_resources,
            sp_details=sp_details_objs,
            kv_client=key_vault_client,
            subscription_id=config.target_subscription_id,
        )

        deleted_count = cleanup_report.total_resources_deleted
        failed_count = len([d for d in cleanup_report.deletions if d.status == "failed"])
        sp_deleted_count = len(cleanup_report.service_principals_deleted)

        # Determine status based on results
        status = (
            cleanup_report.status.value
            if hasattr(cleanup_report.status, "value")
            else str(cleanup_report.status)
        )

        # Map cleanup status to activity result
        if status == "verified":
            activity_status = "completed"
        elif status == "partial_failure":
            activity_status = "partial_failure"
        else:
            activity_status = "failed"

        logger.info(
            f"Activity: force_cleanup - "
            f"status={activity_status}, "
            f"deleted={deleted_count}, "
            f"failed={failed_count}, "
            f"sp_deleted={sp_deleted_count}"
        )

        return {
            "status": activity_status,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "sp_deleted_count": sp_deleted_count,
        }
    except Exception as e:
        logger.error(f"Activity: force_cleanup - Failed: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "deleted_count": 0,
            "failed_count": 0,
            "sp_deleted_count": 0,
            "error": str(e),
        }
