"""Unit tests for knowledge_worker.config module.

Tests the config.py module which handles:
- KnowledgeWorkerConfig dataclass definition
- Worker identity building from configuration
- Configuration validation and defaults

TDD Approach: These tests will FAIL until config.py is implemented.

Testing pyramid:
- 60% unit tests (config creation, defaults, validation)
- 30% integration tests (config → worker identity)
- 10% E2E tests (full config workflows)
"""

from unittest.mock import patch

from azure_haymaker.knowledge_worker.agent.config import (
    KnowledgeWorkerConfig,
    build_worker_identity,
)
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerIdentity,
    WorkerPersona,
)

# ============================================================================
# Unit Tests - KnowledgeWorkerConfig Creation (60%)
# ============================================================================


class TestKnowledgeWorkerConfigCreation:
    """Tests for KnowledgeWorkerConfig dataclass instantiation."""

    def test_config_with_minimal_fields(self):
        """Test creating config with only required fields."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test-001",
            display_name="Test Worker",
            department="engineering",
            persona="engineering",
        )

        assert config.worker_id == "kw-test-001"
        assert config.display_name == "Test Worker"
        assert config.department == "engineering"
        assert config.persona == "engineering"

    def test_config_auto_generates_name_from_worker_id(self):
        """Test that name is auto-generated if not provided."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.name == "knowledge-worker-kw-abc123"

    def test_config_auto_generates_goal_from_display_name(self):
        """Test that goal is auto-generated if not provided."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-abc123",
            display_name="Alice Developer",
            department="eng",
            persona="engineering",
        )

        assert "Alice Developer" in config.goal
        assert "M365 activities" in config.goal

    def test_config_preserves_custom_name(self):
        """Test that custom name is not overwritten."""
        config = KnowledgeWorkerConfig(
            name="my-custom-name",
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.name == "my-custom-name"

    def test_config_preserves_custom_goal(self):
        """Test that custom goal is not overwritten."""
        config = KnowledgeWorkerConfig(
            goal="My custom goal",
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.goal == "My custom goal"


# ============================================================================
# Unit Tests - KnowledgeWorkerConfig Defaults (60%)
# ============================================================================


class TestKnowledgeWorkerConfigDefaults:
    """Tests for KnowledgeWorkerConfig default values."""

    def test_default_endpoint_type_is_cli_container(self):
        """Test that endpoint_type defaults to cli_container."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.endpoint_type == "cli_container"

    def test_default_activity_frequency_is_30_minutes(self):
        """Test that activity_frequency_minutes defaults to 30."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.activity_frequency_minutes == 30

    def test_default_activity_types_is_empty_list(self):
        """Test that activity_types defaults to empty list."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.activity_types == []

    def test_default_team_id_is_empty_string(self):
        """Test that team_id defaults to empty string."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.team_id == ""

    def test_default_tenant_domain_is_empty_string(self):
        """Test that tenant_domain defaults to empty string."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.tenant_domain == ""


# ============================================================================
# Unit Tests - KnowledgeWorkerConfig __all__ Export (60%)
# ============================================================================


class TestKnowledgeWorkerConfigExports:
    """Tests for module __all__ exports."""

    def test_config_module_exports_knowledge_worker_config(self):
        """Test that KnowledgeWorkerConfig is in __all__."""
        from azure_haymaker.knowledge_worker import config

        assert "KnowledgeWorkerConfig" in config.__all__

    def test_config_module_exports_build_worker_identity(self):
        """Test that build_worker_identity is in __all__."""
        from azure_haymaker.knowledge_worker import config

        assert "build_worker_identity" in config.__all__

    def test_config_module_has_exactly_two_exports(self):
        """Test that __all__ contains exactly what we expect."""
        from azure_haymaker.knowledge_worker import config

        assert len(config.__all__) == 2


# ============================================================================
# Unit Tests - build_worker_identity Function (60%)
# ============================================================================


class TestBuildWorkerIdentity:
    """Tests for build_worker_identity function."""

    def test_build_worker_identity_creates_identity_from_config(self):
        """Test that function creates WorkerIdentity from config."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test-001",
            display_name="Test Worker",
            department="engineering",
            persona="engineering",
            endpoint_type="cli_container",
            team_id="team-123",
        )

        identity = build_worker_identity(config)

        assert isinstance(identity, WorkerIdentity)
        assert identity.worker_id == "kw-test-001"
        assert identity.display_name == "Test Worker"
        assert identity.department == "engineering"

    def test_build_worker_identity_maps_persona_to_enum(self):
        """Test that persona string is mapped to WorkerPersona enum."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        identity = build_worker_identity(config)

        assert identity.persona == WorkerPersona.ENGINEERING

    def test_build_worker_identity_maps_endpoint_type_to_enum(self):
        """Test that endpoint_type string is mapped to EndpointType enum."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
            endpoint_type="cloud_pc",
        )

        identity = build_worker_identity(config)

        assert identity.endpoint_type == EndpointType.CLOUD_PC

    def test_build_worker_identity_handles_unknown_persona(self):
        """Test that unknown persona defaults to ENGINEERING with warning."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="unknown_persona",
        )

        with patch("azure_haymaker.knowledge_worker.config.logger") as mock_logger:
            identity = build_worker_identity(config)

            assert identity.persona == WorkerPersona.ENGINEERING
            mock_logger.warning.assert_called_once()

    def test_build_worker_identity_handles_unknown_endpoint_type(self):
        """Test that unknown endpoint type defaults to CLI_CONTAINER."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
            endpoint_type="invalid_type",
        )

        identity = build_worker_identity(config)

        assert identity.endpoint_type == EndpointType.CLI_CONTAINER

    def test_build_worker_identity_includes_team_ids(self):
        """Test that team_id is included in team_ids list."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
            team_id="team-abc",
        )

        identity = build_worker_identity(config)

        assert "team-abc" in identity.team_ids

    def test_build_worker_identity_empty_team_id_creates_empty_list(self):
        """Test that empty team_id results in empty team_ids list."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
            team_id="",
        )

        identity = build_worker_identity(config)

        assert identity.team_ids == []

    def test_build_worker_identity_sets_endpoint_id(self):
        """Test that endpoint_id is set from config."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
            endpoint_id="endpoint-xyz",
        )

        identity = build_worker_identity(config)

        assert identity.endpoint_id == "endpoint-xyz"


# ============================================================================
# Integration Tests (30%)
# ============================================================================


class TestKnowledgeWorkerConfigIntegration:
    """Integration tests for config module."""

    def test_full_config_to_identity_workflow(self):
        """Test complete workflow from config creation to identity building."""
        # Create config
        config = KnowledgeWorkerConfig(
            worker_id="kw-full-001",
            display_name="Full Test Worker",
            department="sales",
            persona="sales",
            team_id="team-sales",
            team_name="Sales Team",
            activity_types=["email", "teams"],
            activity_frequency_minutes=15,
            endpoint_type="cloud_pc",
            endpoint_id="cpc-123",
            tenant_domain="test.onmicrosoft.com",
        )

        # Build identity
        identity = build_worker_identity(config)

        # Verify complete mapping
        assert identity.worker_id == config.worker_id
        assert identity.display_name == config.display_name
        assert identity.department == config.department
        assert identity.persona == WorkerPersona.SALES
        assert identity.endpoint_type == EndpointType.CLOUD_PC
        assert identity.endpoint_id == config.endpoint_id
        assert config.team_id in identity.team_ids

    def test_all_persona_types_map_correctly(self):
        """Test that all persona types map to correct enum."""
        persona_tests = [
            ("executive", WorkerPersona.EXECUTIVE),
            ("legal", WorkerPersona.LEGAL),
            ("engineering", WorkerPersona.ENGINEERING),
            ("hr", WorkerPersona.HR),
            ("finance", WorkerPersona.FINANCE),
            ("sales", WorkerPersona.SALES),
            ("operations", WorkerPersona.OPERATIONS),
            ("marketing", WorkerPersona.MARKETING),
        ]

        for persona_str, expected_enum in persona_tests:
            config = KnowledgeWorkerConfig(
                worker_id=f"kw-{persona_str}",
                display_name="Test",
                department="test",
                persona=persona_str,
            )
            identity = build_worker_identity(config)
            assert identity.persona == expected_enum, f"Failed for {persona_str}"

    def test_all_endpoint_types_map_correctly(self):
        """Test that all endpoint types map to correct enum."""
        endpoint_tests = [
            ("cloud_pc", EndpointType.CLOUD_PC),
            ("windows_vm", EndpointType.WINDOWS_VM),
            ("cli_container", EndpointType.CLI_CONTAINER),
        ]

        for endpoint_str, expected_enum in endpoint_tests:
            config = KnowledgeWorkerConfig(
                worker_id=f"kw-{endpoint_str}",
                display_name="Test",
                department="test",
                persona="engineering",
                endpoint_type=endpoint_str,
            )
            identity = build_worker_identity(config)
            assert identity.endpoint_type == expected_enum

    def test_case_insensitive_persona_mapping(self):
        """Test that persona mapping is case-insensitive."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="test",
            persona="ENGINEERING",  # Uppercase
        )

        identity = build_worker_identity(config)

        assert identity.persona == WorkerPersona.ENGINEERING

    def test_case_insensitive_endpoint_type_mapping(self):
        """Test that endpoint type mapping is case-insensitive."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="test",
            persona="engineering",
            endpoint_type="CLOUD_PC",  # Uppercase
        )

        identity = build_worker_identity(config)

        assert identity.endpoint_type == EndpointType.CLOUD_PC


# ============================================================================
# Edge Case Tests (10%)
# ============================================================================


class TestKnowledgeWorkerConfigEdgeCases:
    """Edge case tests for config module."""

    def test_config_with_empty_worker_id(self):
        """Test handling of empty worker_id."""
        config = KnowledgeWorkerConfig(
            worker_id="",
            display_name="Test",
            department="test",
            persona="engineering",
        )

        assert config.name == "knowledge-worker-"
        assert config.worker_id == ""

    def test_config_with_empty_display_name(self):
        """Test handling of empty display_name."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="",
            department="test",
            persona="engineering",
        )

        assert config.display_name == ""
        # Goal should still be generated
        assert config.goal != ""

    def test_build_worker_identity_with_minimal_config(self):
        """Test building identity from minimal config."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-min",
            display_name="Min",
            department="min",
            persona="engineering",
        )

        identity = build_worker_identity(config)

        # Should have defaults
        assert identity.endpoint_type == EndpointType.CLI_CONTAINER
        assert identity.team_ids == []
        assert identity.endpoint_id == ""

    def test_config_with_special_characters_in_worker_id(self):
        """Test config with special characters in worker_id."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test-123_abc.xyz",
            display_name="Test",
            department="test",
            persona="engineering",
        )

        assert config.worker_id == "kw-test-123_abc.xyz"
        assert "kw-test-123_abc.xyz" in config.name

    def test_config_with_very_long_display_name(self):
        """Test config with very long display name."""
        long_name = "A" * 200
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name=long_name,
            department="test",
            persona="engineering",
        )

        assert config.display_name == long_name
        assert long_name in config.goal
