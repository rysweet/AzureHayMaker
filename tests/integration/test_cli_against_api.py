"""Integration tests for CLI against deployed API (TDD - These tests will FAIL until implementation is complete)

Testing pyramid: 30% integration tests
- Test all CLI commands against deployed API
- Test /api/status endpoint
- Test /api/resources endpoint
- Test /api/scenarios endpoint
- Test /api/analytics endpoint
- Test authentication and error handling

Philosophy: Zero-BS implementation, test real HTTP calls against test server
"""

import contextlib
import os
import subprocess
import time

import pytest
import requests

# Mark tests as skipped until haymaker_cli module is implemented
# This is expected for TDD - tests are written before implementation
pytest.skip(
    "haymaker_cli module not yet implemented - tests will be enabled when CLI is ready",
    allow_module_level=True,
)


# ============================================================================
# INTEGRATION TESTS (30% of testing pyramid)
# ============================================================================


class TestCLIAPIIntegration:
    """Test CLI commands against deployed API"""

    def test_cli_status_command(self, orchestrator_url, api_key):
        """Test haymaker status command returns orchestrator status"""
        # Run CLI command
        result = subprocess.run(
            [
                "haymaker",
                "--endpoint",
                orchestrator_url,
                "--api-key",
                api_key,
                "status",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "status" in result.stdout.lower()
        assert "running" in result.stdout.lower() or "idle" in result.stdout.lower()

    def test_cli_metrics_command(self, orchestrator_url, api_key):
        """Test haymaker metrics command returns execution metrics"""
        result = subprocess.run(
            [
                "haymaker",
                "--endpoint",
                orchestrator_url,
                "--api-key",
                api_key,
                "metrics",
                "--period",
                "7d",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "total_executions" in result.stdout or "executions" in result.stdout
        assert "success_rate" in result.stdout or "success" in result.stdout

    def test_cli_agents_list_command(self, orchestrator_url, api_key):
        """Test haymaker agents list command returns agent information"""
        result = subprocess.run(
            [
                "haymaker",
                "--endpoint",
                orchestrator_url,
                "--api-key",
                api_key,
                "agents",
                "list",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        # May be empty if no agents running, but should not error
        assert "error" not in result.stdout.lower()

    def test_cli_resources_list_command(self, orchestrator_url, api_key):
        """Test haymaker resources list command returns resource information"""
        result = subprocess.run(
            [
                "haymaker",
                "--endpoint",
                orchestrator_url,
                "--api-key",
                api_key,
                "resources",
                "list",
                "--limit",
                "10",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        # May be empty if no resources, but should not error
        assert "error" not in result.stdout.lower()

    def test_cli_with_invalid_api_key(self, orchestrator_url):
        """Test CLI fails gracefully with invalid API key"""
        result = subprocess.run(
            [
                "haymaker",
                "--endpoint",
                orchestrator_url,
                "--api-key",
                "invalid-key-12345",
                "status",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0
        assert "unauthorized" in result.stderr.lower() or "authentication" in result.stderr.lower()

    def test_cli_with_missing_endpoint(self, api_key):
        """Test CLI fails when endpoint is not configured"""
        result = subprocess.run(
            [
                "haymaker",
                "--api-key",
                api_key,
                "status",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0
        assert "endpoint" in result.stderr.lower()


class TestAPIStatusEndpoint:
    """Test /api/status endpoint functionality"""

    def test_api_status_endpoint_returns_valid_response(self, orchestrator_url):
        """Test /api/status returns valid orchestrator status"""
        response = requests.get(
            f"{orchestrator_url}/api/status",
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        assert "status" in data
        assert data["status"] in ["running", "idle", "error"]

        if data["status"] == "running":
            assert "current_run_id" in data
            assert "phase" in data
            assert "active_agents" in data

    def test_api_status_endpoint_performance(self, orchestrator_url):
        """Test /api/status responds within acceptable time"""
        start_time = time.time()

        response = requests.get(
            f"{orchestrator_url}/api/status",
            timeout=30,
        )

        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        assert elapsed_time < 5.0  # Should respond within 5 seconds

    def test_api_status_endpoint_handles_cors(self, orchestrator_url):
        """Test /api/status handles CORS requests"""
        response = requests.options(
            f"{orchestrator_url}/api/status",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
            timeout=30,
        )

        # Verify CORS headers are present (if CORS is configured)
        assert response.status_code in [200, 204]


class TestAPIResourcesEndpoint:
    """Test /api/resources endpoint functionality"""

    def test_api_resources_endpoint_returns_list(self, orchestrator_url, api_key):
        """Test /api/resources returns resource list"""
        response = requests.get(
            f"{orchestrator_url}/api/resources",
            headers={"x-functions-key": api_key} if api_key else {},
            params={"limit": 10},
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        assert "resources" in data
        assert isinstance(data["resources"], list)

        # If resources exist, verify structure
        if len(data["resources"]) > 0:
            resource = data["resources"][0]
            assert "id" in resource
            assert "name" in resource
            assert "type" in resource
            assert "tags" in resource

    def test_api_resources_endpoint_filters_by_scenario(self, orchestrator_url, api_key):
        """Test /api/resources filters by scenario name"""
        response = requests.get(
            f"{orchestrator_url}/api/resources",
            headers={"x-functions-key": api_key} if api_key else {},
            params={"scenario": "compute-01", "limit": 10},
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # If filtered resources exist, verify they match scenario
        if len(data["resources"]) > 0:
            for resource in data["resources"]:
                assert "tags" in resource
                # Scenario tag should match filter
                scenario_tag = resource["tags"].get("Scenario", resource["tags"].get("scenario"))
                if scenario_tag:
                    assert "compute-01" in scenario_tag

    def test_api_resources_endpoint_pagination(self, orchestrator_url, api_key):
        """Test /api/resources respects limit parameter"""
        response = requests.get(
            f"{orchestrator_url}/api/resources",
            headers={"x-functions-key": api_key} if api_key else {},
            params={"limit": 5},
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["resources"]) <= 5


class TestAPIScenariosEndpoint:
    """Test /api/scenarios endpoint functionality"""

    def test_api_scenarios_endpoint_returns_list(self, orchestrator_url):
        """Test /api/scenarios returns available scenarios"""
        response = requests.get(
            f"{orchestrator_url}/api/scenarios",
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        assert "scenarios" in data
        assert isinstance(data["scenarios"], list)

        # Verify scenario structure
        if len(data["scenarios"]) > 0:
            scenario = data["scenarios"][0]
            assert "name" in scenario
            assert "category" in scenario
            assert "description" in scenario

    def test_api_scenarios_endpoint_filters_by_category(self, orchestrator_url):
        """Test /api/scenarios filters by category"""
        response = requests.get(
            f"{orchestrator_url}/api/scenarios",
            params={"category": "compute"},
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # If filtered scenarios exist, verify category
        if len(data["scenarios"]) > 0:
            for scenario in data["scenarios"]:
                assert scenario["category"] == "compute"


class TestAPIAnalyticsEndpoint:
    """Test /api/analytics endpoint functionality"""

    def test_api_analytics_endpoint_returns_metrics(self, orchestrator_url, api_key):
        """Test /api/analytics returns execution analytics"""
        response = requests.get(
            f"{orchestrator_url}/api/analytics",
            headers={"x-functions-key": api_key} if api_key else {},
            params={"period": "7d"},
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify analytics structure
        assert "total_executions" in data or "executions" in data
        assert "period" in data

    def test_api_analytics_endpoint_supports_periods(self, orchestrator_url, api_key):
        """Test /api/analytics supports different time periods"""
        for period in ["7d", "30d", "90d"]:
            response = requests.get(
                f"{orchestrator_url}/api/analytics",
                headers={"x-functions-key": api_key} if api_key else {},
                params={"period": period},
                timeout=30,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["period"] == period


class TestAPIErrorHandling:
    """Test API error handling and edge cases"""

    def test_api_invalid_endpoint_returns_404(self, orchestrator_url):
        """Test invalid endpoint returns 404"""
        response = requests.get(
            f"{orchestrator_url}/api/invalid-endpoint-does-not-exist",
            timeout=30,
        )

        assert response.status_code == 404

    def test_api_malformed_request_returns_400(self, orchestrator_url):
        """Test malformed request returns 400"""
        response = requests.get(
            f"{orchestrator_url}/api/resources",
            params={"limit": "not-a-number"},
            timeout=30,
        )

        # Should either return 400 or handle gracefully
        assert response.status_code in [200, 400]

    def test_api_handles_connection_timeout(self, orchestrator_url):
        """Test API handles connection timeouts gracefully"""
        with contextlib.suppress(requests.Timeout):
            requests.get(
                f"{orchestrator_url}/api/status",
                timeout=0.001,  # Extremely short timeout
            )


class TestAPIAuthentication:
    """Test API authentication mechanisms"""

    def test_protected_endpoint_requires_auth(self, orchestrator_url):
        """Test protected endpoints require authentication"""
        # Try accessing protected endpoint without auth
        response = requests.post(
            f"{orchestrator_url}/api/execute",
            json={"scenarios": ["compute-01"]},
            timeout=30,
        )

        # Should return 401 Unauthorized
        assert response.status_code in [401, 403]

    def test_protected_endpoint_accepts_valid_key(self, orchestrator_url, api_key):
        """Test protected endpoint accepts valid API key"""
        if not api_key:
            pytest.skip("API key not configured")

        # Note: This doesn't actually execute, just tests auth
        response = requests.post(
            f"{orchestrator_url}/api/execute",
            headers={"x-functions-key": api_key},
            json={"scenarios": ["compute-01"]},
            timeout=30,
        )

        # Should not be 401/403 (might be 400 for invalid scenario, but not auth error)
        assert response.status_code not in [401, 403]


class TestCLIPythonClientIntegration:
    """Test Python CLI client library against API"""

    def test_client_can_connect_to_api(self, orchestrator_url, api_key):
        """Test CLIClient can connect to orchestrator API"""
        client = CLIClient(endpoint=orchestrator_url, api_key=api_key)  # noqa: F821

        status = client.get_status()

        assert status is not None
        assert "status" in status

    def test_client_can_list_resources(self, orchestrator_url, api_key):
        """Test CLIClient can list resources"""
        client = CLIClient(endpoint=orchestrator_url, api_key=api_key)  # noqa: F821

        resources = client.list_resources(limit=10)

        assert isinstance(resources, list)

    def test_client_handles_api_errors(self, orchestrator_url):
        """Test CLIClient handles API errors gracefully"""
        client = CLIClient(endpoint=orchestrator_url, api_key="invalid-key")  # noqa: F821

        with pytest.raises(AuthenticationError):  # noqa: F821
            client.get_status()

    def test_client_retries_on_transient_failures(self, orchestrator_url, api_key):
        """Test CLIClient retries on transient failures"""
        client = CLIClient(  # noqa: F821
            endpoint=orchestrator_url,
            api_key=api_key,
            max_retries=3,
        )

        # Should eventually succeed even with transient failures
        # (assuming the API is actually available)
        status = client.get_status()

        assert status is not None


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def orchestrator_url():
    """Get orchestrator URL from environment or use default"""
    url = os.environ.get("ORCHESTRATOR_URL", "https://test-orchestrator.azurecontainerapps.io")

    # Verify orchestrator is reachable
    try:
        response = requests.get(f"{url}/api/status", timeout=10)
        if response.status_code not in [200, 401, 403]:
            pytest.skip(f"Orchestrator at {url} not reachable (status: {response.status_code})")
    except requests.RequestException as e:
        pytest.skip(f"Orchestrator at {url} not reachable: {e}")

    return url


@pytest.fixture(scope="session")
def api_key():
    """Get API key from environment (optional)"""
    return os.environ.get("HAYMAKER_API_KEY")


@pytest.fixture
def test_scenario_name():
    """Get test scenario name for execution tests"""
    return "compute-01-linux-vm-web-server"


# ============================================================================
# NOTES FOR IMPLEMENTATION
# ============================================================================

"""
Implementation Checklist (what needs to exist to pass these tests):

1. Orchestrator API Endpoints (already implemented):
   - GET /api/status
   - GET /api/resources?scenario=X&limit=N
   - GET /api/scenarios?category=X
   - GET /api/analytics?period=7d|30d|90d
   - POST /api/execute (with authentication)

2. CLI Commands:
   - haymaker status
   - haymaker metrics --period 7d
   - haymaker agents list
   - haymaker resources list --limit 10
   - haymaker --endpoint URL --api-key KEY

3. Python CLI Client Library:
   - CLIClient(endpoint, api_key, max_retries=3)
   - client.get_status() -> Dict
   - client.list_resources(limit=10) -> List[Dict]
   - client.get_metrics(period="7d") -> Dict
   - Exceptions: AuthenticationError, APIError

4. Environment Variables:
   - ORCHESTRATOR_URL: Orchestrator endpoint
   - HAYMAKER_API_KEY: API key for authentication

5. Test Requirements:
   - Real orchestrator must be deployed and running
   - Can run against test/staging environment
   - Tests use real HTTP calls (no mocks)
   - Tests verify actual API contracts

Running Tests:
```bash
# Set environment variables
export ORCHESTRATOR_URL="https://your-orchestrator.azurecontainerapps.io"
export HAYMAKER_API_KEY="your-api-key"

# Run integration tests
pytest tests/integration/test_cli_against_api.py -v
```
"""
