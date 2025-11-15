"""Unit tests for .env file loading functionality."""

import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from azure_haymaker.orchestrator.config_env_loader import load_dotenv_with_warnings


class TestLoadDotenvWithWarnings:
    """Tests for load_dotenv_with_warnings function."""

    @pytest.fixture
    def mock_dotenv_file(self, tmp_path: Path) -> Path:
        """Create a mock .env file for testing."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "AZURE_TENANT_ID=test-tenant-id\n"
            "AZURE_CLIENT_ID=test-client-id\n"
            "KEY_VAULT_URL=https://test.vault.azure.net\n"
            "SIMULATION_SIZE=small\n"
        )
        return env_file

    @pytest.fixture
    def mock_empty_dotenv_file(self, tmp_path: Path) -> Path:
        """Create an empty .env file for testing."""
        env_file = tmp_path / ".env"
        env_file.write_text("")
        return env_file

    @pytest.fixture
    def mock_malformed_dotenv_file(self, tmp_path: Path) -> Path:
        """Create a malformed .env file for testing."""
        env_file = tmp_path / ".env"
        env_file.write_text("INVALID LINE WITHOUT EQUALS\n" "VALID_VAR=value\n")
        return env_file

    def test_load_dotenv_file_not_found(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that missing .env file returns empty dict and logs debug message."""
        with (
            patch("azure_haymaker.orchestrator.config_env_loader.Path") as mock_path_class,
            caplog.at_level(logging.DEBUG),
        ):
            # Create a mock path object that returns False for exists()
            mock_env_path = MagicMock()
            mock_env_path.exists.return_value = False

            # Make Path(__file__).parent.parent.parent.parent / ".env" return our mock
            mock_path_instance = MagicMock()
            mock_path_instance.parent.parent.parent.parent.__truediv__.return_value = mock_env_path
            mock_path_class.return_value = mock_path_instance

            result = load_dotenv_with_warnings()

            assert result == {}
            assert any(".env file not found" in record.message for record in caplog.records)

    def test_load_dotenv_success_development(
        self, mock_dotenv_file: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test successful .env loading in development environment."""
        with (
            patch("azure_haymaker.orchestrator.config_env_loader.Path") as mock_path,
            patch.dict(os.environ, {}, clear=True),
            caplog.at_level(logging.INFO),
        ):
            # Mock path to existing file
            mock_env_path = MagicMock()
            mock_env_path.exists.return_value = True
            mock_env_path.__str__.return_value = str(mock_dotenv_file)
            mock_path.return_value.__truediv__.return_value = mock_env_path

            # Mock dotenv_values to return our test data
            with patch(
                "azure_haymaker.orchestrator.config_env_loader.dotenv_values"
            ) as mock_dotenv:
                mock_dotenv.return_value = {
                    "AZURE_TENANT_ID": "test-tenant-id",
                    "AZURE_CLIENT_ID": "test-client-id",
                    "KEY_VAULT_URL": "https://test.vault.azure.net",
                    "SIMULATION_SIZE": "small",
                }

                result = load_dotenv_with_warnings()

                assert result["AZURE_TENANT_ID"] == "test-tenant-id"
                assert result["AZURE_CLIENT_ID"] == "test-client-id"
                assert len(result) == 4
                assert any(
                    "Loading configuration from .env file" in record.message
                    for record in caplog.records
                )

    def test_load_dotenv_warning_production(
        self, mock_dotenv_file: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that .env loading in production logs warning."""
        with (
            patch("azure_haymaker.orchestrator.config_env_loader.Path") as mock_path,
            patch.dict(os.environ, {"AZURE_FUNCTIONS_ENVIRONMENT": "production"}, clear=True),
            caplog.at_level(logging.WARNING),
        ):
            # Mock path to existing file
            mock_env_path = MagicMock()
            mock_env_path.exists.return_value = True
            mock_env_path.__str__.return_value = str(mock_dotenv_file)
            mock_path.return_value.__truediv__.return_value = mock_env_path

            # Mock dotenv_values
            with patch(
                "azure_haymaker.orchestrator.config_env_loader.dotenv_values"
            ) as mock_dotenv:
                mock_dotenv.return_value = {"AZURE_TENANT_ID": "test-tenant-id"}

                result = load_dotenv_with_warnings()

                assert len(result) == 1
                assert any(
                    "WARNING: .env file detected in production" in record.message
                    for record in caplog.records
                )
                assert any("Key Vault" in record.message for record in caplog.records)

    def test_load_dotenv_empty_file(
        self, mock_empty_dotenv_file: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test loading empty .env file returns empty dict."""
        with (
            patch("azure_haymaker.orchestrator.config_env_loader.Path") as mock_path,
            patch.dict(os.environ, {}, clear=True),
            caplog.at_level(logging.INFO),
        ):
            # Mock path to existing file
            mock_env_path = MagicMock()
            mock_env_path.exists.return_value = True
            mock_env_path.__str__.return_value = str(mock_empty_dotenv_file)
            mock_path.return_value.__truediv__.return_value = mock_env_path

            # Mock dotenv_values to return empty dict
            with patch(
                "azure_haymaker.orchestrator.config_env_loader.dotenv_values"
            ) as mock_dotenv:
                mock_dotenv.return_value = {}

                result = load_dotenv_with_warnings()

                assert result == {}

    def test_load_dotenv_filters_none_values(
        self, mock_dotenv_file: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that None values are filtered out from loaded variables."""
        with (
            patch("azure_haymaker.orchestrator.config_env_loader.Path") as mock_path,
            patch.dict(os.environ, {}, clear=True),
            caplog.at_level(logging.INFO),
        ):
            # Mock path to existing file
            mock_env_path = MagicMock()
            mock_env_path.exists.return_value = True
            mock_env_path.__str__.return_value = str(mock_dotenv_file)
            mock_path.return_value.__truediv__.return_value = mock_env_path

            # Mock dotenv_values with None values
            with patch(
                "azure_haymaker.orchestrator.config_env_loader.dotenv_values"
            ) as mock_dotenv:
                mock_dotenv.return_value = {
                    "AZURE_TENANT_ID": "test-tenant-id",
                    "EMPTY_VAR": None,
                    "AZURE_CLIENT_ID": "test-client-id",
                    "ANOTHER_EMPTY": None,
                }

                result = load_dotenv_with_warnings()

                assert len(result) == 2
                assert "AZURE_TENANT_ID" in result
                assert "AZURE_CLIENT_ID" in result
                assert "EMPTY_VAR" not in result
                assert "ANOTHER_EMPTY" not in result

    def test_load_dotenv_error_handling(
        self, mock_dotenv_file: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that errors during .env loading are caught and logged."""
        with (
            patch("azure_haymaker.orchestrator.config_env_loader.Path") as mock_path,
            patch.dict(os.environ, {}, clear=True),
            caplog.at_level(logging.ERROR),
        ):
            # Mock path to existing file
            mock_env_path = MagicMock()
            mock_env_path.exists.return_value = True
            mock_env_path.__str__.return_value = str(mock_dotenv_file)
            mock_path.return_value.__truediv__.return_value = mock_env_path

            # Mock dotenv_values to raise exception
            with patch(
                "azure_haymaker.orchestrator.config_env_loader.dotenv_values"
            ) as mock_dotenv:
                mock_dotenv.side_effect = PermissionError("Permission denied")

                result = load_dotenv_with_warnings()

                assert result == {}
                assert any("Failed to load .env file" in record.message for record in caplog.records)
                assert any("Permission denied" in record.message for record in caplog.records)

    def test_load_dotenv_various_environments(
        self, mock_dotenv_file: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test .env loading with various environment values."""
        test_envs = ["Production", "PRODUCTION", "development", "Development", "staging", ""]

        for env_value in test_envs:
            caplog.clear()

            with (
                patch("azure_haymaker.orchestrator.config_env_loader.Path") as mock_path,
                patch.dict(os.environ, {"AZURE_FUNCTIONS_ENVIRONMENT": env_value}, clear=True),
                caplog.at_level(logging.INFO),
            ):
                # Mock path to existing file
                mock_env_path = MagicMock()
                mock_env_path.exists.return_value = True
                mock_env_path.__str__.return_value = str(mock_dotenv_file)
                mock_path.return_value.__truediv__.return_value = mock_env_path

                # Mock dotenv_values
                with patch(
                    "azure_haymaker.orchestrator.config_env_loader.dotenv_values"
                ) as mock_dotenv:
                    mock_dotenv.return_value = {"TEST_VAR": "value"}

                    result = load_dotenv_with_warnings()

                    assert len(result) == 1

                    # Check appropriate log level
                    if env_value.lower() == "production":
                        assert any(
                            record.levelname == "WARNING" for record in caplog.records
                        ), f"Expected WARNING for env: {env_value}"
                    else:
                        assert any(
                            record.levelname == "INFO" for record in caplog.records
                        ), f"Expected INFO for env: {env_value}"
