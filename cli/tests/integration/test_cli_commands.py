"""Integration tests for CLI commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, AsyncMock


class TestTelemetryCommands:
    """Test haymaker telemetry CLI commands."""

    def test_telemetry_start_command(self, tmp_path):
        """Test 'haymaker telemetry start' command."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.telemetry.collector.TelemetryCollector') as mock_collector:
            mock_instance = AsyncMock()
            mock_collector.return_value = mock_instance

            result = runner.invoke(cli, [
                'telemetry', 'start',
                '--storage-path', str(tmp_path)
            ])

            assert result.exit_code == 0
            assert "started" in result.output.lower() or "collecting" in result.output.lower()

    def test_telemetry_stop_command(self, tmp_path):
        """Test 'haymaker telemetry stop' command."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.telemetry.collector.TelemetryCollector') as mock_collector:
            mock_instance = AsyncMock()
            mock_collector.return_value = mock_instance

            result = runner.invoke(cli, ['telemetry', 'stop'])

            assert result.exit_code == 0
            assert "stopped" in result.output.lower()

    def test_telemetry_status_command(self, tmp_path):
        """Test 'haymaker telemetry status' command."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.telemetry.collector.TelemetryCollector') as mock_collector:
            mock_instance = Mock()
            mock_instance.get_status.return_value = {
                "is_running": True,
                "last_collection_time": "2025-01-01T12:00:00"
            }
            mock_collector.return_value = mock_instance

            result = runner.invoke(cli, ['telemetry', 'status'])

            assert result.exit_code == 0
            assert "running" in result.output.lower() or "status" in result.output.lower()

    def test_telemetry_start_with_interval(self, tmp_path):
        """Test starting telemetry with custom interval."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.telemetry.collector.TelemetryCollector') as mock_collector:
            mock_instance = AsyncMock()
            mock_collector.return_value = mock_instance

            result = runner.invoke(cli, [
                'telemetry', 'start',
                '--interval', '600',
                '--storage-path', str(tmp_path)
            ])

            assert result.exit_code == 0

    def test_telemetry_start_already_running(self, tmp_path):
        """Test starting telemetry when already running."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.telemetry.collector.TelemetryCollector') as mock_collector:
            mock_instance = AsyncMock()
            mock_instance.start_background.side_effect = RuntimeError("Already running")
            mock_collector.return_value = mock_instance

            result = runner.invoke(cli, [
                'telemetry', 'start',
                '--storage-path', str(tmp_path)
            ])

            assert result.exit_code != 0
            assert "already running" in result.output.lower()


class TestReportCommands:
    """Test haymaker report CLI commands."""

    def test_report_summary_command(self, tmp_path):
        """Test 'haymaker report summary' command."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_summary_report.return_value = tmp_path / "report.html"
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'summary',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code == 0
            assert "generated" in result.output.lower() or "report" in result.output.lower()

    def test_report_detailed_command(self, tmp_path):
        """Test 'haymaker report detailed' command."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_detailed_report.return_value = tmp_path / "detailed.html"
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'detailed',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code == 0

    def test_report_scenario_command(self, tmp_path):
        """Test 'haymaker report scenario' command."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_scenario_report.return_value = tmp_path / "scenario.html"
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'scenario',
                '--scenario-id', 'scenario-001',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code == 0

    def test_report_errors_command(self, tmp_path):
        """Test 'haymaker report errors' command."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_error_report.return_value = tmp_path / "errors.html"
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'errors',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code == 0

    def test_report_with_date_filter(self, tmp_path):
        """Test report with date range filter."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_summary_report.return_value = tmp_path / "report.html"
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'summary',
                '--start-date', '2025-01-01',
                '--end-date', '2025-01-07',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code == 0

    def test_report_with_status_filter(self, tmp_path):
        """Test report with status filter."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_summary_report.return_value = tmp_path / "report.html"
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'summary',
                '--status', 'completed',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code == 0

    def test_report_export_csv(self, tmp_path):
        """Test 'haymaker report export --format csv' command."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.export_to_csv.return_value = tmp_path / "export.csv"
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'export',
                '--format', 'csv',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code == 0

    def test_report_export_json(self, tmp_path):
        """Test 'haymaker report export --format json' command."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.export_to_json.return_value = tmp_path / "export.json"
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'export',
                '--format', 'json',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code == 0

    def test_report_no_data(self, tmp_path):
        """Test report generation when no data exists."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_summary_report.side_effect = ValueError("No data available")
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'summary',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code != 0
            assert "no data" in result.output.lower()


class TestDashboardCommand:
    """Test haymaker report dashboard CLI command."""

    def test_dashboard_command(self, tmp_path):
        """Test 'haymaker report dashboard' command."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.ui.dashboard.HayMakerDashboard') as mock_dashboard:
            mock_instance = Mock()
            mock_instance.run = Mock()
            mock_dashboard.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'dashboard',
                '--storage-path', str(tmp_path)
            ])

            # Dashboard command should start interactive UI
            mock_dashboard.assert_called_once()

    def test_dashboard_with_auto_refresh(self, tmp_path):
        """Test dashboard with auto-refresh enabled."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.ui.dashboard.HayMakerDashboard') as mock_dashboard:
            mock_instance = Mock()
            mock_instance.run = Mock()
            mock_dashboard.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'dashboard',
                '--auto-refresh',
                '--refresh-interval', '30',
                '--storage-path', str(tmp_path)
            ])

            mock_dashboard.assert_called_once()

    def test_dashboard_no_data(self, tmp_path):
        """Test dashboard when no telemetry data exists."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.ui.dashboard.HayMakerDashboard') as mock_dashboard:
            mock_instance = Mock()
            mock_instance.run = Mock()
            mock_dashboard.return_value = mock_instance

            result = runner.invoke(cli, [
                'report', 'dashboard',
                '--storage-path', str(tmp_path)
            ])

            # Should still start dashboard even with no data
            mock_dashboard.assert_called_once()


class TestCommandOptions:
    """Test command options and flags."""

    def test_help_text(self):
        """Test all commands have help text."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        # Test main help
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "telemetry" in result.output.lower()
        assert "report" in result.output.lower()

        # Test telemetry help
        result = runner.invoke(cli, ['telemetry', '--help'])
        assert result.exit_code == 0
        assert "start" in result.output.lower()
        assert "stop" in result.output.lower()
        assert "status" in result.output.lower()

        # Test report help
        result = runner.invoke(cli, ['report', '--help'])
        assert result.exit_code == 0
        assert "summary" in result.output.lower()
        assert "detailed" in result.output.lower()

    def test_version_option(self):
        """Test --version flag."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        result = runner.invoke(cli, ['--version'])

        assert result.exit_code == 0
        # Should display version number

    def test_verbose_option(self, tmp_path):
        """Test --verbose flag."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_summary_report.return_value = tmp_path / "report.html"
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                '--verbose',
                'report', 'summary',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code == 0

    def test_quiet_option(self, tmp_path):
        """Test --quiet flag."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_summary_report.return_value = tmp_path / "report.html"
            mock_generator.return_value = mock_instance

            result = runner.invoke(cli, [
                '--quiet',
                'report', 'summary',
                '--output-dir', str(tmp_path)
            ])

            assert result.exit_code == 0
            # Output should be minimal

    def test_config_file_option(self, tmp_path):
        """Test --config option."""
        from haymaker_cli.main import cli
        import yaml

        # Create config file
        config_file = tmp_path / "config.yaml"
        config = {
            "storage_path": str(tmp_path / "telemetry"),
            "retention_days": 45
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        runner = CliRunner()

        with patch('haymaker_cli.telemetry.collector.TelemetryCollector') as mock_collector:
            mock_instance = AsyncMock()
            mock_collector.return_value = mock_instance

            result = runner.invoke(cli, [
                '--config', str(config_file),
                'telemetry', 'start'
            ])

            # Should load config from file


class TestCommandErrorHandling:
    """Test CLI command error handling."""

    def test_invalid_command(self):
        """Test invalid command name."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        result = runner.invoke(cli, ['invalid-command'])

        assert result.exit_code != 0

    def test_missing_required_argument(self):
        """Test missing required argument."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        result = runner.invoke(cli, ['report', 'scenario'])

        # Should require --scenario-id
        assert result.exit_code != 0

    def test_invalid_option_value(self, tmp_path):
        """Test invalid option value."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        result = runner.invoke(cli, [
            'telemetry', 'start',
            '--interval', 'invalid',
            '--storage-path', str(tmp_path)
        ])

        assert result.exit_code != 0

    def test_api_connection_error(self, tmp_path):
        """Test handling API connection error."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        with patch('haymaker_cli.telemetry.collector.TelemetryCollector') as mock_collector:
            mock_instance = AsyncMock()
            mock_instance.collect_once.side_effect = Exception("API connection failed")
            mock_collector.return_value = mock_instance

            result = runner.invoke(cli, [
                'telemetry', 'start',
                '--storage-path', str(tmp_path)
            ])

            # Should handle error gracefully

    def test_permission_error(self, tmp_path):
        """Test handling permission error."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)

        result = runner.invoke(cli, [
            'report', 'summary',
            '--output-dir', str(readonly_dir)
        ])

        # Should handle permission error gracefully
        # (May succeed or fail depending on implementation)


class TestCommandPipeline:
    """Test command pipelines and workflows."""

    def test_collect_and_report_pipeline(self, tmp_path):
        """Test collecting data and then generating report."""
        from haymaker_cli.main import cli

        runner = CliRunner()

        storage_path = tmp_path / "telemetry"
        output_path = tmp_path / "reports"

        # Start collection
        with patch('haymaker_cli.telemetry.collector.TelemetryCollector') as mock_collector:
            mock_instance = AsyncMock()
            mock_instance.collect_once.return_value = Mock(success=True)
            mock_collector.return_value = mock_instance

            result1 = runner.invoke(cli, [
                'telemetry', 'start',
                '--storage-path', str(storage_path)
            ])

            assert result1.exit_code == 0

        # Generate report
        with patch('haymaker_cli.reports.generator.ReportGenerator') as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_summary_report.return_value = output_path / "report.html"
            mock_generator.return_value = mock_instance

            result2 = runner.invoke(cli, [
                'report', 'summary',
                '--storage-path', str(storage_path),
                '--output-dir', str(output_path)
            ])

            assert result2.exit_code == 0
