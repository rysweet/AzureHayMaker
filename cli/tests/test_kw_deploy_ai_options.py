"""TDD tests for CLI AI email generation and marker options.

These tests are written FIRST following TDD principles. They will fail until
the feature is implemented in haymaker_cli/kw/commands.py.

Test Coverage:
1. Validation Tests - Input validation and error handling
2. Config Construction Tests - CLI options map to config objects
3. Dry-run Output Tests - Output formatting and display
4. Environment Variable Tests - API key handling
5. Option Combinations - Multiple options working together

Run with: pytest cli/tests/test_kw_deploy_ai_options.py -v
"""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from haymaker_cli.kw.commands import deploy


class TestAIGenerationValidation:
    """Test validation of AI generation options."""

    def test_email_directive_max_length_1000_chars_fails(self):
        """Email directive longer than 1000 characters should exit with error."""
        runner = CliRunner()
        long_directive = "x" * 1001

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--email-directive",
                long_directive,
                "--dry-run",
            ],
        )

        assert result.exit_code == 1
        assert "directive" in result.output.lower()
        assert "1000" in result.output or "too long" in result.output.lower()

    def test_email_directive_exactly_1000_chars_succeeds(self):
        """Email directive with exactly 1000 characters should succeed."""
        runner = CliRunner()
        directive_1000 = "x" * 1000

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--email-directive",
                directive_1000,
                "--dry-run",
            ],
        )

        # Should succeed (dry-run exits 0)
        assert result.exit_code == 0

    def test_marker_format_max_length_50_chars_fails(self):
        """Marker format longer than 50 characters should exit with error."""
        runner = CliRunner()
        long_marker = "x" * 51

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--marker-format",
                long_marker,
                "--dry-run",
            ],
        )

        assert result.exit_code == 1
        assert "marker" in result.output.lower()
        assert "50" in result.output or "too long" in result.output.lower()

    def test_marker_format_exactly_50_chars_succeeds(self):
        """Marker format with exactly 50 characters should succeed."""
        runner = CliRunner()
        marker_50 = "x" * 50

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--marker-format",
                marker_50,
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

    def test_ai_enabled_without_api_key_fails(self):
        """AI generation enabled without ANTHROPIC_API_KEY should exit with error."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Ensure no API key in environment
            result = runner.invoke(
                deploy,
                [
                    "--workers",
                    "5",
                    "--enable-ai-generation",
                    "--dry-run",
                ],
                env={"ANTHROPIC_API_KEY": ""},  # Empty key
            )

            assert result.exit_code == 1
            assert "ANTHROPIC_API_KEY" in result.output
            assert "not found" in result.output.lower() or "required" in result.output.lower()

    def test_ai_enabled_with_api_key_succeeds(self):
        """AI generation with valid API key should succeed."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test-key-12345"},
        )

        # Should succeed in dry-run mode
        assert result.exit_code == 0

    def test_empty_directive_warns_and_sets_none(self):
        """Empty directive string should warn and set to None (use default)."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--email-directive",
                "",  # Empty string
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test-key"},
        )

        # Should succeed but show warning
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "default" in result.output.lower()

    def test_whitespace_only_directive_warns_and_sets_none(self):
        """Whitespace-only directive should warn and set to None."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--email-directive",
                "   \t\n  ",  # Whitespace only
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test-key"},
        )

        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "default" in result.output.lower()


class TestConfigConstruction:
    """Test that CLI options correctly map to configuration objects."""

    @patch("haymaker_cli.kw.commands.DeploymentConfig")
    @patch("haymaker_cli.kw.commands.KnowledgeWorkerOrchestrator")
    def test_enable_ai_generation_maps_to_config(self, mock_orch, mock_config):
        """--enable-ai-generation should set email_generation.enabled=True."""
        runner = CliRunner()
        mock_config.return_value = MagicMock()
        mock_orch.return_value = MagicMock()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test"},
        )

        assert result.exit_code == 0
        # Verify DeploymentConfig called with email_generation.enabled=True
        call_kwargs = mock_config.call_args.kwargs
        assert "email_generation" in call_kwargs
        assert call_kwargs["email_generation"].enabled is True

    @patch("haymaker_cli.kw.commands.DeploymentConfig")
    @patch("haymaker_cli.kw.commands.KnowledgeWorkerOrchestrator")
    def test_email_directive_maps_to_config(self, mock_orch, mock_config):
        """--email-directive should set email_generation.directive."""
        runner = CliRunner()
        mock_config.return_value = MagicMock()
        mock_orch.return_value = MagicMock()

        test_directive = "Write emails as limericks"

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--email-directive",
                test_directive,
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_config.call_args.kwargs
        assert call_kwargs["email_generation"].directive == test_directive

    @patch("haymaker_cli.kw.commands.DeploymentConfig")
    @patch("haymaker_cli.kw.commands.KnowledgeWorkerOrchestrator")
    def test_marker_config_maps_to_deployment_config(self, mock_orch, mock_config):
        """Marker options should map to DeploymentConfig marker fields."""
        runner = CliRunner()
        mock_config.return_value = MagicMock()
        mock_orch.return_value = MagicMock()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-markers",
                "--marker-format",
                "TEST-ID",
                "--marker-style",
                "hidden",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_config.call_args.kwargs
        assert call_kwargs["email_markers_enabled"] is True
        assert call_kwargs["marker_format"] == "TEST-ID"
        assert call_kwargs["marker_style"] == "hidden"

    @patch("haymaker_cli.kw.commands.DeploymentConfig")
    @patch("haymaker_cli.kw.commands.KnowledgeWorkerOrchestrator")
    def test_no_enable_markers_disables_markers(self, mock_orch, mock_config):
        """--no-enable-markers should set email_markers_enabled=False."""
        runner = CliRunner()
        mock_config.return_value = MagicMock()
        mock_orch.return_value = MagicMock()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--no-enable-markers",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_config.call_args.kwargs
        assert call_kwargs["email_markers_enabled"] is False

    @patch("haymaker_cli.kw.commands.DeploymentConfig")
    @patch("haymaker_cli.kw.commands.KnowledgeWorkerOrchestrator")
    def test_defaults_applied_when_options_not_provided(self, mock_orch, mock_config):
        """Default values should be set when options are not provided."""
        runner = CliRunner()
        mock_config.return_value = MagicMock()
        mock_orch.return_value = MagicMock()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_config.call_args.kwargs

        # Check defaults
        assert call_kwargs["email_generation"].enabled is False
        assert call_kwargs["email_markers_enabled"] is True  # Markers on by default
        assert call_kwargs["marker_format"] == "MARKER"
        assert call_kwargs["marker_style"] == "subject"

    @patch("haymaker_cli.kw.commands.DeploymentConfig")
    @patch("haymaker_cli.kw.commands.KnowledgeWorkerOrchestrator")
    def test_all_options_combined_work_correctly(self, mock_orch, mock_config):
        """All AI and marker options should work together."""
        runner = CliRunner()
        mock_config.return_value = MagicMock()
        mock_orch.return_value = MagicMock()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "25",
                "--department",
                "operations",
                "--enable-ai-generation",
                "--email-directive",
                "Focus on IT operations",
                "--enable-markers",
                "--marker-format",
                "OPS-TEST",
                "--marker-style",
                "both",
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_config.call_args.kwargs

        # Verify all options mapped correctly
        assert call_kwargs["email_generation"].enabled is True
        assert call_kwargs["email_generation"].directive == "Focus on IT operations"
        assert call_kwargs["email_markers_enabled"] is True
        assert call_kwargs["marker_format"] == "OPS-TEST"
        assert call_kwargs["marker_style"] == "both"


class TestDryRunOutput:
    """Test dry-run output formatting and display."""

    def test_dry_run_shows_all_configurations(self):
        """Dry-run should display all configuration details."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "25",
                "--department",
                "operations",
                "--enable-ai-generation",
                "--email-directive",
                "Write emails about IT operations",
                "--marker-format",
                "TEST",
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test"},
        )

        assert result.exit_code == 0

        # Check output contains key information
        output = result.output
        assert "25" in output  # Worker count
        assert "operations" in output.lower()  # Department
        assert "AI" in output or "generation" in output.lower()  # AI enabled
        assert "TEST" in output  # Marker format

    def test_dry_run_truncates_long_directives(self):
        """Directives longer than 80 chars should be truncated in dry-run output."""
        runner = CliRunner()
        long_directive = "x" * 150  # 150 chars

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--email-directive",
                long_directive,
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test"},
        )

        assert result.exit_code == 0

        # Should show truncated version with ellipsis
        assert "..." in result.output or "truncated" in result.output.lower()
        # Full directive should not be in output
        assert long_directive not in result.output

    def test_dry_run_shows_cost_warning_when_ai_enabled(self):
        """Dry-run should show cost warning when AI is enabled."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "25",
                "--enable-ai-generation",
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test"},
        )

        assert result.exit_code == 0

        # Look for cost-related warnings
        output_lower = result.output.lower()
        assert any(
            word in output_lower for word in ["cost", "billing", "api", "charges", "estimated"]
        )

    def test_dry_run_shows_marker_config_when_enabled(self):
        """Dry-run should display marker configuration."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "10",
                "--enable-markers",
                "--marker-format",
                "CUSTOM-ID",
                "--marker-style",
                "hidden",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

        output = result.output
        assert "marker" in output.lower()
        assert "CUSTOM-ID" in output
        assert "hidden" in output.lower()

    def test_dry_run_does_not_show_marker_config_when_disabled(self):
        """Dry-run should not display marker info when markers disabled."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "10",
                "--no-enable-markers",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

        # Marker details should be minimal or indicate disabled
        output_lower = result.output.lower()
        assert "marker" not in output_lower or "disabled" in output_lower


class TestEnvironmentVariables:
    """Test environment variable handling for API keys."""

    def test_anthropic_api_key_from_env(self):
        """Should read ANTHROPIC_API_KEY from environment."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test-12345"},
        )

        assert result.exit_code == 0
        # Should not show API key error

    def test_missing_api_key_shows_helpful_error(self):
        """Missing API key should show clear error message."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--dry-run",
            ],
            env={},  # No API key
        )

        assert result.exit_code == 1
        output = result.output
        assert "ANTHROPIC_API_KEY" in output
        # Should provide helpful guidance
        assert any(word in output.lower() for word in ["set", "export", "environment"])

    def test_api_key_not_checked_when_ai_disabled(self):
        """API key should not be required when AI generation is disabled."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--dry-run",
            ],
            env={},  # No API key, but AI disabled so should be fine
        )

        # Should succeed (dry-run exits 0) even without API key
        assert result.exit_code == 0


class TestMarkerStyleValidation:
    """Test marker style option validation."""

    def test_valid_marker_styles_accepted(self):
        """Valid marker styles should be accepted."""
        runner = CliRunner()

        for style in ["subject", "hidden", "both"]:
            result = runner.invoke(
                deploy,
                [
                    "--workers",
                    "5",
                    "--marker-style",
                    style,
                    "--dry-run",
                ],
            )
            assert result.exit_code == 0, f"Style '{style}' should be valid"

    def test_invalid_marker_style_fails(self):
        """Invalid marker style should exit with error."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--marker-style",
                "invalid-style",
                "--dry-run",
            ],
        )

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()


class TestBoundaryConditions:
    """Test edge cases and boundary conditions."""

    def test_zero_workers_handled(self):
        """Zero workers should be handled gracefully."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "0",
                "--dry-run",
            ],
        )

        # Should either fail with validation error or succeed with warning
        # The exact behavior depends on implementation choice
        assert result.exit_code in [0, 1]

    def test_large_worker_count_with_ai_shows_cost_warning(self):
        """Large worker count with AI should show prominent cost warning."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "100",
                "--enable-ai-generation",
                "--duration",
                "8",
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test"},
        )

        assert result.exit_code == 0

        # Should show cost estimate or warning
        output_lower = result.output.lower()
        assert "cost" in output_lower or "expensive" in output_lower

    def test_directive_with_special_characters(self):
        """Directive with special characters should be handled correctly."""
        runner = CliRunner()
        special_directive = 'Write emails with "quotes", $symbols, and \n newlines'

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--email-directive",
                special_directive,
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test"},
        )

        assert result.exit_code == 0

    def test_marker_format_with_special_characters(self):
        """Marker format with allowed special characters should work."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--marker-format",
                "TEST-ID_2025",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0


class TestOptionInteractions:
    """Test interactions between different options."""

    def test_directive_without_enable_ai_shows_warning(self):
        """Using --email-directive without --enable-ai-generation should warn."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--email-directive",
                "Write as limericks",
                "--dry-run",
            ],
        )

        # Should succeed but show warning
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "warn" in output_lower or "ignored" in output_lower

    def test_markers_work_without_ai_generation(self):
        """Markers should work independently of AI generation."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-markers",
                "--marker-format",
                "MANUAL",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Markers should still be configured

    def test_ai_generation_works_without_custom_markers(self):
        """AI generation should work with default marker settings."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "5",
                "--enable-ai-generation",
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test"},
        )

        assert result.exit_code == 0


class TestIntegrationScenarios:
    """Test realistic end-to-end usage scenarios."""

    def test_typical_ai_deployment_scenario(self):
        """Test a typical deployment with AI enabled."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--name",
                "ai-test-deployment",
                "--workers",
                "25",
                "--department",
                "operations",
                "--duration",
                "4",
                "--enable-ai-generation",
                "--email-directive",
                "Focus on IT operations and infrastructure",
                "--marker-format",
                "OPS-TEST",
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test-key"},
        )

        assert result.exit_code == 0

        output = result.output
        # Verify key details shown
        assert "25" in output
        assert "operations" in output.lower()
        assert "4" in output
        assert "OPS-TEST" in output

    def test_red_team_stealth_scenario(self):
        """Test red team scenario with hidden markers."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "50",
                "--enable-ai-generation",
                "--marker-style",
                "hidden",
                "--marker-format",
                "BENIGN",
                "--dry-run",
            ],
            env={"ANTHROPIC_API_KEY": "sk-ant-test"},
        )

        assert result.exit_code == 0
        assert "hidden" in result.output.lower()
        assert "BENIGN" in result.output

    def test_cost_optimized_scenario(self):
        """Test cost-optimized deployment (no AI, markers only)."""
        runner = CliRunner()

        result = runner.invoke(
            deploy,
            [
                "--workers",
                "100",
                "--duration",
                "8",
                "--enable-markers",
                "--marker-format",
                "TEMPLATE",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Should not show AI cost warnings
        assert "AI" not in result.output or "disabled" in result.output.lower()
