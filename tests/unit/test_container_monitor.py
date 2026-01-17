"""Unit tests for container_monitor module.

Tests for Container App status monitoring and health checking functionality.

This module tests:
- ContainerMonitor initialization
- get_status method
- Standalone get_container_status function
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError

from azure_haymaker.orchestrator.container_monitor import (
    ContainerAppError,
    ContainerMonitor,
    get_container_status,
)


class TestContainerMonitorInit:
    """Tests for ContainerMonitor initialization."""

    def test_init_with_valid_params(self) -> None:
        """Test successful initialization with valid parameters."""
        monitor = ContainerMonitor(
            resource_group_name="test-rg",
            subscription_id="sub-123",
        )

        assert monitor.resource_group_name == "test-rg"
        assert monitor.subscription_id == "sub-123"

    def test_init_requires_resource_group(self) -> None:
        """Test that empty resource_group_name raises ValueError."""
        with pytest.raises(
            ValueError, match="resource_group_name and subscription_id are required"
        ):
            ContainerMonitor(
                resource_group_name="",
                subscription_id="sub-123",
            )

    def test_init_requires_subscription_id(self) -> None:
        """Test that empty subscription_id raises ValueError."""
        with pytest.raises(
            ValueError, match="resource_group_name and subscription_id are required"
        ):
            ContainerMonitor(
                resource_group_name="test-rg",
                subscription_id="",
            )

    def test_init_rejects_none_resource_group(self) -> None:
        """Test that None resource_group_name raises ValueError."""
        with pytest.raises(
            ValueError, match="resource_group_name and subscription_id are required"
        ):
            ContainerMonitor(
                resource_group_name=None,  # type: ignore[arg-type]
                subscription_id="sub-123",
            )

    def test_init_rejects_none_subscription_id(self) -> None:
        """Test that None subscription_id raises ValueError."""
        with pytest.raises(
            ValueError, match="resource_group_name and subscription_id are required"
        ):
            ContainerMonitor(
                resource_group_name="test-rg",
                subscription_id=None,  # type: ignore[arg-type]
            )


class TestContainerMonitorGetStatus:
    """Tests for the get_status method."""

    @pytest.mark.asyncio
    async def test_get_status_requires_app_name(self) -> None:
        """Test that get_status raises ValueError for empty app_name."""
        monitor = ContainerMonitor(
            resource_group_name="test-rg",
            subscription_id="sub-123",
        )

        with pytest.raises(ValueError, match="App name is required"):
            await monitor.get_status("")

    @pytest.mark.asyncio
    async def test_get_status_returns_running_status(self) -> None:
        """Test that get_status returns running_status when available."""
        mock_app = MagicMock()
        mock_app.running_status = "Running"
        mock_app.provisioning_state = "Succeeded"

        # Mock the lazy import of ContainerAppsAPIClient
        with (
            patch("azure_haymaker.orchestrator.container_monitor.DefaultAzureCredential"),
            patch.dict("sys.modules", {"azure.mgmt.appcontainers": MagicMock()}),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_to_thread.return_value = mock_app

            monitor = ContainerMonitor(
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )

            status = await monitor.get_status("test-app")

        assert status == "Running"

    @pytest.mark.asyncio
    async def test_get_status_falls_back_to_provisioning_state(self) -> None:
        """Test that get_status falls back to provisioning_state."""
        mock_app = MagicMock()
        mock_app.running_status = None
        mock_app.provisioning_state = "Succeeded"

        with (
            patch("azure_haymaker.orchestrator.container_monitor.DefaultAzureCredential"),
            patch.dict("sys.modules", {"azure.mgmt.appcontainers": MagicMock()}),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_to_thread.return_value = mock_app

            monitor = ContainerMonitor(
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )

            status = await monitor.get_status("test-app")

        assert status == "Succeeded"

    @pytest.mark.asyncio
    async def test_get_status_returns_unknown_when_no_status(self) -> None:
        """Test that get_status returns 'Unknown' when no status available."""
        mock_app = MagicMock(spec=[])  # Empty spec means no attributes
        # Don't set running_status or provisioning_state

        with (
            patch("azure_haymaker.orchestrator.container_monitor.DefaultAzureCredential"),
            patch.dict("sys.modules", {"azure.mgmt.appcontainers": MagicMock()}),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_to_thread.return_value = mock_app

            monitor = ContainerMonitor(
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )

            status = await monitor.get_status("test-app")

        assert status == "Unknown"

    @pytest.mark.asyncio
    async def test_get_status_raises_error_when_not_found(self) -> None:
        """Test that get_status raises ContainerAppError when app not found."""
        with (
            patch("azure_haymaker.orchestrator.container_monitor.DefaultAzureCredential"),
            patch.dict("sys.modules", {"azure.mgmt.appcontainers": MagicMock()}),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_to_thread.side_effect = ResourceNotFoundError("Not found")

            monitor = ContainerMonitor(
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )

            with pytest.raises(ContainerAppError, match="not found"):
                await monitor.get_status("nonexistent-app")

    @pytest.mark.asyncio
    async def test_get_status_raises_error_on_api_failure(self) -> None:
        """Test that get_status raises ContainerAppError on API failure."""
        with (
            patch("azure_haymaker.orchestrator.container_monitor.DefaultAzureCredential"),
            patch.dict("sys.modules", {"azure.mgmt.appcontainers": MagicMock()}),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_to_thread.side_effect = Exception("Azure API error")

            monitor = ContainerMonitor(
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )

            with pytest.raises(ContainerAppError, match="Failed to get container status"):
                await monitor.get_status("test-app")


class TestGetContainerStatusFunction:
    """Tests for the standalone get_container_status function."""

    @pytest.mark.asyncio
    async def test_get_container_status_requires_app_name(self) -> None:
        """Test that empty app_name raises ValueError."""
        with pytest.raises(
            ValueError, match="app_name, resource_group_name, and subscription_id are required"
        ):
            await get_container_status(
                app_name="",
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )

    @pytest.mark.asyncio
    async def test_get_container_status_requires_resource_group(self) -> None:
        """Test that empty resource_group_name raises ValueError."""
        with pytest.raises(
            ValueError, match="app_name, resource_group_name, and subscription_id are required"
        ):
            await get_container_status(
                app_name="test-app",
                resource_group_name="",
                subscription_id="sub-123",
            )

    @pytest.mark.asyncio
    async def test_get_container_status_requires_subscription(self) -> None:
        """Test that empty subscription_id raises ValueError."""
        with pytest.raises(
            ValueError, match="app_name, resource_group_name, and subscription_id are required"
        ):
            await get_container_status(
                app_name="test-app",
                resource_group_name="test-rg",
                subscription_id="",
            )

    @pytest.mark.asyncio
    async def test_get_container_status_delegates_to_monitor(self) -> None:
        """Test that function delegates to ContainerMonitor."""
        with patch(
            "azure_haymaker.orchestrator.container_monitor.ContainerMonitor"
        ) as mock_monitor_cls:
            mock_instance = MagicMock()
            mock_instance.get_status = AsyncMock(return_value="Running")
            mock_monitor_cls.return_value = mock_instance

            result = await get_container_status(
                app_name="test-app",
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )

            assert result == "Running"
            mock_monitor_cls.assert_called_once_with(
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )
            mock_instance.get_status.assert_called_once_with("test-app")


class TestContainerAppErrorFromMonitor:
    """Tests for ContainerAppError in monitor context."""

    def test_error_contains_app_name(self) -> None:
        """Test that error message can include app name."""
        error = ContainerAppError("Container app my-app not found: Resource not found")
        assert "my-app" in str(error)

    def test_error_is_chainable(self) -> None:
        """Test that ContainerAppError can chain from other exceptions."""
        original = ResourceNotFoundError("Original error")
        error = ContainerAppError("Wrapper error")
        error.__cause__ = original

        assert error.__cause__ == original


class TestContainerMonitorStatusValues:
    """Tests for different status values returned by get_status."""

    @pytest.mark.parametrize(
        ("running_status", "provisioning_state", "expected"),
        [
            ("Running", "Succeeded", "Running"),
            ("Terminating", "Succeeded", "Terminating"),
            ("Failed", "Failed", "Failed"),
            (None, "InProgress", "InProgress"),
            (None, "Updating", "Updating"),
            ("", "Succeeded", "Succeeded"),  # Empty string falls back
        ],
    )
    @pytest.mark.asyncio
    async def test_get_status_various_states(
        self, running_status: str | None, provisioning_state: str, expected: str
    ) -> None:
        """Test get_status with various state combinations."""
        mock_app = MagicMock()
        if running_status is not None:
            mock_app.running_status = running_status if running_status else None
        else:
            mock_app.running_status = None
        mock_app.provisioning_state = provisioning_state

        with (
            patch("azure_haymaker.orchestrator.container_monitor.DefaultAzureCredential"),
            patch.dict("sys.modules", {"azure.mgmt.appcontainers": MagicMock()}),
            patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        ):
            mock_to_thread.return_value = mock_app

            monitor = ContainerMonitor(
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )

            status = await monitor.get_status("test-app")

        assert status == expected
