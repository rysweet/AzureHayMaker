"""Service Principal Manager for Azure HayMaker.

This module manages the lifecycle of ephemeral service principals used for scenario execution.
Each service principal is created per scenario, assigned custom RBAC roles, and deleted after cleanup.
Includes secret expiration monitoring and automatic rotation capabilities.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from azure.core.exceptions import (
    ResourceNotFoundError,
)
from azure.keyvault.secrets import SecretClient
from azure.mgmt.authorization import AuthorizationManagementClient
from kiota_abstractions.api_error import APIError
from msgraph.generated.models.application import Application
from msgraph.generated.models.password_credential import PasswordCredential
from msgraph.generated.models.service_principal import ServicePrincipal
from msgraph.graph_service_client import GraphServiceClient
from pydantic import BaseModel, Field

from azure_haymaker.utils.credentials import get_credential

logger = logging.getLogger(__name__)

# Default secret validity period (days)
DEFAULT_SECRET_VALIDITY_DAYS = 30


def sanitize_odata_value(value: str) -> str:
    """Sanitize input for OData/Graph API query filters to prevent injection attacks.

    Args:
        value: Input string to sanitize

    Returns:
        Sanitized string safe for use in OData filters
    """
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
    secret_expires_at: str | None = Field(
        default=None, description="ISO timestamp of secret expiration"
    )


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


async def create_service_principal(  # pyright: ignore[reportGeneralTypeIssues,reportArgumentType,reportUnnecessaryComparison,reportAttributeAccessIssue]
    scenario_name: str,
    subscription_id: str,
    roles: list[str],
    key_vault_client: SecretClient,
    secret_validity_days: int = DEFAULT_SECRET_VALIDITY_DAYS,
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
        secret_validity_days: Number of days until secret expires (default 30)

    Returns:
        ServicePrincipalDetails with client_id, principal_id, secret reference and expiration

    Raises:
        ServicePrincipalError: If SP creation, role assignment, or secret storage fails
    """
    sp_name = f"AzureHayMaker-{scenario_name}-admin"
    secret_name = f"scenario-sp-{scenario_name}-secret"

    try:
        # Initialize Microsoft Graph client with explicit service principal credentials
        # Use ClientSecretCredential instead of DefaultAzureCredential to ensure
        # we use the SP credentials from environment variables (AZURE_CLIENT_ID/SECRET)
        import os

        from azure.identity import ClientSecretCredential

        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")

        logger.info(f"Creating SP for {scenario_name} using client_id={(client_id or '')[:8]}...")

        credential = ClientSecretCredential(
            tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
        )
        graph_client = GraphServiceClient(credential)

        # Create application registration
        app_request_body = Application()
        app_request_body.display_name = sp_name

        logger.info(f"Calling Graph API to create application: {sp_name}")
        try:
            # Graph SDK methods are already async, await them directly (not asyncio.to_thread)
            app = await graph_client.applications.post(app_request_body)
        except Exception as e:
            logger.error(f"Graph API application creation failed: {type(e).__name__}: {str(e)}")
            raise ServicePrincipalError(
                f"Graph API create app failed: {type(e).__name__}: {e}"
            ) from e

        if not app:
            raise ServicePrincipalError("Failed to create application registration")
        if not app.app_id:
            raise ServicePrincipalError("Failed to create application registration")

        logger.info(f"Application created: id={app.id}, appId={app.app_id}")

        # Verify application exists with retry logic (Azure AD eventual consistency)
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Verify application exists before creating SP
                verify_app = await graph_client.applications.by_application_id(app.id).get()
                if verify_app and verify_app.app_id == app.app_id:
                    logger.info(f"Application verified after {attempt + 1} attempts")
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1, 2, 4, 8, 16 seconds
                    logger.warning(
                        f"Application not yet propagated (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise ServicePrincipalError(
                        f"Application failed to propagate after {max_retries} attempts"
                    ) from e

        # Create service principal with retry (handles eventual consistency)
        sp_request_body = ServicePrincipal()
        sp_request_body.app_id = app.app_id

        logger.info(f"Creating service principal for appId={app.app_id}")
        sp = None
        for attempt in range(max_retries):
            try:
                # Graph SDK methods are async, await directly
                sp = await graph_client.service_principals.post(sp_request_body)
                logger.info(f"Service principal created successfully after {attempt + 1} attempts")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"SP creation failed (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise ServicePrincipalError(
                        f"Failed to create SP after {max_retries} attempts: {e}"
                    ) from e

        if not sp:
            raise ServicePrincipalError("Failed to create service principal")
        if not sp.id:
            raise ServicePrincipalError("Failed to create service principal")

        # Generate password credential (client secret) with expiration
        secret_expiration = datetime.now(UTC) + timedelta(days=secret_validity_days)
        password_credential_request = PasswordCredential()
        password_credential_request.display_name = f"{sp_name}-secret"
        password_credential_request.end_date_time = secret_expiration

        if not app.id:
            raise ServicePrincipalError("Application ID is None")

        logger.info(f"Adding password to application id={app.id}")

        # Retry password addition with exponential backoff (handles eventual consistency)
        password_result = None
        for attempt in range(max_retries):
            try:
                # Graph SDK async method - await directly
                # Note: by_application_id() expects the application's object ID (app.id), not appId
                password_result = await graph_client.applications.by_application_id(
                    app.id
                ).add_password.post(password_credential_request)
                logger.info(f"Password added successfully after {attempt + 1} attempts")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Password addition failed (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise ServicePrincipalError(
                        f"Failed to add password after {max_retries} attempts: {e}"
                    ) from e

        if not password_result:
            raise ServicePrincipalError("Failed to generate service principal secret")
        if not password_result.secret_text:
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

        # Return service principal details with expiration tracking
        return ServicePrincipalDetails(
            sp_name=sp_name,
            client_id=app.app_id,
            principal_id=sp.id,  # Already checked sp.id is not None above
            secret_reference=secret_name,
            created_at=datetime.now(UTC).isoformat(),
            secret_expires_at=secret_expiration.isoformat(),
        )

    except APIError as e:
        raise ServicePrincipalError(f"Microsoft Graph API error: {e}") from e
    except Exception as e:
        raise ServicePrincipalError(f"Failed to create service principal: {e}") from e


async def delete_service_principal(  # pyright: ignore[reportGeneralTypeIssues,reportUnnecessaryComparison,reportAttributeAccessIssue]
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
        credential = get_credential()
        graph_client = GraphServiceClient(credential)

        # Find service principal by display name
        filter_query = f"displayName eq '{sanitize_odata_value(sp_name)}'"

        from kiota_abstractions.base_request_configuration import RequestConfiguration
        from msgraph.generated.service_principals.service_principals_request_builder import (
            ServicePrincipalsRequestBuilder,
        )

        request_config = RequestConfiguration()
        request_config.query_parameters = (
            ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetQueryParameters(
                filter=filter_query
            )
        )

        sp_list = await asyncio.to_thread(
            graph_client.service_principals.get,
            request_configuration=request_config,
        )

        if sp_list and sp_list.value and len(sp_list.value) > 0:
            sp_id = sp_list.value[0].id
            if sp_id:
                # Delete service principal - call the delete method
                sp_delete_client = graph_client.service_principals.by_service_principal_id(sp_id)
                await asyncio.to_thread(sp_delete_client.delete)
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


async def verify_sp_deleted(sp_name: str) -> bool:  # pyright: ignore[reportGeneralTypeIssues,reportUnnecessaryComparison,reportAttributeAccessIssue]
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
        filter_query = f"displayName eq '{sanitize_odata_value(sp_name)}'"

        from kiota_abstractions.base_request_configuration import RequestConfiguration
        from msgraph.generated.service_principals.service_principals_request_builder import (
            ServicePrincipalsRequestBuilder,
        )

        request_config = RequestConfiguration()
        request_config.query_parameters = (
            ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetQueryParameters(
                filter=filter_query
            )
        )

        sp_list = await asyncio.to_thread(
            graph_client.service_principals.get,
            request_configuration=request_config,
        )

        # If no results or empty list, SP is deleted; otherwise it still exists
        return not sp_list or not sp_list.value or len(sp_list.value) == 0

    except Exception as e:
        raise ServicePrincipalError(f"Failed to verify service principal deletion: {e}") from e


async def list_haymaker_service_principals() -> list[str]:  # pyright: ignore[reportGeneralTypeIssues,reportUnnecessaryComparison,reportAttributeAccessIssue]
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
        sp_list = await asyncio.to_thread(graph_client.service_principals.get)

        haymaker_sps = []
        if sp_list and sp_list.value:
            for sp in sp_list.value:
                if sp.display_name and sp.display_name.startswith("AzureHayMaker-"):
                    haymaker_sps.append(sp.display_name)

        return haymaker_sps

    except Exception as e:
        raise ServicePrincipalError(f"Failed to list service principals: {e}") from e


class SecretExpirationInfo(BaseModel):
    """Information about a service principal's secret expiration status."""

    sp_name: str = Field(..., description="Service principal name")
    client_id: str = Field(..., description="Application (client) ID")
    secret_expires_at: datetime | None = Field(default=None, description="When the secret expires")
    days_until_expiration: int | None = Field(default=None, description="Days until expiration")
    needs_rotation: bool = Field(default=False, description="Whether rotation is recommended")
    is_expired: bool = Field(default=False, description="Whether secret is expired")


async def check_secret_expiration(  # pyright: ignore[reportGeneralTypeIssues,reportUnnecessaryComparison,reportAttributeAccessIssue]
    sp_name: str,
    warning_threshold_days: int = 7,
) -> SecretExpirationInfo:
    """Check the expiration status of a service principal's secret.

    Args:
        sp_name: Name of the service principal to check
        warning_threshold_days: Days before expiration to flag for rotation

    Returns:
        SecretExpirationInfo with expiration status details

    Raises:
        ServicePrincipalError: If checking fails
    """
    try:
        credential = get_credential()
        graph_client = GraphServiceClient(credential)

        # Find the application by display name
        filter_query = f"displayName eq '{sanitize_odata_value(sp_name)}'"

        from kiota_abstractions.base_request_configuration import RequestConfiguration
        from msgraph.generated.applications.applications_request_builder import (
            ApplicationsRequestBuilder,
        )

        request_config = RequestConfiguration()
        request_config.query_parameters = (
            ApplicationsRequestBuilder.ApplicationsRequestBuilderGetQueryParameters(
                filter=filter_query
            )
        )

        app_list = await asyncio.to_thread(
            graph_client.applications.get,
            request_configuration=request_config,
        )

        if not app_list or not app_list.value or len(app_list.value) == 0:
            raise ServicePrincipalError(f"Application {sp_name} not found")

        app = app_list.value[0]

        # Get password credentials
        password_credentials = app.password_credentials or []

        if not password_credentials:
            return SecretExpirationInfo(
                sp_name=sp_name,
                client_id=app.app_id or "",
                secret_expires_at=None,
                days_until_expiration=None,
                needs_rotation=True,  # No credentials = needs rotation
                is_expired=True,
            )

        # Find the latest expiration date
        latest_expiration: datetime | None = None
        for cred in password_credentials:
            if cred.end_date_time and (
                latest_expiration is None or cred.end_date_time > latest_expiration
            ):
                latest_expiration = cred.end_date_time

        if latest_expiration is None:
            return SecretExpirationInfo(
                sp_name=sp_name,
                client_id=app.app_id or "",
                secret_expires_at=None,
                days_until_expiration=None,
                needs_rotation=False,
                is_expired=False,
            )

        now = datetime.now(UTC)
        is_expired = now >= latest_expiration
        days_until = max(0, (latest_expiration - now).days) if not is_expired else 0
        needs_rotation = is_expired or days_until <= warning_threshold_days

        return SecretExpirationInfo(
            sp_name=sp_name,
            client_id=app.app_id or "",
            secret_expires_at=latest_expiration,
            days_until_expiration=days_until,
            needs_rotation=needs_rotation,
            is_expired=is_expired,
        )

    except ServicePrincipalError:
        raise
    except Exception as e:
        raise ServicePrincipalError(f"Failed to check secret expiration: {e}") from e


async def rotate_service_principal_secret(  # pyright: ignore[reportGeneralTypeIssues,reportArgumentType,reportUnnecessaryComparison,reportAttributeAccessIssue]
    sp_name: str,
    key_vault_client: SecretClient,
    secret_validity_days: int = DEFAULT_SECRET_VALIDITY_DAYS,
    remove_old_secrets: bool = True,
) -> ServicePrincipalDetails:
    """Rotate the secret for an existing service principal.

    Creates a new secret for the service principal, stores it in Key Vault,
    and optionally removes old secrets.

    Args:
        sp_name: Name of the service principal to rotate
        key_vault_client: Key Vault client for storing new secret
        secret_validity_days: Number of days until new secret expires
        remove_old_secrets: Whether to remove old password credentials

    Returns:
        ServicePrincipalDetails with updated secret reference and expiration

    Raises:
        ServicePrincipalError: If rotation fails
    """
    secret_name = sp_name.replace("AzureHayMaker-", "scenario-sp-").replace("-admin", "-secret")

    try:
        import os

        from azure.identity import ClientSecretCredential

        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")

        credential = ClientSecretCredential(
            tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
        )
        graph_client = GraphServiceClient(credential)

        # Find the application by display name
        filter_query = f"displayName eq '{sanitize_odata_value(sp_name)}'"

        from kiota_abstractions.base_request_configuration import RequestConfiguration
        from msgraph.generated.applications.applications_request_builder import (
            ApplicationsRequestBuilder,
        )

        request_config = RequestConfiguration()
        request_config.query_parameters = (
            ApplicationsRequestBuilder.ApplicationsRequestBuilderGetQueryParameters(
                filter=filter_query
            )
        )

        app_list = await asyncio.to_thread(
            graph_client.applications.get,
            request_configuration=request_config,
        )

        if not app_list or not app_list.value or len(app_list.value) == 0:
            raise ServicePrincipalError(f"Application {sp_name} not found for rotation")

        app = app_list.value[0]
        if not app.id or not app.app_id:
            raise ServicePrincipalError(f"Application {sp_name} has no ID")

        # Find corresponding service principal
        sp_filter = f"appId eq '{sanitize_odata_value(app.app_id)}'"

        from msgraph.generated.service_principals.service_principals_request_builder import (
            ServicePrincipalsRequestBuilder,
        )

        sp_request_config = RequestConfiguration()
        sp_request_config.query_parameters = (
            ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetQueryParameters(
                filter=sp_filter
            )
        )

        sp_list = await asyncio.to_thread(
            graph_client.service_principals.get,
            request_configuration=sp_request_config,
        )

        if not sp_list or not sp_list.value or len(sp_list.value) == 0:
            raise ServicePrincipalError(f"Service principal for {sp_name} not found")

        sp = sp_list.value[0]
        if not sp.id:
            raise ServicePrincipalError(f"Service principal {sp_name} has no ID")

        logger.info(f"Rotating secret for {sp_name} (appId={app.app_id})")

        # Remove old password credentials if requested
        if remove_old_secrets and app.password_credentials:
            for old_cred in app.password_credentials:
                if old_cred.key_id:
                    try:
                        from msgraph.generated.applications.item.remove_password.remove_password_post_request_body import (
                            RemovePasswordPostRequestBody,
                        )

                        remove_body = RemovePasswordPostRequestBody()
                        remove_body.key_id = old_cred.key_id

                        await graph_client.applications.by_application_id(
                            app.id
                        ).remove_password.post(remove_body)
                        logger.info(f"Removed old credential {old_cred.key_id}")
                    except Exception as e:
                        logger.warning(f"Failed to remove old credential: {e}")

        # Create new password credential with expiration
        secret_expiration = datetime.now(UTC) + timedelta(days=secret_validity_days)
        password_credential_request = PasswordCredential()
        password_credential_request.display_name = f"{sp_name}-secret-rotated"
        password_credential_request.end_date_time = secret_expiration

        # Retry password addition with exponential backoff
        max_retries = 5
        password_result = None
        for attempt in range(max_retries):
            try:
                password_result = await graph_client.applications.by_application_id(
                    app.id
                ).add_password.post(password_credential_request)
                logger.info(f"New password added successfully after {attempt + 1} attempts")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Password addition failed (attempt {attempt + 1}/{max_retries}), "
                        f"waiting {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise ServicePrincipalError(
                        f"Failed to add new password after {max_retries} attempts: {e}"
                    ) from e

        if not password_result or not password_result.secret_text:
            raise ServicePrincipalError("Failed to generate new service principal secret")

        # Store new secret in Key Vault (overwrites existing)
        await asyncio.to_thread(
            key_vault_client.set_secret,
            secret_name,
            password_result.secret_text,
        )

        logger.info(f"Secret rotated successfully for {sp_name}, expires {secret_expiration}")

        return ServicePrincipalDetails(
            sp_name=sp_name,
            client_id=app.app_id,
            principal_id=sp.id,
            secret_reference=secret_name,
            created_at=datetime.now(UTC).isoformat(),
            secret_expires_at=secret_expiration.isoformat(),
        )

    except ServicePrincipalError:
        raise
    except APIError as e:
        raise ServicePrincipalError(f"Microsoft Graph API error during rotation: {e}") from e
    except Exception as e:
        raise ServicePrincipalError(f"Failed to rotate service principal secret: {e}") from e


async def check_and_rotate_expiring_secrets(
    key_vault_client: SecretClient,
    warning_threshold_days: int = 7,
    secret_validity_days: int = DEFAULT_SECRET_VALIDITY_DAYS,
    auto_rotate: bool = True,
) -> list[SecretExpirationInfo]:
    """Check all HayMaker service principals for expiring secrets and optionally rotate them.

    Args:
        key_vault_client: Key Vault client for storing rotated secrets
        warning_threshold_days: Days before expiration to flag for rotation
        secret_validity_days: Validity period for rotated secrets
        auto_rotate: Whether to automatically rotate expiring secrets

    Returns:
        List of SecretExpirationInfo for all checked service principals

    Raises:
        ServicePrincipalError: If checking or rotation fails
    """
    results: list[SecretExpirationInfo] = []

    try:
        sp_names = await list_haymaker_service_principals()

        for sp_name in sp_names:
            try:
                expiration_info = await check_secret_expiration(sp_name, warning_threshold_days)
                results.append(expiration_info)

                if auto_rotate and expiration_info.needs_rotation:
                    logger.info(
                        f"Auto-rotating secret for {sp_name} "
                        f"(expired={expiration_info.is_expired}, "
                        f"days_until={expiration_info.days_until_expiration})"
                    )
                    await rotate_service_principal_secret(
                        sp_name=sp_name,
                        key_vault_client=key_vault_client,
                        secret_validity_days=secret_validity_days,
                    )
                    # Update expiration info after rotation
                    expiration_info = await check_secret_expiration(sp_name, warning_threshold_days)
                    # Replace the old info with updated
                    results[-1] = expiration_info

            except ServicePrincipalError as e:
                logger.error(f"Failed to check/rotate {sp_name}: {e}")
                # Continue with other SPs

        return results

    except Exception as e:
        raise ServicePrincipalError(f"Failed to check/rotate expiring secrets: {e}") from e
