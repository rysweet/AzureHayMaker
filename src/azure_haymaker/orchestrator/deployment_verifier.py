"""Deployment Verifier for Azure Container Apps

Verifies deployment health before marking deployment successful.

Philosophy:
- Zero-BS implementation: Every function works
- Ruthless simplicity: Standard library + requests only
- Clear error handling with comprehensive logging
- Retry logic for transient failures

Public API:
    DeploymentVerifier: Main verifier class
    VerificationError: Base verification exception
    ContainerHealthError: Container health check failure
    APIEndpointError: API endpoint verification failure
    RBACPermissionError: RBAC permission check failure
"""

import json
import logging
import subprocess
import time
from datetime import datetime

import requests

__all__ = [
    "DeploymentVerifier",
    "VerificationError",
    "ContainerHealthError",
    "APIEndpointError",
    "RBACPermissionError",
]

# Configure logging
logger = logging.getLogger(__name__)


class VerificationError(Exception):
    """Base exception for verification failures"""

    pass


class ContainerHealthError(VerificationError):
    """Raised when container health check fails"""

    pass


class APIEndpointError(VerificationError):
    """Raised when API endpoint verification fails"""

    pass


class RBACPermissionError(VerificationError):
    """Raised when RBAC permission check fails"""

    pass


class DeploymentVerifier:
    """Verifies deployment health for Azure Container Apps

    Features:
    - Container health checks
    - API endpoint verification with retry
    - RBAC permission checks
    - Verification report generation
    """

    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        orchestrator_url: str,
        timeout_seconds: int = 300,
    ):
        """Initialize deployment verifier

        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            orchestrator_url: Orchestrator base URL
            timeout_seconds: Overall timeout for verification (default 5 minutes)
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def check_container_health(
        self,
        container_app_name: str,
        wait_ready: bool = False,
        max_wait_seconds: int = 300,
    ) -> bool:
        """Check container app health status

        Args:
            container_app_name: Container app name
            wait_ready: If True, wait for container to become ready
            max_wait_seconds: Maximum time to wait for container to be ready

        Returns:
            True if container is healthy

        Raises:
            ContainerHealthError: If container is unhealthy or not found
        """
        logger.info(f"Checking container health for '{container_app_name}'")

        start_time = time.time()
        attempt = 0

        while True:
            attempt += 1

            try:
                # Get container app status
                result = subprocess.run(
                    [
                        "az",
                        "containerapp",
                        "show",
                        "--name",
                        container_app_name,
                        "--resource-group",
                        self.resource_group,
                        "--output",
                        "json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    logger.error(f"Container app '{container_app_name}' not found: {result.stderr}")
                    raise ContainerHealthError(
                        f"Container app '{container_app_name}' not found: {result.stderr}"
                    )

                # Parse JSON response
                container_info = json.loads(result.stdout)
                properties = container_info.get("properties", {})
                running_status = properties.get("runningStatus", "Unknown")
                provisioning_state = properties.get("provisioningState", "Unknown")

                logger.info(
                    f"Container status (attempt {attempt}): "
                    f"runningStatus={running_status}, provisioningState={provisioning_state}"
                )

                # Check if container is healthy
                if running_status == "Running" and provisioning_state == "Succeeded":
                    logger.info(f"Container app '{container_app_name}' is healthy")
                    return True

                # Check if container is in failed state
                if provisioning_state == "Failed":
                    raise ContainerHealthError(
                        f"Container app '{container_app_name}' provisioning failed. "
                        f"Provisioning failed"
                    )

                # If not healthy and not waiting, fail immediately
                if not wait_ready:
                    raise ContainerHealthError(
                        f"Container is not running. Container app '{container_app_name}' "
                        f"Status: {running_status}, Provisioning: {provisioning_state}"
                    )

                # Check if we've exceeded wait time
                elapsed = time.time() - start_time
                if elapsed >= max_wait_seconds:
                    raise ContainerHealthError(
                        f"Container app '{container_app_name}' did not become ready within {max_wait_seconds}s. "
                        f"Last status: {running_status}, Provisioning: {provisioning_state}"
                    )

                # Wait before next check
                logger.info(f"Waiting for container to become ready... (elapsed: {elapsed:.0f}s)")
                time.sleep(10)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse container app response: {e}")
                raise ContainerHealthError(f"Failed to parse container app status: {e}") from e

            except subprocess.TimeoutExpired as err:
                logger.error("Container health check command timed out")
                raise ContainerHealthError(
                    f"Container health check timed out for '{container_app_name}'"
                ) from err

    def verify_api_endpoint(
        self,
        endpoint: str,
        expected_fields: list[str] | None = None,
        max_retries: int = 0,
        retry_delay: int = 5,
    ) -> bool:
        """Verify API endpoint is accessible and returns expected response

        Args:
            endpoint: API endpoint path (e.g., "/api/status")
            expected_fields: Optional list of expected response fields
            max_retries: Maximum number of total attempts (not additional retries)
            retry_delay: Delay between retries in seconds

        Returns:
            True if endpoint is accessible

        Raises:
            APIEndpointError: If endpoint verification fails
        """
        url = f"{self.orchestrator_url}{endpoint}"
        logger.info(f"Verifying API endpoint: {url}")

        # Default max_retries=0 means 1 attempt (no retries)
        max_attempts = max(1, max_retries) if max_retries > 0 else 1

        last_error = None
        for attempt in range(max_attempts):
            try:
                response = requests.get(url, timeout=30)

                # Check status code
                if response.status_code == 200:
                    # Validate expected fields if provided
                    if expected_fields:
                        try:
                            response_json = response.json()
                            for field in expected_fields:
                                if field not in response_json:
                                    raise APIEndpointError(
                                        f"Missing expected field '{field}' in response from {endpoint}"
                                    )
                        except json.JSONDecodeError as e:
                            raise APIEndpointError(
                                f"Expected JSON response from {endpoint} but got invalid JSON"
                            ) from e

                    logger.info(f"API endpoint {endpoint} verified successfully")
                    return True

                # Non-200 status code
                last_error = f"Status {response.status_code}: {response.text}"

                # Retry on 503 (service unavailable)
                if response.status_code == 503 and attempt < (max_attempts - 1):
                    logger.warning(
                        f"API endpoint {endpoint} returned 503, retrying... (attempt {attempt + 1}/{max_attempts})"
                    )
                    time.sleep(retry_delay)
                    continue

                # Other status codes fail immediately
                raise APIEndpointError(
                    f"API endpoint {endpoint} returned status {response.status_code}: {response.text}"
                )

            except requests.Timeout as err:
                last_error = "Request timed out"
                logger.warning(
                    f"API endpoint {endpoint} timed out (attempt {attempt + 1}/{max_attempts})"
                )
                if attempt < (max_attempts - 1):
                    time.sleep(retry_delay)
                    continue
                raise APIEndpointError(f"API endpoint {endpoint} request timeout") from err

            except requests.ConnectionError as e:
                last_error = str(e)
                logger.warning(
                    f"API endpoint {endpoint} connection error: {e} (attempt {attempt + 1}/{max_attempts})"
                )
                if attempt < (max_attempts - 1):
                    time.sleep(retry_delay)
                    continue
                raise APIEndpointError(f"API endpoint {endpoint} connection error: {e}") from e

        # All retries failed
        raise APIEndpointError(
            f"API endpoint {endpoint} verification failed after {max_attempts} attempts: {last_error}"
        )

    def verify_multiple_endpoints(self, endpoints: list[str]) -> dict[str, bool]:
        """Verify multiple API endpoints

        Args:
            endpoints: List of endpoint paths

        Returns:
            Dictionary mapping endpoint to verification result (True/False)
        """
        results = {}
        for endpoint in endpoints:
            try:
                results[endpoint] = self.verify_api_endpoint(endpoint)
            except APIEndpointError as err:
                logger.warning(f"Endpoint verification failed for {endpoint}: {err}")
                results[endpoint] = False
        return results

    def verify_rbac_permissions(
        self,
        principal_id: str,
        resource_id: str,
        required_role: str,
    ) -> bool:
        """Verify RBAC role assignment exists

        Args:
            principal_id: Managed identity principal ID
            resource_id: Azure resource ID
            required_role: Required role name (e.g., "Key Vault Secrets User")

        Returns:
            True if role assignment exists

        Raises:
            RBACPermissionError: If role assignment is missing
        """
        logger.info(
            f"Verifying RBAC permissions for principal '{principal_id}' on resource '{resource_id}'"
        )

        try:
            result = subprocess.run(
                [
                    "az",
                    "role",
                    "assignment",
                    "list",
                    "--assignee",
                    principal_id,
                    "--scope",
                    resource_id,
                    "--output",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RBACPermissionError(f"Failed to check RBAC permissions: {result.stderr}")

            # Parse role assignments
            role_assignments = json.loads(result.stdout)

            # Check if required role exists
            for assignment in role_assignments:
                if assignment.get("roleDefinitionName") == required_role:
                    logger.info(
                        f"RBAC permission verified: '{required_role}' assigned to principal '{principal_id}'"
                    )
                    return True

            # Required role not found
            raise RBACPermissionError(
                f"Missing required role assignment: '{required_role}' for principal '{principal_id}' on resource '{resource_id}'"
            )

        except json.JSONDecodeError as e:
            raise RBACPermissionError(f"Failed to parse RBAC role assignments: {e}") from e

    def verify_complete_deployment(
        self,
        container_app_name: str,
        api_endpoints: list[str],
    ) -> dict:
        """Verify complete deployment (container + API endpoints)

        Args:
            container_app_name: Container app name
            api_endpoints: List of API endpoints to verify

        Returns:
            Dictionary with verification results:
            {
                "success": bool,
                "container_healthy": bool,
                "api_endpoints_verified": {endpoint: bool, ...}
            }
        """
        logger.info(f"Starting complete deployment verification for '{container_app_name}'")

        results = {
            "success": True,
            "container_healthy": False,
            "api_endpoints_verified": {},
        }

        # Check container health
        try:
            results["container_healthy"] = self.check_container_health(container_app_name)
        except ContainerHealthError as err:
            logger.warning(f"Container health check failed: {err}")
            results["success"] = False

        # Verify API endpoints
        for endpoint in api_endpoints:
            try:
                results["api_endpoints_verified"][endpoint] = self.verify_api_endpoint(endpoint)
            except APIEndpointError as err:
                logger.warning(f"API endpoint verification failed for {endpoint}: {err}")
                results["api_endpoints_verified"][endpoint] = False
                results["success"] = False

        # Overall success requires all checks to pass
        if not results["container_healthy"]:
            results["success"] = False

        if not all(results["api_endpoints_verified"].values()):
            results["success"] = False

        logger.info(f"Complete deployment verification finished: success={results['success']}")
        return results

    def generate_verification_report(
        self,
        container_app_name: str,
        api_endpoints: list[str],
    ) -> dict:
        """Generate comprehensive verification report

        Args:
            container_app_name: Container app name
            api_endpoints: List of API endpoints to verify

        Returns:
            Dictionary with verification report
        """
        logger.info(f"Generating verification report for '{container_app_name}'")

        # Run complete verification
        verification_results = self.verify_complete_deployment(container_app_name, api_endpoints)

        # Build report
        report = {
            "container_app_name": container_app_name,
            "verification_time": datetime.now().isoformat(),
            "checks_passed": 0,
            "checks_failed": 0,
            "results": verification_results,
        }

        # Count passes and failures
        if verification_results["container_healthy"]:
            report["checks_passed"] += 1
        else:
            report["checks_failed"] += 1

        for passed in verification_results["api_endpoints_verified"].values():
            if passed:
                report["checks_passed"] += 1
            else:
                report["checks_failed"] += 1

        logger.info(
            f"Verification report complete: "
            f"{report['checks_passed']} passed, {report['checks_failed']} failed"
        )

        return report
