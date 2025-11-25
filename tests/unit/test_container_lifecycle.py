"""
Unit tests for container_lifecycle module.

Tests cover:
- ContainerLifecycle class initialization
- Container app deletion (happy path and errors)
- Resource not found handling
- Standalone delete_container_app function

Testing approach:
- Mock Azure Container Apps SDK
- Test deletion workflow and error cases
"""

import sys
from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock, MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError

from azure_haymaker.orchestrator.container_lifecycle import (
    ContainerAppError,
    ContainerLifecycle,
    delete_container_app,
)


@contextmanager
def mock_container_apps_sdk(mock_client_instance):
    """Context manager to mock the azure.mgmt.appcontainers module for lazy imports."""
    mock_module = MagicMock()
    mock_module.ContainerAppsAPIClient = MagicMock(return_value=mock_client_instance)

    with patch.dict(sys.modules, {"azure.mgmt.appcontainers": mock_module}):
        yield


# ==============================================================================
# TESTS: Initialization
# ==============================================================================


def test_container_lifecycle_init():
    """Test ContainerLifecycle initialization."""
    lifecycle = ContainerLifecycle(
        resource_group_name="test-rg",
        subscription_id="sub-123",
    )

    assert lifecycle.resource_group_name == "test-rg"
    assert lifecycle.subscription_id == "sub-123"


def test_container_lifecycle_init_missing_params():
    """Test error when required parameters missing."""
    with pytest.raises(ValueError, match="resource_group_name and subscription_id are required"):
        ContainerLifecycle(resource_group_name="", subscription_id="sub-123")

    with pytest.raises(ValueError, match="resource_group_name and subscription_id are required"):
        ContainerLifecycle(resource_group_name="test-rg", subscription_id="")


# ==============================================================================
# TESTS: Delete Method
# ==============================================================================


@pytest.mark.asyncio
async def test_delete_happy_path():
    """Test successful container app deletion."""
    mock_poller = Mock()
    mock_poller.result = Mock(return_value=None)

    mock_container_apps = Mock()
    mock_container_apps.begin_delete = Mock(return_value=mock_poller)

    mock_client_instance = Mock()
    mock_client_instance.container_apps = mock_container_apps

    with mock_container_apps_sdk(mock_client_instance):
        lifecycle = ContainerLifecycle("test-rg", "sub-123")
        result = await lifecycle.delete("test-app")

        assert result is True
        mock_container_apps.begin_delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_empty_app_name():
    """Test error when app_name is empty."""
    mock_client_instance = Mock()

    with mock_container_apps_sdk(mock_client_instance):
        lifecycle = ContainerLifecycle("test-rg", "sub-123")

        with pytest.raises(ValueError, match="App name is required"):
            await lifecycle.delete("")


@pytest.mark.asyncio
async def test_delete_not_found():
    """Test deletion when container app doesn't exist."""
    mock_container_apps = Mock()
    mock_container_apps.begin_delete = Mock(side_effect=ResourceNotFoundError("Not found"))

    mock_client_instance = Mock()
    mock_client_instance.container_apps = mock_container_apps

    with mock_container_apps_sdk(mock_client_instance):
        lifecycle = ContainerLifecycle("test-rg", "sub-123")
        result = await lifecycle.delete("nonexistent-app")

        assert result is False


@pytest.mark.asyncio
async def test_delete_api_error():
    """Test error handling when API call fails."""
    mock_container_apps = Mock()
    mock_container_apps.begin_delete = Mock(side_effect=Exception("API error"))

    mock_client_instance = Mock()
    mock_client_instance.container_apps = mock_container_apps

    with mock_container_apps_sdk(mock_client_instance):
        lifecycle = ContainerLifecycle("test-rg", "sub-123")

        with pytest.raises(ContainerAppError, match="Failed to delete container app"):
            await lifecycle.delete("test-app")


# ==============================================================================
# TESTS: Standalone Function
# ==============================================================================


@pytest.mark.asyncio
async def test_delete_container_app_standalone_happy_path():
    """Test standalone delete_container_app function."""
    mock_poller = Mock()
    mock_poller.result = Mock(return_value=None)

    mock_container_apps = Mock()
    mock_container_apps.begin_delete = Mock(return_value=mock_poller)

    mock_client_instance = Mock()
    mock_client_instance.container_apps = mock_container_apps

    with mock_container_apps_sdk(mock_client_instance):
        result = await delete_container_app("test-app", "test-rg", "sub-123")

        assert result is True


@pytest.mark.asyncio
async def test_delete_container_app_standalone_missing_params():
    """Test standalone function with missing parameters."""
    mock_client_instance = Mock()

    with mock_container_apps_sdk(mock_client_instance):
        with pytest.raises(ValueError, match="app_name, resource_group_name, and subscription_id are required"):
            await delete_container_app("", "test-rg", "sub-123")

        with pytest.raises(ValueError, match="app_name, resource_group_name, and subscription_id are required"):
            await delete_container_app("test-app", "", "sub-123")

        with pytest.raises(ValueError, match="app_name, resource_group_name, and subscription_id are required"):
            await delete_container_app("test-app", "test-rg", "")
