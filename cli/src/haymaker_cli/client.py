"""HTTP client SDK for HayMaker API."""

import asyncio
from typing import Any

import httpx
from pydantic import ValidationError

from haymaker_cli.auth import AuthProvider
from haymaker_cli.models import (
    AgentInfo,
    CleanupRequest,
    CleanupResponse,
    ErrorResponse,
    ExecutionRequest,
    ExecutionResponse,
    ExecutionStatus,
    LogEntry,
    MetricsSummary,
    OrchestratorStatus,
    ResourceInfo,
)


class HayMakerClientError(Exception):
    """Base exception for HayMaker client errors."""

    def __init__(self, message: str, status_code: int | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class HayMakerClient:
    """HTTP client for HayMaker API.

    Example:
        >>> from haymaker_cli.auth import ApiKeyAuthProvider
        >>> auth = ApiKeyAuthProvider("my-key")
        >>> client = HayMakerClient("https://api.example.com", auth)
        >>> status = client.get_status()  # doctest: +SKIP
    """

    def __init__(
        self,
        base_url: str,
        auth: AuthProvider,
        timeout: float = 30.0,
        retry_count: int = 3,
    ):
        """Initialize HayMaker client.

        Args:
            base_url: Base URL of HayMaker API
            auth: Authentication provider
            timeout: Request timeout in seconds (default: 30.0)
            retry_count: Number of retries for failed requests (default: 3)
        """
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.timeout = timeout
        self.retry_count = retry_count
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client.

        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._client is None:
            headers = {
                "User-Agent": "haymaker-cli/0.1.0",
                "Accept": "application/json",
            }
            headers.update(self.auth.get_auth_header())

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=headers,
                follow_redirects=True,
            )

        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with error handling and retries.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path (relative to base_url)
            **kwargs: Additional arguments for httpx request

        Returns:
            HTTP response

        Raises:
            HayMakerClientError: If request fails after retries
        """
        client = await self._get_client()

        for attempt in range(self.retry_count):
            try:
                response = await client.request(method, path, **kwargs)

                if response.status_code >= 400:
                    # Parse error response
                    try:
                        error_data = response.json()
                        error = ErrorResponse(**error_data)
                        raise HayMakerClientError(
                            error.error.message,
                            status_code=response.status_code,
                            details=error.error.details,
                        )
                    except (ValidationError, ValueError):
                        # Fallback for non-standard error responses
                        raise HayMakerClientError(
                            f"Request failed: {response.text}",
                            status_code=response.status_code,
                        )

                return response

            except httpx.TimeoutException as e:
                if attempt == self.retry_count - 1:
                    raise HayMakerClientError(f"Request timeout: {e}")
                await asyncio.sleep(2**attempt)  # Exponential backoff

            except httpx.NetworkError as e:
                if attempt == self.retry_count - 1:
                    raise HayMakerClientError(f"Network error: {e}")
                await asyncio.sleep(2**attempt)

        raise HayMakerClientError("Request failed after all retries")

    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # Status endpoints

    async def get_status(self) -> OrchestratorStatus:
        """Get current orchestrator status.

        Returns:
            Orchestrator status

        Raises:
            HayMakerClientError: If request fails

        Example:
            >>> status = await client.get_status()  # doctest: +SKIP
            >>> print(status.status)  # doctest: +SKIP
            'running'
        """
        response = await self._request("GET", "/api/v1/status")
        return OrchestratorStatus(**response.json())

    # Metrics endpoints

    async def get_metrics(
        self, period: str = "7d", scenario: str | None = None
    ) -> MetricsSummary:
        """Get execution metrics.

        Args:
            period: Time period (7d, 30d, 90d)
            scenario: Optional scenario filter

        Returns:
            Metrics summary

        Example:
            >>> metrics = await client.get_metrics(period="30d")  # doctest: +SKIP
            >>> print(metrics.success_rate)  # doctest: +SKIP
            0.95
        """
        params = {"period": period}
        if scenario:
            params["scenario"] = scenario

        response = await self._request("GET", "/api/v1/metrics", params=params)
        return MetricsSummary(**response.json())

    # Execution endpoints

    async def execute_scenario(
        self, scenario_name: str, parameters: dict[str, Any] | None = None
    ) -> ExecutionResponse:
        """Execute a scenario on-demand.

        Args:
            scenario_name: Name of scenario to execute
            parameters: Optional execution parameters

        Returns:
            Execution response with execution_id

        Example:
            >>> execution = await client.execute_scenario("compute-01")  # doctest: +SKIP
            >>> print(execution.execution_id)  # doctest: +SKIP
            'exec-123-456'
        """
        request = ExecutionRequest(
            scenario_name=scenario_name, parameters=parameters or {}
        )

        response = await self._request(
            "POST", "/api/v1/execute", json=request.model_dump()
        )
        return ExecutionResponse(**response.json())

    async def get_execution_status(self, execution_id: str) -> ExecutionStatus:
        """Get execution status.

        Args:
            execution_id: Execution ID

        Returns:
            Execution status

        Example:
            >>> status = await client.get_execution_status("exec-123")  # doctest: +SKIP
            >>> print(status.status)  # doctest: +SKIP
            'completed'
        """
        response = await self._request("GET", f"/api/v1/executions/{execution_id}")
        return ExecutionStatus(**response.json())

    # Agent endpoints

    async def list_agents(
        self, status: str | None = None, limit: int = 100
    ) -> list[AgentInfo]:
        """List agents.

        Args:
            status: Optional status filter (running, completed, failed)
            limit: Maximum number of results (default: 100)

        Returns:
            List of agent information

        Example:
            >>> agents = await client.list_agents(status="running")  # doctest: +SKIP
            >>> print(len(agents))  # doctest: +SKIP
            5
        """
        params = {"limit": limit}
        if status:
            params["status"] = status

        response = await self._request("GET", "/api/v1/agents", params=params)
        data = response.json()
        return [AgentInfo(**agent) for agent in data.get("agents", [])]

    async def get_agent_logs(
        self, agent_id: str, tail: int = 100, follow: bool = False
    ) -> list[LogEntry]:
        """Get agent logs.

        Args:
            agent_id: Agent ID
            tail: Number of recent log entries (default: 100)
            follow: Whether to stream logs (not implemented in HTTP)

        Returns:
            List of log entries

        Example:
            >>> logs = await client.get_agent_logs("agent-123", tail=50)  # doctest: +SKIP
            >>> print(logs[0].message)  # doctest: +SKIP
            'Starting scenario execution'
        """
        params = {"tail": tail, "follow": follow}
        response = await self._request("GET", f"/api/v1/agents/{agent_id}/logs", params=params)
        data = response.json()
        return [LogEntry(**log) for log in data.get("logs", [])]

    # Resource endpoints

    async def list_resources(
        self,
        execution_id: str | None = None,
        scenario: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ResourceInfo]:
        """List resources.

        Args:
            execution_id: Optional execution ID filter
            scenario: Optional scenario filter
            status: Optional status filter (created, deleted)
            limit: Maximum number of results (default: 100)

        Returns:
            List of resource information

        Example:
            >>> resources = await client.list_resources(scenario="compute-01")  # doctest: +SKIP
            >>> print(len(resources))  # doctest: +SKIP
            15
        """
        params = {"limit": limit}
        if execution_id:
            params["execution_id"] = execution_id
        if scenario:
            params["scenario"] = scenario
        if status:
            params["status"] = status

        response = await self._request("GET", "/api/v1/resources", params=params)
        data = response.json()
        return [ResourceInfo(**resource) for resource in data.get("resources", [])]

    # Cleanup endpoints

    async def trigger_cleanup(
        self,
        execution_id: str | None = None,
        scenario: str | None = None,
        dry_run: bool = False,
    ) -> CleanupResponse:
        """Trigger cleanup operation.

        Args:
            execution_id: Optional execution ID to cleanup
            scenario: Optional scenario to cleanup
            dry_run: If True, only show what would be cleaned (default: False)

        Returns:
            Cleanup response

        Example:
            >>> cleanup = await client.trigger_cleanup(dry_run=True)  # doctest: +SKIP
            >>> print(cleanup.resources_found)  # doctest: +SKIP
            25
        """
        request = CleanupRequest(
            execution_id=execution_id, scenario=scenario, dry_run=dry_run
        )

        response = await self._request("POST", "/api/v1/cleanup", json=request.model_dump())
        return CleanupResponse(**response.json())

    async def get_cleanup_status(self, cleanup_id: str) -> CleanupResponse:
        """Get cleanup operation status.

        Args:
            cleanup_id: Cleanup operation ID

        Returns:
            Cleanup response with current status
        """
        response = await self._request("GET", f"/api/v1/cleanup/{cleanup_id}")
        return CleanupResponse(**response.json())


# Synchronous wrapper for easier CLI usage

class SyncHayMakerClient:
    """Synchronous wrapper for HayMakerClient.

    This provides a simpler synchronous API for CLI commands.

    Example:
        >>> from haymaker_cli.auth import ApiKeyAuthProvider
        >>> auth = ApiKeyAuthProvider("my-key")
        >>> client = SyncHayMakerClient("https://api.example.com", auth)
        >>> status = client.get_status()  # doctest: +SKIP
    """

    def __init__(self, *args, **kwargs):
        """Initialize synchronous client with same args as async client."""
        self._async_client = HayMakerClient(*args, **kwargs)

    def _run(self, coro):
        """Run async coroutine in event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create new one
            return asyncio.run(coro)
        else:
            # Running in async context, use existing loop
            return loop.run_until_complete(coro)

    def get_status(self) -> OrchestratorStatus:
        """Sync version of get_status."""
        return self._run(self._async_client.get_status())

    def get_metrics(self, period: str = "7d", scenario: str | None = None) -> MetricsSummary:
        """Sync version of get_metrics."""
        return self._run(self._async_client.get_metrics(period, scenario))

    def execute_scenario(
        self, scenario_name: str, parameters: dict[str, Any] | None = None
    ) -> ExecutionResponse:
        """Sync version of execute_scenario."""
        return self._run(self._async_client.execute_scenario(scenario_name, parameters))

    def get_execution_status(self, execution_id: str) -> ExecutionStatus:
        """Sync version of get_execution_status."""
        return self._run(self._async_client.get_execution_status(execution_id))

    def list_agents(self, status: str | None = None, limit: int = 100) -> list[AgentInfo]:
        """Sync version of list_agents."""
        return self._run(self._async_client.list_agents(status, limit))

    def get_agent_logs(
        self, agent_id: str, tail: int = 100, follow: bool = False
    ) -> list[LogEntry]:
        """Sync version of get_agent_logs."""
        return self._run(self._async_client.get_agent_logs(agent_id, tail, follow))

    def list_resources(
        self,
        execution_id: str | None = None,
        scenario: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ResourceInfo]:
        """Sync version of list_resources."""
        return self._run(
            self._async_client.list_resources(execution_id, scenario, status, limit)
        )

    def trigger_cleanup(
        self,
        execution_id: str | None = None,
        scenario: str | None = None,
        dry_run: bool = False,
    ) -> CleanupResponse:
        """Sync version of trigger_cleanup."""
        return self._run(self._async_client.trigger_cleanup(execution_id, scenario, dry_run))

    def get_cleanup_status(self, cleanup_id: str) -> CleanupResponse:
        """Sync version of get_cleanup_status."""
        return self._run(self._async_client.get_cleanup_status(cleanup_id))

    def close(self) -> None:
        """Close client."""
        self._run(self._async_client.close())
