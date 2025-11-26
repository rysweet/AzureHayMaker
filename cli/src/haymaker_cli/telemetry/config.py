"""Telemetry configuration for Azure HayMaker CLI."""

from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel, Field, field_validator


class TelemetryConfig(BaseModel):
    """Telemetry configuration model.

    Manages configuration settings for telemetry collection and storage.
    """

    enabled: bool = Field(default=True, description="Enable telemetry collection")
    storage_path: Path = Field(
        default=Path("~/.haymaker/telemetry"),
        description="Path to telemetry storage directory",
    )
    collection_interval_seconds: int = Field(
        default=300, gt=0, description="Collection interval in seconds"
    )
    retention_days: int = Field(default=30, gt=0, description="Data retention period in days")
    max_file_size_mb: int = Field(
        default=100, gt=0, description="Maximum file size in MB before rotation"
    )
    compress_old_files: bool = Field(default=True, description="Compress old files")
    api_timeout_seconds: int = Field(default=30, gt=0, description="API request timeout")
    batch_size: int = Field(default=100, gt=0, description="Batch size for API requests")

    @field_validator("storage_path", mode="before")
    @classmethod
    def expand_path(cls, v: Any) -> Path:
        """Expand ~ in storage path."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to ensure path is expanded."""
        self.storage_path = self.storage_path.expanduser()

    # Note: Use .model_dump() directly in calling code instead of this wrapper
    # This method is kept for backwards compatibility but will be removed in future versions

    def validate_storage_path(self) -> bool:
        """Validate that storage path is writable.

        Returns:
            True if path is writable, False otherwise
        """
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            # Try to write a test file
            test_file = self.storage_path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            return False

    def get_file_paths(self) -> Dict[str, Path]:
        """Get paths to telemetry files.

        Returns:
            Dictionary mapping file types to paths
        """
        return {
            "executions": self.storage_path / "executions.jsonl",
            "agents": self.storage_path / "agents.jsonl",
            "resources": self.storage_path / "resources.jsonl",
            "lock": self.storage_path / "telemetry.lock",
            "last_sync": self.storage_path / "last_sync.txt",
        }

    @classmethod
    def from_file(cls, config_file: Path | str) -> "TelemetryConfig":
        """Load configuration from YAML file.

        Args:
            config_file: Path to configuration file

        Returns:
            TelemetryConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file has invalid YAML
        """
        config_path = Path(config_file) if isinstance(config_file, str) else config_file
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)

    def save_to_file(self, config_file: Path) -> None:
        """Save configuration to YAML file.

        Args:
            config_file: Path to save configuration
        """
        config_file.parent.mkdir(parents=True, exist_ok=True)
        # Convert to dict and serialize Path objects
        data = self.model_dump()
        data["storage_path"] = str(data["storage_path"])

        with open(config_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
