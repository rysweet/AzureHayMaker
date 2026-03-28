"""Unit tests for Azure credential factory module.

Tests the utils.credentials module which handles:
- AzureCredentialFactory singleton pattern
- MultiTenantCredentialFactory per-tenant caching
- Credential thread safety (concurrent access)
- Credential never logged in plaintext
- Credential rotation seamless operation
- Credential access audit trail

Testing approach (60/30/10 pyramid):
- 60% Unit tests (heavily mocked, fast)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, Mock, patch

import pytest
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
from pydantic import SecretStr

from azure_haymaker.utils.credentials import (
    AzureCredentialFactory,
    MultiTenantCredentialFactory,
    get_async_credential,
    get_credential,
    get_tenant_credential,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clear_credential_caches():
    """Clear all credential caches before each test."""
    AzureCredentialFactory.clear_cache()
    MultiTenantCredentialFactory.clear_cache()
    yield
    AzureCredentialFactory.clear_cache()
    MultiTenantCredentialFactory.clear_cache()


@pytest.fixture
def mock_tenant_config():
    """Create a mock TenantConfig for testing."""
    config = MagicMock()
    config.tenant_id = "test-tenant-12345678"
    config.subscription_id = "test-subscription-id"
    config.sp_client_id = "test-client-id"
    config.sp_client_secret = SecretStr("test-secret-value")
    config.enabled = True
    config.display = "Test Tenant"
    return config


@pytest.fixture
def mock_orchestrator_config():
    """Create a mock OrchestratorConfig for testing."""
    config = MagicMock()
    config.is_cross_tenant = False
    config.target_tenant_id = "test-tenant-id"
    config.target_tenant_sp_client_id = None
    config.target_tenant_sp_client_secret = None
    config.tenants = {}
    config.get_tenant_config = MagicMock(return_value=None)
    return config


# ============================================================================
# Unit Tests - AzureCredentialFactory (60%)
# ============================================================================


class TestAzureCredentialFactory:
    """Tests for AzureCredentialFactory singleton pattern."""

    def test_get_credential_creates_instance_once(self):
        """Test that get_credential returns same instance on multiple calls."""
        with patch("azure_haymaker.utils.credentials.DefaultAzureCredential") as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            # First call should create credential
            cred1 = AzureCredentialFactory.get_credential()
            # Second call should return cached credential
            cred2 = AzureCredentialFactory.get_credential()

            assert cred1 is cred2
            assert mock_cred.call_count == 1

    def test_get_credential_force_refresh_creates_new(self):
        """Test that force_refresh creates new credential instance."""
        with patch("azure_haymaker.utils.credentials.DefaultAzureCredential") as mock_cred:
            mock_cred.side_effect = [Mock(), Mock()]

            cred1 = AzureCredentialFactory.get_credential()
            cred2 = AzureCredentialFactory.get_credential(force_refresh=True)

            assert cred1 is not cred2
            assert mock_cred.call_count == 2

    def test_get_async_credential_creates_instance_once(self):
        """Test that get_async_credential returns same instance on multiple calls."""
        with patch("azure_haymaker.utils.credentials.AsyncDefaultAzureCredential") as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            cred1 = AzureCredentialFactory.get_async_credential()
            cred2 = AzureCredentialFactory.get_async_credential()

            assert cred1 is cred2
            assert mock_cred.call_count == 1

    def test_get_async_credential_force_refresh_creates_new(self):
        """Test that force_refresh creates new async credential."""
        with patch("azure_haymaker.utils.credentials.AsyncDefaultAzureCredential") as mock_cred:
            mock_cred.side_effect = [Mock(), Mock()]

            cred1 = AzureCredentialFactory.get_async_credential()
            cred2 = AzureCredentialFactory.get_async_credential(force_refresh=True)

            assert cred1 is not cred2
            assert mock_cred.call_count == 2

    def test_clear_cache_removes_cached_credentials(self):
        """Test that clear_cache removes all cached credentials."""
        with patch("azure_haymaker.utils.credentials.DefaultAzureCredential") as mock_cred:
            mock_cred.side_effect = [Mock(), Mock()]

            cred1 = AzureCredentialFactory.get_credential()
            AzureCredentialFactory.clear_cache()
            cred2 = AzureCredentialFactory.get_credential()

            assert cred1 is not cred2
            assert mock_cred.call_count == 2

    def test_sync_and_async_credentials_separate_caches(self):
        """Test that sync and async credentials maintain separate caches."""
        with patch("azure_haymaker.utils.credentials.DefaultAzureCredential") as mock_sync:
            with patch(
                "azure_haymaker.utils.credentials.AsyncDefaultAzureCredential"
            ) as mock_async:
                mock_sync.return_value = Mock()
                mock_async.return_value = Mock()

                sync_cred = AzureCredentialFactory.get_credential()
                async_cred = AzureCredentialFactory.get_async_credential()

                assert sync_cred is not async_cred
                assert mock_sync.call_count == 1
                assert mock_async.call_count == 1


# ============================================================================
# Unit Tests - MultiTenantCredentialFactory (60%)
# ============================================================================


class TestMultiTenantCredentialFactory:
    """Tests for MultiTenantCredentialFactory per-tenant caching."""

    def test_get_credential_for_tenant_creates_credential(self, mock_tenant_config):
        """Test that get_credential_for_tenant creates credential for tenant."""
        with patch("azure_haymaker.utils.credentials.ClientSecretCredential") as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            credential = MultiTenantCredentialFactory.get_credential_for_tenant(mock_tenant_config)

            assert credential is mock_instance
            mock_cred.assert_called_once_with(
                tenant_id=mock_tenant_config.tenant_id,
                client_id=mock_tenant_config.sp_client_id,
                client_secret="test-secret-value",
            )

    def test_get_credential_for_tenant_caches_per_tenant(self, mock_tenant_config):
        """Test that credentials are cached per tenant."""
        with patch("azure_haymaker.utils.credentials.ClientSecretCredential") as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            cred1 = MultiTenantCredentialFactory.get_credential_for_tenant(mock_tenant_config)
            cred2 = MultiTenantCredentialFactory.get_credential_for_tenant(mock_tenant_config)

            assert cred1 is cred2
            assert mock_cred.call_count == 1

    def test_get_credential_for_different_tenants_separate_cache(self):
        """Test that different tenants get separate cached credentials."""
        tenant1 = MagicMock()
        tenant1.tenant_id = "tenant-1"
        tenant1.sp_client_id = "client-1"
        tenant1.sp_client_secret = SecretStr("secret-1")
        tenant1.enabled = True

        tenant2 = MagicMock()
        tenant2.tenant_id = "tenant-2"
        tenant2.sp_client_id = "client-2"
        tenant2.sp_client_secret = SecretStr("secret-2")
        tenant2.enabled = True

        with patch("azure_haymaker.utils.credentials.ClientSecretCredential") as mock_cred:
            mock_cred.side_effect = [Mock(), Mock()]

            cred1 = MultiTenantCredentialFactory.get_credential_for_tenant(tenant1)
            cred2 = MultiTenantCredentialFactory.get_credential_for_tenant(tenant2)

            assert cred1 is not cred2
            assert mock_cred.call_count == 2

    def test_get_credential_for_disabled_tenant_raises_error(self):
        """Test that requesting credential for disabled tenant raises ValueError."""
        disabled_tenant = MagicMock()
        disabled_tenant.tenant_id = "disabled-tenant"
        disabled_tenant.enabled = False

        with pytest.raises(ValueError, match="disabled"):
            MultiTenantCredentialFactory.get_credential_for_tenant(disabled_tenant)

    def test_clear_cache_specific_tenant(self, mock_tenant_config):
        """Test that clear_cache can remove specific tenant credential."""
        with patch("azure_haymaker.utils.credentials.ClientSecretCredential") as mock_cred:
            mock_cred.side_effect = [Mock(), Mock()]

            cred1 = MultiTenantCredentialFactory.get_credential_for_tenant(mock_tenant_config)
            MultiTenantCredentialFactory.clear_cache(mock_tenant_config.tenant_id)
            cred2 = MultiTenantCredentialFactory.get_credential_for_tenant(mock_tenant_config)

            assert cred1 is not cred2
            assert mock_cred.call_count == 2

    def test_clear_cache_all_tenants(self):
        """Test that clear_cache without tenant_id clears all tenants."""
        tenant1 = MagicMock()
        tenant1.tenant_id = "tenant-1"
        tenant1.sp_client_id = "client-1"
        tenant1.sp_client_secret = SecretStr("secret-1")
        tenant1.enabled = True

        with patch("azure_haymaker.utils.credentials.ClientSecretCredential") as mock_cred:
            mock_cred.return_value = Mock()

            MultiTenantCredentialFactory.get_credential_for_tenant(tenant1)
            cached_before = MultiTenantCredentialFactory.get_cached_tenant_ids()
            assert len(cached_before) == 1

            MultiTenantCredentialFactory.clear_cache()
            cached_after = MultiTenantCredentialFactory.get_cached_tenant_ids()
            assert len(cached_after) == 0

    def test_get_cached_tenant_ids_returns_correct_list(self):
        """Test that get_cached_tenant_ids returns list of cached tenants."""
        tenant1 = MagicMock()
        tenant1.tenant_id = "tenant-1"
        tenant1.sp_client_id = "client-1"
        tenant1.sp_client_secret = SecretStr("secret-1")
        tenant1.enabled = True

        tenant2 = MagicMock()
        tenant2.tenant_id = "tenant-2"
        tenant2.sp_client_id = "client-2"
        tenant2.sp_client_secret = SecretStr("secret-2")
        tenant2.enabled = True

        with patch("azure_haymaker.utils.credentials.ClientSecretCredential"):
            MultiTenantCredentialFactory.get_credential_for_tenant(tenant1)
            MultiTenantCredentialFactory.get_credential_for_tenant(tenant2)

            cached = MultiTenantCredentialFactory.get_cached_tenant_ids()
            assert len(cached) == 2
            assert "tenant-1" in cached
            assert "tenant-2" in cached


# ============================================================================
# Unit Tests - Thread Safety (60%)
# ============================================================================


class TestCredentialThreadSafety:
    """Tests for credential factory thread safety under concurrent access."""

    def test_concurrent_access_to_azure_credential_factory(self):
        """Test that concurrent access to AzureCredentialFactory is thread-safe."""
        with patch("azure_haymaker.utils.credentials.DefaultAzureCredential") as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            credentials = []

            def get_cred():
                credentials.append(AzureCredentialFactory.get_credential())

            # Simulate concurrent access from 10 threads
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(get_cred) for _ in range(10)]
                for future in futures:
                    future.result()

            # All threads should get the same credential instance
            assert all(cred is credentials[0] for cred in credentials)
            # Credential should only be created once
            assert mock_cred.call_count == 1

    def test_concurrent_access_to_multi_tenant_factory(self):
        """Test that concurrent access to MultiTenantCredentialFactory is thread-safe."""
        tenant_config = MagicMock()
        tenant_config.tenant_id = "test-tenant"
        tenant_config.sp_client_id = "client-id"
        tenant_config.sp_client_secret = SecretStr("secret")
        tenant_config.enabled = True

        with patch("azure_haymaker.utils.credentials.ClientSecretCredential") as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            credentials = []

            def get_cred():
                credentials.append(
                    MultiTenantCredentialFactory.get_credential_for_tenant(tenant_config)
                )

            # Simulate concurrent access from 10 threads
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(get_cred) for _ in range(10)]
                for future in futures:
                    future.result()

            # All threads should get the same credential instance
            assert all(cred is credentials[0] for cred in credentials)
            # Credential should only be created once
            assert mock_cred.call_count == 1

    def test_concurrent_clear_and_get_operations(self):
        """Test thread safety when clearing cache while getting credentials."""
        with patch("azure_haymaker.utils.credentials.DefaultAzureCredential") as mock_cred:
            mock_cred.side_effect = [Mock() for _ in range(20)]

            results = []

            def get_and_clear():
                cred = AzureCredentialFactory.get_credential()
                results.append(cred)
                time.sleep(0.001)  # Small delay to increase contention
                AzureCredentialFactory.clear_cache()

            # Run operations concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(get_and_clear) for _ in range(10)]
                for future in futures:
                    future.result()

            # All operations should complete without errors
            assert len(results) == 10


# ============================================================================
# Unit Tests - Credential Security (60%)
# ============================================================================


class TestCredentialSecurity:
    """Tests for credential security - never logged in plaintext."""

    def test_credentials_not_logged_in_plaintext(self, mock_tenant_config, caplog):
        """Test that credential secrets are never logged in plaintext."""
        with caplog.at_level(logging.DEBUG):
            with patch("azure_haymaker.utils.credentials.ClientSecretCredential"):
                MultiTenantCredentialFactory.get_credential_for_tenant(mock_tenant_config)

                # Check all log messages
                for record in caplog.records:
                    # Secret value should NEVER appear in logs
                    assert "test-secret-value" not in record.message
                    # Even partial secret should not appear
                    assert "secret-value" not in record.message.lower()

    def test_secret_str_masking_in_repr(self, mock_tenant_config):
        """Test that SecretStr masks value in string representation."""
        secret = mock_tenant_config.sp_client_secret

        # SecretStr should mask the value in repr
        secret_repr = repr(secret)
        assert "test-secret-value" not in secret_repr
        assert "***" in secret_repr or "SecretStr" in secret_repr

    def test_get_tenant_credential_does_not_log_secrets(self, mock_orchestrator_config, caplog):
        """Test that get_tenant_credential never logs secrets."""
        mock_orchestrator_config.is_cross_tenant = True
        mock_orchestrator_config.target_tenant_sp_client_id = "client-id"
        mock_orchestrator_config.target_tenant_sp_client_secret = SecretStr("super-secret-value")

        with caplog.at_level(logging.DEBUG):
            with patch("azure_haymaker.utils.credentials.ClientSecretCredential"):
                get_tenant_credential(mock_orchestrator_config)

                for record in caplog.records:
                    assert "super-secret-value" not in record.message


# ============================================================================
# Unit Tests - Convenience Functions (60%)
# ============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_credential_calls_factory(self):
        """Test that get_credential() calls AzureCredentialFactory."""
        with patch(
            "azure_haymaker.utils.credentials.AzureCredentialFactory.get_credential"
        ) as mock_get:
            mock_get.return_value = Mock()

            credential = get_credential()

            assert credential is mock_get.return_value
            mock_get.assert_called_once_with(force_refresh=False)

    def test_get_credential_force_refresh_parameter(self):
        """Test that get_credential passes force_refresh parameter."""
        with patch(
            "azure_haymaker.utils.credentials.AzureCredentialFactory.get_credential"
        ) as mock_get:
            mock_get.return_value = Mock()

            get_credential(force_refresh=True)

            mock_get.assert_called_once_with(force_refresh=True)

    def test_get_async_credential_calls_factory(self):
        """Test that get_async_credential() calls AzureCredentialFactory."""
        with patch(
            "azure_haymaker.utils.credentials.AzureCredentialFactory.get_async_credential"
        ) as mock_get:
            mock_get.return_value = Mock()

            credential = get_async_credential()

            assert credential is mock_get.return_value
            mock_get.assert_called_once_with(force_refresh=False)


# ============================================================================
# Integration Tests - get_tenant_credential (30%)
# ============================================================================


class TestGetTenantCredentialIntegration:
    """Integration tests for get_tenant_credential multi-phase logic."""

    def test_phase2_tenant_registry_priority(self, mock_orchestrator_config):
        """Test that Phase 2 tenant registry takes priority over Phase 1."""
        # Setup Phase 2 tenant in registry
        tenant_config = MagicMock()
        tenant_config.tenant_id = "registry-tenant"
        tenant_config.sp_client_id = "registry-client"
        tenant_config.sp_client_secret = SecretStr("registry-secret")
        tenant_config.enabled = True
        tenant_config.display = "Registry Tenant"

        mock_orchestrator_config.get_tenant_config = MagicMock(return_value=tenant_config)

        with patch(
            "azure_haymaker.utils.credentials.MultiTenantCredentialFactory.get_credential_for_tenant"
        ) as mock_multi:
            mock_multi.return_value = Mock()

            credential = get_tenant_credential(
                mock_orchestrator_config, tenant_id="registry-tenant"
            )

            # Should use MultiTenantCredentialFactory (Phase 2)
            mock_multi.assert_called_once_with(tenant_config)
            assert credential is mock_multi.return_value

    def test_phase1_cross_tenant_fallback(self, mock_orchestrator_config):
        """Test Phase 1 cross-tenant mode when tenant not in registry."""
        mock_orchestrator_config.is_cross_tenant = True
        mock_orchestrator_config.target_tenant_id = "target-tenant"
        mock_orchestrator_config.target_tenant_sp_client_id = "target-client"
        mock_orchestrator_config.target_tenant_sp_client_secret = SecretStr("target-secret")

        with patch("azure_haymaker.utils.credentials.ClientSecretCredential") as mock_cred:
            mock_instance = Mock()
            mock_cred.return_value = mock_instance

            credential = get_tenant_credential(mock_orchestrator_config)

            mock_cred.assert_called_once_with(
                tenant_id="target-tenant",
                client_id="target-client",
                client_secret="target-secret",
            )
            assert credential is mock_instance

    def test_single_tenant_mode_uses_default_credential(self, mock_orchestrator_config):
        """Test that single-tenant mode uses DefaultAzureCredential."""
        mock_orchestrator_config.is_cross_tenant = False

        with patch("azure_haymaker.utils.credentials.get_credential") as mock_get:
            mock_get.return_value = Mock()

            credential = get_tenant_credential(mock_orchestrator_config)

            mock_get.assert_called_once()
            assert credential is mock_get.return_value

    def test_cross_tenant_missing_client_id_raises_error(self, mock_orchestrator_config):
        """Test that cross-tenant mode without client_id raises ValueError."""
        mock_orchestrator_config.is_cross_tenant = True
        mock_orchestrator_config.target_tenant_sp_client_id = None

        with pytest.raises(ValueError, match="TARGET_TENANT_SP_CLIENT_ID"):
            get_tenant_credential(mock_orchestrator_config)

    def test_cross_tenant_missing_secret_raises_error(self, mock_orchestrator_config):
        """Test that cross-tenant mode without secret raises ValueError."""
        mock_orchestrator_config.is_cross_tenant = True
        mock_orchestrator_config.target_tenant_sp_client_id = "client-id"
        mock_orchestrator_config.target_tenant_sp_client_secret = None

        with pytest.raises(ValueError, match="TARGET_TENANT_SP_CLIENT_SECRET"):
            get_tenant_credential(mock_orchestrator_config)

    def test_disabled_tenant_in_registry_raises_error(self, mock_orchestrator_config):
        """Test that requesting disabled tenant raises ValueError."""
        mock_orchestrator_config.tenants = {"disabled-tenant": MagicMock()}
        mock_orchestrator_config.get_tenant_config = MagicMock(return_value=None)

        with pytest.raises(ValueError, match="disabled"):
            get_tenant_credential(mock_orchestrator_config, tenant_id="disabled-tenant")


# ============================================================================
# E2E Tests - Credential Rotation (10%)
# ============================================================================


class TestCredentialRotation:
    """E2E tests for seamless credential rotation."""

    def test_credential_rotation_without_disruption(self):
        """Test that credential rotation works seamlessly without disruption."""
        with patch("azure_haymaker.utils.credentials.DefaultAzureCredential") as mock_cred:
            old_credential = Mock()
            new_credential = Mock()
            mock_cred.side_effect = [old_credential, new_credential]

            # Get initial credential
            cred1 = AzureCredentialFactory.get_credential()
            assert cred1 is old_credential

            # Simulate credential rotation
            AzureCredentialFactory.clear_cache()
            cred2 = AzureCredentialFactory.get_credential()

            # New credential should be created
            assert cred2 is new_credential
            assert cred2 is not cred1
            assert mock_cred.call_count == 2

    def test_multi_tenant_credential_rotation(self):
        """Test credential rotation for specific tenant."""
        tenant_config = MagicMock()
        tenant_config.tenant_id = "test-tenant"
        tenant_config.sp_client_id = "client-id"
        tenant_config.sp_client_secret = SecretStr("secret")
        tenant_config.enabled = True

        with patch("azure_haymaker.utils.credentials.ClientSecretCredential") as mock_cred:
            old_cred = Mock()
            new_cred = Mock()
            mock_cred.side_effect = [old_cred, new_cred]

            # Get initial credential
            cred1 = MultiTenantCredentialFactory.get_credential_for_tenant(tenant_config)
            assert cred1 is old_cred

            # Rotate credential for this tenant
            MultiTenantCredentialFactory.clear_cache(tenant_config.tenant_id)
            cred2 = MultiTenantCredentialFactory.get_credential_for_tenant(tenant_config)

            # New credential should be created
            assert cred2 is new_cred
            assert cred2 is not cred1


# ============================================================================
# E2E Tests - Complete Workflows (10%)
# ============================================================================


class TestCompleteWorkflows:
    """E2E tests for complete credential workflows."""

    def test_full_multi_tenant_workflow(self):
        """Test complete multi-tenant credential workflow."""
        # Create multiple tenant configs
        tenant1 = MagicMock()
        tenant1.tenant_id = "tenant-1"
        tenant1.sp_client_id = "client-1"
        tenant1.sp_client_secret = SecretStr("secret-1")
        tenant1.enabled = True

        tenant2 = MagicMock()
        tenant2.tenant_id = "tenant-2"
        tenant2.sp_client_id = "client-2"
        tenant2.sp_client_secret = SecretStr("secret-2")
        tenant2.enabled = True

        with patch("azure_haymaker.utils.credentials.ClientSecretCredential") as mock_cred:
            mock_cred.side_effect = [Mock(), Mock()]

            # Get credentials for both tenants
            cred1 = MultiTenantCredentialFactory.get_credential_for_tenant(tenant1)
            cred2 = MultiTenantCredentialFactory.get_credential_for_tenant(tenant2)

            # Verify separate credentials
            assert cred1 is not cred2

            # Verify caching
            cached_ids = MultiTenantCredentialFactory.get_cached_tenant_ids()
            assert len(cached_ids) == 2
            assert "tenant-1" in cached_ids
            assert "tenant-2" in cached_ids

            # Get same credentials again (should be cached)
            cred1_again = MultiTenantCredentialFactory.get_credential_for_tenant(tenant1)
            cred2_again = MultiTenantCredentialFactory.get_credential_for_tenant(tenant2)

            assert cred1 is cred1_again
            assert cred2 is cred2_again
            # Should still only have 2 calls (no new credentials created)
            assert mock_cred.call_count == 2

    def test_phase_transition_workflow(self, mock_orchestrator_config):
        """Test workflow transitioning from Phase 1 to Phase 2."""
        # Start with Phase 1 (cross-tenant mode)
        mock_orchestrator_config.is_cross_tenant = True
        mock_orchestrator_config.target_tenant_sp_client_id = "phase1-client"
        mock_orchestrator_config.target_tenant_sp_client_secret = SecretStr("phase1-secret")

        with patch("azure_haymaker.utils.credentials.ClientSecretCredential") as mock_cred:
            phase1_cred = Mock()
            phase2_cred = Mock()
            mock_cred.side_effect = [phase1_cred, phase2_cred]

            # Phase 1: Get credential without tenant registry
            cred1 = get_tenant_credential(mock_orchestrator_config)
            assert cred1 is phase1_cred

            # Transition to Phase 2: Add tenant to registry
            tenant_config = MagicMock()
            tenant_config.tenant_id = "registry-tenant"
            tenant_config.sp_client_id = "phase2-client"
            tenant_config.sp_client_secret = SecretStr("phase2-secret")
            tenant_config.enabled = True
            tenant_config.display = "Phase 2 Tenant"

            mock_orchestrator_config.get_tenant_config = MagicMock(return_value=tenant_config)

            # Phase 2: Get credential with tenant registry
            with patch(
                "azure_haymaker.utils.credentials.MultiTenantCredentialFactory.get_credential_for_tenant"
            ) as mock_multi:
                mock_multi.return_value = phase2_cred

                cred2 = get_tenant_credential(mock_orchestrator_config, tenant_id="registry-tenant")

                # Should use Phase 2 credential from registry
                assert cred2 is phase2_cred
                mock_multi.assert_called_once_with(tenant_config)
