"""Service Principal Manager for Azure HayMaker.

This module manages the lifecycle of ephemeral service principals used for scenario execution.
Each service principal is created per scenario, assigned custom RBAC roles, and deleted after cleanup.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.mgmt.authorization import AuthorizationManagementClient
from kiota_abstractions.api_error import APIError
from msgraph import GraphServiceClient
from msgraph.generated.models.application import Application
from msgraph.generated.models.password_credential import PasswordCredential
from msgraph.generated.models.service_principal import ServicePrincipal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def sanitize_odata_value(value: str) -> str:
    """Sanitize input for OData/Graph API query filters to prevent injection attacks.

    Args:
        value: Input string to sanitize

    Returns:
        Sanitized string safe for use in OData filters
    """
    if not isinstance(value, str):
        value = str(value)
    # Escape single quotes by doubling them (OData standard)
    return value.replace("'", "''")


class ServicePrincipalError(Exception):
    """Raised when service principal operations fail."""

    pass


class ServicePrincipalDetails(BaseModel):
    """Details of a created service principal."""

    sp_name: str = Field(..., description="Service principal display name")
    client_id: str = Field(..., description="Application (client) ID")
    principal_id: str = Field(..., description="Object ID of the service principal")
    secret_reference: str = Field(..., description="Key Vault secret name for SP secret")
    created_at: str = Field(..., description="ISO timestamp of creation")


# Built-in Azure role definition IDs (consistent across all subscriptions)
ROLE_DEFINITIONS = {
    "Contributor": "b24988ac-6180-42a0-ab88-20f7382dd24c",
    "Reader": "acdd72a7-3385-48ef-bd42-f606fba81ae7",
    "Custom RBAC Agent": "CUSTOM_RBAC_AGENT_ROLE_ID",  # Custom role - must be created in subscription
}

# Custom RBAC role definition for HayMaker scenario agents
# This role provides minimal required permissions for scenario execution
# and avoids the over-privileged User Access Administrator role
CUSTOM_RBAC_ROLE_DEFINITION = {
    "roleName": "AzureHayMaker-Agent-Role",
    "description": "Custom role for Azure HayMaker scenario execution with minimal permissions",
    "permissions": [
        {
            "actions": [
                "Microsoft.Resources/subscriptions/resourceGroups/read",
                "Microsoft.Compute/virtualMachines/read",
                "Microsoft.Network/virtualNetworks/read",
                "Microsoft.Network/networkInterfaces/read",
                "Microsoft.Storage/storageAccounts/read",
                "Microsoft.KeyVault/vaults/read",
                "Microsoft.ContainerRegistry/registries/read",
                "Microsoft.ServiceBus/namespaces/read",
            ],
            "notActions": [],
            "dataActions": [
                "Microsoft.KeyVault/vaults/secrets/getSecret/action",
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
            ],
            "notDataActions": [],
        }
    ],
    "assignableScopes": ["/subscriptions/{subscription_id}"],
}

# Role propagation wait time (seconds)
ROLE_PROPAGATION_WAIT = 60


async def create_service_principal(
    scenario_name: str,
    subscription_id: str,
    roles: list[str],
    key_vault_client: SecretClient,
) -> ServicePrincipalDetails:
    """Create ephemeral service principal for scenario execution.

    This function creates a service principal with the naming convention
    'AzureHayMaker-{scenario_name}-admin', assigns the specified roles,
    stores the secret in Key Vault, and returns the SP details.

    Args:
        scenario_name: Name of the scenario (used in SP name)
        subscription_id: Azure subscription ID for role assignments
        roles: List of role names to assign (e.g., ["Contributor", "Reader"])
        key_vault_client: Key Vault client for storing SP secret

    Returns:
        ServicePrincipalDetails with client_id, principal_id, and secret reference

    Raises:
        ServicePrincipalError: If SP creation, role assignment, or secret storage fails
    """
    sp_name = f"AzureHayMaker-{scenario_name}-admin"
    secret_name = f"scenario-sp-{scenario_name}-secret"

    try:
        # Initialize Microsoft Graph client
        credential = DefaultAzureCredential()
        graph_client = GraphServiceClient(credential)

        # Create application registration
        app_request_body = Application()
        app_request_body.display_name = sp_name

        app = await asyncio.to_thread(graph_client.applications.post, app_request_body)

        if not app or not app.app_id:
            raise ServicePrincipalError("Failed to create application registration")

        # Create service principal
        sp_request_body = ServicePrincipal()
        sp_request_body.app_id = app.app_id

        sp = await asyncio.to_thread(graph_client.service_principals.post, sp_request_body)

        if not sp or not sp.id:
            raise ServicePrincipalError("Failed to create service principal")

        # Generate password credential (client secret)
        password_credential_request = PasswordCredential()
        password_credential_request.display_name = f"{sp_name}-secret"

        password_result = await asyncio.to_thread(
            graph_client.applications.by_application_id(app.id).add_password.post,
            password_credential_request,
        )

        if not password_result or not password_result.secret_text:
            raise ServicePrincipalError("Failed to generate service principal secret")

        # Store secret in Key Vault
        await asyncio.to_thread(
            key_vault_client.set_secret,
            secret_name,
            password_result.secret_text,
        )

        # Assign roles to service principal
        auth_client = AuthorizationManagementClient(
            credential=credential,
            subscription_id=subscription_id,
        )

        for role_name in roles:
            role_definition_id = ROLE_DEFINITIONS.get(role_name)
            if not role_definition_id:
                raise ServicePrincipalError(f"Unknown role: {role_name}")

            # Create role assignment
            role_assignment_name = str(uuid.uuid4())
            scope = f"/subscriptions/{subscription_id}"
            role_definition_id_full = (
                f"{scope}/providers/Microsoft.Authorization/roleDefinitions/{role_definition_id}"
            )

            await asyncio.to_thread(
                auth_client.role_assignments.create,
                scope=scope,
                role_assignment_name=role_assignment_name,
                parameters={
                    "properties": {
                        "roleDefinitionId": role_definition_id_full,
                        "principalId": sp.id,
                        "principalType": "ServicePrincipal",
                    }
                },
            )

        # Wait for role propagation (Azure RBAC eventual consistency)
        await asyncio.sleep(ROLE_PROPAGATION_WAIT)

        # Return service principal details
        return ServicePrincipalDetails(
            sp_name=sp_name,
            client_id=app.app_id,
            principal_id=sp.id,
            secret_reference=secret_name,
            created_at=datetime.now(UTC).isoformat(),
        )

    except APIError as e:
        raise ServicePrincipalError(f"Microsoft Graph API error: {e}") from e
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
    secret_name = sp_name.replace("AzureHayMaker-", "scenario-sp-").replace("-admin", "-secret")

    try:
        credential = DefaultAzureCredential()
        graph_client = GraphServiceClient(credential)

        # Find service principal by display name
        filter_query = f"displayName eq '{sanitize_odata_value(sp_name)}'"
        sp_list = await asyncio.to_thread(
            graph_client.service_principals.get,
            request_configuration=lambda config: setattr(
                config.query_parameters, "filter", filter_query
            ),
        )

        if sp_list and sp_list.value and len(sp_list.value) > 0:
            sp_id = sp_list.value[0].id
            # Delete service principal
            await asyncio.to_thread(
                graph_client.service_principals.by_service_principal_id(sp_id).delete
            )
        else:
            # SP not found, log but continue
            logger.warning("Service principal %s not found for deletion", sp_name)

    except Exception as e:
        # Log error but continue to try deleting secret
        logger.error("Error deleting service principal %s: %s", sp_name, e)

    # Delete secret from Key Vault
    try:
        await asyncio.to_thread(
            key_vault_client.begin_delete_secret,
            secret_name,
        )
    except ResourceNotFoundError:
        # Secret not found, that's okay
        logger.warning("Key Vault secret %s not found for deletion", secret_name)
    except Exception as e:
        logger.error("Error deleting Key Vault secret %s: %s", secret_name, e)


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
        credential = DefaultAzureCredential()
        graph_client = GraphServiceClient(credential)

        # Query for service principal by display name
        filter_query = f"displayName eq '{sanitize_odata_value(sp_name)}'"
        sp_list = await asyncio.to_thread(
            graph_client.service_principals.get,
            request_configuration=lambda config: setattr(
                config.query_parameters, "filter", filter_query
            ),
        )

        # If no results or empty list, SP is deleted; otherwise it still exists
        return not sp_list or not sp_list.value or len(sp_list.value) == 0

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
        credential = DefaultAzureCredential()
        graph_client = GraphServiceClient(credential)

        # List all service principals (filter applied client-side due to Graph API limitations)
        sp_list = await asyncio.to_thread(graph_client.service_principals.get)

        haymaker_sps = []
        if sp_list and sp_list.value:
            for sp in sp_list.value:
                if sp.display_name and sp.display_name.startswith("AzureHayMaker-"):
                    haymaker_sps.append(sp.display_name)

        return haymaker_sps

    except Exception as e:
        raise ServicePrincipalError(f"Failed to list service principals: {e}") from e
