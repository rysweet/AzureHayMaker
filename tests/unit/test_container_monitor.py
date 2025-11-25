"""
Unit tests for container_monitor module.

Tests cover:
- ContainerMonitor class initialization
- Status checking for container apps
- Error handling (not found, API failures)
- Standalone get_container_status function

Testing approach:
- Mock Azure Container Apps SDK using sys.modules patching
- The ContainerAppsAPIClient is imported inside the async methods (lazy import)
- We need to patch at azure.mgmt.appcontainers level, not at the module level
"""

import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError

from azure_haymaker.orchestrator.container_monitor import (
    ContainerAppError,
    ContainerMonitor,
    get_container_status,
)


@contextmanager
def mock_container_apps_sdk(mock_client_instance):
    """Context manager to mock the azure.mgmt.appcontainers module for lazy imports.

    The ContainerAppsAPIClient is imported inside the async methods, so we need to
    patch sys.modules to intercept the import.
    """
    mock_module = MagicMock()
    mock_module.ContainerAppsAPIClient = MagicMock(return_value=mock_client_instance)

    with patch.dict(sys.modules, {"azure.mgmt.appcontainers": mock_module}):
        yield


# ==============================================================================
# TESTS: Initialization
# ==============================================================================


def test_container_monitor_init():
    """Test ContainerMonitor initialization."""
    monitor = ContainerMonitor(
        resource_group_name="test-rg",
        subscription_id="sub-123",
    )

    assert monitor.resource_group_name == "test-rg"
    assert monitor.subscription_id == "sub-123"


def test_container_monitor_init_missing_params():
    """Test error when required parameters missing."""
    with pytest.raises(ValueError, match="resource_group_name and subscription_id are required"):
        ContainerMonitor(resource_group_name="", subscription_id="sub-123")

    with pytest.raises(ValueError, match="resource_group_name and subscription_id are required"):
        ContainerMonitor(resource_group_name="test-rg", subscription_id="")


# ==============================================================================
# TESTS: Get Status Method
# ==============================================================================


@pytest.mark.asyncio
async def test_get_status_happy_path_running_status():
    """Test getting status when container has running_status."""
    mock_app = Mock()
    mock_app.running_status = "Running"
    mock_app.provisioning_state = "Succeeded"

    mock_container_apps = Mock()
    mock_container_apps.get = Mock(return_value=mock_app)

    mock_client_instance = Mock()
    mock_client_instance.container_apps = mock_container_apps

    with mock_container_apps_sdk(mock_client_instance):
        monitor = ContainerMonitor("test-rg", "sub-123")
        status = await monitor.get_status("test-app")

    assert status == "Running"


@pytest.mark.asyncio
async def test_get_status_happy_path_provisioning_state():
    """Test getting status when only provisioning_state is available."""
    mock_app = Mock()
    mock_app.running_status = None
    mock_app.provisioning_state = "Provisioning"

    mock_container_apps = Mock()
    mock_container_apps.get = Mock(return_value=mock_app)

    mock_client_instance = Mock()
    mock_client_instance.container_apps = mock_container_apps

    with mock_container_apps_sdk(mock_client_instance):
        monitor = ContainerMonitor("test-rg", "sub-123")
        status = await monitor.get_status("test-app")

    assert status == "Provisioning"


@pytest.mark.asyncio
async def test_get_status_unknown():
    """Test getting status when neither running_status nor provisioning_state available."""
    mock_app = Mock(spec=[])  # No attributes

    mock_container_apps = Mock()
    mock_container_apps.get = Mock(return_value=mock_app)

    mock_client_instance = Mock()
    mock_client_instance.container_apps = mock_container_apps

    with mock_container_apps_sdk(mock_client_instance):
        monitor = ContainerMonitor("test-rg", "sub-123")
        status = await monitor.get_status("test-app")

    assert status == "Unknown"


@pytest.mark.asyncio
async def test_get_status_empty_app_name():
    """Test error when app_name is empty."""
    monitor = ContainerMonitor("test-rg", "sub-123")

    with pytest.raises(ValueError, match="App name is required"):
        await monitor.get_status("")


@pytest.mark.asyncio
async def test_get_status_not_found():
    """Test error when container app doesn't exist."""
    mock_container_apps = Mock()
    mock_container_apps.get = Mock(side_effect=ResourceNotFoundError("Not found"))

    mock_client_instance = Mock()
    mock_client_instance.container_apps = mock_container_apps

    with mock_container_apps_sdk(mock_client_instance):
        monitor = ContainerMonitor("test-rg", "sub-123")

        with pytest.raises(ContainerAppError, match="Container app test-app not found"):
            await monitor.get_status("test-app")


@pytest.mark.asyncio
async def test_get_status_api_error():
    """Test error handling when API call fails."""
    mock_container_apps = Mock()
    mock_container_apps.get = Mock(side_effect=Exception("API error"))

    mock_client_instance = Mock()
    mock_client_instance.container_apps = mock_container_apps

    with mock_container_apps_sdk(mock_client_instance):
        monitor = ContainerMonitor("test-rg", "sub-123")

        with pytest.raises(ContainerAppError, match="Failed to get container status"):
            await monitor.get_status("test-app")


# ==============================================================================
# TESTS: Standalone Function
# ==============================================================================


@pytest.mark.asyncio
async def test_get_container_status_standalone_happy_path():
    """Test standalone get_container_status function."""
    mock_app = Mock()
    mock_app.running_status = "Running"
    mock_app.provisioning_state = "Succeeded"

    mock_container_apps = Mock()
    mock_container_apps.get = Mock(return_value=mock_app)

    mock_client_instance = Mock()
    mock_client_instance.container_apps = mock_container_apps

    with mock_container_apps_sdk(mock_client_instance):
        status = await get_container_status("test-app", "test-rg", "sub-123")

    assert status == "Running"


@pytest.mark.asyncio
async def test_get_container_status_standalone_missing_params():
    """Test standalone function with missing parameters."""
    with pytest.raises(ValueError, match="app_name, resource_group_name, and subscription_id are required"):
        await get_container_status("", "test-rg", "sub-123")

    with pytest.raises(ValueError, match="app_name, resource_group_name, and subscription_id are required"):
        await get_container_status("test-app", "", "sub-123")

    with pytest.raises(ValueError, match="app_name, resource_group_name, and subscription_id are required"):
        await get_container_status("test-app", "test-rg", "")
