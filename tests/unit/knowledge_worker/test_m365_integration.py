"""Unit tests for knowledge_worker.m365_integration module.

Tests the m365_integration.py module which handles:
- M365ClientFactory for creating Graph API clients
- initialize_m365_client helper with error handling

Note: send_email and create_calendar_event are methods on KnowledgeWorkerAgent
(in core.py) and are tested in test_core.py, not here.

TDD Approach: These tests will FAIL until m365_integration.py is implemented.

Testing pyramid:
- 60% unit tests (factory, error handling)
- 30% integration tests (client creation)
- 10% E2E tests (tested in test_core.py via agent)
"""

from unittest.mock import MagicMock, patch

import pytest

# Import from refactored agent module location
from azure_haymaker.knowledge_worker.agent.m365_integration import (
    M365ClientFactory,
    initialize_m365_client,
)

# ============================================================================
# Unit Tests - Module __all__ Exports (60%)
# ============================================================================


class TestM365IntegrationModuleExports:
    """Tests for module __all__ exports."""

    def test_module_exports_initialize_m365_client(self):
        """Test that initialize_m365_client is in __all__."""
        from azure_haymaker.knowledge_worker.agent import m365_integration

        assert "initialize_m365_client" in m365_integration.__all__

    def test_module_exports_m365_client_factory(self):
        """Test that M365ClientFactory is in __all__."""
        from azure_haymaker.knowledge_worker.agent import m365_integration

        assert "M365ClientFactory" in m365_integration.__all__

    def test_module_has_exactly_five_exports(self):
        """Test that __all__ contains exactly what we expect."""
        from azure_haymaker.knowledge_worker.agent import m365_integration

        assert len(m365_integration.__all__) == 5
        expected_exports = {
            "M365ClientFactory",
            "initialize_m365_client",
            "validate_content",
            "send_email",
            "create_calendar_event",
        }
        assert set(m365_integration.__all__) == expected_exports


# ============================================================================
# Unit Tests - initialize_m365_client (60%)
# ============================================================================


class TestInitializeM365Client:
    """Tests for initialize_m365_client function."""

    def test_initialize_m365_client_returns_client(self):
        """Test that function returns a client instance."""
        with patch(
            "azure_haymaker.knowledge_worker.agent.m365_integration.M365ClientFactory"
        ) as mock_factory:
            mock_factory.create.return_value = MagicMock()

            client = initialize_m365_client(worker_id="kw-test-001")

            assert client is not None
            mock_factory.create.assert_called_once()

    def test_initialize_m365_client_handles_import_error(self):
        """Test that ImportError is handled gracefully."""
        with patch(
            "azure_haymaker.knowledge_worker.agent.m365_integration.M365ClientFactory.create",
            side_effect=ImportError("msgraph-sdk not installed"),
        ):
            client = initialize_m365_client(worker_id="kw-test-001")

            assert client is None

    def test_initialize_m365_client_handles_value_error(self):
        """Test that ValueError (missing credentials) is handled."""
        with patch(
            "azure_haymaker.knowledge_worker.agent.m365_integration.M365ClientFactory.create",
            side_effect=ValueError("Missing credentials"),
        ):
            client = initialize_m365_client(worker_id="kw-test-001")

            assert client is None

    def test_initialize_m365_client_handles_general_exception(self):
        """Test that general exceptions are handled."""
        with patch(
            "azure_haymaker.knowledge_worker.agent.m365_integration.M365ClientFactory.create",
            side_effect=Exception("Unexpected error"),
        ):
            client = initialize_m365_client(worker_id="kw-test-001")

            assert client is None

    def test_initialize_m365_client_logs_import_error(self, caplog):
        """Test that ImportError is logged with warning."""
        import logging

        with patch(
            "azure_haymaker.knowledge_worker.agent.m365_integration.M365ClientFactory.create",
            side_effect=ImportError("msgraph-sdk not installed"),
        ):
            with caplog.at_level(logging.WARNING):
                initialize_m365_client(worker_id="kw-test-001")

            assert any("Microsoft Graph SDK not installed" in rec.message for rec in caplog.records)

    def test_initialize_m365_client_logs_value_error_as_debug(self, caplog):
        """Test that ValueError is logged at debug level."""
        import logging

        with patch(
            "azure_haymaker.knowledge_worker.agent.m365_integration.M365ClientFactory.create",
            side_effect=ValueError("Missing credentials"),
        ):
            with caplog.at_level(logging.DEBUG):
                initialize_m365_client(worker_id="kw-test-001")

            assert any(rec.levelname == "DEBUG" for rec in caplog.records)


# ============================================================================
# Integration Tests - M365ClientFactory (30%)
# ============================================================================


class TestM365ClientFactory:
    """Tests for M365ClientFactory class."""

    def test_factory_create_returns_client(self):
        """Test that factory create returns a client instance."""
        with patch("azure.identity.ClientSecretCredential"), \
             patch("msgraph.GraphServiceClient") as mock_graph:
            mock_graph.return_value = MagicMock()

            client = M365ClientFactory.create(
                app_id="test-app-id",
                client_secret="test-secret",
                tenant_id="test-tenant-id"
            )

            assert client is not None
            mock_graph.assert_called_once()

    def test_factory_raises_value_error_without_credentials(self):
        """Test that factory raises ValueError when credentials missing."""
        with pytest.raises(ValueError, match="M365 credentials required"):
            M365ClientFactory.create()

    def test_factory_uses_environment_variables(self):
        """Test that factory falls back to environment variables."""
        with patch("azure_haymaker.knowledge_worker.agent.m365_integration.os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key: {
                "KW_APP_ID": "env-app-id",
                "KW_CLIENT_SECRET": "env-secret",
                "KW_TENANT_ID": "env-tenant-id"
            }.get(key)

            with patch("azure.identity.ClientSecretCredential"), \
                 patch("msgraph.GraphServiceClient") as mock_graph:
                mock_graph.return_value = MagicMock()

                client = M365ClientFactory.create()

                assert client is not None
