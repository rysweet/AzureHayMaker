"""Provisioning activities for Azure HayMaker orchestrator.

This module contains activity functions for provisioning service principals
and deploying container apps for scenario execution.

Activities:
- create_service_principal_activity: Creates ephemeral SPs with RBAC roles
- deploy_container_app_activity: Deploys Container Apps with scenario agents

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

from azure_haymaker.models.scenario import ScenarioMetadata
from azure_haymaker.models.service_principal import ServicePrincipalDetails as SPDetailsModel
from azure_haymaker.orchestrator.config import load_config
from azure_haymaker.orchestrator.container_manager import deploy_container_app
from azure_haymaker.orchestrator.orchestrator_app import app
from azure_haymaker.orchestrator.sp_manager import create_service_principal

logger = logging.getLogger(__name__)


@app.activity_trigger(input_name="params")
async def create_service_principal_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Create service principal for a scenario.

    Creates an ephemeral service principal with naming convention:
    AzureHayMaker-{scenario_name}-admin

    Assigns roles:
    - User Access Administrator
    - Contributor

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - scenario: Scenario metadata dictionary

    Returns:
        Dictionary with SP details or failure info:
        {
            "status": "success" | "failed",
            "sp_details": {
                "sp_name": str,
                "client_id": str,
                "principal_id": str,
                "secret_reference": str
            },
            "error": str (if failed)
        }
    """
    try:
        scenario = params.get("scenario", {})
        if not isinstance(scenario, dict):
            scenario = {}
        scenario_name = scenario.get("scenario_name")

        logger.info(f"Activity: create_service_principal - scenario={scenario_name}")

        config = await load_config()
        sub_id = config.target_subscription_id
        key_vault_url = config.key_vault_url

        # Create Key Vault client for secret storage
        credential = DefaultAzureCredential()
        key_vault_client = SecretClient(vault_url=key_vault_url, credential=credential)

        # Assign minimal required roles to service principal
        roles = ["Contributor", "Reader"]

        if not scenario_name:
            raise ValueError("scenario_name is required")

        sp_details = await create_service_principal(
            scenario_name=scenario_name,
            subscription_id=sub_id,
            roles=roles,
            key_vault_client=key_vault_client,
        )

        logger.info(f"Activity: create_service_principal - Created SP: {sp_details.sp_name}")
        return {
            "status": "success",
            "sp_details": {
                "sp_name": sp_details.sp_name,
                "client_id": sp_details.client_id,
                "principal_id": sp_details.principal_id,
                "secret_reference": sp_details.secret_reference,
                "created_at": sp_details.created_at,
            },
        }
    except Exception as e:
        logger.error(
            f"Activity: create_service_principal - Failed: {str(e)}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": str(e),
        }


@app.activity_trigger(input_name="params")
async def deploy_container_app_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Activity: Deploy Container App for scenario execution.

    Deploys a Container App with:
    - Scenario-specific instructions
    - Service principal credentials (via Key Vault)
    - 64GB RAM, 2 CPU minimum
    - 10-hour timeout
    - Never restart policy

    Args:
        params: Dictionary containing:
            - run_id: Execution run ID
            - scenario: Scenario metadata dictionary
            - sp_details: Service principal details dictionary

    Returns:
        Dictionary with Container App details or failure info:
        {
            "status": "success" | "failed",
            "container_id": str,
            "container_name": str,
            "resource_id": str,
            "error": str (if failed)
        }
    """
    try:
        scenario = params.get("scenario", {})
        sp_details = params.get("sp_details", {})
        if not isinstance(scenario, dict):
            scenario = {}
        if not isinstance(sp_details, dict):
            sp_details = {}
        scenario_name = scenario.get("scenario_name")

        logger.info(f"Activity: deploy_container_app - scenario={scenario_name}")

        config = await load_config()

        # Convert created_at string to datetime
        created_at_str = sp_details.get("created_at")
        if created_at_str and isinstance(created_at_str, str):
            created_at_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        else:
            created_at_dt = datetime.now(UTC)

        # Validate required fields
        if not scenario_name:
            raise ValueError("scenario_name is required")

        # deploy_container_app returns resource ID string
        container_resource_id = await deploy_container_app(
            scenario=ScenarioMetadata(
                scenario_name=scenario_name,
                scenario_doc_path=scenario.get("scenario_doc_path", ""),
                agent_path=scenario.get("agent_path", ""),
                technology_area=scenario.get("technology_area", ""),
            ),
            sp=SPDetailsModel(
                sp_name=sp_details.get("sp_name", ""),
                client_id=sp_details.get("client_id", ""),
                principal_id=sp_details.get("principal_id", ""),
                secret_reference=sp_details.get("secret_reference", ""),
                created_at=created_at_dt,
                scenario_name=scenario_name,
            ),
            config=config,
        )

        # Extract container name from resource ID
        # Format: /subscriptions/.../resourceGroups/.../providers/Microsoft.App/containerApps/{name}
        container_name = container_resource_id.split("/")[-1]

        logger.info(f"Activity: deploy_container_app - Deployed: {container_name}")
        return {
            "status": "success",
            "container_id": container_name,
            "container_name": container_name,
            "resource_id": container_resource_id,
        }
    except Exception as e:
        logger.error(
            f"Activity: deploy_container_app - Failed: {str(e)}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": str(e),
        }
