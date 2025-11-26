"""Tests for haymaker_cli.validate module."""

import json
from unittest.mock import MagicMock, patch

import httpx
from click.testing import CliRunner

from haymaker_cli.validate import (
    CheckResult,
    CheckStatus,
    check_api_connectivity,
    check_config,
    check_environment_variables,
    format_status,
    validate,
)


class TestCheckStatus:
    """Tests for CheckStatus enum."""

    def test_status_values(self):
        """Test that all status values are defined."""
        assert CheckStatus.PASS.value == "pass"
        assert CheckStatus.FAIL.value == "fail"
        assert CheckStatus.WARN.value == "warn"
        assert CheckStatus.SKIP.value == "skip"


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_required_fields(self):
        """Test CheckResult with required fields only."""
        result = CheckResult(
            name="Test Check",
            status=CheckStatus.PASS,
            message="Test passed",
        )
        assert result.name == "Test Check"
        assert result.status == CheckStatus.PASS
        assert result.message == "Test passed"
        assert result.details is None

    def test_with_details(self):
        """Test CheckResult with optional details."""
        result = CheckResult(
            name="Test Check",
            status=CheckStatus.FAIL,
            message="Test failed",
            details="Additional information",
        )
        assert result.details == "Additional information"


class TestFormatStatus:
    """Tests for format_status function."""

    def test_pass_status(self):
        """Test formatting of PASS status."""
        text = format_status(CheckStatus.PASS)
        assert "[OK]" in str(text)

    def test_fail_status(self):
        """Test formatting of FAIL status."""
        text = format_status(CheckStatus.FAIL)
        assert "[FAIL]" in str(text)

    def test_warn_status(self):
        """Test formatting of WARN status."""
        text = format_status(CheckStatus.WARN)
        assert "[WARN]" in str(text)

    def test_skip_status(self):
        """Test formatting of SKIP status."""
        text = format_status(CheckStatus.SKIP)
        assert "[SKIP]" in str(text)


class TestCheckConfig:
    """Tests for check_config function."""

    @patch("haymaker_cli.validate.load_cli_config")
    def test_successful_config_load(self, mock_load_config):
        """Test successful configuration loading."""
        mock_config = MagicMock()
        mock_config.endpoint = "https://api.example.com"
        mock_load_config.return_value = mock_config

        result = check_config()

        assert result.status == CheckStatus.PASS
        assert result.name == "CLI Configuration"
        assert "successfully" in result.message.lower()

    @patch("haymaker_cli.validate.load_cli_config")
    def test_config_not_found(self, mock_load_config):
        """Test configuration file not found."""
        mock_load_config.side_effect = ValueError("Configuration file not found")

        result = check_config()

        assert result.status == CheckStatus.FAIL
        assert "not found" in result.message.lower()

    @patch("haymaker_cli.validate.load_cli_config")
    def test_config_error(self, mock_load_config):
        """Test generic configuration error."""
        mock_load_config.side_effect = ValueError("Invalid format")

        result = check_config()

        assert result.status == CheckStatus.FAIL


class TestCheckApiConnectivity:
    """Tests for check_api_connectivity function."""

    @patch("haymaker_cli.validate.create_auth_provider")
    @patch("haymaker_cli.validate.load_cli_config")
    def test_successful_connection(self, mock_load_config, mock_create_auth):
        """Test successful API connection."""
        mock_config = MagicMock()
        mock_config.endpoint = "https://api.example.com"
        mock_load_config.return_value = mock_config

        mock_auth = MagicMock()
        mock_auth.get_auth_header.return_value = {"Authorization": "Bearer token"}
        mock_create_auth.return_value = mock_auth

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = check_api_connectivity()

            assert result.status == CheckStatus.PASS
            assert "reachable" in result.message.lower()

    @patch("haymaker_cli.validate.create_auth_provider")
    @patch("haymaker_cli.validate.load_cli_config")
    def test_authentication_failure(self, mock_load_config, mock_create_auth):
        """Test API returns 401 unauthorized."""
        mock_config = MagicMock()
        mock_config.endpoint = "https://api.example.com"
        mock_load_config.return_value = mock_config

        mock_auth = MagicMock()
        mock_auth.get_auth_header.return_value = {"Authorization": "Bearer token"}
        mock_create_auth.return_value = mock_auth

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = check_api_connectivity()

            assert result.status == CheckStatus.FAIL
            assert "authentication" in result.message.lower()

    @patch("haymaker_cli.validate.create_auth_provider")
    @patch("haymaker_cli.validate.load_cli_config")
    def test_all_endpoints_unreachable(self, mock_load_config, mock_create_auth):
        """Test when all endpoints fail with RequestError - fixes unbound variable bug."""
        mock_config = MagicMock()
        mock_config.endpoint = "https://api.example.com"
        mock_load_config.return_value = mock_config

        mock_auth = MagicMock()
        mock_auth.get_auth_header.return_value = {"Authorization": "Bearer token"}
        mock_create_auth.return_value = mock_auth

        with patch("httpx.Client") as mock_client:
            # All requests raise RequestError
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.RequestError("Connection failed")
            )

            result = check_api_connectivity()

            # Should return FAIL, not raise UnboundLocalError
            assert result.status == CheckStatus.FAIL
            assert "unreachable" in result.message.lower()
            assert result.name == "API Connectivity"

    @patch("haymaker_cli.validate.load_cli_config")
    def test_config_not_available(self, mock_load_config):
        """Test when configuration is not available."""
        mock_load_config.side_effect = ValueError("No config")

        result = check_api_connectivity()

        assert result.status == CheckStatus.SKIP

    @patch("haymaker_cli.validate.create_auth_provider")
    @patch("haymaker_cli.validate.load_cli_config")
    def test_network_timeout(self, mock_load_config, mock_create_auth):
        """Test API connection timeout."""
        mock_config = MagicMock()
        mock_config.endpoint = "https://api.example.com"
        mock_load_config.return_value = mock_config

        mock_auth = MagicMock()
        mock_auth.get_auth_header.return_value = {"Authorization": "Bearer token"}
        mock_create_auth.return_value = mock_auth

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.TimeoutException("Timeout")
            )

            result = check_api_connectivity()

            assert result.status == CheckStatus.FAIL
            assert "timeout" in result.message.lower()


class TestCheckEnvironmentVariables:
    """Tests for check_environment_variables function."""

    @patch.dict("os.environ", {}, clear=True)
    def test_no_env_vars_set(self):
        """Test when no HayMaker environment variables are set."""
        result = check_environment_variables()

        assert result.status == CheckStatus.SKIP
        assert "no" in result.message.lower()

    @patch.dict(
        "os.environ",
        {"HAYMAKER_ENDPOINT": "https://api.example.com"},
        clear=True,
    )
    def test_endpoint_env_var(self):
        """Test when endpoint environment variable is set."""
        result = check_environment_variables()

        assert result.status == CheckStatus.PASS
        assert "1" in result.message

    @patch.dict(
        "os.environ",
        {"HAYMAKER_API_KEY": "secret-key-12345"},
        clear=True,
    )
    def test_api_key_masked(self):
        """Test that API key is masked in output."""
        result = check_environment_variables()

        assert result.status == CheckStatus.PASS
        # API key should be masked
        assert "secret-key-12345" not in result.details
        assert "****" in result.details


class TestValidateCommand:
    """Tests for validate CLI command."""

    @patch("haymaker_cli.validate.check_scenarios_directory")
    @patch("haymaker_cli.validate.check_azure_auth")
    @patch("haymaker_cli.validate.check_azure_cli")
    @patch("haymaker_cli.validate.check_api_connectivity")
    @patch("haymaker_cli.validate.check_environment_variables")
    @patch("haymaker_cli.validate.check_config")
    def test_json_output(
        self,
        mock_check_config,
        mock_check_env,
        mock_check_api,
        mock_check_azure_cli,
        mock_check_azure_auth,
        mock_check_scenarios,
    ):
        """Test JSON output format."""
        # Setup all mocks to return PASS
        for mock_check in [
            mock_check_config,
            mock_check_env,
            mock_check_api,
            mock_check_azure_cli,
            mock_check_azure_auth,
            mock_check_scenarios,
        ]:
            mock_check.return_value = CheckResult(
                name="Test",
                status=CheckStatus.PASS,
                message="Passed",
            )

        runner = CliRunner()
        result = runner.invoke(validate, ["--json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "results" in output
        assert "summary" in output
        assert output["summary"]["total"] == 6

    @patch("haymaker_cli.validate.check_scenarios_directory")
    @patch("haymaker_cli.validate.check_azure_auth")
    @patch("haymaker_cli.validate.check_azure_cli")
    @patch("haymaker_cli.validate.check_api_connectivity")
    @patch("haymaker_cli.validate.check_environment_variables")
    @patch("haymaker_cli.validate.check_config")
    def test_json_output_masks_api_key(
        self,
        mock_check_config,
        mock_check_env,
        mock_check_api,
        mock_check_azure_cli,
        mock_check_azure_auth,
        mock_check_scenarios,
    ):
        """Test that JSON output masks sensitive data like API keys."""
        mock_check_config.return_value = CheckResult(
            name="CLI Configuration",
            status=CheckStatus.PASS,
            message="Config loaded",
        )
        # Environment variables check with masked API key
        mock_check_env.return_value = CheckResult(
            name="Environment Variables",
            status=CheckStatus.PASS,
            message="1 environment variable(s) configured",
            details="HAYMAKER_API_KEY=****",
        )
        for mock_check in [
            mock_check_api,
            mock_check_azure_cli,
            mock_check_azure_auth,
            mock_check_scenarios,
        ]:
            mock_check.return_value = CheckResult(
                name="Test",
                status=CheckStatus.PASS,
                message="Passed",
            )

        runner = CliRunner()
        result = runner.invoke(validate, ["--json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        # Check that the API key is masked in JSON output
        env_result = next(
            r for r in output["results"] if r["name"] == "Environment Variables"
        )
        assert "****" in env_result["details"]

    @patch("haymaker_cli.validate.check_scenarios_directory")
    @patch("haymaker_cli.validate.check_azure_auth")
    @patch("haymaker_cli.validate.check_azure_cli")
    @patch("haymaker_cli.validate.check_api_connectivity")
    @patch("haymaker_cli.validate.check_environment_variables")
    @patch("haymaker_cli.validate.check_config")
    def test_exit_code_on_failure(
        self,
        mock_check_config,
        mock_check_env,
        mock_check_api,
        mock_check_azure_cli,
        mock_check_azure_auth,
        mock_check_scenarios,
    ):
        """Test that exit code is 1 when any check fails."""
        mock_check_config.return_value = CheckResult(
            name="CLI Configuration",
            status=CheckStatus.FAIL,
            message="Config failed",
        )
        for mock_check in [
            mock_check_env,
            mock_check_api,
            mock_check_azure_cli,
            mock_check_azure_auth,
            mock_check_scenarios,
        ]:
            mock_check.return_value = CheckResult(
                name="Test",
                status=CheckStatus.PASS,
                message="Passed",
            )

        runner = CliRunner()
        result = runner.invoke(validate, [])

        assert result.exit_code == 1
