"""Unit tests for telemetry configuration."""

import pytest
from pathlib import Path
from pydantic import ValidationError


class TestTelemetryConfig:
    """Test TelemetryConfig data model."""

    def test_config_default_values(self):
        """Test TelemetryConfig loads with default values."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        config = TelemetryConfig()

        assert config.enabled is True
        assert config.collection_interval_seconds == 300
        assert config.retention_days == 30
        assert config.api_timeout_seconds == 30
        assert config.batch_size == 100

    def test_config_custom_values(self):
        """Test TelemetryConfig accepts custom values."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        config = TelemetryConfig(
            enabled=False,
            storage_path="/custom/path",
            collection_interval_seconds=600,
            retention_days=60,
            max_file_size_mb=200
        )

        assert config.enabled is False
        assert config.storage_path == Path("/custom/path")
        assert config.collection_interval_seconds == 600
        assert config.retention_days == 60
        assert config.max_file_size_mb == 200

    def test_config_storage_path_expansion(self):
        """Test TelemetryConfig expands ~ in storage path."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        config = TelemetryConfig(storage_path="~/haymaker/telemetry")

        assert str(config.storage_path).startswith("/")
        assert "~" not in str(config.storage_path)

    def test_config_invalid_interval(self):
        """Test TelemetryConfig rejects invalid collection interval."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        with pytest.raises(ValidationError):
            TelemetryConfig(collection_interval_seconds=0)

        with pytest.raises(ValidationError):
            TelemetryConfig(collection_interval_seconds=-100)

    def test_config_invalid_retention(self):
        """Test TelemetryConfig rejects invalid retention days."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        with pytest.raises(ValidationError):
            TelemetryConfig(retention_days=0)

        with pytest.raises(ValidationError):
            TelemetryConfig(retention_days=-30)

    def test_config_invalid_file_size(self):
        """Test TelemetryConfig rejects invalid max file size."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        with pytest.raises(ValidationError):
            TelemetryConfig(max_file_size_mb=0)

        with pytest.raises(ValidationError):
            TelemetryConfig(max_file_size_mb=-100)

    def test_config_from_dict(self):
        """Test TelemetryConfig loads from dictionary."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        config_dict = {
            "enabled": True,
            "storage_path": "/tmp/telemetry",
            "collection_interval_seconds": 300,
            "retention_days": 30,
            "compress_old_files": True
        }

        config = TelemetryConfig(**config_dict)

        assert config.enabled is True
        assert str(config.storage_path) == "/tmp/telemetry"
        assert config.compress_old_files is True

    def test_config_to_dict(self):
        """Test TelemetryConfig serialization to dictionary."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        config = TelemetryConfig(
            storage_path="/tmp/telemetry",
            retention_days=45
        )

        config_dict = config.dict()

        assert isinstance(config_dict, dict)
        assert "enabled" in config_dict
        assert "storage_path" in config_dict
        assert config_dict["retention_days"] == 45

    def test_config_load_from_file(self, tmp_path):
        """Test TelemetryConfig loads from YAML file."""
        from haymaker_cli.telemetry.config import TelemetryConfig
        import yaml

        config_file = tmp_path / "telemetry.yaml"
        config_data = {
            "enabled": False,
            "storage_path": "/custom/path",
            "collection_interval_seconds": 600
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = TelemetryConfig.from_file(config_file)

        assert config.enabled is False
        assert config.collection_interval_seconds == 600

    def test_config_save_to_file(self, tmp_path):
        """Test TelemetryConfig saves to YAML file."""
        from haymaker_cli.telemetry.config import TelemetryConfig
        import yaml

        config = TelemetryConfig(
            enabled=False,
            storage_path="/tmp/telemetry",
            retention_days=45
        )

        config_file = tmp_path / "telemetry.yaml"
        config.save_to_file(config_file)

        assert config_file.exists()

        with open(config_file) as f:
            loaded_data = yaml.safe_load(f)

        assert loaded_data["enabled"] is False
        assert loaded_data["retention_days"] == 45

    def test_config_missing_file(self):
        """Test TelemetryConfig handles missing config file."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        with pytest.raises(FileNotFoundError):
            TelemetryConfig.from_file("/nonexistent/config.yaml")

    def test_config_invalid_yaml(self, tmp_path):
        """Test TelemetryConfig handles invalid YAML file."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        config_file = tmp_path / "invalid.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(Exception):  # YAML parsing error
            TelemetryConfig.from_file(config_file)

    def test_config_merge_defaults(self):
        """Test TelemetryConfig merges partial config with defaults."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        # Only set some fields
        config = TelemetryConfig(
            retention_days=45,
            batch_size=200
        )

        # Other fields should have defaults
        assert config.enabled is True
        assert config.collection_interval_seconds == 300
        assert config.retention_days == 45
        assert config.batch_size == 200

    def test_config_validate_storage_path(self, tmp_path):
        """Test TelemetryConfig validates storage path is writable."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        # Valid writable path
        config = TelemetryConfig(storage_path=str(tmp_path))
        assert config.validate_storage_path() is True

        # Invalid non-writable path (if we can create one)
        # This test might be skipped if we can't create a non-writable directory
        readonly_path = tmp_path / "readonly"
        readonly_path.mkdir()
        readonly_path.chmod(0o444)

        config = TelemetryConfig(storage_path=str(readonly_path))
        assert config.validate_storage_path() is False

    def test_config_get_file_paths(self):
        """Test TelemetryConfig returns expected file paths."""
        from haymaker_cli.telemetry.config import TelemetryConfig

        config = TelemetryConfig(storage_path="/tmp/telemetry")

        paths = config.get_file_paths()

        assert "executions" in paths
        assert "agents" in paths
        assert "resources" in paths
        assert "lock" in paths
        assert str(paths["executions"]).endswith("executions.jsonl")
        assert str(paths["lock"]).endswith("telemetry.lock")
