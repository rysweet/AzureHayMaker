"""Integration tests for complete GitOps deployment workflow (TDD - These tests will FAIL until implementation is complete)

Testing pyramid: 10% E2E tests
- Test complete GitOps deployment flow
- Test secret injection step
- Test integration tests step
- Test verification step

Philosophy: Zero-BS implementation, test real deployment workflow
"""

import os
import subprocess

import pytest

from azure_haymaker.orchestrator.deployment_verifier import DeploymentVerifier

# Modules now exist - direct imports
from azure_haymaker.orchestrator.secret_injection_handler import SecretInjectionHandler

# ============================================================================
# END-TO-END TESTS (10% of testing pyramid)
# ============================================================================


class TestCompleteGitOpsWorkflow:
    """Test complete GitOps deployment workflow end-to-end"""

    def test_complete_gitops_deployment_succeeds(
        self,
        azure_subscription_id,
        azure_resource_group,
        azure_keyvault_name,
    ):
        """Test complete GitOps deployment workflow from start to finish

        Workflow steps:
        1. Deploy infrastructure via GitHub Actions
        2. Wait for RBAC propagation
        3. Inject secrets to container app
        4. Verify deployment health
        5. Run integration tests against API
        """
        # Step 1: Trigger GitHub Actions workflow (simulated)
        # In real scenario, this would be triggered by git push
        print("Step 1: GitHub Actions deployment (assumed complete)")

        # Step 2: Wait for RBAC propagation
        print("Step 2: Waiting for RBAC propagation...")
        handler = SecretInjectionHandler(
            subscription_id=azure_subscription_id,
            resource_group=azure_resource_group,
            max_retries=10,
            initial_backoff_seconds=10,
        )

        # Get orchestrator identity principal ID
        result = subprocess.run(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                "orchestrator",
                "--resource-group",
                azure_resource_group,
                "--subscription",
                azure_subscription_id,
                "--query",
                "identity.principalId",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Failed to get orchestrator identity: {result.stderr}"
        principal_id = result.stdout.strip()

        # Wait for RBAC propagation
        rbac_ready = handler.wait_for_rbac_propagation(
            keyvault_name=azure_keyvault_name,
            identity_principal_id=principal_id,
        )
        assert rbac_ready is True, "RBAC propagation failed"

        # Step 3: Inject secrets
        print("Step 3: Injecting secrets to container app...")
        secrets_injected = handler.inject_secrets_to_container_app(
            container_app_name="orchestrator",
            keyvault_name=azure_keyvault_name,
            secrets=[
                {"name": "ANTHROPIC_API_KEY", "keyvault_secret": "anthropic-api-key"},
                {"name": "AZURE_CLIENT_ID", "keyvault_secret": "azure-client-id"},
                {"name": "AZURE_CLIENT_SECRET", "keyvault_secret": "azure-client-secret"},
                {"name": "AZURE_TENANT_ID", "keyvault_secret": "azure-tenant-id"},
            ],
        )
        assert secrets_injected is True, "Secret injection failed"

        # Step 4: Verify deployment health
        print("Step 4: Verifying deployment health...")

        # Get orchestrator URL
        result = subprocess.run(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                "orchestrator",
                "--resource-group",
                azure_resource_group,
                "--subscription",
                azure_subscription_id,
                "--query",
                "properties.configuration.ingress.fqdn",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Failed to get orchestrator URL: {result.stderr}"
        orchestrator_fqdn = result.stdout.strip()
        orchestrator_url = f"https://{orchestrator_fqdn}"

        verifier = DeploymentVerifier(
            subscription_id=azure_subscription_id,
            resource_group=azure_resource_group,
            orchestrator_url=orchestrator_url,
        )

        # Check container health
        container_healthy = verifier.check_container_health(
            container_app_name="orchestrator",
            wait_ready=True,
            max_wait_seconds=300,
        )
        assert container_healthy is True, "Container is not healthy"

        # Step 5: Run integration tests
        print("Step 5: Running integration tests against API...")
        api_endpoints = [
            "/api/status",
            "/api/resources",
            "/api/scenarios",
        ]

        endpoints_verified = verifier.verify_multiple_endpoints(api_endpoints)

        assert all(endpoints_verified.values()), f"Some endpoints failed: {endpoints_verified}"

        print("✅ Complete GitOps deployment workflow succeeded!")


class TestSecretInjectionStep:
    """Test secret injection step in GitOps workflow"""

    def test_secret_injection_with_rbac_wait(
        self,
        azure_subscription_id,
        azure_resource_group,
        azure_keyvault_name,
    ):
        """Test secret injection waits for RBAC propagation before injecting"""
        handler = SecretInjectionHandler(
            subscription_id=azure_subscription_id,
            resource_group=azure_resource_group,
            max_retries=5,
            initial_backoff_seconds=10,
        )

        # Get orchestrator identity
        result = subprocess.run(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                "orchestrator",
                "--resource-group",
                azure_resource_group,
                "--query",
                "identity.principalId",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        principal_id = result.stdout.strip()

        # Wait for RBAC (should succeed eventually)
        rbac_ready = handler.wait_for_rbac_propagation(
            keyvault_name=azure_keyvault_name,
            identity_principal_id=principal_id,
        )

        assert rbac_ready is True

        # Inject one test secret
        result = handler.inject_secrets_to_container_app(
            container_app_name="orchestrator",
            keyvault_name=azure_keyvault_name,
            secrets=[
                {"name": "TEST_SECRET", "keyvault_secret": "test-secret"},
            ],
        )

        assert result is True

    def test_secret_injection_handles_missing_keyvault_secret(
        self,
        azure_subscription_id,
        azure_resource_group,
        azure_keyvault_name,
    ):
        """Test secret injection fails gracefully when Key Vault secret doesn't exist"""
        handler = SecretInjectionHandler(
            subscription_id=azure_subscription_id,
            resource_group=azure_resource_group,
            max_retries=1,  # Don't retry for missing secrets
        )

        # Try to inject non-existent secret
        from azure_haymaker.orchestrator.secret_injection_handler import SecretInjectionError

        with pytest.raises(SecretInjectionError):
            handler.inject_secrets_to_container_app(
                container_app_name="orchestrator",
                keyvault_name=azure_keyvault_name,
                secrets=[
                    {
                        "name": "DOES_NOT_EXIST",
                        "keyvault_secret": "secret-that-does-not-exist-12345",
                    },
                ],
            )


class TestDeploymentVerificationStep:
    """Test deployment verification step in GitOps workflow"""

    def test_verify_orchestrator_container_health(
        self,
        azure_subscription_id,
        azure_resource_group,
    ):
        """Test verification step checks orchestrator container health"""
        # Get orchestrator URL
        result = subprocess.run(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                "orchestrator",
                "--resource-group",
                azure_resource_group,
                "--query",
                "properties.configuration.ingress.fqdn",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        orchestrator_fqdn = result.stdout.strip()
        orchestrator_url = f"https://{orchestrator_fqdn}"

        verifier = DeploymentVerifier(
            subscription_id=azure_subscription_id,
            resource_group=azure_resource_group,
            orchestrator_url=orchestrator_url,
        )

        # Verify container is healthy
        is_healthy = verifier.check_container_health("orchestrator")

        assert is_healthy is True

    def test_verify_all_api_endpoints(
        self,
        azure_subscription_id,
        azure_resource_group,
    ):
        """Test verification step checks all API endpoints"""
        # Get orchestrator URL
        result = subprocess.run(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                "orchestrator",
                "--resource-group",
                azure_resource_group,
                "--query",
                "properties.configuration.ingress.fqdn",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        orchestrator_fqdn = result.stdout.strip()
        orchestrator_url = f"https://{orchestrator_fqdn}"

        verifier = DeploymentVerifier(
            subscription_id=azure_subscription_id,
            resource_group=azure_resource_group,
            orchestrator_url=orchestrator_url,
        )

        # Verify all critical endpoints
        endpoints_to_verify = [
            "/api/status",
            "/api/resources",
            "/api/scenarios",
            "/api/analytics",
        ]

        results = verifier.verify_multiple_endpoints(endpoints_to_verify)

        # All endpoints should be accessible
        assert all(
            results.values()
        ), f"Failed endpoints: {[k for k, v in results.items() if not v]}"

    def test_generate_verification_report(
        self,
        azure_subscription_id,
        azure_resource_group,
    ):
        """Test verification step generates deployment report"""
        # Get orchestrator URL
        result = subprocess.run(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                "orchestrator",
                "--resource-group",
                azure_resource_group,
                "--query",
                "properties.configuration.ingress.fqdn",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        orchestrator_fqdn = result.stdout.strip()
        orchestrator_url = f"https://{orchestrator_fqdn}"

        verifier = DeploymentVerifier(
            subscription_id=azure_subscription_id,
            resource_group=azure_resource_group,
            orchestrator_url=orchestrator_url,
        )

        # Generate verification report
        report = verifier.generate_verification_report(
            container_app_name="orchestrator",
            api_endpoints=["/api/status", "/api/resources"],
        )

        # Verify report structure
        assert "container_app_name" in report
        assert report["container_app_name"] == "orchestrator"
        assert "verification_time" in report
        assert "checks_passed" in report
        assert "checks_failed" in report
        assert report["checks_passed"] >= 2  # At least container + 1 API endpoint


class TestIntegrationTestsStep:
    """Test integration tests step in GitOps workflow"""

    def test_run_cli_integration_tests_against_deployed_api(
        self,
        azure_subscription_id,
        azure_resource_group,
    ):
        """Test integration tests run successfully against deployed API"""
        # Get orchestrator URL
        result = subprocess.run(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                "orchestrator",
                "--resource-group",
                azure_resource_group,
                "--query",
                "properties.configuration.ingress.fqdn",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        orchestrator_fqdn = result.stdout.strip()
        orchestrator_url = f"https://{orchestrator_fqdn}"

        # Set environment variable for tests
        env = os.environ.copy()
        env["ORCHESTRATOR_URL"] = orchestrator_url

        # Run CLI integration tests
        result = subprocess.run(
            [
                "pytest",
                "tests/integration/test_cli_against_api.py",
                "-v",
                "-k",
                "test_api_status_endpoint_returns_valid_response",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Integration tests should pass
        assert (
            result.returncode == 0
        ), f"Integration tests failed:\n{result.stdout}\n{result.stderr}"
        assert "PASSED" in result.stdout


class TestGitOpsErrorRecovery:
    """Test GitOps workflow error recovery"""

    def test_workflow_retries_on_rbac_propagation_delay(
        self,
        azure_subscription_id,
        azure_resource_group,
        azure_keyvault_name,
    ):
        """Test workflow retries when RBAC propagation is delayed"""
        handler = SecretInjectionHandler(
            subscription_id=azure_subscription_id,
            resource_group=azure_resource_group,
            max_retries=10,  # Allow sufficient retries
            initial_backoff_seconds=5,
        )

        # Simulate fresh RBAC assignment (might not be propagated yet)
        result = subprocess.run(
            [
                "az",
                "containerapp",
                "show",
                "--name",
                "orchestrator",
                "--resource-group",
                azure_resource_group,
                "--query",
                "identity.principalId",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        principal_id = result.stdout.strip()

        # Wait for RBAC - should succeed with retries
        rbac_ready = handler.wait_for_rbac_propagation(
            keyvault_name=azure_keyvault_name,
            identity_principal_id=principal_id,
        )

        assert rbac_ready is True

    def test_workflow_reports_verification_failures(
        self,
        azure_subscription_id,
        azure_resource_group,
    ):
        """Test workflow reports verification failures clearly"""
        # Try to verify non-existent container
        verifier = DeploymentVerifier(
            subscription_id=azure_subscription_id,
            resource_group=azure_resource_group,
            orchestrator_url="https://fake.com",
        )

        # Should fail with clear error message
        from azure_haymaker.orchestrator.deployment_verifier import ContainerHealthError

        with pytest.raises(ContainerHealthError) as exc_info:
            verifier.check_container_health("non-existent-container")

        # Error should be descriptive
        error_message = str(exc_info.value)
        assert "non-existent-container" in error_message or "not found" in error_message.lower()


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def azure_subscription_id():
    """Get Azure subscription ID from environment"""
    sub_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
    if not sub_id:
        pytest.skip("AZURE_SUBSCRIPTION_ID not set")
    return sub_id


@pytest.fixture(scope="session")
def azure_resource_group():
    """Get Azure resource group from environment"""
    rg = os.environ.get("AZURE_RESOURCE_GROUP", "rg-azurehaymaker-dev")
    return rg


@pytest.fixture(scope="session")
def azure_keyvault_name():
    """Get Key Vault name from environment"""
    kv = os.environ.get("AZURE_KEYVAULT_NAME")
    if not kv:
        # Try to discover from resource group
        result = subprocess.run(
            [
                "az",
                "keyvault",
                "list",
                "--resource-group",
                azure_resource_group(),
                "--query",
                "[0].name",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            kv = result.stdout.strip()
        else:
            pytest.skip("AZURE_KEYVAULT_NAME not set and could not be discovered")
    return kv


@pytest.fixture(scope="session", autouse=True)
def verify_azure_login():
    """Verify Azure CLI is logged in before running tests"""
    try:
        result = subprocess.run(
            ["az", "account", "show"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            pytest.skip("Not logged in to Azure CLI. Run: az login")
    except subprocess.TimeoutExpired:
        pytest.skip("Azure CLI not responding (likely not logged in). Run: az login")


# ============================================================================
# NOTES FOR IMPLEMENTATION
# ============================================================================

"""
Implementation Checklist (what needs to exist to pass these tests):

1. Infrastructure (already deployed):
   - Azure Container Apps environment
   - Orchestrator container app with system-assigned identity
   - Key Vault with secrets
   - RBAC role assignments (Key Vault Secrets User)

2. Python Modules:
   - azure_haymaker.orchestrator.secret_injection_handler
   - azure_haymaker.orchestrator.deployment_verifier

3. GitHub Actions Workflow:
   - Deploy infrastructure (bicep)
   - Wait for RBAC propagation
   - Inject secrets
   - Verify deployment
   - Run integration tests

4. Environment Variables (for running tests):
   - AZURE_SUBSCRIPTION_ID: Azure subscription
   - AZURE_RESOURCE_GROUP: Resource group name
   - AZURE_KEYVAULT_NAME: Key Vault name

5. Prerequisites:
   - Azure CLI installed and logged in
   - Python pytest installed
   - Real Azure resources deployed

Running Tests:
```bash
# Login to Azure
az login

# Set environment variables
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_RESOURCE_GROUP="rg-azurehaymaker-dev"
export AZURE_KEYVAULT_NAME="kv-haymaker-dev"

# Run E2E tests
pytest tests/integration/test_gitops_workflow.py -v -s
```

Note: These tests require real Azure resources and will:
- Make real Azure API calls
- Interact with deployed containers
- Verify actual RBAC permissions
- Test real secret injection
- Take 5-10 minutes to run completely
"""
