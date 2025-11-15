"""Queue processor for on-demand execution requests.

This module processes execution requests from Service Bus queue and
orchestrates container deployment, monitoring, and cleanup.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import azure.functions as func
from azure.data.tables import TableClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

from azure_haymaker.models.execution import OnDemandExecutionStatus
from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.orchestrator.cleanup import (
    force_delete_resources,
    query_managed_resources,
)
from azure_haymaker.orchestrator.config import load_config
from azure_haymaker.orchestrator.container_manager import (
    ContainerManager,
    deploy_container_app,
)
from azure_haymaker.orchestrator.execution_tracker import ExecutionTracker
from azure_haymaker.orchestrator.sp_manager import create_service_principal

logger = logging.getLogger(__name__)

# Azure Functions app instance
app = func.FunctionApp()


def load_scenario_metadata(scenario_name: str) -> ScenarioMetadata | None:
    """Load scenario metadata from docs directory.

    Args:
        scenario_name: Scenario name to load

    Returns:
        ScenarioMetadata or None if not found

    Example:
        >>> scenario = load_scenario_metadata("compute-01-linux-vm-web-server")
        >>> if scenario:
        ...     print(scenario.technology_area)
    """
    project_root = Path(__file__).parent.parent.parent.parent
    scenarios_dir = project_root / "docs" / "scenarios"

    if not scenarios_dir.exists():
        logger.error(f"Scenarios directory not found: {scenarios_dir}")
        return None

    # Search for scenario file
    for scenario_file in scenarios_dir.glob("**/*.md"):
        if scenario_name in scenario_file.stem:
            # Extract technology area from directory structure
            technology_area = scenario_file.parent.name

            return ScenarioMetadata(
                scenario_name=scenario_name,
                scenario_doc_path=str(scenario_file),
                technology_area=technology_area,
            )

    logger.error(f"Scenario not found: {scenario_name}")
    return None


@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="execution-requests",
    connection="ServiceBusConnection",
)
async def process_execution(msg: func.ServiceBusMessage) -> None:
    """Process execution request from Service Bus queue.

    Message Body: {
        "execution_id": str,
        "scenarios": list[str],
        "duration_hours": int,
        "tags": dict[str, str],
        "requested_at": str
    }

    Side Effects:
        - Creates service principals for each scenario
        - Deploys Container Apps for each scenario
        - Updates execution status in Table Storage
        - Monitors execution for duration_hours
        - Verifies cleanup and forces deletion if needed
        - Stores execution report to Blob Storage

    Args:
        msg: Service Bus message with execution request
    """
    execution_id = None

    try:
        # Parse message body
        message_body = json.loads(msg.get_body().decode("utf-8"))
        execution_id = message_body.get("execution_id")
        scenarios = message_body.get("scenarios", [])
        duration_hours = message_body.get("duration_hours", 8)
        tags = message_body.get("tags", {})

        logger.info(
            f"Processing execution request: {execution_id}, scenarios={len(scenarios)}, duration={duration_hours}h"
        )

        # Load config
        config = await load_config()
        credential = DefaultAzureCredential()

        # Initialize tracker
        execution_table = TableClient(
            endpoint=config.table_storage.account_url,
            table_name="Executions",
            credential=credential,
        )
        tracker = ExecutionTracker(execution_table)

        # Update status to RUNNING
        await tracker.update_status(
            execution_id=execution_id,
            status=OnDemandExecutionStatus.RUNNING,
        )

        # ========================================================================
        # PHASE 1: SERVICE PRINCIPAL CREATION
        # ========================================================================
        logger.info(f"[{execution_id}] Creating service principals...")

        key_vault_client = SecretClient(vault_url=config.key_vault_url, credential=credential)

        sp_details_list = []
        for scenario_name in scenarios:
            try:
                sp_details = await create_service_principal(
                    scenario_name=scenario_name,
                    subscription_id=config.target_subscription_id,
                    roles=["Contributor", "Reader"],
                    key_vault_client=key_vault_client,
                )
                sp_details_list.append((scenario_name, sp_details))
                logger.info(f"[{execution_id}] Created SP for {scenario_name}")
            except Exception as e:
                logger.error(f"[{execution_id}] Failed to create SP for {scenario_name}: {e}")
                # Continue with other scenarios

        if not sp_details_list:
            logger.error(f"[{execution_id}] No service principals created, aborting")
            await tracker.update_status(
                execution_id=execution_id,
                status=OnDemandExecutionStatus.FAILED,
                error_message="Failed to create any service principals",
            )
            return

        # ========================================================================
        # PHASE 2: CONTAINER APP DEPLOYMENT
        # ========================================================================
        logger.info(f"[{execution_id}] Deploying container apps...")

        container_ids = []
        for scenario_name, sp_details in sp_details_list:
            try:
                scenario_metadata = load_scenario_metadata(scenario_name)
                if not scenario_metadata:
                    logger.warning(f"[{execution_id}] Scenario metadata not found: {scenario_name}")
                    continue

                container_details = await deploy_container_app(
                    scenario=scenario_metadata,
                    sp=sp_details,
                    config=config,
                )

                container_id = container_details.get("name")
                container_ids.append(container_id)
                logger.info(f"[{execution_id}] Deployed container: {container_id}")

            except Exception as e:
                logger.error(
                    f"[{execution_id}] Failed to deploy container for {scenario_name}: {e}"
                )
                # Continue with other scenarios

        if not container_ids:
            logger.error(f"[{execution_id}] No containers deployed, aborting")
            await tracker.update_status(
                execution_id=execution_id,
                status=OnDemandExecutionStatus.FAILED,
                error_message="Failed to deploy any containers",
            )
            return

        # Update tracker with container IDs
        await tracker.update_status(
            execution_id=execution_id,
            status=OnDemandExecutionStatus.RUNNING,
            container_ids=container_ids,
        )

        # ========================================================================
        # PHASE 3: MONITORING
        # ========================================================================
        logger.info(f"[{execution_id}] Monitoring execution for {duration_hours} hours...")

        container_manager = ContainerManager(config)
        end_time = datetime.now(UTC) + timedelta(hours=duration_hours)

        # Monitor periodically (every 15 minutes)
        while datetime.now(UTC) < end_time:
            running_count = 0
            completed_count = 0
            failed_count = 0

            for container_id in container_ids:
                try:
                    status = await container_manager.get_container_status(container_id)
                    if status in ["Running", "Processing"]:
                        running_count += 1
                    elif status == "Terminated":
                        completed_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.warning(f"[{execution_id}] Failed to check {container_id}: {e}")
                    failed_count += 1

            logger.info(
                f"[{execution_id}] Status check: running={running_count}, "
                f"completed={completed_count}, failed={failed_count}"
            )

            # Check if all completed
            if running_count == 0:
                logger.info(f"[{execution_id}] All containers completed/failed")
                break

            # Wait 15 minutes before next check
            await asyncio.sleep(900)  # 15 minutes

        # ========================================================================
        # PHASE 4: CLEANUP VERIFICATION
        # ========================================================================
        logger.info(f"[{execution_id}] Verifying cleanup...")

        remaining_resources = await query_managed_resources(
            subscription_id=config.target_subscription_id,
            run_id=execution_id,
        )

        logger.info(
            f"[{execution_id}] Found {len(remaining_resources)} remaining resources"
        )

        # ========================================================================
        # PHASE 5: FORCED CLEANUP
        # ========================================================================
        if remaining_resources:
            logger.warning(f"[{execution_id}] Starting forced cleanup...")

            cleanup_report = await force_delete_resources(
                subscription_id=config.target_subscription_id,
                run_id=execution_id,
                sp_details_list=[sp for _, sp in sp_details_list],
            )

            logger.info(
                f"[{execution_id}] Cleanup complete: "
                f"deleted={cleanup_report.total_resources_deleted}, "
                f"sps={len(cleanup_report.service_principals_deleted)}"
            )
        else:
            logger.info(f"[{execution_id}] No cleanup needed")

        # ========================================================================
        # PHASE 6: REPORT GENERATION
        # ========================================================================
        logger.info(f"[{execution_id}] Generating execution report...")

        report = {
            "execution_id": execution_id,
            "scenarios": scenarios,
            "duration_hours": duration_hours,
            "tags": tags,
            "service_principals_created": len(sp_details_list),
            "containers_deployed": len(container_ids),
            "resources_remaining": len(remaining_resources),
            "completed_at": datetime.now(UTC).isoformat(),
        }

        # Store report to blob storage
        blob_service_client = BlobServiceClient(
            account_url=config.storage.account_url,
            credential=credential,
        )

        container_client = blob_service_client.get_container_client("execution-reports")
        blob_client = container_client.get_blob_client(f"{execution_id}/report.json")
        await blob_client.upload_blob(json.dumps(report, indent=2), overwrite=True)

        report_url = blob_client.url
        logger.info(f"[{execution_id}] Report stored: {report_url}")

        # ========================================================================
        # FINAL STATUS UPDATE
        # ========================================================================
        await tracker.update_status(
            execution_id=execution_id,
            status=OnDemandExecutionStatus.COMPLETED,
            resources_created=len(sp_details_list) + len(container_ids),
            report_url=report_url,
        )

        logger.info(f"[{execution_id}] Execution completed successfully")

    except Exception as e:
        logger.error(f"[{execution_id}] Execution failed: {e}", exc_info=True)

        # Update status to FAILED
        if execution_id:
            try:
                config = await load_config()
                credential = DefaultAzureCredential()
                execution_table = TableClient(
                    endpoint=config.table_storage.account_url,
                    table_name="Executions",
                    credential=credential,
                )
                tracker = ExecutionTracker(execution_table)

                await tracker.update_status(
                    execution_id=execution_id,
                    status=OnDemandExecutionStatus.FAILED,
                    error_message=str(e),
                )
            except Exception as update_error:
                logger.error(f"Failed to update status: {update_error}")
