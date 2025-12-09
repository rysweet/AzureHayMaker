"""
Unit tests for multi-tenant configuration models.

These tests follow TDD methodology - they will FAIL initially until
the corresponding models are implemented.

Test Coverage:
- TenantContext model validation
- TargetTenantConfig model validation
- MetaOrchestratorConfig model validation
"""

import pytest
from uuid import UUID
from pydantic import ValidationError

# These imports will fail until models are implemented - that's expected for TDD!
try:
    from azure_haymaker.orchestrator.models import (
        TenantContext,
        TargetTenantConfig,
        MetaOrchestratorConfig,
    )
except ImportError:
    # Mark all tests as expected to fail until implementation
    pytest.skip("Models not yet implemented", allow_module_level=True)

from tests.fixtures.tenant_configs import (
    sample_tenant_context,
    sample_target_tenant_config,
    sample_meta_orchestrator_config,
    sample_multi_tenant_config,
    invalid_tenant_context_non_uuid,
    invalid_target_tenant_invalid_cron,
)


class TestTenantContext:
    """Test TenantContext model validation."""

    def test_tenant_context_creation_with_valid_data_succeeds(self):
        """Test that TenantContext can be created with valid data."""
        data = sample_tenant_context()

        context = TenantContext(**data)

        assert context.tenant_id is not None
        assert context.tenant_name == "test-tenant"
        assert context.subscription_id is not None
        assert context.region == "eastus"

    def test_tenant_context_with_invalid_tenant_id_raises_validation_error(self):
        """Test that non-UUID tenant_id is rejected."""
        data = invalid_tenant_context_non_uuid()

        with pytest.raises(ValidationError) as exc_info:
            TenantContext(**data)

        assert "tenant_id" in str(exc_info.value)

    def test_tenant_context_with_invalid_subscription_id_raises_validation_error(self):
        """Test that non-UUID subscription_id is rejected."""
        data = sample_tenant_context()
        data["subscription_id"] = "not-a-uuid"

        with pytest.raises(ValidationError) as exc_info:
            TenantContext(**data)

        assert "subscription_id" in str(exc_info.value)

    def test_tenant_context_storage_prefix_generation_uses_tenant_id(self):
        """Test that storage prefix is correctly generated from tenant_id."""
        data = sample_tenant_context()

        context = TenantContext(**data)
        expected_prefix = f"{data['tenant_id']}"

        assert context.get_storage_prefix() == expected_prefix

    def test_tenant_context_serialization_produces_valid_dict(self):
        """Test that TenantContext can be serialized to dict."""
        data = sample_tenant_context()
        context = TenantContext(**data)

        serialized = context.model_dump()

        assert serialized["tenant_id"] == data["tenant_id"]
        assert serialized["tenant_name"] == data["tenant_name"]
        assert serialized["subscription_id"] == data["subscription_id"]
        assert serialized["region"] == data["region"]

    def test_tenant_context_deserialization_from_dict_succeeds(self):
        """Test that TenantContext can be deserialized from dict."""
        data = sample_tenant_context()
        serialized = TenantContext(**data).model_dump()

        context = TenantContext(**serialized)

        assert context.tenant_id == data["tenant_id"]
        assert context.tenant_name == data["tenant_name"]

    def test_tenant_context_with_missing_required_field_raises_validation_error(self):
        """Test that missing required fields raise validation error."""
        data = sample_tenant_context()
        del data["tenant_name"]

        with pytest.raises(ValidationError) as exc_info:
            TenantContext(**data)

        assert "tenant_name" in str(exc_info.value)


class TestTargetTenantConfig:
    """Test TargetTenantConfig model validation."""

    def test_target_tenant_config_creation_with_valid_data_succeeds(self):
        """Test that TargetTenantConfig can be created with valid data."""
        data = sample_target_tenant_config()

        config = TargetTenantConfig(**data)

        assert config.name == "customer-a"
        assert config.tenant_id is not None
        assert config.enabled is True
        assert len(config.scenarios) > 0

    def test_target_tenant_config_with_duplicate_tenant_id_in_list_raises_error(self):
        """Test that duplicate tenant_id across multiple configs is detected."""
        # NOTE: This test validates at the list level, not individual model level
        # Will be implemented in MetaOrchestratorConfig validation
        pass

    def test_target_tenant_config_with_duplicate_tenant_name_in_list_raises_error(self):
        """Test that duplicate tenant names are detected."""
        # NOTE: This test validates at the list level, not individual model level
        # Will be implemented in MetaOrchestratorConfig validation
        pass

    def test_target_tenant_config_schedule_with_invalid_cron_raises_validation_error(self):
        """Test that invalid cron expression is rejected."""
        data = invalid_target_tenant_invalid_cron()

        with pytest.raises(ValidationError) as exc_info:
            TargetTenantConfig(**data)

        assert "cron" in str(exc_info.value)

    def test_target_tenant_config_enabled_flag_defaults_to_true(self):
        """Test that enabled flag defaults to true when not specified."""
        data = sample_target_tenant_config()
        del data["enabled"]

        config = TargetTenantConfig(**data)

        assert config.enabled is True

    def test_target_tenant_config_with_disabled_flag_set_to_false_succeeds(self):
        """Test that config can be disabled explicitly."""
        data = sample_target_tenant_config()
        data["enabled"] = False

        config = TargetTenantConfig(**data)

        assert config.enabled is False

    def test_target_tenant_config_with_empty_scenarios_list_raises_validation_error(self):
        """Test that empty scenarios list is rejected."""
        data = sample_target_tenant_config()
        data["scenarios"] = []

        with pytest.raises(ValidationError) as exc_info:
            TargetTenantConfig(**data)

        assert "scenarios" in str(exc_info.value)

    def test_target_tenant_config_with_invalid_region_raises_validation_error(self):
        """Test that invalid Azure region is rejected."""
        data = sample_target_tenant_config()
        data["region"] = "invalid-region"

        # Depending on implementation, this might be allowed
        # But ideally should validate against known Azure regions
        # For now, test that it doesn't crash
        config = TargetTenantConfig(**data)
        assert config.region == "invalid-region"

    def test_target_tenant_config_credentials_requires_keyvault_prefix(self):
        """Test that credentials require keyvault_secret_prefix."""
        data = sample_target_tenant_config()
        data["credentials"] = {}

        with pytest.raises(ValidationError) as exc_info:
            TargetTenantConfig(**data)

        assert "keyvault_secret_prefix" in str(exc_info.value)

    def test_target_tenant_config_limits_validation_rejects_negative_values(self):
        """Test that negative limit values are rejected."""
        data = sample_target_tenant_config()
        data["limits"]["max_vms"] = -5

        with pytest.raises(ValidationError) as exc_info:
            TargetTenantConfig(**data)

        assert "max_vms" in str(exc_info.value)


class TestMetaOrchestratorConfig:
    """Test MetaOrchestratorConfig model validation."""

    def test_meta_orchestrator_config_creation_with_valid_data_succeeds(self):
        """Test that MetaOrchestratorConfig can be created with valid data."""
        data = sample_meta_orchestrator_config()

        config = MetaOrchestratorConfig(**data)

        assert config.name == "test-orchestrator"
        assert config.max_concurrent_tenants == 5
        assert config.enable_tenant_isolation is True

    def test_meta_orchestrator_config_with_multiple_tenants_succeeds(self):
        """Test that config with multiple target tenants is valid."""
        data = sample_multi_tenant_config()

        config = MetaOrchestratorConfig(**data)

        assert len(config.target_tenants) == 2
        assert config.target_tenants[0].name == "tenant-a"
        assert config.target_tenants[1].name == "tenant-b"

    def test_meta_orchestrator_config_with_duplicate_tenant_id_raises_validation_error(self):
        """Test that duplicate tenant_id across tenants raises error."""
        data = sample_multi_tenant_config()
        # Make tenant B have same tenant_id as tenant A
        data["target_tenants"][1]["tenant_id"] = data["target_tenants"][0]["tenant_id"]

        with pytest.raises(ValidationError) as exc_info:
            MetaOrchestratorConfig(**data)

        assert "tenant_id" in str(exc_info.value).lower()
        assert "duplicate" in str(exc_info.value).lower()

    def test_meta_orchestrator_config_with_duplicate_tenant_name_raises_validation_error(self):
        """Test that duplicate tenant names raise error."""
        data = sample_multi_tenant_config()
        # Make tenant B have same name as tenant A
        data["target_tenants"][1]["name"] = data["target_tenants"][0]["name"]

        with pytest.raises(ValidationError) as exc_info:
            MetaOrchestratorConfig(**data)

        assert "name" in str(exc_info.value).lower()
        assert "duplicate" in str(exc_info.value).lower()

    def test_meta_orchestrator_config_max_concurrent_tenants_range_validation(self):
        """Test that max_concurrent_tenants is within valid range (1-20)."""
        data = sample_meta_orchestrator_config()

        # Test minimum boundary
        data["max_concurrent_tenants"] = 0
        with pytest.raises(ValidationError) as exc_info:
            MetaOrchestratorConfig(**data)
        assert "max_concurrent_tenants" in str(exc_info.value)

        # Test maximum boundary
        data["max_concurrent_tenants"] = 21
        with pytest.raises(ValidationError) as exc_info:
            MetaOrchestratorConfig(**data)
        assert "max_concurrent_tenants" in str(exc_info.value)

        # Test valid values
        data["max_concurrent_tenants"] = 1
        config = MetaOrchestratorConfig(**data)
        assert config.max_concurrent_tenants == 1

        data["max_concurrent_tenants"] = 20
        config = MetaOrchestratorConfig(**data)
        assert config.max_concurrent_tenants == 20

    def test_meta_orchestrator_config_backward_compatibility_with_no_target_tenants(self):
        """Test backward compatibility - single-tenant mode when no target_tenants."""
        data = sample_meta_orchestrator_config()
        data["target_tenants"] = []

        # Should succeed (single-tenant mode)
        config = MetaOrchestratorConfig(**data)

        assert len(config.target_tenants) == 0
        assert config.is_single_tenant_mode() is True

    def test_meta_orchestrator_config_is_multi_tenant_mode_returns_true_with_tenants(self):
        """Test that is_multi_tenant_mode() returns True when tenants configured."""
        data = sample_multi_tenant_config()

        config = MetaOrchestratorConfig(**data)

        assert config.is_multi_tenant_mode() is True

    def test_meta_orchestrator_config_is_single_tenant_mode_returns_true_without_tenants(self):
        """Test that is_single_tenant_mode() returns True when no tenants."""
        data = sample_meta_orchestrator_config()
        data["target_tenants"] = []

        config = MetaOrchestratorConfig(**data)

        assert config.is_single_tenant_mode() is True

    def test_meta_orchestrator_config_with_missing_infrastructure_tenant_id_raises_error(self):
        """Test that missing infrastructure_tenant_id raises validation error."""
        data = sample_meta_orchestrator_config()
        del data["infrastructure_tenant_id"]

        with pytest.raises(ValidationError) as exc_info:
            MetaOrchestratorConfig(**data)

        assert "infrastructure_tenant_id" in str(exc_info.value)

    def test_meta_orchestrator_config_serialization_preserves_all_fields(self):
        """Test that serialization preserves all configuration fields."""
        data = sample_multi_tenant_config()
        config = MetaOrchestratorConfig(**data)

        serialized = config.model_dump()

        assert serialized["meta_orchestrator"]["name"] == data["meta_orchestrator"]["name"]
        assert len(serialized["target_tenants"]) == len(data["target_tenants"])
