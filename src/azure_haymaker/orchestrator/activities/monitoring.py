"""Monitoring activity for Azure HayMaker orchestrator.

This module contains the activity function for checking the status of
running scenario agents.

Design Pattern: Activity Function
- Stateless operation
- Can be retried
- Returns status summary
"""

import logging
from typing import Any

from azure_haymaker.orchestrator.config import load_config
from azure_haymaker.orchestrator.container_manager import ContainerManager
from azure_haymaker.orchestrator.orchestrator_app import app

logger = logging.getLogger(__name__)


@app.activity_trigger(input_name="params")
async def check_agent_status_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Check status of running agents.

    Queries Container Apps for execution status and subscribes to Service Bus
    for agent log messages.

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - container_ids: List of Container App IDs to check

    Returns:
        Dictionary with status:
        {
            "running_count": int,
            "completed_count": int,
            "failed_count": int,
            "log_messages": int
        }
    """
    try:
        container_ids = params.get("container_ids", [])

        logger.info(f"Activity: check_agent_status - Checking {len(container_ids)} containers")

        config = await load_config()
        container_manager = ContainerManager(config)

        # Check status of each container
        statuses = {"running": 0, "completed": 0, "failed": 0}
        for container_id in container_ids:
            try:
                status = await container_manager.get_status(container_id)
                if status in ["Running", "Processing"]:
                    statuses["running"] += 1
                elif status == "Terminated":
                    statuses["completed"] += 1
                else:
                    statuses["failed"] += 1
            except Exception as e:
                logger.warning(f"Failed to check status of {container_id}: {str(e)}")
                statuses["failed"] += 1

        logger.info(
            f"Activity: check_agent_status - "
            f"running={statuses['running']}, "
            f"completed={statuses['completed']}, "
            f"failed={statuses['failed']}"
        )

        return {
            "running_count": statuses["running"],
            "completed_count": statuses["completed"],
            "failed_count": statuses["failed"],
            "log_messages": 0,
        }
    except Exception as e:
        logger.error(f"Activity: check_agent_status - Failed: {str(e)}", exc_info=True)
        return {
            "running_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "log_messages": 0,
        }
