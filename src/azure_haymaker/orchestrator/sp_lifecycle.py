"""Service Principal lifecycle management (create, delete, list).

This module coordinates the creation and deletion of ephemeral service principals
for scenario execution by orchestrating graph operations, secret storage, and
RBAC assignments.

Philosophy:
- Single responsibility: SP lifecycle coordination
- Thin coordination layer (delegates to specialized modules)
- Cross-tenant aware
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from azure_haymaker.models.config import OrchestratorConfig

from azure.keyvault.secrets import SecretClient
from pydantic import BaseModel, Field

from azure_haymaker.exceptions import ServicePrincipalError
from azure_haymaker.orchestrator.graph_operations import (
    DEFAULT_SECRET_VALIDITY_DAYS,
    add_application_password,
    create_application,
    create_service_principal_for_app,
    delete_service_principal_by_id,
    find_service_principal_by_name,
    list_all_service_principals,
    verify_application_exists,
)
from azure_haymaker.orchestrator.rbac_manager import assign_roles
from azure_haymaker.orchestrator.secret_manager import delete_secret, get_secret_name_for_sp, store_secret
from azure_haymaker.utils.credentials import get_credential, get_tenant_credential
from msgraph.graph_service_client import GraphServiceClient

logger = logging.getLogger(__name__)


class ServicePrincipalDetails(BaseModel):
    """Details of a created service principal."""

    sp_name: str = Field(..., description="Service principal display name")
    client_id: str = Field(..., description="Application (client) ID")
    principal_id: str = Field(..., description="Object ID of the service principal")
    secret_reference: str = Field(..., description="Key Vault secret name for SP secret")
    created_at: str = Field(..., description="ISO timestamp of creation")
    secret_expires_at: str | None = Field(
        default=None, description="ISO timestamp of secret expiration"
    )


async def create_service_principal(
    scenario_name: str,
    subscription_id: str,
    roles: list[str],
    key_vault_client: SecretClient,
    config: "OrchestratorConfig",
    secret_validity_days: int = DEFAULT_SECRET_VALIDITY_DAYS,
) -> ServicePrincipalDetails:
    """Create ephemeral service principal for scenario execution.

    This function creates a service principal with the naming convention
    'AzureHayMaker-{scenario_name}-admin', assigns the specified roles,
    stores the secret in Key Vault, and returns the SP details.

    In cross-tenant mode: Creates SP in target tenant using target tenant credentials
    In single-tenant mode: Uses orchestrator credentials (backward compatible)

    Args:
        scenario_name: Name of the scenario (used in SP name)
        subscription_id: Azure subscription ID for role assignments
        roles: List of role names to assign (e.g., ["Contributor", "Reader"])
        key_vault_client: Key Vault client for storing SP secret
        config: Orchestrator configuration with tenant context
        secret_validity_days: Number of days until secret expires (default 30)

    Returns:
        ServicePrincipalDetails with client_id, principal_id, secret reference and expiration

    Raises:
        ServicePrincipalError: If SP creation, role assignment, or secret storage fails
    """
    sp_name = f"AzureHayMaker-{scenario_name}-admin"
    secret_name = get_secret_name_for_sp(sp_name)

    try:
        # Use tenant-aware credential (cross-tenant aware)
        credential = get_tenant_credential(config)

        # Log which tenant we're creating SP in
        logger.info(
            "Creating service principal in target tenant",
            extra={
                "scenario": scenario_name,
                "target_tenant": config.target_tenant_id[:8] + "...",
                "mode": "cross-tenant" if config.is_cross_tenant else "single-tenant",
            },
        )

        graph_client = GraphServiceClient(credential)

        # Create application registration
        app = await create_application(graph_client, sp_name)

        # Verify application exists (Azure AD eventual consistency)
        await verify_application_exists(graph_client, app)

        # Create service principal
        sp = await create_service_principal_for_app(graph_client, app.app_id)

        # Generate password credential (client secret) with expiration
        password_result = await add_application_password(
            graph_client,
            app.id,
            f"{sp_name}-secret",
            secret_validity_days
        )

        # Store secret in Key Vault
        await store_secret(
            key_vault_client,
            secret_name,
            password_result.secret_text,
        )

        # Assign roles to service principal
        await assign_roles(
            principal_id=sp.id,
            subscription_id=subscription_id,
            roles=roles,
            credential=credential,
        )

        # Return service principal details with expiration tracking
        secret_expiration = password_result.end_date_time
        return ServicePrincipalDetails(
            sp_name=sp_name,
            client_id=app.app_id,
            principal_id=sp.id,
            secret_reference=secret_name,
            created_at=datetime.now(UTC).isoformat(),
            secret_expires_at=secret_expiration.isoformat() if secret_expiration else None,
        )

    except ServicePrincipalError:
        raise
    except Exception as e:
        raise ServicePrincipalError(f"Failed to create service principal: {e}") from e


async def delete_service_principal(
    sp_name: str,
    key_vault_client: SecretClient,
) -> None:
    """Delete service principal and its secret from Key Vault.

    This function deletes the service principal and removes its secret
    from Key Vault. It handles cases where the SP or secret doesn't exist gracefully.

    Args:
        sp_name: Name of the service principal to delete
        key_vault_client: Key Vault client for deleting SP secret

    Raises:
        ServicePrincipalError: If deletion encounters a fatal error
    """
    secret_name = get_secret_name_for_sp(sp_name)

    try:
        credential = get_credential()
        graph_client = GraphServiceClient(credential)

        # Find service principal by display name
        sp_id = await find_service_principal_by_name(graph_client, sp_name)

        if sp_id:
            # Delete service principal
            await delete_service_principal_by_id(graph_client, sp_id)
        else:
            # SP not found, log but continue
            logger.warning("Service principal %s not found for deletion", sp_name)

    except Exception as e:
        # Log error but continue to try deleting secret
        logger.error("Error deleting service principal %s: %s", sp_name, e)

    # Delete secret from Key Vault
    await delete_secret(key_vault_client, secret_name)


async def verify_sp_deleted(sp_name: str) -> bool:
    """Verify that a service principal has been deleted from Entra ID.

    This function checks if a service principal with the given name still exists
    in Entra ID. It's used during cleanup verification to ensure SPs are properly
    removed before proceeding with resource cleanup.

    Args:
        sp_name: Name of the service principal to verify deletion

    Returns:
        True if SP is deleted (not found), False if it still exists

    Raises:
        ServicePrincipalError: If verification fails
    """
    try:
        credential = get_credential()
        graph_client = GraphServiceClient(credential)

        # Query for service principal by display name
        sp_id = await find_service_principal_by_name(graph_client, sp_name)

        # If no result, SP is deleted; otherwise it still exists
        return sp_id is None

    except Exception as e:
        raise ServicePrincipalError(f"Failed to verify service principal deletion: {e}") from e


async def list_haymaker_service_principals() -> list[str]:
    """List all service principals created by HayMaker.

    This is useful for debugging and cleanup verification.

    Returns:
        List of service principal names with 'AzureHayMaker-' prefix

    Raises:
        ServicePrincipalError: If listing fails
    """
    try:
        credential = get_credential()
        graph_client = GraphServiceClient(credential)

        # List all service principals (filter applied client-side due to Graph API limitations)
        sp_list = await list_all_service_principals(graph_client)

        haymaker_sps = []
        for sp in sp_list:
            if sp.display_name and sp.display_name.startswith("AzureHayMaker-"):
                haymaker_sps.append(sp.display_name)

        return haymaker_sps

    except Exception as e:
        raise ServicePrincipalError(f"Failed to list service principals: {e}") from e


__all__ = [
    "ServicePrincipalDetails",
    "create_service_principal",
    "delete_service_principal",
    "list_haymaker_service_principals",
    "verify_sp_deleted",
]
