"""Secret rotation and expiration management for Service Principals.

This module handles checking secret expiration status and rotating
service principal credentials before they expire.

Philosophy:
- Single responsibility: Secret lifecycle management
- Proactive expiration monitoring
- Automatic rotation capabilities
"""

import logging
import os
from datetime import UTC, datetime

from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from msgraph.graph_service_client import GraphServiceClient
from pydantic import BaseModel, Field

from azure_haymaker.exceptions import ServicePrincipalError
from azure_haymaker.orchestrator.graph_operations import (
    DEFAULT_SECRET_VALIDITY_DAYS,
    add_application_password,
    find_application_by_name,
    find_service_principal_by_name,
    remove_application_password,
)
from azure_haymaker.orchestrator.secret_manager import get_secret_name_for_sp, store_secret

logger = logging.getLogger(__name__)


class SecretExpirationInfo(BaseModel):
    """Information about a service principal's secret expiration status."""

    sp_name: str = Field(..., description="Service principal name")
    client_id: str = Field(..., description="Application (client) ID")
    secret_expires_at: datetime | None = Field(default=None, description="When the secret expires")
    days_until_expiration: int | None = Field(default=None, description="Days until expiration")
    needs_rotation: bool = Field(default=False, description="Whether rotation is recommended")
    is_expired: bool = Field(default=False, description="Whether secret is expired")


async def check_secret_expiration(
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
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")

        credential = ClientSecretCredential(
            tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
        )
        graph_client = GraphServiceClient(credential)

        # Find the application by display name
        app = await find_application_by_name(graph_client, sp_name)

        if not app:
            raise ServicePrincipalError(f"Application {sp_name} not found")

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


async def rotate_service_principal_secret(
    sp_name: str,
    key_vault_client: SecretClient,
    secret_validity_days: int = DEFAULT_SECRET_VALIDITY_DAYS,
    remove_old_secrets: bool = True,
):
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
    from azure_haymaker.orchestrator.sp_manager import ServicePrincipalDetails

    secret_name = get_secret_name_for_sp(sp_name)

    try:
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")

        credential = ClientSecretCredential(
            tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
        )
        graph_client = GraphServiceClient(credential)

        # Find the application by display name
        app = await find_application_by_name(graph_client, sp_name)

        if not app or not app.id or not app.app_id:
            raise ServicePrincipalError(f"Application {sp_name} not found for rotation")

        # Find corresponding service principal
        sp_id = await find_service_principal_by_name(graph_client, sp_name)

        if not sp_id:
            raise ServicePrincipalError(f"Service principal for {sp_name} not found")

        logger.info(f"Rotating secret for {sp_name} (appId={app.app_id})")

        # Remove old password credentials if requested
        if remove_old_secrets and app.password_credentials:
            for old_cred in app.password_credentials:
                if old_cred.key_id:
                    try:
                        await remove_application_password(
                            graph_client,
                            app.id,
                            old_cred.key_id
                        )
                    except Exception as e:
                        logger.warning(f"Failed to remove old credential: {e}")

        # Create new password credential with expiration
        password_result = await add_application_password(
            graph_client,
            app.id,
            f"{sp_name}-secret-rotated",
            secret_validity_days
        )

        # Store new secret in Key Vault (overwrites existing)
        await store_secret(
            key_vault_client,
            secret_name,
            password_result.secret_text,
        )

        secret_expiration = password_result.end_date_time
        logger.info(f"Secret rotated successfully for {sp_name}, expires {secret_expiration}")

        return ServicePrincipalDetails(
            sp_name=sp_name,
            client_id=app.app_id,
            principal_id=sp_id,
            secret_reference=secret_name,
            created_at=datetime.now(UTC).isoformat(),
            secret_expires_at=secret_expiration.isoformat() if secret_expiration else None,
        )

    except ServicePrincipalError:
        raise
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
    from azure_haymaker.orchestrator.sp_lifecycle import list_haymaker_service_principals

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


__all__ = [
    "SecretExpirationInfo",
    "check_and_rotate_expiring_secrets",
    "check_secret_expiration",
    "rotate_service_principal_secret",
]
