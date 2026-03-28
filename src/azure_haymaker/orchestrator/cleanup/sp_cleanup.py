"""Service principal cleanup for Azure HayMaker.

This module handles deletion of service principals and their Key Vault secrets
during cleanup operations.

Philosophy:
- Single responsibility: Service principal deletion only
- Graceful handling of not-found errors (idempotent)
- Self-contained and regeneratable

Public API (the "studs"):
    delete_service_principals: Delete SPs and their Key Vault secrets
"""

import asyncio
import logging

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
    ServiceRequestError,
)
from azure.keyvault.secrets import SecretClient
from kiota_abstractions.api_error import APIError
from msgraph.graph_service_client import GraphServiceClient

from azure_haymaker.models.service_principal import ServicePrincipalDetails
from azure_haymaker.utils.credentials import get_credential

logger = logging.getLogger(__name__)


async def delete_service_principals(  # pyright: ignore[reportGeneralTypeIssues,reportUnnecessaryComparison,reportAttributeAccessIssue]
    sp_details: list[ServicePrincipalDetails],
    kv_client: SecretClient,
) -> list[str]:
    """Delete service principals and their Key Vault secrets.

    Deletes each service principal from Entra ID and removes the corresponding
    secret from Key Vault. Handles not-found errors gracefully (idempotent).

    Args:
        sp_details: List of service principal details to delete
        kv_client: Key Vault client for deleting secrets

    Returns:
        List of deleted service principal names

    Raises:
        ClientAuthenticationError: If authentication fails
        APIError: If Microsoft Graph API call fails
        HttpResponseError: If HTTP error occurs
        ServiceRequestError: If service request fails
    """
    credentials = get_credential()
    graph_client = GraphServiceClient(credentials)

    deleted_sps = []

    for sp in sp_details:
        try:
            # Import sanitization utility from sp_manager
            from azure_haymaker.orchestrator.sp_manager import sanitize_odata_value

            # Find SP by display name
            filter_query = f"displayName eq '{sanitize_odata_value(sp.sp_name)}'"

            # Use request configuration for filter
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

            # Check if result is valid
            if sp_list and hasattr(sp_list, "value") and sp_list.value:
                sp_obj = sp_list.value[0]
                if sp_obj.id:
                    # Delete the SP - call the delete method
                    sp_delete_client = graph_client.service_principals.by_service_principal_id(
                        sp_obj.id
                    )
                    await asyncio.to_thread(sp_delete_client.delete)
                    logger.info(f"Deleted service principal {sp.sp_name}")
                    deleted_sps.append(sp.sp_name)

            # Delete Key Vault secret
            try:
                kv_client.begin_delete_secret(sp.secret_reference)
                logger.info(f"Deleted Key Vault secret {sp.secret_reference}")
            except ResourceNotFoundError:
                logger.warning(f"Key Vault secret {sp.secret_reference} not found")
            except HttpResponseError as e:
                logger.error(f"HTTP error deleting Key Vault secret {sp.secret_reference}: {e}")

        except ClientAuthenticationError as e:
            logger.error(f"Authentication failed deleting service principal {sp.sp_name}: {e}")
        except (APIError, HttpResponseError, ServiceRequestError) as e:
            logger.error(f"Failed to delete service principal {sp.sp_name}: {e}")

    return deleted_sps


__all__ = [
    "delete_service_principals",
]
