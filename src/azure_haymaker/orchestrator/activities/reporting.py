"""Reporting activity for Azure HayMaker orchestrator.

This module contains the activity function for generating and storing
execution reports.

Design Pattern: Activity Function
- Stateless operation
- Can be retried
- Stores report to Azure Storage
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from azure_haymaker.orchestrator.config import load_config
from azure_haymaker.orchestrator.orchestrator_app import app

logger = logging.getLogger(__name__)


@app.activity_trigger(input_name="params")
async def generate_report_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Generate execution report and store to storage account.

    Creates final execution report summarizing:
    - Selected scenarios
    - Created resources
    - Cleanup status
    - Errors and warnings

    Stores report to Azure Storage Account.

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - execution_report: Full execution report data
            - selected_scenarios: List of selected scenario names
            - sp_count: Number of created service principals
            - container_count: Number of deployed containers

    Returns:
        Dictionary with report details:
        {
            "report_url": str,
            "report_id": str,
            "generated_at": str
        }
    """
    try:
        run_id = params.get("run_id")
        execution_report = params.get("execution_report", {})
        selected_scenarios = params.get("selected_scenarios", [])
        sp_count = params.get("sp_count", 0)
        container_count = params.get("container_count", 0)

        logger.info(
            f"Activity: generate_report - "
            f"run_id={run_id}, "
            f"scenarios={len(selected_scenarios)}, "
            f"sps={sp_count}, "
            f"containers={container_count}"
        )

        config = await load_config()
        credential = DefaultAzureCredential()

        # Store report to blob storage
        blob_service_client = BlobServiceClient(
            account_url=config.storage.account_url,
            credential=credential,
        )

        # Prepare report
        report = {
            "run_id": run_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "execution_report": execution_report,
            "summary": {
                "selected_scenarios": selected_scenarios,
                "scenario_count": len(selected_scenarios),
                "service_principals_created": sp_count,
                "containers_deployed": container_count,
            },
        }

        # Store to blob
        container_client = blob_service_client.get_container_client("execution-reports")
        blob_client = container_client.get_blob_client(f"{run_id}/report.json")
        await blob_client.upload_blob(json.dumps(report, indent=2), overwrite=True)  # type: ignore[misc]

        report_url = blob_client.url
        logger.info(f"Activity: generate_report - Report stored at {report_url}")

        return {
            "report_url": report_url,
            "report_id": run_id,
            "generated_at": report["generated_at"],
        }
    except Exception as e:
        logger.error(f"Activity: generate_report - Failed: {str(e)}", exc_info=True)
        return {
            "report_url": "",
            "report_id": params.get("run_id"),
            "error": str(e),
        }
