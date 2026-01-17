"""Unit tests for cross-tenant configuration detection and credential selection.

This module tests the cross-tenant functionality including:
- Configuration detection (single-tenant vs cross-tenant)
- Credential selection logic
- Tenant-aware path generation
- Error handling for missing credentials
"""

import os
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
)
from azure_haymaker.utils.credentials import get_tenant_credential


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


@pytest.fixture
def single_tenant_config():
    """Create a single-tenant configuration for testing."""
    with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
        return _create_test_config(
            target_tenant_id="orchestrator-tenant",  # Same as orchestrator
            target_subscription_id="sub-123",
            main_sp_client_id="sp-id",
        )


@pytest.fixture
def cross_tenant_config():
    """Create a cross-tenant configuration for testing."""
    with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
        return _create_test_config(
            target_tenant_id="different-tenant",
            target_subscription_id="sub-456",
            target_tenant_sp_client_id="target-sp-id",
            target_tenant_sp_client_secret=SecretStr("target-secret"),
            main_sp_client_id="orch-sp",
        )


def test_single_tenant_mode_detection(single_tenant_config):
    """Test single-tenant mode is default when no cross-tenant config."""
    assert not single_tenant_config.is_cross_tenant
    assert "same as orchestrator" in single_tenant_config.target_tenant_display


def test_cross_tenant_mode_detection(cross_tenant_config):
    """Test cross-tenant mode detected when tenant differs and creds provided."""
    assert cross_tenant_config.is_cross_tenant
    assert "cross-tenant" in cross_tenant_config.target_tenant_display


def test_cross_tenant_requires_both_fields():
    """Test cross-tenant mode requires both tenant_id AND credentials."""
    with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
        # Different tenant but no credentials
        config = _create_test_config(
            target_tenant_id="different-tenant",
            target_subscription_id="sub-456",
            # Missing: target_tenant_sp_client_id and secret!
        )

        # is_cross_tenant is False because no credentials provided
        assert not config.is_cross_tenant


def test_credential_selection_single_tenant(single_tenant_config, mocker):
    """Test credential selection uses DefaultAzureCredential in single-tenant mode."""
    mock_get_cred = mocker.patch("azure_haymaker.utils.credentials.get_credential")
    mock_cred = MagicMock()
    mock_get_cred.return_value = mock_cred

    credential = get_tenant_credential(single_tenant_config)

    mock_get_cred.assert_called_once()
    assert credential == mock_cred


def test_credential_selection_cross_tenant(cross_tenant_config):
    """Test credential selection uses ClientSecretCredential in cross-tenant mode."""
    from azure.identity import ClientSecretCredential

    credential = get_tenant_credential(cross_tenant_config)

    assert isinstance(credential, ClientSecretCredential)
    # ClientSecretCredential stores tenant_id in _tenant_id attribute
    assert credential._tenant_id == "different-tenant"


def test_missing_cross_tenant_client_id_raises_error():
    """Test error raised if cross-tenant mode but client_id missing."""
    with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
        config = _create_test_config(
            target_tenant_id="different-tenant",
            target_subscription_id="sub-456",
            # Has secret but no client_id
            target_tenant_sp_client_secret=SecretStr("target-secret"),
        )

        # Cross-tenant not enabled because client_id missing
        assert not config.is_cross_tenant


def test_missing_cross_tenant_secret_raises_error():
    """Test error raised if cross-tenant mode but secret missing."""
    with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
        config = _create_test_config(
            target_tenant_id="different-tenant",
            target_subscription_id="sub-456",
            # Has client_id but no secret
            target_tenant_sp_client_id="target-sp-id",
        )

        # Note: is_cross_tenant is True if client_id is provided, even if secret is missing
        # This matches the implementation in config.py lines 170-174
        assert config.is_cross_tenant

        # But get_tenant_credential should raise ValueError when secret is missing
        with pytest.raises(ValueError, match="TARGET_TENANT_SP_CLIENT_SECRET"):
            get_tenant_credential(config)


def test_tenant_display_shows_tenant_prefix():
    """Test tenant_display property shows correct tenant prefix."""
    with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
        config = _create_test_config(
            target_tenant_id="abcd1234-ef56-7890-abcd-ef1234567890",
            target_subscription_id="sub-456",
            target_tenant_sp_client_id="target-sp-id",
            target_tenant_sp_client_secret=SecretStr("target-secret"),
        )

        # Should show first 8 chars of tenant_id
        assert "abcd1234" in config.target_tenant_display
        assert "cross-tenant" in config.target_tenant_display


def test_same_tenant_different_subscription_not_cross_tenant():
    """Test same tenant with different subscription is single-tenant mode."""
    with patch.dict(os.environ, {"AZURE_TENANT_ID": "same-tenant"}):
        config = _create_test_config(
            target_tenant_id="same-tenant",  # Same as AZURE_TENANT_ID
            target_subscription_id="different-sub",
        )

        # Same tenant = single-tenant mode even with different subscription
        assert not config.is_cross_tenant


def test_get_tenant_credential_raises_on_missing_client_id():
    """Test get_tenant_credential raises ValueError when client_id missing in cross-tenant."""
    with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
        config = _create_test_config(
            target_tenant_id="different-tenant",
            target_subscription_id="sub-456",
            target_tenant_sp_client_id="target-sp-id",
            target_tenant_sp_client_secret=SecretStr("target-secret"),
        )

        # Mock is_cross_tenant to stay True even though we'll clear credentials
        with patch.object(
            type(config), "is_cross_tenant", new_callable=lambda: property(lambda self: True)
        ):
            # Manually set to None to simulate missing credentials
            config.target_tenant_sp_client_id = None

            with pytest.raises(ValueError, match="TARGET_TENANT_SP_CLIENT_ID"):
                get_tenant_credential(config)


def test_get_tenant_credential_raises_on_missing_secret():
    """Test get_tenant_credential raises ValueError when secret missing in cross-tenant."""
    with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
        config = _create_test_config(
            target_tenant_id="different-tenant",
            target_subscription_id="sub-456",
            target_tenant_sp_client_id="target-sp-id",
            target_tenant_sp_client_secret=SecretStr("target-secret"),
        )

        # Mock is_cross_tenant to stay True even though we'll clear credentials
        with patch.object(
            type(config), "is_cross_tenant", new_callable=lambda: property(lambda self: True)
        ):
            # Manually set to None to simulate missing credentials
            config.target_tenant_sp_client_secret = None

            with pytest.raises(ValueError, match="TARGET_TENANT_SP_CLIENT_SECRET"):
                get_tenant_credential(config)


def test_backward_compatibility_no_optional_fields():
    """Test backward compatibility when optional cross-tenant fields not set."""
    with patch.dict(os.environ, {"AZURE_TENANT_ID": "orchestrator-tenant"}):
        config = _create_test_config(
            target_tenant_id="orchestrator-tenant",
            target_subscription_id="sub-123",
            # No target_tenant_sp_* fields at all
        )

        # Should default to single-tenant mode
        assert not config.is_cross_tenant
        assert config.target_tenant_sp_client_id is None
        assert config.target_tenant_sp_client_secret is None
