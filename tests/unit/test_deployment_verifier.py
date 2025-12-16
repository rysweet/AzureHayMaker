"""Unit tests for Deployment Verifier (TDD - These tests will FAIL until implementation is complete)

Testing pyramid: 60% unit tests
- Test container health checks
- Test API endpoint verification
- Test RBAC permission checks
- Test error scenarios

Philosophy: Zero-BS implementation, ruthless simplicity
"""

from unittest.mock import Mock, patch

import pytest
import requests

# Import the module now that it's implemented
from azure_haymaker.orchestrator.deployment_verifier import (
    APIEndpointError,
    ContainerHealthError,
    DeploymentVerifier,
    RBACPermissionError,
)

# ============================================================================
# UNIT TESTS (60% of testing pyramid)
# ============================================================================


class TestDeploymentVerifierInit:
    """Test verifier initialization"""

    def test_init_with_valid_params(self):
        """Test verifier can be initialized with valid parameters"""
        verifier = DeploymentVerifier(
            subscription_id="test-sub-id",
            resource_group="test-rg",
            orchestrator_url="https://test-orchestrator.azurecontainerapps.io",
        )

        assert verifier.subscription_id == "test-sub-id"
        assert verifier.resource_group == "test-rg"
        assert verifier.orchestrator_url == "https://test-orchestrator.azurecontainerapps.io"
        assert verifier.timeout_seconds == 300  # Default 5 minutes

    def test_init_with_custom_timeout(self):
        """Test verifier accepts custom timeout"""
        verifier = DeploymentVerifier(
            subscription_id="test-sub-id",
            resource_group="test-rg",
            orchestrator_url="https://test.com",
            timeout_seconds=600,
        )

        assert verifier.timeout_seconds == 600


class TestContainerHealthChecks:
    """Test container health verification"""

    @patch("subprocess.run")
    def test_check_container_health_success(self, mock_run):
        """Test successful container health check"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test.com")

        # Mock az containerapp show command returning healthy status
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"properties":{"runningStatus":"Running","provisioningState":"Succeeded"}}',
            stderr="",
        )

        result = verifier.check_container_health("orchestrator")

        assert result is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_check_container_health_not_running(self, mock_run):
        """Test container health check fails when container is not running"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test.com")

        # Mock container in stopped state
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"properties":{"runningStatus":"Stopped","provisioningState":"Succeeded"}}',
            stderr="",
        )

        with pytest.raises(ContainerHealthError) as exc_info:
            verifier.check_container_health("orchestrator")

        assert "Container is not running" in str(exc_info.value)

    @patch("subprocess.run")
    def test_check_container_health_provisioning_failed(self, mock_run):
        """Test container health check fails when provisioning failed"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test.com")

        # Mock container with failed provisioning
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"properties":{"runningStatus":"Running","provisioningState":"Failed"}}',
            stderr="",
        )

        with pytest.raises(ContainerHealthError) as exc_info:
            verifier.check_container_health("orchestrator")

        assert "Provisioning failed" in str(exc_info.value)

    @patch("subprocess.run")
    def test_check_container_health_not_found(self, mock_run):
        """Test container health check fails when container doesn't exist"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test.com")

        # Mock container not found
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Container app 'orchestrator' not found",
        )

        with pytest.raises(ContainerHealthError) as exc_info:
            verifier.check_container_health("orchestrator")

        assert "not found" in str(exc_info.value).lower()

    @patch("time.sleep")
    @patch("subprocess.run")
    def test_check_container_health_waits_for_ready(self, mock_run, mock_sleep):
        """Test container health check waits for container to become ready"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test.com")

        # Mock container transitioning from starting to running
        mock_run.side_effect = [
            Mock(
                returncode=0,
                stdout='{"properties":{"runningStatus":"Starting","provisioningState":"InProgress"}}',
                stderr="",
            ),
            Mock(
                returncode=0,
                stdout='{"properties":{"runningStatus":"Starting","provisioningState":"InProgress"}}',
                stderr="",
            ),
            Mock(
                returncode=0,
                stdout='{"properties":{"runningStatus":"Running","provisioningState":"Succeeded"}}',
                stderr="",
            ),
        ]

        result = verifier.check_container_health(
            "orchestrator", wait_ready=True, max_wait_seconds=60
        )

        assert result is True
        assert mock_run.call_count == 3
        assert mock_sleep.call_count == 2  # Slept twice waiting


class TestAPIEndpointVerification:
    """Test API endpoint verification"""

    @patch("requests.get")
    def test_verify_api_endpoint_success(self, mock_get):
        """Test successful API endpoint verification"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock successful /api/status response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running"}
        mock_get.return_value = mock_response

        result = verifier.verify_api_endpoint("/api/status")

        assert result is True
        mock_get.assert_called_once_with(
            "https://test-orchestrator.com/api/status",
            timeout=30,
        )

    @patch("requests.get")
    def test_verify_api_endpoint_not_found(self, mock_get):
        """Test API endpoint verification fails on 404"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        with pytest.raises(APIEndpointError) as exc_info:
            verifier.verify_api_endpoint("/api/missing")

        assert "404" in str(exc_info.value)
        assert "/api/missing" in str(exc_info.value)

    @patch("requests.get")
    def test_verify_api_endpoint_timeout(self, mock_get):
        """Test API endpoint verification fails on timeout"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock timeout
        mock_get.side_effect = requests.Timeout("Request timed out")

        with pytest.raises(APIEndpointError) as exc_info:
            verifier.verify_api_endpoint("/api/status")

        assert "timeout" in str(exc_info.value).lower()

    @patch("requests.get")
    def test_verify_multiple_api_endpoints(self, mock_get):
        """Test verifying multiple API endpoints"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock successful responses for all endpoints
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        endpoints = [
            "/api/status",
            "/api/resources",
            "/api/scenarios",
            "/api/analytics",
        ]

        results = verifier.verify_multiple_endpoints(endpoints)

        assert all(results.values())
        assert len(results) == 4
        assert mock_get.call_count == 4

    @patch("requests.get")
    def test_verify_api_endpoint_with_expected_response(self, mock_get):
        """Test API verification with expected response validation"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "running",
            "version": "1.0.0",
        }
        mock_get.return_value = mock_response

        result = verifier.verify_api_endpoint(
            "/api/status",
            expected_fields=["status", "version"],
        )

        assert result is True

    @patch("requests.get")
    def test_verify_api_endpoint_missing_expected_field(self, mock_get):
        """Test API verification fails when expected field is missing"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock response missing 'version' field
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running"}
        mock_get.return_value = mock_response

        with pytest.raises(APIEndpointError) as exc_info:
            verifier.verify_api_endpoint(
                "/api/status",
                expected_fields=["status", "version"],
            )

        assert "Missing expected field" in str(exc_info.value)
        assert "version" in str(exc_info.value)


class TestRBACPermissionChecks:
    """Test RBAC permission verification"""

    @patch("subprocess.run")
    def test_verify_rbac_permissions_success(self, mock_run):
        """Test successful RBAC permission verification"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test.com")

        # Mock az role assignment list command
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[{"roleDefinitionName":"Key Vault Secrets User","principalId":"test-principal-id"}]',
            stderr="",
        )

        result = verifier.verify_rbac_permissions(
            principal_id="test-principal-id",
            resource_id="/subscriptions/test/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/test-kv",
            required_role="Key Vault Secrets User",
        )

        assert result is True

    @patch("subprocess.run")
    def test_verify_rbac_permissions_missing(self, mock_run):
        """Test RBAC verification fails when permission is missing"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test.com")

        # Mock empty role assignment list
        mock_run.return_value = Mock(
            returncode=0,
            stdout="[]",
            stderr="",
        )

        with pytest.raises(RBACPermissionError) as exc_info:
            verifier.verify_rbac_permissions(
                principal_id="test-principal-id",
                resource_id="/subscriptions/test/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/test-kv",
                required_role="Key Vault Secrets User",
            )

        assert "Missing required role assignment" in str(exc_info.value)
        assert "Key Vault Secrets User" in str(exc_info.value)

    @patch("subprocess.run")
    def test_verify_rbac_permissions_wrong_role(self, mock_run):
        """Test RBAC verification fails when wrong role is assigned"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test.com")

        # Mock role assignment with different role
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[{"roleDefinitionName":"Reader","principalId":"test-principal-id"}]',
            stderr="",
        )

        with pytest.raises(RBACPermissionError) as exc_info:
            verifier.verify_rbac_permissions(
                principal_id="test-principal-id",
                resource_id="/subscriptions/test/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/test-kv",
                required_role="Key Vault Secrets User",
            )

        assert "Missing required role assignment" in str(exc_info.value)


class TestCompleteDeploymentVerification:
    """Test complete deployment verification workflow"""

    @patch("requests.get")
    @patch("subprocess.run")
    def test_verify_complete_deployment_success(self, mock_run, mock_get):
        """Test complete deployment verification passes all checks"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock container health check
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"properties":{"runningStatus":"Running","provisioningState":"Succeeded"}}',
            stderr="",
        )

        # Mock API endpoint checks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running"}
        mock_get.return_value = mock_response

        verification_result = verifier.verify_complete_deployment(
            container_app_name="orchestrator",
            api_endpoints=["/api/status", "/api/resources"],
        )

        assert verification_result["success"] is True
        assert verification_result["container_healthy"] is True
        assert len(verification_result["api_endpoints_verified"]) == 2
        assert all(verification_result["api_endpoints_verified"].values())

    @patch("requests.get")
    @patch("subprocess.run")
    def test_verify_complete_deployment_partial_failure(self, mock_run, mock_get):
        """Test complete deployment verification with partial failures"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock container health check (success)
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"properties":{"runningStatus":"Running","provisioningState":"Succeeded"}}',
            stderr="",
        )

        # Mock API endpoint checks (one fails)
        def mock_get_side_effect(url, timeout):
            if "/api/status" in url:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "running"}
                return mock_response
            else:
                mock_response = Mock()
                mock_response.status_code = 404
                return mock_response

        mock_get.side_effect = mock_get_side_effect

        verification_result = verifier.verify_complete_deployment(
            container_app_name="orchestrator",
            api_endpoints=["/api/status", "/api/missing"],
        )

        assert verification_result["success"] is False
        assert verification_result["container_healthy"] is True
        assert verification_result["api_endpoints_verified"]["/api/status"] is True
        assert verification_result["api_endpoints_verified"]["/api/missing"] is False


class TestErrorHandlingAndRetry:
    """Test error handling and retry logic"""

    @patch("time.sleep")
    @patch("requests.get")
    def test_verify_api_endpoint_with_retry(self, mock_get, mock_sleep):
        """Test API verification retries on transient failures"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock failing then succeeding
        mock_responses = [
            Mock(status_code=503, text="Service Unavailable"),
            Mock(status_code=503, text="Service Unavailable"),
            Mock(status_code=200, json=lambda: {"status": "running"}),
        ]
        mock_get.side_effect = mock_responses

        result = verifier.verify_api_endpoint("/api/status", max_retries=3, retry_delay=2)

        assert result is True
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2  # Slept twice before success

    @patch("requests.get")
    def test_verify_api_endpoint_fails_after_max_retries(self, mock_get):
        """Test API verification fails after max retries"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock always failing
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_get.return_value = mock_response

        with pytest.raises(APIEndpointError) as exc_info:
            verifier.verify_api_endpoint("/api/status", max_retries=2)

        assert "503" in str(exc_info.value)
        assert mock_get.call_count == 2


class TestLoggingAndReporting:
    """Test logging and reporting functionality"""

    @patch("logging.Logger.info")
    @patch("subprocess.run")
    def test_logs_verification_progress(self, mock_run, mock_log_info):
        """Test verifier logs verification progress"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test.com")

        # Mock successful health check
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"properties":{"runningStatus":"Running","provisioningState":"Succeeded"}}',
            stderr="",
        )

        verifier.check_container_health("orchestrator")

        # Verify progress was logged
        log_calls = [str(call) for call in mock_log_info.call_args_list]
        assert any("Checking container health" in str(call) for call in log_calls)

    @patch("logging.Logger.error")
    @patch("subprocess.run")
    def test_logs_verification_errors(self, mock_run, mock_log_error):
        """Test verifier logs verification errors"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test.com")

        # Mock container not found
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Container not found",
        )

        with pytest.raises(ContainerHealthError):
            verifier.check_container_health("orchestrator")

        # Verify error was logged
        mock_log_error.assert_called()

    @patch("requests.get")
    @patch("subprocess.run")
    def test_generate_verification_report(self, mock_run, mock_get):
        """Test generation of verification report"""
        verifier = DeploymentVerifier("sub-id", "rg", "https://test-orchestrator.com")

        # Mock successful checks
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"properties":{"runningStatus":"Running","provisioningState":"Succeeded"}}',
            stderr="",
        )
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running"}
        mock_get.return_value = mock_response

        report = verifier.generate_verification_report(
            container_app_name="orchestrator",
            api_endpoints=["/api/status"],
        )

        assert "container_app_name" in report
        assert "verification_time" in report
        assert "checks_passed" in report
        assert "checks_failed" in report
        assert report["checks_passed"] >= 2  # Container + API


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_verifier():
    """Create a DeploymentVerifier with default test configuration"""
    return DeploymentVerifier(
        subscription_id="test-sub-id",
        resource_group="test-rg",
        orchestrator_url="https://test-orchestrator.azurecontainerapps.io",
        timeout_seconds=300,
    )


# ============================================================================
# NOTES FOR IMPLEMENTATION
# ============================================================================

"""
Implementation Checklist (what the code needs to do to pass these tests):

1. DeploymentVerifier class:
   - __init__(subscription_id, resource_group, orchestrator_url, timeout_seconds=300)
   - check_container_health(container_app_name, wait_ready=False, max_wait_seconds=300) -> bool
   - verify_api_endpoint(endpoint, expected_fields=None, max_retries=0, retry_delay=5) -> bool
   - verify_multiple_endpoints(endpoints) -> Dict[str, bool]
   - verify_rbac_permissions(principal_id, resource_id, required_role) -> bool
   - verify_complete_deployment(container_app_name, api_endpoints) -> Dict
   - generate_verification_report(container_app_name, api_endpoints) -> Dict

2. Custom Exceptions:
   - VerificationError (base)
   - ContainerHealthError
   - APIEndpointError
   - RBACPermissionError

3. Container Health Checks:
   - Use az containerapp show to get status
   - Parse JSON response for runningStatus and provisioningState
   - Wait for container to become ready if wait_ready=True

4. API Endpoint Verification:
   - Use requests.get() to check endpoints
   - Validate response status codes
   - Validate expected response fields
   - Retry on transient failures (503, timeouts)

5. RBAC Permission Checks:
   - Use az role assignment list to check permissions
   - Validate required role is assigned to principal

6. Logging:
   - Log verification progress
   - Log errors with context
   - Generate structured verification reports
"""
