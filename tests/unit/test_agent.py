"""Unit tests for Knowledge Worker Agent module.

Tests the knowledge_worker/agent.py module which handles:
- Agent initialization and configuration validation
- Lifecycle hooks (on_start, on_execute, on_cleanup)
- Worker identity building
- Recipient validation and management
- M365 client initialization

Testing approach:
- 60% unit tests (heavily mocked)
- 30% integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

from unittest.mock import MagicMock, patch

import pytest

from azure_haymaker.knowledge_worker.agent import (
    KnowledgeWorkerAgent,
    KnowledgeWorkerConfig,
)
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerIdentity,
    WorkerPersona,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def basic_worker_config():
    """Create a basic worker configuration for testing."""
    return KnowledgeWorkerConfig(
        worker_id="kw-test-001",
        display_name="Test Worker",
        department="engineering",
        persona="engineering",
        tenant_domain="test.onmicrosoft.com",
        team_id="team-123",
        team_name="Test Team",
    )


@pytest.fixture
def full_worker_config():
    """Create a fully populated worker configuration."""
    return KnowledgeWorkerConfig(
        name="custom-agent-name",
        goal="Custom agent goal",
        worker_id="kw-full-001",
        display_name="Full Config Worker",
        department="sales",
        persona="sales",
        team_id="team-sales",
        team_name="Sales Team",
        activity_types=["email", "teams", "calendar"],
        activity_frequency_minutes=15,
        endpoint_type="cloud_pc",
        endpoint_id="cpc-123",
        m365_app_id="app-id-123",
        m365_cert_thumbprint="cert-thumb",
        tenant_domain="corp.onmicrosoft.com",
    )


@pytest.fixture
def mock_worker_identity():
    """Create a mock WorkerIdentity for testing."""
    return WorkerIdentity(
        worker_id="kw-identity-001",
        display_name="Identity Test Worker",
        user_principal_name="test@corp.onmicrosoft.com",
        department="engineering",
        persona=WorkerPersona.ENGINEERING,
        endpoint_type=EndpointType.CLI_CONTAINER,
        team_ids=["team-1", "team-2"],
    )


# ============================================================================
# Unit Tests - KnowledgeWorkerConfig (60%)
# ============================================================================


class TestKnowledgeWorkerConfig:
    """Tests for KnowledgeWorkerConfig dataclass."""

    def test_default_name_generated_from_worker_id(self):
        """Test that name is auto-generated from worker_id when not provided."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.name == "knowledge-worker-kw-abc123"

    def test_default_goal_generated_from_display_name(self):
        """Test that goal is auto-generated from display_name when not provided."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-abc123",
            display_name="Alice Developer",
            department="eng",
            persona="engineering",
        )

        assert "Alice Developer" in config.goal
        assert "M365 activities" in config.goal

    def test_custom_name_preserved(self):
        """Test that custom name is not overwritten."""
        config = KnowledgeWorkerConfig(
            name="my-custom-agent",
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.name == "my-custom-agent"

    def test_custom_goal_preserved(self):
        """Test that custom goal is not overwritten."""
        config = KnowledgeWorkerConfig(
            goal="My custom goal",
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.goal == "My custom goal"

    def test_default_endpoint_type_is_cli_container(self):
        """Test that default endpoint type is cli_container."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.endpoint_type == "cli_container"

    def test_default_activity_frequency(self):
        """Test default activity frequency is 30 minutes."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.activity_frequency_minutes == 30

    def test_activity_types_default_to_empty(self):
        """Test that activity_types defaults to empty list."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
        )

        assert config.activity_types == []


# ============================================================================
# Unit Tests - KnowledgeWorkerAgent Initialization (60%)
# ============================================================================


class TestKnowledgeWorkerAgentInit:
    """Tests for KnowledgeWorkerAgent initialization."""

    def test_basic_initialization(self, basic_worker_config):
        """Test basic agent initialization."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        assert agent.worker_config == basic_worker_config
        assert agent._m365_client is None
        assert agent._allowed_recipients == set()
        assert agent._validator is None

    def test_initialization_with_identity(self, basic_worker_config, mock_worker_identity):
        """Test agent initialization with pre-built identity."""
        agent = KnowledgeWorkerAgent(basic_worker_config, worker_identity=mock_worker_identity)

        assert agent.worker_identity == mock_worker_identity

    def test_identity_built_from_config(self, basic_worker_config):
        """Test that worker identity is built from config when not provided."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        assert agent.worker_identity.worker_id == "kw-test-001"
        assert agent.worker_identity.display_name == "Test Worker"
        assert agent.worker_identity.department == "engineering"

    def test_persona_mapped_to_enum(self, basic_worker_config):
        """Test that persona string is mapped to WorkerPersona enum."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        assert agent.worker_identity.persona == WorkerPersona.ENGINEERING

    def test_unknown_persona_defaults_to_engineering(self):
        """Test that unknown persona defaults to ENGINEERING with warning."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="unknown_persona",
        )

        agent = KnowledgeWorkerAgent(config)

        assert agent.worker_identity.persona == WorkerPersona.ENGINEERING

    def test_endpoint_type_mapped_to_enum(self, full_worker_config):
        """Test that endpoint_type string is mapped to EndpointType enum."""
        agent = KnowledgeWorkerAgent(full_worker_config)

        assert agent.worker_identity.endpoint_type == EndpointType.CLOUD_PC

    def test_team_ids_set_from_config(self, basic_worker_config):
        """Test that team_ids is set from config.team_id."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        assert "team-123" in agent.worker_identity.team_ids

    def test_empty_team_id_results_in_empty_list(self):
        """Test that empty team_id results in empty team_ids list."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
            team_id="",  # Empty
        )

        agent = KnowledgeWorkerAgent(config)

        assert agent.worker_identity.team_ids == []

    def test_get_config_returns_worker_config(self, basic_worker_config):
        """Test that get_config returns the worker configuration."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        result = agent.get_config()

        assert result == basic_worker_config


# ============================================================================
# Unit Tests - Lifecycle Hooks (60%)
# ============================================================================


class TestKnowledgeWorkerAgentLifecycle:
    """Tests for agent lifecycle hooks."""

    def test_on_start_initializes_validator(self, basic_worker_config):
        """Test that on_start initializes the validator."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        # Mock M365 client initialization to avoid dependency
        with patch.object(agent, "_initialize_m365_client"):
            agent.on_start()

        assert agent._validator is not None
        assert agent._validator.tenant_domain == "test.onmicrosoft.com"

    def test_on_start_without_tenant_domain(self):
        """Test on_start with missing tenant domain uses invalid.domain."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-abc123",
            display_name="Test",
            department="eng",
            persona="engineering",
            tenant_domain="",  # Empty
        )
        agent = KnowledgeWorkerAgent(config)

        with patch.object(agent, "_initialize_m365_client"):
            agent.on_start()

        assert agent._validator.tenant_domain == "invalid.domain"

    def test_on_cleanup_disconnects_m365_client(self, basic_worker_config):
        """Test that on_cleanup disconnects M365 client."""
        agent = KnowledgeWorkerAgent(basic_worker_config)
        agent._m365_client = MagicMock()  # Simulate initialized client

        agent.on_cleanup(0)

        assert agent._m365_client is None

    def test_on_execute_calls_parent(self, basic_worker_config):
        """Test that on_execute delegates to parent class."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with patch.object(
            agent.__class__.__bases__[0], "on_execute", return_value=0
        ) as mock_execute:
            result = agent.on_execute()

            mock_execute.assert_called_once()
            assert result == 0


# ============================================================================
# Unit Tests - Validator Property (60%)
# ============================================================================


class TestKnowledgeWorkerAgentValidator:
    """Tests for validator property and initialization."""

    def test_validator_property_raises_when_not_initialized(self, basic_worker_config):
        """Test that accessing validator before on_start raises RuntimeError."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with pytest.raises(RuntimeError) as exc_info:
            _ = agent.validator

        assert "not initialized" in str(exc_info.value).lower()
        assert "on_start" in str(exc_info.value)

    def test_validator_property_returns_validator_after_init(self, basic_worker_config):
        """Test that validator property works after on_start."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with patch.object(agent, "_initialize_m365_client"):
            agent.on_start()

        assert agent.validator is not None


# ============================================================================
# Unit Tests - M365 Client Property (60%)
# ============================================================================


class TestKnowledgeWorkerAgentM365Client:
    """Tests for M365 client property and initialization."""

    def test_m365_client_property_raises_when_not_initialized(self, basic_worker_config):
        """Test that accessing m365_client before on_start raises RuntimeError."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with pytest.raises(RuntimeError) as exc_info:
            _ = agent.m365_client

        assert "not initialized" in str(exc_info.value).lower()
        assert "on_start" in str(exc_info.value)

    def test_m365_client_initialization_handles_import_error(self, basic_worker_config):
        """Test that ImportError during M365 client init is handled.

        This test verifies that when the m365_client module cannot be imported
        (missing dependencies), the agent gracefully handles it by logging
        a warning and leaving _m365_client as None.
        """
        import builtins

        agent = KnowledgeWorkerAgent(basic_worker_config)
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "azure_haymaker.knowledge_worker.m365_client":
                raise ImportError("msgraph-sdk not installed")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            # Should not raise, just log warning
            agent._initialize_m365_client()

        assert agent._m365_client is None

    def test_m365_client_initialization_handles_value_error(self, basic_worker_config):
        """Test that ValueError during M365 client init is handled."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with patch(
            "azure_haymaker.knowledge_worker.m365_client.M365ClientFactory.create",
            side_effect=ValueError("Missing credentials"),
        ):
            # Should not raise, just log debug
            agent._initialize_m365_client()

        assert agent._m365_client is None


# ============================================================================
# Unit Tests - Recipient Management (60%)
# ============================================================================


class TestKnowledgeWorkerAgentRecipients:
    """Tests for recipient management methods."""

    def test_add_allowed_recipient(self, basic_worker_config):
        """Test adding a single allowed recipient."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        agent.add_allowed_recipient("user@test.onmicrosoft.com")

        assert "user@test.onmicrosoft.com" in agent._allowed_recipients

    def test_add_allowed_recipient_normalizes_to_lowercase(self, basic_worker_config):
        """Test that recipients are normalized to lowercase."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        agent.add_allowed_recipient("USER@TEST.ONMICROSOFT.COM")

        assert "user@test.onmicrosoft.com" in agent._allowed_recipients

    def test_add_allowed_recipient_strips_whitespace(self, basic_worker_config):
        """Test that whitespace is stripped from recipients."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        agent.add_allowed_recipient("  user@test.onmicrosoft.com  ")

        assert "user@test.onmicrosoft.com" in agent._allowed_recipients

    def test_add_allowed_recipients_batch(self, basic_worker_config):
        """Test adding multiple recipients at once."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        agent.add_allowed_recipients(["user1@test.com", "user2@test.com", "user3@test.com"])

        assert len(agent._allowed_recipients) == 3
        assert "user1@test.com" in agent._allowed_recipients
        assert "user2@test.com" in agent._allowed_recipients
        assert "user3@test.com" in agent._allowed_recipients

    def test_add_allowed_recipient_updates_validator(self, basic_worker_config):
        """Test that adding recipient also updates validator if initialized."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with patch.object(agent, "_initialize_m365_client"):
            agent.on_start()

        agent.add_allowed_recipient("new@test.onmicrosoft.com")

        assert "new@test.onmicrosoft.com" in agent._validator.allowed_upns

    def test_get_allowed_recipients(self, basic_worker_config):
        """Test getting list of allowed recipients."""
        agent = KnowledgeWorkerAgent(basic_worker_config)
        agent.add_allowed_recipients(["user1@test.com", "user2@test.com"])

        result = agent.get_allowed_recipients()

        assert len(result) == 2
        assert "user1@test.com" in result
        assert "user2@test.com" in result


# ============================================================================
# Unit Tests - validate_recipient (60%)
# ============================================================================


class TestKnowledgeWorkerAgentValidateRecipient:
    """Tests for validate_recipient method."""

    def test_validate_recipient_without_validator_returns_false(self, basic_worker_config):
        """Test that validation without initialized validator returns False."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        result = agent.validate_recipient("user@test.onmicrosoft.com")

        assert result is False

    def test_validate_recipient_internal_returns_true(self, basic_worker_config):
        """Test that internal recipient validation returns True."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with patch.object(agent, "_initialize_m365_client"):
            agent.on_start()

        # Internal recipient matches tenant domain
        result = agent.validate_recipient("user@test.onmicrosoft.com")

        assert result is True

    def test_validate_recipient_external_returns_false(self, basic_worker_config):
        """Test that external recipient validation returns False."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with patch.object(agent, "_initialize_m365_client"):
            agent.on_start()

        # External recipient doesn't match tenant domain
        result = agent.validate_recipient("user@external.com")

        assert result is False

    def test_validate_recipient_in_allowed_list_returns_true(self, basic_worker_config):
        """Test that recipient in allowed list returns True."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with patch.object(agent, "_initialize_m365_client"):
            agent.on_start()

        agent.add_allowed_recipient("special@external.com")

        result = agent.validate_recipient("special@external.com")

        assert result is True


# ============================================================================
# Unit Tests - get_worker_stats (60%)
# ============================================================================


class TestKnowledgeWorkerAgentStats:
    """Tests for get_worker_stats method."""

    def test_get_worker_stats_returns_expected_fields(self, basic_worker_config):
        """Test that worker stats contain expected fields."""
        agent = KnowledgeWorkerAgent(basic_worker_config)
        agent.add_allowed_recipients(["user1@test.com", "user2@test.com"])

        stats = agent.get_worker_stats()

        assert stats["worker_id"] == "kw-test-001"
        assert stats["display_name"] == "Test Worker"
        assert stats["department"] == "engineering"
        assert stats["persona"] == "engineering"
        assert stats["endpoint_type"] == "cli_container"
        assert stats["allowed_recipients_count"] == 2
        assert stats["m365_client_initialized"] is False
        assert stats["validator_initialized"] is False

    def test_get_worker_stats_reflects_initialized_state(self, basic_worker_config):
        """Test that stats reflect initialized state after on_start."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with patch.object(agent, "_initialize_m365_client"):
            agent.on_start()

        stats = agent.get_worker_stats()

        assert stats["validator_initialized"] is True


# ============================================================================
# Integration Tests (30%)
# ============================================================================


class TestKnowledgeWorkerAgentIntegration:
    """Integration tests for agent components working together."""

    def test_full_lifecycle_flow(self, basic_worker_config):
        """Test complete lifecycle: init -> start -> execute -> cleanup."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        # Mock external dependencies
        with (
            patch.object(agent, "_initialize_m365_client"),
            patch.object(agent.__class__.__bases__[0], "on_execute", return_value=0),
        ):
            # Start
            agent.on_start()
            assert agent._validator is not None

            # Execute
            exit_code = agent.on_execute()
            assert exit_code == 0

            # Cleanup
            agent.on_cleanup(exit_code)

    def test_recipient_management_with_validator(self, basic_worker_config):
        """Test recipient management integrates with validator."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with patch.object(agent, "_initialize_m365_client"):
            agent.on_start()

        # Add recipient after validator is initialized
        agent.add_allowed_recipient("colleague@test.onmicrosoft.com")

        # Validate through the agent
        assert agent.validate_recipient("colleague@test.onmicrosoft.com") is True
        assert agent.validate_recipient("external@gmail.com") is False

    def test_allowed_recipients_persisted_through_validator_init(self, basic_worker_config):
        """Test that recipients added before on_start are used in validator."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        # Add recipients before on_start
        agent.add_allowed_recipients(["pre1@test.com", "pre2@test.com"])

        with patch.object(agent, "_initialize_m365_client"):
            agent.on_start()

        # Pre-added recipients should work after validator init
        # Note: These won't validate since they don't match tenant domain
        # unless explicitly in allowed list
        stats = agent.get_worker_stats()
        assert stats["allowed_recipients_count"] == 2


# ============================================================================
# Async Operation Tests (30%)
# ============================================================================


class TestKnowledgeWorkerAgentAsyncOps:
    """Tests for async operations like send_email and create_calendar_event."""

    @pytest.mark.anyio
    async def test_send_email_requires_m365_client(self, basic_worker_config):
        """Test that send_email raises RuntimeError without M365 client."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with pytest.raises(RuntimeError) as exc_info:
            await agent.send_email(to=["user@test.com"], subject="Test", body="Hello")

        assert "M365 client not initialized" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_send_email_requires_recipients(self, basic_worker_config):
        """Test that send_email raises ValueError without recipients."""
        agent = KnowledgeWorkerAgent(basic_worker_config)
        agent._m365_client = MagicMock()  # Fake client

        with pytest.raises(ValueError, match="(?i)at least one recipient"):
            await agent.send_email(to=[], subject="Test", body="Hello")

    @pytest.mark.anyio
    async def test_create_calendar_event_requires_m365_client(self, basic_worker_config):
        """Test that create_calendar_event raises RuntimeError without M365 client."""
        agent = KnowledgeWorkerAgent(basic_worker_config)

        with pytest.raises(RuntimeError) as exc_info:
            await agent.create_calendar_event(
                subject="Meeting",
                start_time="2024-01-01T10:00:00Z",
                end_time="2024-01-01T11:00:00Z",
            )

        assert "M365 client not initialized" in str(exc_info.value)


# ============================================================================
# Edge Case Tests (10%)
# ============================================================================


class TestKnowledgeWorkerAgentEdgeCases:
    """Edge case tests for agent module."""

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
            agent = KnowledgeWorkerAgent(config)
            assert agent.worker_identity.persona == expected_enum, f"Failed for {persona_str}"

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
            agent = KnowledgeWorkerAgent(config)
            assert agent.worker_identity.endpoint_type == expected_enum

    def test_invalid_endpoint_type_defaults_to_cli_container(self):
        """Test that invalid endpoint type defaults to CLI_CONTAINER."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="test",
            persona="engineering",
            endpoint_type="invalid_type",
        )
        agent = KnowledgeWorkerAgent(config)

        assert agent.worker_identity.endpoint_type == EndpointType.CLI_CONTAINER

    def test_case_insensitive_persona(self):
        """Test that persona matching is case-insensitive."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="test",
            persona="ENGINEERING",  # Uppercase
        )
        agent = KnowledgeWorkerAgent(config)

        assert agent.worker_identity.persona == WorkerPersona.ENGINEERING

    def test_case_insensitive_endpoint_type(self):
        """Test that endpoint type matching is case-insensitive."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="test",
            persona="engineering",
            endpoint_type="CLOUD_PC",  # Uppercase
        )
        agent = KnowledgeWorkerAgent(config)

        assert agent.worker_identity.endpoint_type == EndpointType.CLOUD_PC

    def test_empty_worker_id(self):
        """Test handling of empty worker_id."""
        config = KnowledgeWorkerConfig(
            worker_id="",
            display_name="Test",
            department="test",
            persona="engineering",
        )
        agent = KnowledgeWorkerAgent(config)

        assert agent.worker_config.name == "knowledge-worker-"
        assert agent.worker_identity.worker_id == ""
