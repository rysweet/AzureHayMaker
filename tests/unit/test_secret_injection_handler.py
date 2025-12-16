"""Unit tests for Secret Injection Handler (TDD - These tests will FAIL until implementation is complete)

Testing pyramid: 60% unit tests
- Test RBAC propagation wait with exponential backoff
- Test secret injection to container app
- Test error handling and timeouts
- Test logging and retry logic

Philosophy: Zero-BS implementation, ruthless simplicity
"""

from unittest.mock import Mock, call, patch

import pytest
from azure.core.exceptions import HttpResponseError

# Import the module now that it's implemented
from azure_haymaker.orchestrator.secret_injection_handler import (
    RBACPropagationError,
    SecretInjectionError,
    SecretInjectionHandler,
)

# ============================================================================
# UNIT TESTS (60% of testing pyramid)
# ============================================================================


class TestSecretInjectionHandlerInit:
    """Test handler initialization"""

    def test_init_with_valid_params(self):
        """Test handler can be initialized with valid parameters"""
        handler = SecretInjectionHandler(
            subscription_id="test-sub-id",
            resource_group="test-rg",
        )

        assert handler.subscription_id == "test-sub-id"
        assert handler.resource_group == "test-rg"
        assert handler.max_retries == 5  # Default
        assert handler.initial_backoff_seconds == 10  # Default

    def test_init_with_custom_retry_params(self):
        """Test handler accepts custom retry parameters"""
        handler = SecretInjectionHandler(
            subscription_id="test-sub-id",
            resource_group="test-rg",
            max_retries=10,
            initial_backoff_seconds=5,
        )

        assert handler.max_retries == 10
        assert handler.initial_backoff_seconds == 5


class TestRBACPropagationWait:
    """Test RBAC propagation wait logic"""

    @patch("time.sleep")
    @patch("azure.identity.DefaultAzureCredential")
    def test_wait_for_rbac_propagation_success_immediate(self, mock_cred, mock_sleep):
        """Test RBAC wait succeeds immediately if permissions are ready"""
        handler = SecretInjectionHandler("sub-id", "rg")

        # Mock successful Key Vault access check
        with patch.object(handler, "_check_keyvault_access", return_value=True):
            result = handler.wait_for_rbac_propagation(
                keyvault_name="test-kv",
                identity_principal_id="test-principal-id",
            )

        assert result is True
        mock_sleep.assert_not_called()  # No wait needed

    @patch("time.sleep")
    @patch("azure.identity.DefaultAzureCredential")
    def test_wait_for_rbac_propagation_with_retries(self, mock_cred, mock_sleep):
        """Test RBAC wait retries with exponential backoff"""
        handler = SecretInjectionHandler(
            subscription_id="sub-id",
            resource_group="rg",
            max_retries=3,
            initial_backoff_seconds=2,
        )

        # Mock failing then succeeding access checks
        access_checks = [False, False, True]
        with patch.object(handler, "_check_keyvault_access", side_effect=access_checks):
            result = handler.wait_for_rbac_propagation(
                keyvault_name="test-kv",
                identity_principal_id="test-principal-id",
            )

        assert result is True
        # Should sleep twice with exponential backoff: 2s, 4s
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(2), call(4)])

    @patch("time.sleep")
    @patch("azure.identity.DefaultAzureCredential")
    def test_wait_for_rbac_propagation_timeout(self, mock_cred, mock_sleep):
        """Test RBAC wait raises error after max retries"""
        handler = SecretInjectionHandler(
            subscription_id="sub-id",
            resource_group="rg",
            max_retries=3,
            initial_backoff_seconds=2,
        )

        # Mock always failing access checks
        with (
            patch.object(handler, "_check_keyvault_access", return_value=False),
            pytest.raises(RBACPropagationError) as exc_info,
        ):
            handler.wait_for_rbac_propagation(
                keyvault_name="test-kv",
                identity_principal_id="test-principal-id",
            )

        assert "RBAC propagation timeout" in str(exc_info.value)
        assert "test-kv" in str(exc_info.value)
        assert mock_sleep.call_count == 3  # Slept 3 times before giving up


class TestKeyVaultAccessCheck:
    """Test Key Vault access verification"""

    @patch("azure_haymaker.orchestrator.secret_injection_handler.SecretClient")
    @patch("azure_haymaker.orchestrator.secret_injection_handler.DefaultAzureCredential")
    def test_check_keyvault_access_success(self, mock_cred, mock_secret_client):
        """Test successful Key Vault access check"""
        handler = SecretInjectionHandler("sub-id", "rg")

        # Mock successful secret list operation
        mock_client_instance = Mock()
        mock_client_instance.list_properties_of_secrets.return_value = iter([])
        mock_secret_client.return_value = mock_client_instance

        result = handler._check_keyvault_access("test-kv")

        assert result is True
        mock_client_instance.list_properties_of_secrets.assert_called_once()

    @patch("azure_haymaker.orchestrator.secret_injection_handler.SecretClient")
    @patch("azure_haymaker.orchestrator.secret_injection_handler.DefaultAzureCredential")
    def test_check_keyvault_access_forbidden(self, mock_cred, mock_secret_client):
        """Test Key Vault access check returns False on permission error"""
        handler = SecretInjectionHandler("sub-id", "rg")

        # Mock forbidden response (403)
        mock_client_instance = Mock()
        mock_error = HttpResponseError(message="Forbidden")
        mock_error.status_code = 403
        mock_client_instance.list_properties_of_secrets.return_value = iter(
            [Mock()]
        )  # Create an iterator

        # Make the iteration raise the error
        def raise_on_next():
            raise mock_error

        mock_client_instance.list_properties_of_secrets.return_value = Mock(
            __next__=lambda self: raise_on_next()
        )
        mock_secret_client.return_value = mock_client_instance

        result = handler._check_keyvault_access("test-kv")

        assert result is False  # Not ready yet, but not a fatal error

    @patch("azure_haymaker.orchestrator.secret_injection_handler.SecretClient")
    @patch("azure_haymaker.orchestrator.secret_injection_handler.DefaultAzureCredential")
    def test_check_keyvault_access_other_error(self, mock_cred, mock_secret_client):
        """Test Key Vault access check raises on unexpected errors"""
        handler = SecretInjectionHandler("sub-id", "rg")

        # Mock unexpected error (500)
        mock_client_instance = Mock()
        mock_error = HttpResponseError(message="Internal Server Error")
        mock_error.status_code = 500

        # Make the iteration raise the error
        def raise_on_next():
            raise mock_error

        mock_client_instance.list_properties_of_secrets.return_value = Mock(
            __next__=lambda self: raise_on_next()
        )
        mock_secret_client.return_value = mock_client_instance

        with pytest.raises(HttpResponseError):
            handler._check_keyvault_access("test-kv")


class TestSecretInjection:
    """Test secret injection to container app"""

    @patch("subprocess.run")
    def test_inject_secrets_to_container_app_success(self, mock_run):
        """Test successful secret injection to container app"""
        handler = SecretInjectionHandler("sub-id", "test-rg")

        # Mock successful az containerapp update command
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Container app updated successfully",
            stderr="",
        )

        result = handler.inject_secrets_to_container_app(
            container_app_name="orchestrator",
            keyvault_name="test-kv",
            secrets=[
                {"name": "ANTHROPIC_API_KEY", "keyvault_secret": "anthropic-api-key"},
                {"name": "AZURE_CLIENT_SECRET", "keyvault_secret": "azure-client-secret"},
            ],
        )

        assert result is True

        # Verify correct az command was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "az"
        assert call_args[1] == "containerapp"
        assert call_args[2] == "update"
        assert "--name" in call_args
        assert "orchestrator" in call_args
        assert "--resource-group" in call_args
        assert "test-rg" in call_args

    @patch("subprocess.run")
    def test_inject_secrets_with_retry_on_failure(self, mock_run):
        """Test secret injection retries on transient failures"""
        handler = SecretInjectionHandler(
            subscription_id="sub-id",
            resource_group="rg",
            max_retries=3,
        )

        # Mock failing then succeeding
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="Transient error"),
            Mock(returncode=1, stdout="", stderr="Transient error"),
            Mock(returncode=0, stdout="Success", stderr=""),
        ]

        result = handler.inject_secrets_to_container_app(
            container_app_name="orchestrator",
            keyvault_name="test-kv",
            secrets=[{"name": "TEST_SECRET", "keyvault_secret": "test-secret"}],
        )

        assert result is True
        assert mock_run.call_count == 3

    @patch("subprocess.run")
    def test_inject_secrets_fails_after_max_retries(self, mock_run):
        """Test secret injection raises error after max retries"""
        handler = SecretInjectionHandler(
            subscription_id="sub-id",
            resource_group="rg",
            max_retries=2,
        )

        # Mock always failing
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Persistent error",
        )

        with pytest.raises(SecretInjectionError) as exc_info:
            handler.inject_secrets_to_container_app(
                container_app_name="orchestrator",
                keyvault_name="test-kv",
                secrets=[{"name": "TEST_SECRET", "keyvault_secret": "test-secret"}],
            )

        assert "Failed to inject secrets" in str(exc_info.value)
        assert mock_run.call_count == 2  # max_retries


class TestEndToEndWorkflow:
    """Test complete secret injection workflow"""

    @patch("subprocess.run")
    @patch("time.sleep")
    @patch("azure.identity.DefaultAzureCredential")
    def test_complete_workflow_success(self, mock_cred, mock_sleep, mock_run):
        """Test complete workflow: wait for RBAC -> inject secrets"""
        handler = SecretInjectionHandler("sub-id", "rg", initial_backoff_seconds=1)

        # Mock RBAC check succeeding on second try
        access_checks = [False, True]

        # Mock successful secret injection
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        with patch.object(handler, "_check_keyvault_access", side_effect=access_checks):
            # Step 1: Wait for RBAC propagation
            rbac_ready = handler.wait_for_rbac_propagation(
                keyvault_name="test-kv",
                identity_principal_id="test-principal",
            )

            assert rbac_ready is True

            # Step 2: Inject secrets
            result = handler.inject_secrets_to_container_app(
                container_app_name="orchestrator",
                keyvault_name="test-kv",
                secrets=[
                    {"name": "ANTHROPIC_API_KEY", "keyvault_secret": "anthropic-api-key"},
                ],
            )

            assert result is True

        # Verify RBAC wait slept once
        assert mock_sleep.call_count == 1

        # Verify secret injection command was called
        mock_run.assert_called_once()


class TestLoggingAndMonitoring:
    """Test logging and monitoring functionality"""

    @patch("logging.Logger.info")
    @patch("time.sleep")
    @patch("azure.identity.DefaultAzureCredential")
    def test_logs_rbac_wait_progress(self, mock_cred, mock_sleep, mock_log_info):
        """Test handler logs RBAC wait progress"""
        handler = SecretInjectionHandler("sub-id", "rg", max_retries=2)

        # Mock access checks
        with patch.object(handler, "_check_keyvault_access", side_effect=[False, True]):
            handler.wait_for_rbac_propagation(
                keyvault_name="test-kv",
                identity_principal_id="test-principal",
            )

        # Verify progress was logged
        log_calls = [str(call) for call in mock_log_info.call_args_list]
        assert any("Waiting for RBAC propagation" in str(call) for call in log_calls)
        assert any("RBAC propagation complete" in str(call) for call in log_calls)

    @patch("logging.Logger.error")
    @patch("subprocess.run")
    def test_logs_injection_errors(self, mock_run, mock_log_error):
        """Test handler logs secret injection errors"""
        handler = SecretInjectionHandler("sub-id", "rg", max_retries=1)

        # Mock failing injection
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Permission denied",
        )

        with pytest.raises(SecretInjectionError):
            handler.inject_secrets_to_container_app(
                container_app_name="orchestrator",
                keyvault_name="test-kv",
                secrets=[{"name": "TEST", "keyvault_secret": "test"}],
            )

        # Verify error was logged
        mock_log_error.assert_called()
        log_message = str(mock_log_error.call_args)
        assert "Failed to inject secrets" in log_message


class TestErrorScenarios:
    """Test various error scenarios and edge cases"""

    def test_empty_secrets_list(self):
        """Test handler validates non-empty secrets list"""
        handler = SecretInjectionHandler("sub-id", "rg")

        with pytest.raises(ValueError, match="secrets list cannot be empty"):
            handler.inject_secrets_to_container_app(
                container_app_name="orchestrator",
                keyvault_name="test-kv",
                secrets=[],
            )

    def test_invalid_secret_format(self):
        """Test handler validates secret dictionary format"""
        handler = SecretInjectionHandler("sub-id", "rg")

        with pytest.raises(ValueError, match="Secret must have 'name' and 'keyvault_secret' keys"):
            handler.inject_secrets_to_container_app(
                container_app_name="orchestrator",
                keyvault_name="test-kv",
                secrets=[{"invalid": "format"}],
            )

    @patch("azure.identity.DefaultAzureCredential")
    def test_missing_keyvault_name(self, mock_cred):
        """Test handler validates Key Vault name is provided"""
        handler = SecretInjectionHandler("sub-id", "rg")

        with pytest.raises(ValueError, match="keyvault_name cannot be empty"):
            handler.wait_for_rbac_propagation(
                keyvault_name="",
                identity_principal_id="test-principal",
            )


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_handler():
    """Create a SecretInjectionHandler with mocked Azure clients"""
    with patch("azure.identity.DefaultAzureCredential"):
        return SecretInjectionHandler(
            subscription_id="test-sub-id",
            resource_group="test-rg",
            max_retries=3,
            initial_backoff_seconds=1,
        )


# ============================================================================
# NOTES FOR IMPLEMENTATION
# ============================================================================

"""
Implementation Checklist (what the code needs to do to pass these tests):

1. SecretInjectionHandler class:
   - __init__(subscription_id, resource_group, max_retries=5, initial_backoff_seconds=10)
   - wait_for_rbac_propagation(keyvault_name, identity_principal_id) -> bool
   - inject_secrets_to_container_app(container_app_name, keyvault_name, secrets) -> bool
   - _check_keyvault_access(keyvault_name) -> bool

2. Custom Exceptions:
   - RBACPropagationError
   - SecretInjectionError

3. Retry Logic:
   - Exponential backoff for RBAC wait (2^attempt * initial_backoff_seconds)
   - Linear retry for secret injection
   - Proper error handling and logging

4. Azure SDK Integration:
   - Use azure.identity.DefaultAzureCredential for authentication
   - Use azure.keyvault.secrets.SecretClient for Key Vault access checks
   - Use subprocess for az containerapp CLI commands

5. Validation:
   - Validate secrets list is not empty
   - Validate secret dictionary format
   - Validate required parameters

6. Logging:
   - Log RBAC wait progress
   - Log secret injection attempts
   - Log errors with context
"""
