"""Unit tests for knowledge_worker.core module.

Tests the core.py module which handles:
- KnowledgeWorkerAgent class implementation
- Agent lifecycle management (on_start, on_execute, on_cleanup)
- Recipient validation and management
- Worker statistics and state

TDD Approach: These tests will FAIL until core.py is implemented.

Testing pyramid:
- 60% unit tests (agent methods, state management)
- 30% integration tests (lifecycle flows)
- 10% E2E tests (complete agent workflows)
"""

from unittest.mock import MagicMock, patch

import pytest

# Import from refactored agent module location
from azure_haymaker.knowledge_worker.agent.config import KnowledgeWorkerConfig
from azure_haymaker.knowledge_worker.agent.core import KnowledgeWorkerAgent
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerConfig,
    WorkerIdentity,
    WorkerPersona,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def basic_config():
    """Create a basic worker configuration for testing."""
    return KnowledgeWorkerConfig(
        worker_id="kw-test-001",
        display_name="Test Worker",
        department="engineering",
        persona="engineering",
        tenant_domain="test.onmicrosoft.com",
        team_id="team-123",
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
        team_ids=["team-1"],
    )


# ============================================================================
# Unit Tests - KnowledgeWorkerAgent Initialization (60%)
# ============================================================================


class TestKnowledgeWorkerAgentInitialization:
    """Tests for KnowledgeWorkerAgent initialization."""

    def test_agent_initialization_with_config(self, basic_config):
        """Test basic agent initialization with config."""
        agent = KnowledgeWorkerAgent(basic_config)

        assert agent.worker_config == basic_config
        assert agent._m365_client is None
        assert agent._allowed_recipients == set()
        assert agent._validator is None

    def test_agent_initialization_with_identity(self, basic_config, mock_worker_identity):
        """Test agent initialization with pre-built identity."""
        agent = KnowledgeWorkerAgent(basic_config, worker_identity=mock_worker_identity)

        assert agent.worker_identity == mock_worker_identity

    def test_agent_initialization_builds_identity_from_config(self, basic_config):
        """Test that identity is built from config when not provided."""
        agent = KnowledgeWorkerAgent(basic_config)

        assert agent.worker_identity.worker_id == "kw-test-001"
        assert agent.worker_identity.display_name == "Test Worker"
        assert agent.worker_identity.department == "engineering"

    def test_agent_initialization_with_activity_config(self, basic_config):
        """Test agent initialization with activity configuration."""
        activity_config = WorkerConfig()
        agent = KnowledgeWorkerAgent(basic_config, activity_config=activity_config)

        assert agent.activity_config == activity_config

    def test_agent_initialization_default_activity_config(self, basic_config):
        """Test that default activity config is created if not provided."""
        agent = KnowledgeWorkerAgent(basic_config)

        assert agent.activity_config is not None
        assert isinstance(agent.activity_config, WorkerConfig)


# ============================================================================
# Unit Tests - Module __all__ Exports (60%)
# ============================================================================


class TestCoreModuleExports:
    """Tests for module __all__ exports."""

    def test_core_module_exports_knowledge_worker_agent(self):
        """Test that KnowledgeWorkerAgent is in __all__."""
        from azure_haymaker.knowledge_worker import core

        assert "KnowledgeWorkerAgent" in core.__all__

    def test_core_module_has_exactly_one_export(self):
        """Test that __all__ contains exactly what we expect."""
        from azure_haymaker.knowledge_worker import core

        assert len(core.__all__) == 1


# ============================================================================
# Unit Tests - Agent Properties (60%)
# ============================================================================


class TestKnowledgeWorkerAgentProperties:
    """Tests for agent property accessors."""

    def test_validator_property_raises_when_not_initialized(self, basic_config):
        """Test that accessing validator before on_start raises RuntimeError."""
        agent = KnowledgeWorkerAgent(basic_config)

        with pytest.raises(RuntimeError, match=r"(?i)not initialized.*on_start"):
            _ = agent.validator

    def test_m365_client_property_raises_when_not_initialized(self, basic_config):
        """Test that accessing m365_client before on_start raises RuntimeError."""
        agent = KnowledgeWorkerAgent(basic_config)

        with pytest.raises(RuntimeError, match=r"(?i)not initialized.*on_start"):
            _ = agent.m365_client

    def test_get_config_returns_worker_config(self, basic_config):
        """Test that get_config returns the worker configuration."""
        agent = KnowledgeWorkerAgent(basic_config)

        result = agent.get_config()

        assert result == basic_config


# ============================================================================
# Unit Tests - Lifecycle Methods (60%)
# ============================================================================


class TestKnowledgeWorkerAgentLifecycle:
    """Tests for agent lifecycle methods."""

    def test_on_start_initializes_validator(self, basic_config):
        """Test that on_start initializes the validator."""
        agent = KnowledgeWorkerAgent(basic_config)

        # Mock M365 initialization to avoid dependency
        with patch(
            "azure_haymaker.knowledge_worker.agent.core.initialize_m365_client"
        ) as mock_init:
            mock_init.return_value = MagicMock()
            agent.on_start()

        assert agent._validator is not None
        assert agent._validator.tenant_domain == "test.onmicrosoft.com"

    def test_on_start_initializes_m365_client(self, basic_config):
        """Test that on_start initializes M365 client."""
        agent = KnowledgeWorkerAgent(basic_config)

        with patch(
            "azure_haymaker.knowledge_worker.agent.core.initialize_m365_client"
        ) as mock_init:
            mock_client = MagicMock()
            mock_init.return_value = mock_client

            agent.on_start()

        assert agent._m365_client == mock_client

    def test_on_start_with_empty_tenant_domain_raises_value_error(self):
        """Test on_start with missing tenant domain raises ValueError."""
        config = KnowledgeWorkerConfig(
            worker_id="kw-test",
            display_name="Test",
            department="eng",
            persona="engineering",
            tenant_domain="",  # Empty
        )
        agent = KnowledgeWorkerAgent(config)

        with patch("azure_haymaker.knowledge_worker.agent.core.initialize_m365_client"), \
             pytest.raises(ValueError, match="tenant_domain is required"):
            agent.on_start()

    def test_on_cleanup_disconnects_m365_client(self, basic_config):
        """Test that on_cleanup clears M365 client."""
        agent = KnowledgeWorkerAgent(basic_config)
        agent._m365_client = MagicMock()  # Simulate initialized client

        agent.on_cleanup(0)

        assert agent._m365_client is None

    def test_on_execute_calls_parent_implementation(self, basic_config):
        """Test that on_execute delegates to parent class."""
        agent = KnowledgeWorkerAgent(basic_config)

        with patch.object(
            agent.__class__.__bases__[0], "on_execute", return_value=0
        ) as mock_execute:
            result = agent.on_execute()

            mock_execute.assert_called_once()
            assert result == 0


# ============================================================================
# Unit Tests - Recipient Management (60%)
# ============================================================================


class TestKnowledgeWorkerAgentRecipients:
    """Tests for recipient management methods."""

    def test_add_allowed_recipient(self, basic_config):
        """Test adding a single allowed recipient."""
        agent = KnowledgeWorkerAgent(basic_config)

        agent.add_allowed_recipient("user@test.onmicrosoft.com")

        assert "user@test.onmicrosoft.com" in agent._allowed_recipients

    def test_add_allowed_recipient_normalizes_to_lowercase(self, basic_config):
        """Test that recipients are normalized to lowercase."""
        agent = KnowledgeWorkerAgent(basic_config)

        agent.add_allowed_recipient("USER@TEST.ONMICROSOFT.COM")

        assert "user@test.onmicrosoft.com" in agent._allowed_recipients

    def test_add_allowed_recipient_strips_whitespace(self, basic_config):
        """Test that whitespace is stripped from recipients."""
        agent = KnowledgeWorkerAgent(basic_config)

        agent.add_allowed_recipient("  user@test.onmicrosoft.com  ")

        assert "user@test.onmicrosoft.com" in agent._allowed_recipients

    def test_add_allowed_recipients_batch(self, basic_config):
        """Test adding multiple recipients at once."""
        agent = KnowledgeWorkerAgent(basic_config)

        agent.add_allowed_recipients(["user1@test.com", "user2@test.com", "user3@test.com"])

        assert len(agent._allowed_recipients) == 3

    def test_add_allowed_recipient_updates_validator_if_initialized(self, basic_config):
        """Test that adding recipient updates validator if initialized."""
        agent = KnowledgeWorkerAgent(basic_config)

        with patch("azure_haymaker.knowledge_worker.core.initialize_m365_client"):
            agent.on_start()

        agent.add_allowed_recipient("new@test.onmicrosoft.com")

        assert "new@test.onmicrosoft.com" in agent._validator.allowed_upns

    def test_get_allowed_recipients(self, basic_config):
        """Test getting list of allowed recipients."""
        agent = KnowledgeWorkerAgent(basic_config)
        agent.add_allowed_recipients(["user1@test.com", "user2@test.com"])

        result = agent.get_allowed_recipients()

        assert len(result) == 2
        assert "user1@test.com" in result

    def test_validate_recipient_without_validator_returns_false(self, basic_config):
        """Test that validation without initialized validator returns False."""
        agent = KnowledgeWorkerAgent(basic_config)

        result = agent.validate_recipient("user@test.onmicrosoft.com")

        assert result is False

    def test_validate_recipient_internal_returns_true(self, basic_config):
        """Test that internal recipient validation returns True."""
        agent = KnowledgeWorkerAgent(basic_config)

        with patch("azure_haymaker.knowledge_worker.core.initialize_m365_client"):
            agent.on_start()

        result = agent.validate_recipient("user@test.onmicrosoft.com")

        assert result is True

    def test_validate_recipient_external_returns_false(self, basic_config):
        """Test that external recipient validation returns False."""
        agent = KnowledgeWorkerAgent(basic_config)

        with patch("azure_haymaker.knowledge_worker.core.initialize_m365_client"):
            agent.on_start()

        result = agent.validate_recipient("user@external.com")

        assert result is False


# ============================================================================
# Unit Tests - Worker Statistics (60%)
# ============================================================================


class TestKnowledgeWorkerAgentStatistics:
    """Tests for get_worker_stats method."""

    def test_get_worker_stats_returns_expected_fields(self, basic_config):
        """Test that worker stats contain expected fields."""
        agent = KnowledgeWorkerAgent(basic_config)
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

    def test_get_worker_stats_reflects_initialized_state(self, basic_config):
        """Test that stats reflect initialized state after on_start."""
        agent = KnowledgeWorkerAgent(basic_config)

        with patch("azure_haymaker.knowledge_worker.core.initialize_m365_client"):
            agent.on_start()

        stats = agent.get_worker_stats()

        assert stats["validator_initialized"] is True


# ============================================================================
# Integration Tests (30%)
# ============================================================================


class TestKnowledgeWorkerAgentIntegration:
    """Integration tests for agent lifecycle and operations."""

    def test_full_lifecycle_flow(self, basic_config):
        """Test complete lifecycle: init -> start -> execute -> cleanup."""
        agent = KnowledgeWorkerAgent(basic_config)

        # Mock external dependencies
        with patch("azure_haymaker.knowledge_worker.core.initialize_m365_client"), \
             patch.object(agent.__class__.__bases__[0], "on_execute", return_value=0):
            # Start
            agent.on_start()
            assert agent._validator is not None

            # Execute
            exit_code = agent.on_execute()
            assert exit_code == 0

            # Cleanup
            agent.on_cleanup(exit_code)

    def test_recipient_management_with_validator(self, basic_config):
        """Test recipient management integrates with validator."""
        agent = KnowledgeWorkerAgent(basic_config)

        with patch("azure_haymaker.knowledge_worker.core.initialize_m365_client"):
            agent.on_start()

        # Add recipient after validator is initialized
        agent.add_allowed_recipient("colleague@test.onmicrosoft.com")

        # Validate through the agent
        assert agent.validate_recipient("colleague@test.onmicrosoft.com") is True
        assert agent.validate_recipient("external@gmail.com") is False

    def test_allowed_recipients_persisted_through_validator_init(self, basic_config):
        """Test that recipients added before on_start are used in validator."""
        agent = KnowledgeWorkerAgent(basic_config)

        # Add recipients before on_start
        agent.add_allowed_recipients(["pre1@test.com", "pre2@test.com"])

        with patch("azure_haymaker.knowledge_worker.core.initialize_m365_client"):
            agent.on_start()

        stats = agent.get_worker_stats()
        assert stats["allowed_recipients_count"] == 2

    def test_agent_with_custom_identity_and_activity_config(self, basic_config, mock_worker_identity):
        """Test agent with custom identity and activity config."""
        activity_config = WorkerConfig()
        agent = KnowledgeWorkerAgent(
            basic_config,
            worker_identity=mock_worker_identity,
            activity_config=activity_config,
        )

        assert agent.worker_identity == mock_worker_identity
        assert agent.activity_config == activity_config


# ============================================================================
# Edge Case Tests (10%)
# ============================================================================


class TestKnowledgeWorkerAgentEdgeCases:
    """Edge case tests for core agent functionality."""

    def test_agent_with_empty_worker_id(self):
        """Test agent initialization with empty worker_id."""
        config = KnowledgeWorkerConfig(
            worker_id="",
            display_name="Test",
            department="test",
            persona="engineering",
        )
        agent = KnowledgeWorkerAgent(config)

        assert agent.worker_identity.worker_id == ""

    def test_multiple_on_start_calls_idempotent(self, basic_config):
        """Test that multiple on_start calls don't break state."""
        agent = KnowledgeWorkerAgent(basic_config)

        with patch("azure_haymaker.knowledge_worker.core.initialize_m365_client"):
            agent.on_start()
            first_validator = agent._validator

            # Call again
            agent.on_start()
            second_validator = agent._validator

        # Should have different validators (re-initialized)
        assert first_validator is not None
        assert second_validator is not None

    def test_on_cleanup_with_no_m365_client(self, basic_config):
        """Test on_cleanup when M365 client was never initialized."""
        agent = KnowledgeWorkerAgent(basic_config)

        # Should not raise
        agent.on_cleanup(0)

        assert agent._m365_client is None

    def test_validator_property_after_initialization(self, basic_config):
        """Test validator property returns validator after on_start."""
        agent = KnowledgeWorkerAgent(basic_config)

        with patch("azure_haymaker.knowledge_worker.core.initialize_m365_client"):
            agent.on_start()

        # Should not raise
        validator = agent.validator
        assert validator is not None

    def test_m365_client_property_after_initialization(self, basic_config):
        """Test m365_client property returns client after on_start."""
        agent = KnowledgeWorkerAgent(basic_config)

        mock_client = MagicMock()
        with patch(
            "azure_haymaker.knowledge_worker.core.initialize_m365_client",
            return_value=mock_client,
        ):
            agent.on_start()

        # Should not raise
        client = agent.m365_client
        assert client == mock_client

    def test_add_recipient_to_uninitialized_validator(self, basic_config):
        """Test adding recipient before validator initialization."""
        agent = KnowledgeWorkerAgent(basic_config)

        # Should not raise
        agent.add_allowed_recipient("user@test.com")

        assert "user@test.com" in agent._allowed_recipients

    def test_duplicate_recipients_not_added_twice(self, basic_config):
        """Test that duplicate recipients are not added multiple times (set behavior)."""
        agent = KnowledgeWorkerAgent(basic_config)

        agent.add_allowed_recipient("user@test.com")
        agent.add_allowed_recipient("user@test.com")
        agent.add_allowed_recipient("user@test.com")

        assert len(agent._allowed_recipients) == 1
