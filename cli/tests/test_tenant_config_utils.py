"""Tests for haymaker_cli.orch.tenant_config_utils module.

This test suite validates configuration file management utilities for multi-tenant
orchestration. Tests use temporary directories and mock file operations.

Test Coverage:
    - Config path resolution (3 tests)
    - Config loading (6 tests)
    - Config saving (3 tests)
    - Config validation (2 tests)
    - Adding tenants (4 tests)
    - Updating tenants (3 tests)
    - Removing tenants (2 tests)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from haymaker_cli.orch.tenant_config_utils import (
    TenantConfigError,
    add_tenant_to_config,
    get_tenant_config_path,
    list_tenant_configs,
    load_tenant_config,
    remove_tenant_from_config,
    save_tenant_config,
    update_tenant_in_config,
    validate_tenant_config,
)


# Fixtures


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Create temporary config directory and set HOME env var.

    This ensures tests don't modify the real user configuration.
    """
    config_dir = tmp_path / ".haymaker"
    config_dir.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    return config_dir


@pytest.fixture
def sample_tenant():
    """Provide a valid tenant configuration for testing."""
    return {
        "name": "prod-east",
        "display_name": "Production East",
        "tenant_id": "12345678-1234-1234-1234-123456789012",
        "subscription_id": "87654321-4321-4321-4321-210987654321",
        "region": "eastus",
        "resource_group_name": "haymaker-prod-rg",
        "credentials": {
            "keyvault_secret_prefix": "prod-east"
        },
        "enabled": True,
        "scenarios": ["compute-01", "storage-02"],
    }


@pytest.fixture
def sample_config_with_tenants(sample_tenant):
    """Provide a complete configuration with tenants."""
    return {
        "meta_orchestrator": {
            "name": "default",
            "infrastructure_tenant_id": "00000000-0000-0000-0000-000000000000",
            "storage_account_name": "default",
        },
        "target_tenants": [
            sample_tenant,
            {
                "name": "dev-west",
                "tenant_id": "11111111-1111-1111-1111-111111111111",
                "subscription_id": "22222222-2222-2222-2222-222222222222",
                "region": "westus",
                "resource_group_name": "haymaker-dev-rg",
                "credentials": {
                    "keyvault_secret_prefix": "dev-west"
                },
                "scenarios": [],
            },
        ],
    }


@pytest.fixture
def empty_config():
    """Provide an empty configuration."""
    return {
        "meta_orchestrator": {
            "name": "default",
            "infrastructure_tenant_id": "00000000-0000-0000-0000-000000000000",
            "storage_account_name": "default",
        },
        "target_tenants": [],
    }


# Path Tests


class TestGetConfigPath:
    """Tests for get_tenant_config_path function."""

    def test_get_config_path_yaml_preferred(self, temp_config_dir):
        """Test that YAML format is preferred when no config exists."""
        path = get_tenant_config_path()

        assert path.name == "tenants.yaml"
        assert path.parent == temp_config_dir

    def test_get_config_path_json_fallback(self, temp_config_dir):
        """Test that existing JSON config is detected."""
        json_path = temp_config_dir / "tenants.json"
        json_path.write_text("{}")

        path = get_tenant_config_path()

        assert path == json_path

    def test_get_config_path_creates_directory(self, tmp_path, monkeypatch):
        """Test that config directory is created if it doesn't exist."""
        monkeypatch.setenv("HOME", str(tmp_path))
        config_dir = tmp_path / ".haymaker"

        # Ensure directory doesn't exist
        assert not config_dir.exists()

        path = get_tenant_config_path()

        assert config_dir.exists()
        assert path.parent == config_dir


# Load Tests


class TestLoadConfig:
    """Tests for load_tenant_config function."""

    def test_load_config_yaml_succeeds(self, temp_config_dir, sample_config_with_tenants):
        """Test loading valid YAML configuration."""
        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        config = load_tenant_config()

        assert config["target_tenants"] == sample_config_with_tenants["target_tenants"]
        assert len(config["target_tenants"]) == 2

    def test_load_config_json_succeeds(self, temp_config_dir, sample_config_with_tenants):
        """Test loading valid JSON configuration."""
        json_path = temp_config_dir / "tenants.json"
        with open(json_path, "w") as f:
            json.dump(sample_config_with_tenants, f)

        config = load_tenant_config()

        assert config["target_tenants"] == sample_config_with_tenants["target_tenants"]
        assert len(config["target_tenants"]) == 2

    def test_load_config_file_not_found_creates_default(self, temp_config_dir):
        """Test that missing config file raises appropriate error."""
        with pytest.raises(TenantConfigError) as exc_info:
            load_tenant_config()

        assert "not found" in str(exc_info.value)
        assert "haymaker orch tenant add" in str(exc_info.value)

    def test_load_config_empty_file_handled(self, temp_config_dir):
        """Test that empty config file is handled properly."""
        yaml_path = temp_config_dir / "tenants.yaml"
        yaml_path.write_text("")

        with pytest.raises(TenantConfigError) as exc_info:
            load_tenant_config()

        assert "empty" in str(exc_info.value).lower()

    def test_load_config_invalid_yaml_raises(self, temp_config_dir):
        """Test that invalid YAML syntax raises error."""
        yaml_path = temp_config_dir / "tenants.yaml"
        yaml_path.write_text("invalid: yaml: syntax: here:")

        with pytest.raises(TenantConfigError) as exc_info:
            load_tenant_config()

        assert "YAML" in str(exc_info.value) or "failed" in str(exc_info.value).lower()

    def test_load_config_backward_compatible(self, temp_config_dir):
        """Test loading config without meta_orchestrator section (backward compat)."""
        # Old format: just target_tenants
        old_format = {
            "target_tenants": [
                {
                    "name": "test",
                    "tenant_id": "12345678-1234-1234-1234-123456789012",
                    "subscription_id": "87654321-4321-4321-4321-210987654321",
                    "region": "eastus",
                    "credentials": {"keyvault_secret_prefix": "test"},
                    "scenarios": [],
                }
            ]
        }

        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(old_format, f)

        config = load_tenant_config()

        # Should auto-create meta_orchestrator section
        assert "meta_orchestrator" in config
        assert "target_tenants" in config
        assert len(config["target_tenants"]) == 1


# Save Tests


class TestSaveConfig:
    """Tests for save_tenant_config function."""

    def test_save_config_yaml_format_correct(self, temp_config_dir, sample_config_with_tenants):
        """Test that configuration is saved in correct YAML format."""
        save_tenant_config(sample_config_with_tenants)

        yaml_path = temp_config_dir / "tenants.yaml"
        assert yaml_path.exists()

        # Verify content
        with open(yaml_path) as f:
            loaded = yaml.safe_load(f)

        assert loaded == sample_config_with_tenants
        assert len(loaded["target_tenants"]) == 2

    def test_save_config_sets_permissions_0600(self, temp_config_dir, sample_config_with_tenants):
        """Test that saved config has secure permissions (0600)."""
        save_tenant_config(sample_config_with_tenants)

        yaml_path = temp_config_dir / "tenants.yaml"
        stat = yaml_path.stat()

        # Check permissions are 0600 (owner read/write only)
        import stat as stat_module
        mode = stat_module.S_IMODE(stat.st_mode)
        assert mode == 0o600

    def test_save_config_validates_structure(self, temp_config_dir):
        """Test that saving config without target_tenants field raises error."""
        invalid_config = {
            "meta_orchestrator": {
                "name": "test"
            }
            # Missing target_tenants field
        }

        with pytest.raises(TenantConfigError) as exc_info:
            save_tenant_config(invalid_config)

        assert "target_tenants" in str(exc_info.value)


# Validation Tests


class TestValidateConfig:
    """Tests for validate_tenant_config function."""

    def test_validate_config_valid_passes(self, sample_tenant):
        """Test that valid tenant configuration passes validation."""
        # Should not raise exception
        validate_tenant_config(sample_tenant)

    def test_validate_config_invalid_shows_error(self):
        """Test that invalid tenant configuration raises error."""
        invalid_tenant = {
            "name": "test",
            # Missing required fields
        }

        with pytest.raises(TenantConfigError) as exc_info:
            validate_tenant_config(invalid_tenant)

        assert "Invalid tenant configuration" in str(exc_info.value)


# Add Tests


class TestAddTenant:
    """Tests for add_tenant_to_config function."""

    def test_add_tenant_to_empty_config(self, temp_config_dir, sample_tenant):
        """Test adding tenant when no config exists."""
        add_tenant_to_config(sample_tenant)

        # Verify config was created
        yaml_path = temp_config_dir / "tenants.yaml"
        assert yaml_path.exists()

        # Verify tenant was added
        config = load_tenant_config()
        assert len(config["target_tenants"]) == 1
        assert config["target_tenants"][0]["name"] == "prod-east"

    def test_add_tenant_to_existing_appends(
        self, temp_config_dir, sample_config_with_tenants, sample_tenant
    ):
        """Test adding tenant to existing configuration appends correctly."""
        # Save existing config
        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        # Add new tenant
        new_tenant = {
            "name": "staging-central",
            "display_name": "Staging Central",
            "tenant_id": "99999999-9999-9999-9999-999999999999",
            "subscription_id": "88888888-8888-8888-8888-888888888888",
            "region": "centralus",
            "resource_group_name": "haymaker-staging-rg",
            "credentials": {"keyvault_secret_prefix": "staging"},
            "scenarios": ["test-scenario"],
        }

        add_tenant_to_config(new_tenant)

        # Verify tenant was appended
        config = load_tenant_config()
        assert len(config["target_tenants"]) == 3
        assert config["target_tenants"][2]["name"] == "staging-central"

    def test_add_tenant_duplicate_name_raises(
        self, temp_config_dir, sample_config_with_tenants, sample_tenant
    ):
        """Test that adding tenant with duplicate name raises error."""
        # Save existing config
        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        # Try to add tenant with same name
        duplicate = sample_tenant.copy()

        with pytest.raises(TenantConfigError) as exc_info:
            add_tenant_to_config(duplicate)

        assert "already exists" in str(exc_info.value)
        assert "prod-east" in str(exc_info.value)

    def test_add_tenant_duplicate_id_raises(
        self, temp_config_dir, sample_config_with_tenants, sample_tenant
    ):
        """Test that adding tenant with duplicate tenant_id raises error."""
        # Save existing config
        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        # Try to add tenant with different name but same tenant_id
        duplicate_id = sample_tenant.copy()
        duplicate_id["name"] = "different-name"

        with pytest.raises(TenantConfigError) as exc_info:
            add_tenant_to_config(duplicate_id)

        assert "tenant_id" in str(exc_info.value)
        assert "already exists" in str(exc_info.value)


# Update Tests


class TestUpdateTenant:
    """Tests for update_tenant_in_config function."""

    def test_update_tenant_field_changes(
        self, temp_config_dir, sample_config_with_tenants
    ):
        """Test updating simple tenant fields."""
        # Save config
        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        # Update tenant
        updates = {
            "display_name": "Production East - Updated",
            "region": "eastus2",
            "enabled": False,
        }
        update_tenant_in_config("prod-east", updates)

        # Verify updates
        config = load_tenant_config()
        tenant = next(t for t in config["target_tenants"] if t["name"] == "prod-east")
        assert tenant["display_name"] == "Production East - Updated"
        assert tenant["region"] == "eastus2"
        assert tenant["enabled"] is False

    def test_update_tenant_nested_limits_merged(
        self, temp_config_dir, sample_config_with_tenants
    ):
        """Test updating nested limits fields are merged correctly."""
        # Add limits to existing tenant
        sample_config_with_tenants["target_tenants"][0]["limits"] = {
            "max_knowledge_workers": 100,
            "max_concurrent_scenarios": 10,
        }

        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        # Update only one limit field
        updates = {
            "limits": {
                "max_knowledge_workers": 200,
            }
        }
        update_tenant_in_config("prod-east", updates)

        # Verify merge behavior
        config = load_tenant_config()
        tenant = next(t for t in config["target_tenants"] if t["name"] == "prod-east")
        assert tenant["limits"]["max_knowledge_workers"] == 200
        # Original field should be preserved
        assert tenant["limits"]["max_concurrent_scenarios"] == 10

    def test_update_tenant_not_found_raises(
        self, temp_config_dir, sample_config_with_tenants
    ):
        """Test that updating nonexistent tenant raises error."""
        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        with pytest.raises(TenantConfigError) as exc_info:
            update_tenant_in_config("nonexistent", {"enabled": False})

        assert "not found" in str(exc_info.value)


# Remove Tests


class TestRemoveTenant:
    """Tests for remove_tenant_from_config function."""

    def test_remove_tenant_removes_entry(
        self, temp_config_dir, sample_config_with_tenants
    ):
        """Test removing tenant from configuration."""
        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        # Verify initial state
        config = load_tenant_config()
        assert len(config["target_tenants"]) == 2

        # Remove tenant
        remove_tenant_from_config("prod-east")

        # Verify removal
        config = load_tenant_config()
        assert len(config["target_tenants"]) == 1
        assert config["target_tenants"][0]["name"] == "dev-west"

    def test_remove_tenant_not_found_raises(
        self, temp_config_dir, sample_config_with_tenants
    ):
        """Test that removing nonexistent tenant raises error."""
        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        with pytest.raises(TenantConfigError) as exc_info:
            remove_tenant_from_config("nonexistent")

        assert "not found" in str(exc_info.value)


# List Tests


class TestListTenants:
    """Tests for list_tenant_configs function."""

    def test_list_returns_all_tenants(
        self, temp_config_dir, sample_config_with_tenants
    ):
        """Test that list returns all configured tenants."""
        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        tenants = list_tenant_configs()

        assert len(tenants) == 2
        assert tenants[0]["name"] == "prod-east"
        assert tenants[1]["name"] == "dev-west"

    def test_list_empty_config_returns_empty_list(self, temp_config_dir):
        """Test that listing nonexistent config returns empty list."""
        tenants = list_tenant_configs()

        assert tenants == []


# Edge Cases


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_save_config_with_json_extension(
        self, temp_config_dir, sample_config_with_tenants
    ):
        """Test that JSON format is used when config file has .json extension."""
        # Create JSON config first
        json_path = temp_config_dir / "tenants.json"
        json_path.write_text("{}")

        # Now save should use JSON format
        save_tenant_config(sample_config_with_tenants)

        # Verify JSON format
        with open(json_path) as f:
            loaded = json.load(f)

        assert loaded == sample_config_with_tenants

    def test_config_path_prefers_existing_yaml_over_json(self, temp_config_dir):
        """Test that YAML is preferred when both exist."""
        yaml_path = temp_config_dir / "tenants.yaml"
        json_path = temp_config_dir / "tenants.json"

        # Create both files
        yaml_path.write_text("target_tenants: []")
        json_path.write_text('{"target_tenants": []}')

        path = get_tenant_config_path()

        assert path == yaml_path

    def test_validate_tenant_with_optional_fields(self):
        """Test validation passes with minimal required fields."""
        minimal_tenant = {
            "name": "test",
            "display_name": "Test",
            "tenant_id": "12345678-1234-1234-1234-123456789012",
            "subscription_id": "87654321-4321-4321-4321-210987654321",
            "region": "eastus",
            "credentials": {"keyvault_secret_prefix": "test"},
            "scenarios": ["test-scenario"],
        }

        # Should not raise
        validate_tenant_config(minimal_tenant)

    def test_update_preserves_unmodified_fields(
        self, temp_config_dir, sample_config_with_tenants
    ):
        """Test that update only changes specified fields."""
        yaml_path = temp_config_dir / "tenants.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(sample_config_with_tenants, f)

        original_config = load_tenant_config()
        original_tenant = next(
            t for t in original_config["target_tenants"] if t["name"] == "prod-east"
        )
        original_tenant_id = original_tenant["tenant_id"]
        original_scenarios = original_tenant["scenarios"].copy()

        # Update only display name
        update_tenant_in_config("prod-east", {"display_name": "New Name"})

        # Verify other fields unchanged
        config = load_tenant_config()
        tenant = next(t for t in config["target_tenants"] if t["name"] == "prod-east")
        assert tenant["display_name"] == "New Name"
        assert tenant["tenant_id"] == original_tenant_id
        assert tenant["scenarios"] == original_scenarios
