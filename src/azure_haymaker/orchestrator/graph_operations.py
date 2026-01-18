"""Microsoft Graph API operations for Service Principal management.

This module handles all interactions with Microsoft Graph API for application
registration and service principal CRUD operations, including retry logic
for handling Azure AD eventual consistency.

Philosophy:
- Single responsibility: Graph API operations only
- Retry strategy pattern to eliminate duplication
- Exponential backoff for eventual consistency
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, TypeVar, Callable, Any

if TYPE_CHECKING:
    from msgraph.generated.models.application import Application
    from msgraph.generated.models.service_principal import ServicePrincipal
    from msgraph.generated.models.password_credential import PasswordCredential

from msgraph.generated.models.application import Application
from msgraph.generated.models.password_credential import PasswordCredential
from msgraph.generated.models.service_principal import ServicePrincipal
from msgraph.graph_service_client import GraphServiceClient

from azure_haymaker.exceptions import ServicePrincipalError
from azure_haymaker.orchestrator.sp_validation import sanitize_odata_value

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 5
DEFAULT_SECRET_VALIDITY_DAYS = 30

T = TypeVar("T")


async def retry_with_backoff(
    operation: Callable[[], Any],
    max_retries: int = DEFAULT_MAX_RETRIES,
    operation_name: str = "operation",
) -> T:
    """Execute an operation with exponential backoff retry logic.

    This pattern handles Azure AD eventual consistency by retrying operations
    that may fail initially due to propagation delays.

    Args:
        operation: Async callable to execute
        max_retries: Maximum number of retry attempts
        operation_name: Human-readable operation name for logging

    Returns:
        Result of the operation

    Raises:
        ServicePrincipalError: If operation fails after all retries
    """
    for attempt in range(max_retries):
        try:
            result = await operation()
            if attempt > 0:
                logger.info(f"{operation_name} succeeded after {attempt + 1} attempts")
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff: 1, 2, 4, 8, 16 seconds
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{max_retries}), "
                    f"waiting {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                raise ServicePrincipalError(
                    f"{operation_name} failed after {max_retries} attempts: {e}"
                ) from e


async def create_application(
    graph_client: GraphServiceClient,
    display_name: str,
) -> "Application":
    """Create an application registration in Entra ID.

    Args:
        graph_client: Microsoft Graph API client
        display_name: Display name for the application

    Returns:
        Created Application object

    Raises:
        ServicePrincipalError: If application creation fails
    """
    app_request_body = Application()
    app_request_body.display_name = display_name

    logger.info(f"Creating application: {display_name}")

    try:
        app = await graph_client.applications.post(app_request_body)
    except Exception as e:
        logger.error(f"Graph API application creation failed: {type(e).__name__}: {str(e)}")
        raise ServicePrincipalError(
            f"Graph API create app failed: {type(e).__name__}: {e}"
        ) from e

    if not app or not app.app_id or not app.id:
        raise ServicePrincipalError("Failed to create application registration")

    logger.info(f"Application created: id={app.id}, appId={app.app_id}")
    return app


async def verify_application_exists(
    graph_client: GraphServiceClient,
    app: "Application",
) -> None:
    """Verify application exists with retry logic (Azure AD eventual consistency).

    Args:
        graph_client: Microsoft Graph API client
        app: Application to verify

    Raises:
        ServicePrincipalError: If application verification fails
    """
    async def verify_op():
        verify_app = await graph_client.applications.by_application_id(app.id).get()
        if verify_app and verify_app.app_id == app.app_id:
            return True
        raise Exception("Application not yet propagated")

    await retry_with_backoff(
        verify_op,
        operation_name=f"Application verification (id={app.id})"
    )


async def create_service_principal_for_app(
    graph_client: GraphServiceClient,
    app_id: str,
) -> "ServicePrincipal":
    """Create a service principal for an application.

    Args:
        graph_client: Microsoft Graph API client
        app_id: Application (client) ID

    Returns:
        Created ServicePrincipal object

    Raises:
        ServicePrincipalError: If service principal creation fails
    """
    sp_request_body = ServicePrincipal()
    sp_request_body.app_id = app_id

    logger.info(f"Creating service principal for appId={app_id}")

    async def create_sp_op():
        sp = await graph_client.service_principals.post(sp_request_body)
        if not sp or not sp.id:
            raise Exception("Service principal creation returned invalid result")
        return sp

    sp = await retry_with_backoff(
        create_sp_op,
        operation_name=f"Service principal creation (appId={app_id})"
    )

    logger.info(f"Service principal created: id={sp.id}")
    return sp


async def add_application_password(
    graph_client: GraphServiceClient,
    application_id: str,
    display_name: str,
    validity_days: int = DEFAULT_SECRET_VALIDITY_DAYS,
) -> "PasswordCredential":
    """Add a password credential to an application.

    Args:
        graph_client: Microsoft Graph API client
        application_id: Application object ID (not appId)
        display_name: Display name for the credential
        validity_days: Number of days until password expires

    Returns:
        PasswordCredential with secret_text populated

    Raises:
        ServicePrincipalError: If password creation fails
    """
    secret_expiration = datetime.now(UTC) + timedelta(days=validity_days)
    password_credential_request = PasswordCredential()
    password_credential_request.display_name = display_name
    password_credential_request.end_date_time = secret_expiration

    logger.info(f"Adding password to application id={application_id}")

    async def add_password_op():
        password_result = await graph_client.applications.by_application_id(
            application_id
        ).add_password.post(password_credential_request)

        if not password_result or not password_result.secret_text:
            raise Exception("Password generation returned no secret")
        return password_result

    password_result = await retry_with_backoff(
        add_password_op,
        operation_name=f"Password addition (app_id={application_id})"
    )

    logger.info(f"Password added successfully, expires {secret_expiration}")
    return password_result


async def find_service_principal_by_name(
    graph_client: GraphServiceClient,
    sp_name: str,
) -> str | None:
    """Find a service principal by display name.

    Args:
        graph_client: Microsoft Graph API client
        sp_name: Service principal display name

    Returns:
        Service principal object ID if found, None otherwise

    Raises:
        ServicePrincipalError: If search fails
    """
    try:
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
            return sp_list.value[0].id

        return None

    except Exception as e:
        raise ServicePrincipalError(f"Failed to find service principal: {e}") from e


async def delete_service_principal_by_id(
    graph_client: GraphServiceClient,
    sp_id: str,
) -> None:
    """Delete a service principal by object ID.

    Args:
        graph_client: Microsoft Graph API client
        sp_id: Service principal object ID

    Raises:
        ServicePrincipalError: If deletion fails
    """
    try:
        sp_delete_client = graph_client.service_principals.by_service_principal_id(sp_id)
        await asyncio.to_thread(sp_delete_client.delete)
        logger.info(f"Service principal deleted: id={sp_id}")
    except Exception as e:
        raise ServicePrincipalError(f"Failed to delete service principal: {e}") from e


async def find_application_by_name(
    graph_client: GraphServiceClient,
    app_name: str,
):
    """Find an application by display name.

    Args:
        graph_client: Microsoft Graph API client
        app_name: Application display name

    Returns:
        Application object if found, None otherwise

    Raises:
        ServicePrincipalError: If search fails
    """
    try:
        filter_query = f"displayName eq '{sanitize_odata_value(app_name)}'"

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

        if app_list and app_list.value and len(app_list.value) > 0:
            return app_list.value[0]

        return None

    except Exception as e:
        raise ServicePrincipalError(f"Failed to find application: {e}") from e


async def remove_application_password(
    graph_client: GraphServiceClient,
    application_id: str,
    key_id: str,
) -> None:
    """Remove a password credential from an application.

    Args:
        graph_client: Microsoft Graph API client
        application_id: Application object ID
        key_id: Key ID of the credential to remove

    Raises:
        ServicePrincipalError: If removal fails
    """
    try:
        from msgraph.generated.applications.item.remove_password.remove_password_post_request_body import (
            RemovePasswordPostRequestBody,
        )

        remove_body = RemovePasswordPostRequestBody()
        remove_body.key_id = key_id

        await graph_client.applications.by_application_id(
            application_id
        ).remove_password.post(remove_body)

        logger.info(f"Removed credential {key_id} from application {application_id}")

    except Exception as e:
        raise ServicePrincipalError(f"Failed to remove password credential: {e}") from e


async def list_all_service_principals(
    graph_client: GraphServiceClient,
) -> list[Any]:
    """List all service principals in the directory.

    Args:
        graph_client: Microsoft Graph API client

    Returns:
        List of ServicePrincipal objects

    Raises:
        ServicePrincipalError: If listing fails
    """
    try:
        sp_list = await asyncio.to_thread(graph_client.service_principals.get)
        return sp_list.value if sp_list and sp_list.value else []
    except Exception as e:
        raise ServicePrincipalError(f"Failed to list service principals: {e}") from e


__all__ = [
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_SECRET_VALIDITY_DAYS",
    "add_application_password",
    "create_application",
    "create_service_principal_for_app",
    "delete_service_principal_by_id",
    "find_application_by_name",
    "find_service_principal_by_name",
    "list_all_service_principals",
    "remove_application_password",
    "retry_with_backoff",
    "verify_application_exists",
]
