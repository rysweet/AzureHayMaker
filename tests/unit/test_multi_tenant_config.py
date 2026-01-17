"""Unit tests for Phase 2 multi-tenant configuration support.

This module tests:
- TenantConfig model
- OrchestratorConfig tenant registry methods
- MultiTenantCredentialFactory
- Key Vault loading (with mocked Key Vault client)
- get_tenant_credential() with tenant_id parameter
"""

import json
import os
import threading
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from azure_haymaker.models.config import (
    CosmosDBConfig,
    LogAnalyticsConfig,
    OrchestratorConfig,
    SimulationSize,
    StorageConfig,
    TableStorageConfig,
    TenantConfig,
)
from azure_haymaker.utils.credentials import (
    MultiTenantCredentialFactory,
    get_tenant_credential,
)


def _create_test_config(**overrides):
    """Helper function to create test configs with all required fields."""
    defaults = {
        "target_tenant_id": "orchestrator-tenant",
        "target_subscription_id": "sub-123",
        "main_sp_client_id": "sp",
        "main_sp_client_secret": SecretStr("secret"),
        "anthropic_api_key": SecretStr("test-anthropic-key"),
        "service_bus_namespace": "test-servicebus",
        "container_registry": "testreg.azurecr.io",
        "container_image": "test:latest",
        "key_vault_url": "https://test-kv.vault.azure.net/",
        "simulation_size": SimulationSize.SMALL,
        "storage": StorageConfig(
            account_name="teststorage",
            container_logs="logs",
            container_state="state",
            container_reports="reports",
            container_scenarios="scenarios",
        ),
        "table_storage": TableStorageConfig(
            account_name="testtablestorage",
            table_execution_runs="executionruns",
            table_scenario_status="scenariostatus",
            table_resource_inventory="resourceinventory",
        ),
        "cosmosdb": CosmosDBConfig(
            endpoint="https://test-cosmos.documents.azure.com:443/",
            database_name="testdb",
            container_metrics="metrics",
        ),
        "log_analytics": LogAnalyticsConfig(
            workspace_id="test-workspace-id",
            workspace_key=SecretStr("test-workspace-key"),
        ),
        "resource_group_name": "test-rg",
        "vnet_integration_enabled": False,
    }
    defaults.update(overrides)
    return OrchestratorConfig(**defaults)


def _create_tenant_config(tenant_id: str, **overrides):
    """Helper to create TenantConfig for testing."""
    defaults = {
        "tenant_id": tenant_id,
        "subscription_id": f"sub-{tenant_id[:8]}",
        "sp_client_id": f"sp-{tenant_id[:8]}",
        "sp_client_secret": SecretStr(f"secret-{tenant_id[:8]}"),
        "display_name": f"Test Tenant {tenant_id[:8]}",
        "enabled": True,
    }
    defaults.update(overrides)
    return TenantConfig(**defaults)


# ============================================================================
# TenantConfig Model Tests
# ============================================================================


class TestTenantConfigModel:
    """Tests for TenantConfig model."""

    def test_tenant_config_creation(self):
        """Test basic TenantConfig creation."""
        config = TenantConfig(
            tenant_id="12345678-1234-1234-1234-123456789abc",
            subscription_id="87654321-4321-4321-4321-cba987654321",
            sp_client_id="abcdef12-3456-7890-abcd-ef1234567890",
            sp_client_secret=SecretStr("test-secret"),
        )

        assert config.tenant_id == "12345678-1234-1234-1234-123456789abc"
        assert config.subscription_id == "87654321-4321-4321-4321-cba987654321"
        assert config.enabled is True  # Default
        assert config.display_name is None  # Optional

    def test_tenant_config_with_optional_fields(self):
        """Test TenantConfig with all optional fields."""
        config = TenantConfig(
            tenant_id="12345678-1234-1234-1234-123456789abc",
            subscription_id="87654321-4321-4321-4321-cba987654321",
            sp_client_id="abcdef12-3456-7890-abcd-ef1234567890",
            sp_client_secret=SecretStr("test-secret"),
            display_name="Customer A",
            enabled=False,
            resource_group="rg-customer-a",
        )

        assert config.display_name == "Customer A"
        assert config.enabled is False
        assert config.resource_group == "rg-customer-a"

    def test_tenant_config_display_property(self):
        """Test display property for logging."""
        config = TenantConfig(
            tenant_id="12345678-1234-1234-1234-123456789abc",
            subscription_id="sub-123",
            sp_client_id="sp-123",
            sp_client_secret=SecretStr("secret"),
            display_name="Customer A",
            enabled=True,
        )

        assert "Customer A" in config.display
        assert "enabled" in config.display

    def test_tenant_config_display_without_name(self):
        """Test display property falls back to tenant_id prefix."""
        config = TenantConfig(
            tenant_id="12345678-1234-1234-1234-123456789abc",
            subscription_id="sub-123",
            sp_client_id="sp-123",
            sp_client_secret=SecretStr("secret"),
        )

        assert "12345678" in config.display
        assert "enabled" in config.display

    def test_tenant_config_display_disabled(self):
        """Test display shows disabled status."""
        config = TenantConfig(
            tenant_id="12345678-1234-1234-1234-123456789abc",
            subscription_id="sub-123",
            sp_client_id="sp-123",
            sp_client_secret=SecretStr("secret"),
            enabled=False,
        )

        assert "disabled" in config.display


# ============================================================================
# OrchestratorConfig Tenant Registry Tests
# ============================================================================


class TestOrchestratorConfigTenantRegistry:
    """Tests for OrchestratorConfig tenant registry methods."""

    def test_empty_tenant_registry_by_default(self):
        """Test tenant registry is empty by default (backward compatible)."""
        config = _create_test_config()

        assert config.tenants == {}
        assert not config.has_multi_tenant_registry
        assert config.list_tenants() == []

    def test_config_with_tenants(self):
        """Test OrchestratorConfig with tenant registry."""
        tenant_a = _create_tenant_config("tenant-a-12345678")
        tenant_b = _create_tenant_config("tenant-b-87654321")

        config = _create_test_config(
            tenants={
                tenant_a.tenant_id: tenant_a,
                tenant_b.tenant_id: tenant_b,
            }
        )

        assert config.has_multi_tenant_registry
        assert len(config.tenants) == 2

    def test_get_tenant_config_found(self):
        """Test get_tenant_config returns tenant when found."""
        tenant = _create_tenant_config("tenant-12345678")
        config = _create_test_config(tenants={tenant.tenant_id: tenant})

        result = config.get_tenant_config("tenant-12345678")

        assert result is not None
        assert result.tenant_id == "tenant-12345678"

    def test_get_tenant_config_not_found(self):
        """Test get_tenant_config returns None when not found."""
        config = _create_test_config()

        result = config.get_tenant_config("nonexistent-tenant")

        assert result is None

    def test_get_tenant_config_disabled(self):
        """Test get_tenant_config returns None for disabled tenant."""
        tenant = _create_tenant_config("tenant-12345678", enabled=False)
        config = _create_test_config(tenants={tenant.tenant_id: tenant})

        result = config.get_tenant_config("tenant-12345678")

        assert result is None

    def test_list_tenants_enabled_only(self):
        """Test list_tenants returns only enabled tenants by default."""
        tenant_a = _create_tenant_config("tenant-a", enabled=True)
        tenant_b = _create_tenant_config("tenant-b", enabled=False)
        tenant_c = _create_tenant_config("tenant-c", enabled=True)

        config = _create_test_config(
            tenants={
                tenant_a.tenant_id: tenant_a,
                tenant_b.tenant_id: tenant_b,
                tenant_c.tenant_id: tenant_c,
            }
        )

        result = config.list_tenants()

        assert len(result) == 2
        tenant_ids = [t.tenant_id for t in result]
        assert "tenant-a" in tenant_ids
        assert "tenant-c" in tenant_ids
        assert "tenant-b" not in tenant_ids

    def test_list_tenants_include_disabled(self):
        """Test list_tenants can include disabled tenants."""
        tenant_a = _create_tenant_config("tenant-a", enabled=True)
        tenant_b = _create_tenant_config("tenant-b", enabled=False)

        config = _create_test_config(
            tenants={
                tenant_a.tenant_id: tenant_a,
                tenant_b.tenant_id: tenant_b,
            }
        )

        result = config.list_tenants(include_disabled=True)

        assert len(result) == 2


# ============================================================================
# MultiTenantCredentialFactory Tests
# ============================================================================


class TestMultiTenantCredentialFactory:
    """Tests for MultiTenantCredentialFactory."""

    def setup_method(self):
        """Clear cache before each test."""
        MultiTenantCredentialFactory.clear_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        MultiTenantCredentialFactory.clear_cache()

    def test_get_credential_for_tenant(self):
        """Test getting credential for a tenant."""
        tenant = _create_tenant_config("tenant-12345678")

        credential = MultiTenantCredentialFactory.get_credential_for_tenant(tenant)

        from azure.identity import ClientSecretCredential

        assert isinstance(credential, ClientSecretCredential)

    def test_credential_caching(self):
        """Test that credentials are cached."""
        tenant = _create_tenant_config("tenant-12345678")

        cred1 = MultiTenantCredentialFactory.get_credential_for_tenant(tenant)
        cred2 = MultiTenantCredentialFactory.get_credential_for_tenant(tenant)

        # Same object (cached)
        assert cred1 is cred2

    def test_credential_force_refresh(self):
        """Test force_refresh creates new credential."""
        tenant = _create_tenant_config("tenant-12345678")

        cred1 = MultiTenantCredentialFactory.get_credential_for_tenant(tenant)
        cred2 = MultiTenantCredentialFactory.get_credential_for_tenant(tenant, force_refresh=True)

        # Different objects
        assert cred1 is not cred2

    def test_disabled_tenant_raises_error(self):
        """Test getting credential for disabled tenant raises error."""
        tenant = _create_tenant_config("tenant-12345678", enabled=False)

        with pytest.raises(ValueError, match="disabled"):
            MultiTenantCredentialFactory.get_credential_for_tenant(tenant)

    def test_clear_cache_specific_tenant(self):
        """Test clearing cache for specific tenant."""
        tenant_a = _create_tenant_config("tenant-a")
        tenant_b = _create_tenant_config("tenant-b")

        MultiTenantCredentialFactory.get_credential_for_tenant(tenant_a)
        MultiTenantCredentialFactory.get_credential_for_tenant(tenant_b)

        assert len(MultiTenantCredentialFactory.get_cached_tenant_ids()) == 2

        MultiTenantCredentialFactory.clear_cache("tenant-a")

        cached = MultiTenantCredentialFactory.get_cached_tenant_ids()
        assert "tenant-a" not in cached
        assert "tenant-b" in cached

    def test_clear_cache_all(self):
        """Test clearing all cached credentials."""
        tenant_a = _create_tenant_config("tenant-a")
        tenant_b = _create_tenant_config("tenant-b")

        MultiTenantCredentialFactory.get_credential_for_tenant(tenant_a)
        MultiTenantCredentialFactory.get_credential_for_tenant(tenant_b)

        MultiTenantCredentialFactory.clear_cache()

        assert len(MultiTenantCredentialFactory.get_cached_tenant_ids()) == 0

    def test_thread_safety(self):
        """Test credential factory is thread-safe."""
        tenant = _create_tenant_config("tenant-12345678")
        credentials = []
        errors = []

        def get_credential():
            try:
                cred = MultiTenantCredentialFactory.get_credential_for_tenant(tenant)
                credentials.append(cred)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_credential) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(credentials) == 10
        # All should be the same cached credential
        assert all(c is credentials[0] for c in credentials)


# ============================================================================
# get_tenant_credential() Multi-Tenant Tests
# ============================================================================


class TestGetTenantCredentialMultiTenant:
    """Tests for get_tenant_credential with tenant_id parameter."""

    def setup_method(self):
        """Clear cache before each test."""
        MultiTenantCredentialFactory.clear_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        MultiTenantCredentialFactory.clear_cache()

    def test_tenant_id_from_registry(self):
        """Test get_tenant_credential uses registry when tenant_id provided."""
        tenant = _create_tenant_config("tenant-12345678")
        config = _create_test_config(tenants={tenant.tenant_id: tenant})

        with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
            credential = get_tenant_credential(config, tenant_id="tenant-12345678")

        from azure.identity import ClientSecretCredential

        assert isinstance(credential, ClientSecretCredential)

    def test_tenant_id_disabled_raises_error(self):
        """Test get_tenant_credential raises error for disabled tenant."""
        tenant = _create_tenant_config("tenant-12345678", enabled=False)
        config = _create_test_config(tenants={tenant.tenant_id: tenant})

        with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
            with pytest.raises(ValueError, match="disabled"):
                get_tenant_credential(config, tenant_id="tenant-12345678")

    def test_tenant_id_not_in_registry_falls_back(self):
        """Test falls back to Phase 1 logic when tenant not in registry."""
        config = _create_test_config(tenants={})

        with patch("azure_haymaker.utils.credentials.get_credential") as mock_get_cred:
            mock_cred = MagicMock()
            mock_get_cred.return_value = mock_cred

            with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
                credential = get_tenant_credential(config, tenant_id="unknown-tenant")

            # Falls back to single-tenant mode
            mock_get_cred.assert_called_once()
            assert credential == mock_cred

    def test_backward_compatible_without_tenant_id(self):
        """Test backward compatibility when no tenant_id provided."""
        config = _create_test_config(tenants={})

        with patch("azure_haymaker.utils.credentials.get_credential") as mock_get_cred:
            mock_cred = MagicMock()
            mock_get_cred.return_value = mock_cred

            with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
                credential = get_tenant_credential(config)

            mock_get_cred.assert_called_once()
            assert credential == mock_cred


# ============================================================================
# Key Vault Loading Tests
# ============================================================================


class TestLoadTenantConfigsFromKeyVault:
    """Tests for load_tenant_configs_from_keyvault function."""

    def test_load_tenant_configs_success(self):
        """Test successful loading of tenant configs from Key Vault."""
        from azure_haymaker.orchestrator.config import load_tenant_configs_from_keyvault

        # Mock Key Vault client
        mock_kv_client = MagicMock()

        # Mock secret properties
        mock_prop_a = MagicMock()
        mock_prop_a.name = "tenant-customerA-config"
        mock_prop_b = MagicMock()
        mock_prop_b.name = "tenant-customerB-config"
        mock_prop_other = MagicMock()
        mock_prop_other.name = "other-secret"

        mock_kv_client.list_properties_of_secrets.return_value = [
            mock_prop_a,
            mock_prop_b,
            mock_prop_other,
        ]

        # Mock get_secret for configs and secrets
        def mock_get_secret(name):
            secrets = {
                "tenant-customerA-config": MagicMock(
                    value=json.dumps(
                        {
                            "tenant_id": "tenant-a-12345678",
                            "subscription_id": "sub-a",
                            "sp_client_id": "sp-a",
                            "display_name": "Customer A",
                        }
                    )
                ),
                "tenant-customerA-secret": MagicMock(value="secret-a"),
                "tenant-customerB-config": MagicMock(
                    value=json.dumps(
                        {
                            "tenant_id": "tenant-b-87654321",
                            "subscription_id": "sub-b",
                            "sp_client_id": "sp-b",
                        }
                    )
                ),
                "tenant-customerB-secret": MagicMock(value="secret-b"),
            }
            return secrets.get(name)

        mock_kv_client.get_secret = mock_get_secret

        result = load_tenant_configs_from_keyvault(mock_kv_client)

        assert len(result) == 2
        assert "tenant-a-12345678" in result
        assert "tenant-b-87654321" in result
        assert result["tenant-a-12345678"].display_name == "Customer A"

    def test_load_tenant_configs_with_prefix_filter(self):
        """Test loading tenant configs with prefix filter."""
        from azure_haymaker.orchestrator.config import load_tenant_configs_from_keyvault

        mock_kv_client = MagicMock()

        mock_prop_prod = MagicMock()
        mock_prop_prod.name = "tenant-prod-customerA-config"
        mock_prop_dev = MagicMock()
        mock_prop_dev.name = "tenant-dev-customerB-config"

        mock_kv_client.list_properties_of_secrets.return_value = [
            mock_prop_prod,
            mock_prop_dev,
        ]

        def mock_get_secret(name):
            secrets = {
                "tenant-prod-customerA-config": MagicMock(
                    value=json.dumps(
                        {
                            "tenant_id": "prod-tenant",
                            "subscription_id": "sub-prod",
                            "sp_client_id": "sp-prod",
                        }
                    )
                ),
                "tenant-prod-customerA-secret": MagicMock(value="secret-prod"),
            }
            return secrets.get(name)

        mock_kv_client.get_secret = mock_get_secret

        result = load_tenant_configs_from_keyvault(mock_kv_client, prefix_filter="prod")

        assert len(result) == 1
        assert "prod-tenant" in result

    def test_load_tenant_configs_missing_secret_raises_error(self):
        """Test error raised when SP secret is missing."""
        from azure_haymaker.orchestrator.config import (
            ConfigurationError,
            load_tenant_configs_from_keyvault,
        )

        mock_kv_client = MagicMock()

        mock_prop = MagicMock()
        mock_prop.name = "tenant-test-config"
        mock_kv_client.list_properties_of_secrets.return_value = [mock_prop]

        def mock_get_secret(name):
            if name == "tenant-test-config":
                return MagicMock(
                    value=json.dumps(
                        {
                            "tenant_id": "test-tenant",
                            "subscription_id": "sub",
                            "sp_client_id": "sp",
                        }
                    )
                )
            raise Exception("Secret not found")

        mock_kv_client.get_secret = mock_get_secret

        with pytest.raises(ConfigurationError, match="Failed to load SP secret"):
            load_tenant_configs_from_keyvault(mock_kv_client)

    def test_load_tenant_configs_invalid_json_raises_error(self):
        """Test error raised when config JSON is invalid."""
        from azure_haymaker.orchestrator.config import (
            ConfigurationError,
            load_tenant_configs_from_keyvault,
        )

        mock_kv_client = MagicMock()

        mock_prop = MagicMock()
        mock_prop.name = "tenant-test-config"
        mock_kv_client.list_properties_of_secrets.return_value = [mock_prop]

        mock_kv_client.get_secret.return_value = MagicMock(value="not-valid-json")

        with pytest.raises(ConfigurationError, match="Invalid JSON"):
            load_tenant_configs_from_keyvault(mock_kv_client)

    def test_load_tenant_configs_missing_required_fields(self):
        """Test error raised when required fields are missing."""
        from azure_haymaker.orchestrator.config import (
            ConfigurationError,
            load_tenant_configs_from_keyvault,
        )

        mock_kv_client = MagicMock()

        mock_prop = MagicMock()
        mock_prop.name = "tenant-test-config"
        mock_kv_client.list_properties_of_secrets.return_value = [mock_prop]

        def mock_get_secret(name):
            if name == "tenant-test-config":
                return MagicMock(
                    value=json.dumps(
                        {
                            "tenant_id": "test-tenant",
                            # Missing: subscription_id, sp_client_id
                        }
                    )
                )
            return MagicMock(value="secret")

        mock_kv_client.get_secret = mock_get_secret

        with pytest.raises(ConfigurationError, match="missing required fields"):
            load_tenant_configs_from_keyvault(mock_kv_client)


# ============================================================================
# Backward Compatibility Tests
# ============================================================================


class TestBackwardCompatibility:
    """Tests ensuring Phase 2 is backward compatible with Phase 1."""

    def setup_method(self):
        """Clear cache before each test."""
        MultiTenantCredentialFactory.clear_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        MultiTenantCredentialFactory.clear_cache()

    def test_config_without_tenants_works(self):
        """Test config without tenants field works (backward compatible)."""
        config = _create_test_config()

        assert not config.has_multi_tenant_registry
        assert config.list_tenants() == []
        assert config.get_tenant_config("any") is None

    def test_phase1_cross_tenant_still_works(self):
        """Test Phase 1 cross-tenant mode still works with Phase 2."""
        with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
            config = _create_test_config(
                target_tenant_id="different-tenant",
                target_tenant_sp_client_id="target-sp",
                target_tenant_sp_client_secret=SecretStr("target-secret"),
                tenants={},  # Empty registry
            )

            credential = get_tenant_credential(config)

            from azure.identity import ClientSecretCredential

            assert isinstance(credential, ClientSecretCredential)

    def test_single_tenant_mode_unchanged(self):
        """Test single-tenant mode behavior unchanged."""
        with patch("azure_haymaker.utils.credentials.get_credential") as mock_get_cred:
            mock_cred = MagicMock()
            mock_get_cred.return_value = mock_cred

            with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
                config = _create_test_config(
                    target_tenant_id="orchestrator-tenant",
                    tenants={},
                )

                credential = get_tenant_credential(config)

                mock_get_cred.assert_called_once()
                assert credential == mock_cred
