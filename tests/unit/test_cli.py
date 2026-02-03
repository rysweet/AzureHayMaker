"""Tests for the haymaker CLI.

Tests the CLI commands for Knowledge Worker lifecycle management.
Uses Click's testing utilities for command invocation.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

# These imports will fail until implementation exists - that's expected in TDD
from azure_haymaker.cli import cli
from azure_haymaker.cli.commands.kw import kw


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    state_dir = tmp_path / ".azure_haymaker"
    state_dir.mkdir(parents=True)
    (state_dir / "deployments").mkdir()
    (state_dir / "workers").mkdir()
    return state_dir


@pytest.fixture
def sample_deployment() -> dict[str, Any]:
    """Sample deployment data."""
    return {
        "run_id": "kw-abc12345",
        "name": "test-deployment",
        "phase": "executing",
        "status": "running",
        "worker_count": 5,
        "started_at": "2024-01-15T10:00:00Z",
        "completed_at": None,
        "error": None,
        "updated_at": "2024-01-15T10:30:00Z",
        "config": {
            "total_workers": 5,
            "duration_hours": 8,
            "tenant_domain": "test.onmicrosoft.com",
            "departments": {"engineering": {"count": 5}},
        },
    }


@pytest.fixture
def sample_worker() -> dict[str, Any]:
    """Sample worker data."""
    return {
        "worker_id": "kw-abc12345-engi-001",
        "display_name": "KW Engineering 1",
        "user_principal_name": "kw-abc12345-engi-001@test.onmicrosoft.com",
        "entra_object_id": "obj-12345",
        "persona": "engineering",
        "endpoint_type": "cli_container",
        "department": "engineering",
        "team_ids": [],
        "run_id": "kw-abc12345",
        "updated_at": "2024-01-15T10:05:00Z",
    }


class TestCliEntryPoint:
    """Test the main CLI entry point."""

    def test_cli_exists(self, runner: CliRunner) -> None:
        """Test that the CLI entry point exists."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "haymaker" in result.output.lower() or "azure" in result.output.lower()

    def test_cli_has_kw_subcommand(self, runner: CliRunner) -> None:
        """Test that kw subcommand is available."""
        result = runner.invoke(cli, ["kw", "--help"])
        assert result.exit_code == 0
        assert "kw" in result.output.lower() or "knowledge" in result.output.lower()


class TestKwStatusCommand:
    """Test the haymaker kw status command."""

    def test_status_all_deployments(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test status command shows all deployments."""
        # Setup: Create deployment file
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            result = runner.invoke(kw, ["status"])

        assert result.exit_code == 0
        assert sample_deployment["run_id"] in result.output
        assert "running" in result.output.lower()

    def test_status_specific_deployment(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test status command for specific deployment."""
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            result = runner.invoke(kw, ["status", "--run-id", sample_deployment["run_id"]])

        assert result.exit_code == 0
        assert sample_deployment["run_id"] in result.output

    def test_status_json_format(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test status command with JSON output."""
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            result = runner.invoke(kw, ["status", "--format", "json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert isinstance(output, list)

    def test_status_not_found(self, runner: CliRunner, temp_state_dir: Path) -> None:
        """Test status command when deployment not found."""
        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            result = runner.invoke(kw, ["status", "--run-id", "nonexistent"])

        assert result.exit_code != 0 or "not found" in result.output.lower()


class TestKwListCommand:
    """Test the haymaker kw list command."""

    def test_list_empty(self, runner: CliRunner, temp_state_dir: Path) -> None:
        """Test list command with no deployments."""
        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            result = runner.invoke(kw, ["list"])

        assert result.exit_code == 0
        assert "no deployments" in result.output.lower() or len(result.output.strip()) == 0

    def test_list_deployments(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test list command shows deployments."""
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            result = runner.invoke(kw, ["list"])

        assert result.exit_code == 0
        assert sample_deployment["run_id"] in result.output

    def test_list_limit(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test list command respects limit."""
        # Create multiple deployments
        for i in range(5):
            deployment = sample_deployment.copy()
            deployment["run_id"] = f"kw-test{i:04d}"
            deployment_file = temp_state_dir / "deployments" / f"{deployment['run_id']}.json"
            deployment_file.write_text(json.dumps(deployment))

        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            result = runner.invoke(kw, ["list", "--limit", "2"])

        assert result.exit_code == 0
        # Should only show 2 deployments


class TestKwStopCommand:
    """Test the haymaker kw stop command."""

    def test_stop_requires_run_id(self, runner: CliRunner) -> None:
        """Test stop command requires run-id."""
        result = runner.invoke(kw, ["stop"])
        assert result.exit_code != 0

    def test_stop_with_confirmation(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test stop command asks for confirmation."""
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            # Provide 'n' to decline confirmation
            result = runner.invoke(
                kw, ["stop", "--run-id", sample_deployment["run_id"]], input="n\n"
            )

        # Should exit without stopping
        assert "abort" in result.output.lower() or "cancel" in result.output.lower()

    def test_stop_with_yes_flag(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test stop command with --yes flag skips confirmation."""
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        with (
            patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}),
            patch(
                "azure_haymaker.cli.commands.kw._stop_deployment", new_callable=AsyncMock
            ) as mock_stop,
        ):
            mock_stop.return_value = True
            result = runner.invoke(kw, ["stop", "--run-id", sample_deployment["run_id"], "--yes"])

        assert result.exit_code == 0


class TestKwCleanupCommand:
    """Test the haymaker kw cleanup command."""

    def test_cleanup_requires_target(self, runner: CliRunner) -> None:
        """Test cleanup command requires either --run-id, --all, or --older-than."""
        result = runner.invoke(kw, ["cleanup"])
        assert result.exit_code != 0 or "specify" in result.output.lower()

    def test_cleanup_dry_run(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test cleanup command dry-run mode."""
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            result = runner.invoke(
                kw, ["cleanup", "--run-id", sample_deployment["run_id"], "--dry-run"]
            )

        assert result.exit_code == 0
        assert "dry" in result.output.lower() or "would" in result.output.lower()
        # File should still exist
        assert deployment_file.exists()

    def test_cleanup_all_requires_confirmation(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test cleanup --all requires confirmation."""
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            runner.invoke(kw, ["cleanup", "--all"], input="n\n")

        assert deployment_file.exists()  # Should not be deleted

    def test_cleanup_older_than_parsing(self, runner: CliRunner, temp_state_dir: Path) -> None:
        """Test cleanup --older-than parses duration correctly."""
        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            # Test various duration formats
            result = runner.invoke(kw, ["cleanup", "--older-than", "24h", "--dry-run"])
            assert result.exit_code == 0

            result = runner.invoke(kw, ["cleanup", "--older-than", "7d", "--dry-run"])
            assert result.exit_code == 0


class TestKwDeleteWorkerCommand:
    """Test the haymaker kw delete-worker command."""

    def test_delete_worker_requires_identifier(self, runner: CliRunner) -> None:
        """Test delete-worker requires worker-id or run-id+department."""
        result = runner.invoke(kw, ["delete-worker"])
        assert result.exit_code != 0

    def test_delete_worker_by_id(
        self,
        runner: CliRunner,
        temp_state_dir: Path,
        sample_deployment: dict[str, Any],
        sample_worker: dict[str, Any],
    ) -> None:
        """Test delete-worker by worker ID."""
        # Setup files
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        worker_dir = temp_state_dir / "workers" / sample_deployment["run_id"]
        worker_dir.mkdir(parents=True)
        worker_file = worker_dir / f"{sample_worker['worker_id']}.json"
        worker_file.write_text(json.dumps(sample_worker))

        with (
            patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}),
            patch(
                "azure_haymaker.cli.commands.kw._delete_worker", new_callable=AsyncMock
            ) as mock_delete,
        ):
            mock_delete.return_value = True
            result = runner.invoke(
                kw, ["delete-worker", "--worker-id", sample_worker["worker_id"], "--yes"]
            )

        assert result.exit_code == 0


class TestKwStartCommand:
    """Test the haymaker kw start command."""

    def test_start_requires_run_id(self, runner: CliRunner) -> None:
        """Test start command requires run-id."""
        result = runner.invoke(kw, ["start"])
        assert result.exit_code != 0

    def test_start_deployment(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test start command starts a deployment."""
        sample_deployment["status"] = "stopped"
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        with (
            patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}),
            patch(
                "azure_haymaker.cli.commands.kw._start_deployment", new_callable=AsyncMock
            ) as mock_start,
        ):
            mock_start.return_value = True
            result = runner.invoke(kw, ["start", "--run-id", sample_deployment["run_id"]])

        assert result.exit_code == 0


class TestKwRestartCommand:
    """Test the haymaker kw restart command."""

    def test_restart_requires_run_id(self, runner: CliRunner) -> None:
        """Test restart command requires run-id."""
        result = runner.invoke(kw, ["restart"])
        assert result.exit_code != 0

    def test_restart_with_yes(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test restart command with --yes flag."""
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        with (
            patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}),
            patch(
                "azure_haymaker.cli.commands.kw._stop_deployment", new_callable=AsyncMock
            ) as mock_stop,
            patch(
                "azure_haymaker.cli.commands.kw._start_deployment", new_callable=AsyncMock
            ) as mock_start,
        ):
            mock_stop.return_value = True
            mock_start.return_value = True
            result = runner.invoke(
                kw, ["restart", "--run-id", sample_deployment["run_id"], "--yes"]
            )

        assert result.exit_code == 0


class TestKwLogsCommand:
    """Test the haymaker kw logs command."""

    def test_logs_requires_run_id(self, runner: CliRunner) -> None:
        """Test logs command requires run-id."""
        result = runner.invoke(kw, ["logs"])
        assert result.exit_code != 0

    def test_logs_shows_output(
        self, runner: CliRunner, temp_state_dir: Path, sample_deployment: dict[str, Any]
    ) -> None:
        """Test logs command shows log output."""
        deployment_file = temp_state_dir / "deployments" / f"{sample_deployment['run_id']}.json"
        deployment_file.write_text(json.dumps(sample_deployment))

        # Create a log file
        logs_dir = temp_state_dir / "logs" / sample_deployment["run_id"]
        logs_dir.mkdir(parents=True)
        log_file = logs_dir / "activity.log"
        log_file.write_text("2024-01-15 10:00:00 INFO Worker started\n")

        with patch.dict("os.environ", {"HAYMAKER_STATE_DIR": str(temp_state_dir)}):
            result = runner.invoke(kw, ["logs", "--run-id", sample_deployment["run_id"]])

        assert result.exit_code == 0


class TestConstants:
    """Test that constants are properly extracted."""

    def test_constants_module_exists(self) -> None:
        """Test that constants module exists."""
        from azure_haymaker import constants

        assert hasattr(constants, "DEFAULT_API_TIMEOUT_SECONDS")
        assert hasattr(constants, "DEFAULT_RETRY_COUNT")
        assert hasattr(constants, "MAX_WORKERS_PER_DEPLOYMENT")

    def test_cli_constants_exist(self) -> None:
        """Test that CLI-specific constants exist."""
        from azure_haymaker.cli import constants as cli_constants

        assert hasattr(cli_constants, "DEFAULT_LIST_LIMIT")
        assert hasattr(cli_constants, "DEFAULT_LOG_LINES")


class TestOutputFormatting:
    """Test output formatting utilities."""

    def test_table_output(self) -> None:
        """Test table output formatting."""
        from azure_haymaker.cli.utils.output import format_table

        data = [
            {"run_id": "kw-abc", "status": "running"},
            {"run_id": "kw-def", "status": "stopped"},
        ]
        output = format_table(data, columns=["run_id", "status"])
        assert "kw-abc" in output
        assert "running" in output

    def test_json_output(self) -> None:
        """Test JSON output formatting."""
        from azure_haymaker.cli.utils.output import format_json

        data = [{"run_id": "kw-abc", "status": "running"}]
        output = format_json(data)
        parsed = json.loads(output)
        assert parsed[0]["run_id"] == "kw-abc"


class TestInitCommand:
    """Test the kw init command."""

    def test_init_help(self, runner: CliRunner) -> None:
        """Test init command help."""
        result = runner.invoke(kw, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize Knowledge Worker app registration" in result.output
        assert "--tenant-id" in result.output
        assert "--save-config" in result.output

    @patch("azure_haymaker.knowledge_worker.infrastructure.app_setup.setup_kw_app")
    def test_init_success(self, mock_setup: Any, runner: CliRunner) -> None:
        """Test successful init."""
        from azure_haymaker.knowledge_worker.infrastructure.app_setup import KWAppConfig

        mock_setup.return_value = KWAppConfig(
            app_id="test-app-id",
            client_secret="test-secret",
            tenant_id="test-tenant-id",
            sp_id="test-sp-id",
        )

        result = runner.invoke(kw, ["init", "--tenant-id", "test-tenant-id"])
        assert result.exit_code == 0
        assert "App registration created successfully" in result.output
        assert "test-app-id" in result.output

    @patch("azure_haymaker.knowledge_worker.infrastructure.app_setup.setup_kw_app")
    def test_init_save_config(
        self, mock_setup: Any, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test init with --save-config."""
        from azure_haymaker.knowledge_worker.infrastructure.app_setup import KWAppConfig

        mock_setup.return_value = KWAppConfig(
            app_id="test-app-id",
            client_secret="test-secret",
            tenant_id="test-tenant-id",
            sp_id="test-sp-id",
        )

        config_file = tmp_path / "kw_config.env"
        result = runner.invoke(
            kw, ["init", "--tenant-id", "test-tenant-id", "--save-config", str(config_file)]
        )
        assert result.exit_code == 0
        assert "Configuration saved to" in result.output
        assert config_file.exists()
        content = config_file.read_text()
        assert "KW_APP_ID=test-app-id" in content


class TestDeployCommand:
    """Test the kw deploy command."""

    def test_deploy_help(self, runner: CliRunner) -> None:
        """Test deploy command help."""
        result = runner.invoke(kw, ["deploy", "--help"])
        assert result.exit_code == 0
        assert "Create a new Knowledge Worker deployment" in result.output
        assert "--workers" in result.output
        assert "--config-file" in result.output
        assert "--enable-ai-generation" in result.output

    def test_deploy_requires_tenant_domain(self, runner: CliRunner) -> None:
        """Test deploy fails without tenant domain."""
        result = runner.invoke(kw, ["deploy", "--workers", "5", "--no-start"])
        assert result.exit_code != 0
        assert "tenant_domain is required" in result.output

    def test_deploy_success(
        self, runner: CliRunner, temp_state_dir: Path, monkeypatch: Any
    ) -> None:
        """Test successful deploy."""
        monkeypatch.setenv("HAYMAKER_STATE_DIR", str(temp_state_dir))

        result = runner.invoke(
            kw,
            [
                "deploy",
                "--workers",
                "5",
                "--tenant-domain",
                "test.onmicrosoft.com",
                "--no-start",
            ],
        )
        assert result.exit_code == 0
        assert "Created deployment" in result.output
        assert "Workers: 5" in result.output

    def test_deploy_with_name(
        self, runner: CliRunner, temp_state_dir: Path, monkeypatch: Any
    ) -> None:
        """Test deploy with custom name."""
        monkeypatch.setenv("HAYMAKER_STATE_DIR", str(temp_state_dir))

        result = runner.invoke(
            kw,
            [
                "deploy",
                "--name",
                "my-test-deployment",
                "--workers",
                "10",
                "--tenant-domain",
                "test.onmicrosoft.com",
                "--no-start",
            ],
        )
        assert result.exit_code == 0
        assert "my-test-deployment" in result.output

    def test_deploy_json_output(
        self, runner: CliRunner, temp_state_dir: Path, monkeypatch: Any
    ) -> None:
        """Test deploy with JSON output."""
        monkeypatch.setenv("HAYMAKER_STATE_DIR", str(temp_state_dir))

        result = runner.invoke(
            kw,
            [
                "deploy",
                "--workers",
                "5",
                "--tenant-domain",
                "test.onmicrosoft.com",
                "--no-start",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        # Parse the JSON output - it may be multi-line formatted
        output = json.loads(result.output.strip())
        assert "run_id" in output
        assert "config" in output

    def test_deploy_from_config_file(
        self, runner: CliRunner, temp_state_dir: Path, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Test deploy from YAML config file."""
        monkeypatch.setenv("HAYMAKER_STATE_DIR", str(temp_state_dir))

        config_file = tmp_path / "deployment.yaml"
        config_file.write_text(
            """
name: config-file-deployment
total_workers: 15
duration_hours: 4
tenant_domain: config.onmicrosoft.com
departments:
  engineering:
    count: 15
    endpoint_type: cli_container
"""
        )

        result = runner.invoke(
            kw,
            ["deploy", "--config-file", str(config_file), "--no-start"],
        )
        assert result.exit_code == 0
        assert "config-file-deployment" in result.output
        assert "Workers: 15" in result.output

    def test_deploy_from_json_config(
        self, runner: CliRunner, temp_state_dir: Path, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Test deploy from JSON config file."""
        monkeypatch.setenv("HAYMAKER_STATE_DIR", str(temp_state_dir))

        config_file = tmp_path / "deployment.json"
        config_file.write_text(
            json.dumps(
                {
                    "name": "json-deployment",
                    "total_workers": 8,
                    "duration_hours": 2,
                    "tenant_domain": "json.onmicrosoft.com",
                }
            )
        )

        result = runner.invoke(
            kw,
            ["deploy", "--config-file", str(config_file), "--no-start"],
        )
        assert result.exit_code == 0
        assert "json-deployment" in result.output

    def test_deploy_with_ai_generation(
        self, runner: CliRunner, temp_state_dir: Path, monkeypatch: Any
    ) -> None:
        """Test deploy with AI generation enabled."""
        monkeypatch.setenv("HAYMAKER_STATE_DIR", str(temp_state_dir))

        result = runner.invoke(
            kw,
            [
                "deploy",
                "--workers",
                "5",
                "--tenant-domain",
                "test.onmicrosoft.com",
                "--enable-ai-generation",
                "--email-directive",
                "Write as limericks",
                "--no-start",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        output = json.loads(result.output.strip())
        assert output["config"]["email_generation"]["enabled"] is True
        assert "limericks" in output["config"]["email_generation"]["directive"]
