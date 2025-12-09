"""
Unit tests for tenant authentication and credential management.

These tests follow TDD methodology - they will FAIL initially until
the TenantCredentialManager class is implemented.

Test Coverage:
- Get tenant credential from Key Vault
- Credential caching
- Cache invalidation
- Handle missing Key Vault secret
- Validate tenant access
- Store tenant credentials
- Credential rotation handling
"""

import pytest
from pydantic import SecretStr
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

# These imports will fail until implementation - that's expected for TDD!
try:
    from azure_haymaker.orchestrator.tenant_auth import (
        TenantCredentialManager,
        TenantCredential,
        CredentialNotFoundError,
        InvalidCredentialError,
    )
except ImportError:
    pytest.skip("TenantCredentialManager not yet implemented", allow_module_level=True)

from tests.fixtures.mock_clients import MockKeyVaultClient, create_sample_tenant_credentials


class TestTenantCredentialManager:
    """Test TenantCredentialManager class."""

    @pytest.fixture
    def mock_kv_client(self):
        """Create mock Key Vault client."""
        return MockKeyVaultClient()

    @pytest.fixture
    def credential_manager(self, mock_kv_client):
        """Create TenantCredentialManager instance."""
        return TenantCredentialManager(keyvault_client=mock_kv_client)

    @pytest.mark.asyncio
    async def test_get_tenant_credential_from_keyvault_successfully(
        self, credential_manager, mock_kv_client
    ):
        """Test that TenantCredentialManager retrieves credentials from Key Vault."""
        # Arrange
        tenant_name = "tenant-123"
        creds = create_sample_tenant_credentials()

        # Store credentials in mock Key Vault
        mock_kv_client.set_secret(f"{tenant_name}-client-id", creds["client_id"])
        mock_kv_client.set_secret(f"{tenant_name}-client-secret", creds["client_secret"])
        mock_kv_client.set_secret(f"{tenant_name}-tenant-id", creds["tenant_id"])
        mock_kv_client.set_secret(f"{tenant_name}-subscription-id", creds["subscription_id"])

        # Act
        credential = await credential_manager.get_tenant_credential(tenant_name)

        # Assert
        assert credential is not None
        assert credential.client_id == creds["client_id"]
        assert credential.client_secret.get_secret_value() == creds["client_secret"]
        assert credential.tenant_id == creds["tenant_id"]
        assert credential.subscription_id == creds["subscription_id"]

    @pytest.mark.asyncio
    async def test_get_tenant_credential_caches_credentials_on_first_fetch(
        self, credential_manager, mock_kv_client
    ):
        """Test that credentials are cached after first fetch."""
        # Arrange
        tenant_name = "tenant-cache-test"
        creds = create_sample_tenant_credentials()

        mock_kv_client.set_secret(f"{tenant_name}-client-id", creds["client_id"])
        mock_kv_client.set_secret(f"{tenant_name}-client-secret", creds["client_secret"])
        mock_kv_client.set_secret(f"{tenant_name}-tenant-id", creds["tenant_id"])
        mock_kv_client.set_secret(f"{tenant_name}-subscription-id", creds["subscription_id"])

        # Act - First call
        credential1 = await credential_manager.get_tenant_credential(tenant_name)

        # Record number of calls
        call_count_first = len(mock_kv_client.get_secret_calls)

        # Act - Second call (should use cache)
        credential2 = await credential_manager.get_tenant_credential(tenant_name)

        # Assert
        assert credential1.client_id == credential2.client_id
        # Should not make additional Key Vault calls
        assert len(mock_kv_client.get_secret_calls) == call_count_first

    @pytest.mark.asyncio
    async def test_invalidate_cache_clears_cached_credentials(
        self, credential_manager, mock_kv_client
    ):
        """Test that cache invalidation forces fresh fetch."""
        # Arrange
        tenant_name = "tenant-invalidate-test"
        creds = create_sample_tenant_credentials()

        mock_kv_client.set_secret(f"{tenant_name}-client-id", creds["client_id"])
        mock_kv_client.set_secret(f"{tenant_name}-client-secret", creds["client_secret"])
        mock_kv_client.set_secret(f"{tenant_name}-tenant-id", creds["tenant_id"])
        mock_kv_client.set_secret(f"{tenant_name}-subscription-id", creds["subscription_id"])

        # Act - First call
        await credential_manager.get_tenant_credential(tenant_name)
        call_count_before = len(mock_kv_client.get_secret_calls)

        # Invalidate cache
        credential_manager.invalidate_cache(tenant_name)

        # Act - Second call (should fetch again)
        await credential_manager.get_tenant_credential(tenant_name)

        # Assert
        assert len(mock_kv_client.get_secret_calls) > call_count_before

    @pytest.mark.asyncio
    async def test_get_tenant_credential_with_missing_secret_raises_error(
        self, credential_manager, mock_kv_client
    ):
        """Test that missing Key Vault secret raises CredentialNotFoundError."""
        # Arrange
        tenant_name = "nonexistent-tenant"

        # Act & Assert
        with pytest.raises(CredentialNotFoundError) as exc_info:
            await credential_manager.get_tenant_credential(tenant_name)

        assert tenant_name in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_tenant_access_succeeds_with_valid_credentials(
        self, credential_manager, mock_kv_client
    ):
        """Test that validate_tenant_access checks permissions successfully."""
        # Arrange
        tenant_name = "tenant-validate"
        creds = create_sample_tenant_credentials()

        mock_kv_client.set_secret(f"{tenant_name}-client-id", creds["client_id"])
        mock_kv_client.set_secret(f"{tenant_name}-client-secret", creds["client_secret"])
        mock_kv_client.set_secret(f"{tenant_name}-tenant-id", creds["tenant_id"])
        mock_kv_client.set_secret(f"{tenant_name}-subscription-id", creds["subscription_id"])

        # Act
        is_valid = await credential_manager.validate_tenant_access(tenant_name)

        # Assert
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_tenant_access_with_invalid_credentials_returns_false(
        self, credential_manager, mock_kv_client
    ):
        """Test that validate_tenant_access returns False for invalid credentials."""
        # Arrange
        tenant_name = "tenant-invalid"
        # Store invalid credentials (empty client_secret)
        mock_kv_client.set_secret(f"{tenant_name}-client-id", str(uuid4()))
        mock_kv_client.set_secret(f"{tenant_name}-client-secret", "")
        mock_kv_client.set_secret(f"{tenant_name}-tenant-id", str(uuid4()))
        mock_kv_client.set_secret(f"{tenant_name}-subscription-id", str(uuid4()))

        # Act
        is_valid = await credential_manager.validate_tenant_access(tenant_name)

        # Assert
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_store_tenant_credentials_in_keyvault_succeeds(
        self, credential_manager, mock_kv_client
    ):
        """Test that credentials can be stored in Key Vault."""
        # Arrange
        tenant_name = "tenant-store"
        creds = create_sample_tenant_credentials()

        # Act
        await credential_manager.store_tenant_credentials(
            tenant_name=tenant_name,
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            tenant_id=creds["tenant_id"],
            subscription_id=creds["subscription_id"],
        )

        # Assert - Verify secrets were stored
        stored_client_id = mock_kv_client.get_secret(f"{tenant_name}-client-id").value
        stored_client_secret = mock_kv_client.get_secret(f"{tenant_name}-client-secret").value

        assert stored_client_id == creds["client_id"]
        assert stored_client_secret == creds["client_secret"]

    @pytest.mark.asyncio
    async def test_rotate_credentials_updates_keyvault_and_invalidates_cache(
        self, credential_manager, mock_kv_client
    ):
        """Test that credential rotation updates Key Vault and cache."""
        # Arrange
        tenant_name = "tenant-rotate"
        old_creds = create_sample_tenant_credentials()
        new_creds = create_sample_tenant_credentials()

        # Store old credentials
        mock_kv_client.set_secret(f"{tenant_name}-client-id", old_creds["client_id"])
        mock_kv_client.set_secret(f"{tenant_name}-client-secret", old_creds["client_secret"])
        mock_kv_client.set_secret(f"{tenant_name}-tenant-id", old_creds["tenant_id"])
        mock_kv_client.set_secret(f"{tenant_name}-subscription-id", old_creds["subscription_id"])

        # Fetch and cache old credentials
        old_credential = await credential_manager.get_tenant_credential(tenant_name)
        assert old_credential.client_secret.get_secret_value() == old_creds["client_secret"]

        # Act - Rotate credentials
        await credential_manager.rotate_credentials(
            tenant_name=tenant_name,
            new_client_secret=new_creds["client_secret"],
        )

        # Assert - Fetch should return new credentials
        new_credential = await credential_manager.get_tenant_credential(tenant_name)
        assert new_credential.client_secret.get_secret_value() == new_creds["client_secret"]
        assert new_credential.client_secret.get_secret_value() != old_creds["client_secret"]

    @pytest.mark.asyncio
    async def test_get_all_tenant_names_returns_configured_tenants(
        self, credential_manager, mock_kv_client
    ):
        """Test that get_all_tenant_names lists all tenants with credentials."""
        # Arrange
        tenant1 = "tenant-alpha"
        tenant2 = "tenant-beta"

        # Store credentials for two tenants
        for tenant_name in [tenant1, tenant2]:
            creds = create_sample_tenant_credentials()
            mock_kv_client.set_secret(f"{tenant_name}-client-id", creds["client_id"])
            mock_kv_client.set_secret(f"{tenant_name}-client-secret", creds["client_secret"])
            mock_kv_client.set_secret(f"{tenant_name}-tenant-id", creds["tenant_id"])
            mock_kv_client.set_secret(
                f"{tenant_name}-subscription-id", creds["subscription_id"]
            )

        # Act
        tenant_names = await credential_manager.get_all_tenant_names()

        # Assert
        assert tenant1 in tenant_names
        assert tenant2 in tenant_names
        assert len(tenant_names) >= 2


class TestTenantCredential:
    """Test TenantCredential data class."""

    def test_tenant_credential_creation_with_valid_data_succeeds(self):
        """Test that TenantCredential can be created with SecretStr."""
        creds = create_sample_tenant_credentials()

        credential = TenantCredential(
            client_id=creds["client_id"],
            client_secret=SecretStr(creds["client_secret"]),
            tenant_id=creds["tenant_id"],
            subscription_id=creds["subscription_id"],
        )

        assert credential.client_id == creds["client_id"]
        assert credential.client_secret.get_secret_value() == creds["client_secret"]
        assert credential.tenant_id == creds["tenant_id"]
        assert credential.subscription_id == creds["subscription_id"]

    def test_tenant_credential_to_dict_returns_valid_dict(self):
        """Test that TenantCredential can be converted to dict with unwrapped secret."""
        creds = create_sample_tenant_credentials()
        credential = TenantCredential(
            client_id=creds["client_id"],
            client_secret=SecretStr(creds["client_secret"]),
            tenant_id=creds["tenant_id"],
            subscription_id=creds["subscription_id"],
        )

        cred_dict = credential.to_dict()

        assert cred_dict["client_id"] == creds["client_id"]
        assert cred_dict["client_secret"] == creds["client_secret"]

    def test_tenant_credential_masks_secret_in_str_representation(self):
        """Test that client_secret is masked when converting to string."""
        creds = create_sample_tenant_credentials()
        credential = TenantCredential(
            client_id=creds["client_id"],
            client_secret=SecretStr(creds["client_secret"]),
            tenant_id=creds["tenant_id"],
            subscription_id=creds["subscription_id"],
        )

        cred_str = str(credential)

        # Should not contain actual secret
        assert creds["client_secret"] not in cred_str
        assert "***" in cred_str
