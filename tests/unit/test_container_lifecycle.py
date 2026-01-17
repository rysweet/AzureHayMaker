"""Unit tests for container_lifecycle module.

Tests for Container App lifecycle management including deletion and cleanup operations.

This module tests:
- ContainerLifecycle initialization
- delete method
- exists method
- get_status method
- Standalone delete_container_app function
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from azure_haymaker.orchestrator.container_lifecycle import (
    ContainerAppError,
    ContainerLifecycle,
    delete_container_app,
)
from azure_haymaker.orchestrator.repositories.base_repository import RepositoryError


class TestContainerLifecycleInit:
    """Tests for ContainerLifecycle initialization."""

    def test_init_with_valid_params(self) -> None:
        """Test successful initialization with valid parameters."""
        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
        )

        assert lifecycle.resource_group_name == "test-rg"
        assert lifecycle.subscription_id == "sub-123"

    def test_init_requires_resource_group(self) -> None:
        """Test that empty resource_group_name raises ValueError."""
        with pytest.raises(
            ValueError, match="resource_group_name and subscription_id are required"
        ):
            ContainerLifecycle(
                resource_group_name="",
                subscription_id="sub-123",
            )

    def test_init_requires_subscription_id(self) -> None:
        """Test that empty subscription_id raises ValueError."""
        with pytest.raises(
            ValueError, match="resource_group_name and subscription_id are required"
        ):
            ContainerLifecycle(
                resource_group_name="test-rg",
                subscription_id="",
            )

    def test_init_with_custom_repository(self) -> None:
        """Test initialization with injected repository."""
        mock_repo = MagicMock()

        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        assert lifecycle._repository == mock_repo


class TestContainerLifecycleDelete:
    """Tests for the delete method."""

    @pytest.mark.asyncio
    async def test_delete_requires_app_name(self) -> None:
        """Test that delete raises ValueError for empty app_name."""
        mock_repo = MagicMock()
        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        with pytest.raises(ValueError, match="App name is required"):
            await lifecycle.delete("")

    @pytest.mark.asyncio
    async def test_delete_returns_true_on_success(self) -> None:
        """Test that delete returns True when app is deleted."""
        mock_repo = MagicMock()
        mock_repo.delete = AsyncMock(return_value=True)

        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        result = await lifecycle.delete("test-app")

        assert result is True
        mock_repo.delete.assert_called_once_with("test-app")

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(self) -> None:
        """Test that delete returns False when app is not found."""
        mock_repo = MagicMock()
        mock_repo.delete = AsyncMock(return_value=False)

        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        result = await lifecycle.delete("nonexistent-app")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_raises_container_error_on_failure(self) -> None:
        """Test that delete raises ContainerAppError on repository failure."""
        mock_repo = MagicMock()
        mock_repo.delete = AsyncMock(side_effect=RepositoryError("Azure API error"))

        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        with pytest.raises(ContainerAppError, match="Failed to delete container app"):
            await lifecycle.delete("test-app")


class TestContainerLifecycleExists:
    """Tests for the exists method."""

    @pytest.mark.asyncio
    async def test_exists_requires_app_name(self) -> None:
        """Test that exists raises ValueError for empty app_name."""
        mock_repo = MagicMock()
        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        with pytest.raises(ValueError, match="App name is required"):
            await lifecycle.exists("")

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_found(self) -> None:
        """Test that exists returns True when app exists."""
        mock_repo = MagicMock()
        mock_repo.exists = AsyncMock(return_value=True)

        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        result = await lifecycle.exists("test-app")

        assert result is True
        mock_repo.exists.assert_called_once_with("test-app")

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_not_found(self) -> None:
        """Test that exists returns False when app doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.exists = AsyncMock(return_value=False)

        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        result = await lifecycle.exists("nonexistent-app")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_raises_container_error_on_failure(self) -> None:
        """Test that exists raises ContainerAppError on repository failure."""
        mock_repo = MagicMock()
        mock_repo.exists = AsyncMock(side_effect=RepositoryError("Azure API error"))

        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        with pytest.raises(ContainerAppError, match="Failed to check container app"):
            await lifecycle.exists("test-app")


class TestContainerLifecycleGetStatus:
    """Tests for the get_status method."""

    @pytest.mark.asyncio
    async def test_get_status_requires_app_name(self) -> None:
        """Test that get_status raises ValueError for empty app_name."""
        mock_repo = MagicMock()
        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        with pytest.raises(ValueError, match="App name is required"):
            await lifecycle.get_status("")

    @pytest.mark.asyncio
    async def test_get_status_returns_status(self) -> None:
        """Test that get_status returns the status string."""
        mock_repo = MagicMock()
        mock_repo.get_status = AsyncMock(return_value="Running")

        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        result = await lifecycle.get_status("test-app")

        assert result == "Running"
        mock_repo.get_status.assert_called_once_with("test-app")

    @pytest.mark.asyncio
    async def test_get_status_returns_none_when_not_found(self) -> None:
        """Test that get_status returns None when app doesn't exist."""
        mock_repo = MagicMock()
        mock_repo.get_status = AsyncMock(return_value=None)

        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        result = await lifecycle.get_status("nonexistent-app")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_status_raises_container_error_on_failure(self) -> None:
        """Test that get_status raises ContainerAppError on repository failure."""
        mock_repo = MagicMock()
        mock_repo.get_status = AsyncMock(side_effect=RepositoryError("Azure API error"))

        lifecycle = ContainerLifecycle(
            resource_group_name="test-rg",
            subscription_id="sub-123",
            repository=mock_repo,
        )

        with pytest.raises(ContainerAppError, match="Failed to get container app status"):
            await lifecycle.get_status("test-app")


class TestDeleteContainerAppFunction:
    """Tests for the standalone delete_container_app function."""

    @pytest.mark.asyncio
    async def test_delete_container_app_requires_app_name(self) -> None:
        """Test that empty app_name raises ValueError."""
        with pytest.raises(
            ValueError, match="app_name, resource_group_name, and subscription_id are required"
        ):
            await delete_container_app(
                app_name="",
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )

    @pytest.mark.asyncio
    async def test_delete_container_app_requires_resource_group(self) -> None:
        """Test that empty resource_group_name raises ValueError."""
        with pytest.raises(
            ValueError, match="app_name, resource_group_name, and subscription_id are required"
        ):
            await delete_container_app(
                app_name="test-app",
                resource_group_name="",
                subscription_id="sub-123",
            )

    @pytest.mark.asyncio
    async def test_delete_container_app_requires_subscription(self) -> None:
        """Test that empty subscription_id raises ValueError."""
        with pytest.raises(
            ValueError, match="app_name, resource_group_name, and subscription_id are required"
        ):
            await delete_container_app(
                app_name="test-app",
                resource_group_name="test-rg",
                subscription_id="",
            )

    @pytest.mark.asyncio
    async def test_delete_container_app_delegates_to_lifecycle(self) -> None:
        """Test that function delegates to ContainerLifecycle."""
        with patch(
            "azure_haymaker.orchestrator.container_lifecycle.ContainerLifecycle"
        ) as mock_lifecycle_cls:
            mock_instance = MagicMock()
            mock_instance.delete = AsyncMock(return_value=True)
            mock_lifecycle_cls.return_value = mock_instance

            result = await delete_container_app(
                app_name="test-app",
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )

            assert result is True
            mock_lifecycle_cls.assert_called_once_with(
                resource_group_name="test-rg",
                subscription_id="sub-123",
            )
            mock_instance.delete.assert_called_once_with("test-app")


class TestContainerAppError:
    """Tests for ContainerAppError exception."""

    def test_container_app_error_is_exception(self) -> None:
        """Test that ContainerAppError is an Exception."""
        error = ContainerAppError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_container_app_error_preserves_message(self) -> None:
        """Test that error message is preserved."""
        error = ContainerAppError("Detailed error message")
        assert "Detailed error message" in str(error)
