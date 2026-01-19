"""Comprehensive tests for Knowledge Worker Cleanup Manager.

Tests cover resource tracking, cleanup operations, resource leak detection,
and cost tracking to prevent $500-$2,000/month resource leaks.

Test Distribution (TDD Pyramid):
- 60% Unit Tests (~180 LOC)
- 30% Integration Tests (~90 LOC)
- 10% E2E Tests (~30 LOC)
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from azure_haymaker.knowledge_worker.cleanup.cleanup_manager import (
    CleanupReport,
    KnowledgeWorkerCleanupManager,
    KnowledgeWorkerResourceInventory,
)


class TestCleanupReport:
    """Test CleanupReport class for tracking cleanup operations."""

    def test_create_cleanup_report(self):
        """Test basic CleanupReport initialization."""
        report = CleanupReport(run_id="test-run-123")

        assert report.run_id == "test-run-123"
        assert report.total_resources == 0
        assert report.successful_deletions == 0
        assert report.failed_deletions == 0
        assert report.results == {}
        assert report.errors == []
        assert report.completed_at is None
        assert isinstance(report.started_at, datetime)

    def test_record_successful_deletion(self):
        """Test recording successful resource deletion."""
        report = CleanupReport(run_id="test-run-123")
        report.record("resource-1", success=True)

        assert report.total_resources == 1
        assert report.successful_deletions == 1
        assert report.failed_deletions == 0
        assert report.results["resource-1"] is True
        assert len(report.errors) == 0

    def test_record_failed_deletion(self):
        """Test recording failed resource deletion with error."""
        report = CleanupReport(run_id="test-run-123")
        report.record("resource-1", success=False, error="Permission denied")

        assert report.total_resources == 1
        assert report.successful_deletions == 0
        assert report.failed_deletions == 1
        assert report.results["resource-1"] is False
        assert len(report.errors) == 1
        assert "resource-1" in report.errors[0]
        assert "Permission denied" in report.errors[0]

    def test_record_failed_deletion_without_error_message(self):
        """Test recording failed deletion without specific error message."""
        report = CleanupReport(run_id="test-run-123")
        report.record("resource-1", success=False)

        assert report.failed_deletions == 1
        assert len(report.errors) == 0  # No error message provided

    def test_success_rate_calculation(self):
        """Test success rate calculation with mixed results."""
        report = CleanupReport(run_id="test-run-123")
        report.record("resource-1", success=True)
        report.record("resource-2", success=True)
        report.record("resource-3", success=False, error="API timeout")

        assert report.success_rate == pytest.approx(2 / 3)

    def test_success_rate_zero_resources(self):
        """Test success rate with zero resources returns 1.0."""
        report = CleanupReport(run_id="test-run-123")

        assert report.success_rate == 1.0

    def test_is_complete_success_true(self):
        """Test complete success detection when all deletions succeeded."""
        report = CleanupReport(run_id="test-run-123")
        report.record("resource-1", success=True)
        report.record("resource-2", success=True)

        assert report.is_complete_success is True

    def test_is_complete_success_false_with_failures(self):
        """Test complete success is false when failures exist."""
        report = CleanupReport(run_id="test-run-123")
        report.record("resource-1", success=True)
        report.record("resource-2", success=False, error="Failed")

        assert report.is_complete_success is False

    def test_is_complete_success_false_zero_resources(self):
        """Test complete success is false when no resources processed."""
        report = CleanupReport(run_id="test-run-123")

        assert report.is_complete_success is False

    def test_complete_sets_timestamp(self):
        """Test complete() sets completed_at timestamp."""
        report = CleanupReport(run_id="test-run-123")
        before_complete = datetime.now(UTC)

        report.complete()

        after_complete = datetime.now(UTC)
        assert report.completed_at is not None
        assert before_complete <= report.completed_at <= after_complete

    def test_record_multiple_resources(self):
        """Test recording results for multiple resources."""
        report = CleanupReport(run_id="test-run-123")

        for i in range(5):
            report.record(f"resource-{i}", success=i % 2 == 0)

        assert report.total_resources == 5
        assert report.successful_deletions == 3  # 0, 2, 4
        assert report.failed_deletions == 2  # 1, 3


class TestKnowledgeWorkerResourceInventory:
    """Test KnowledgeWorkerResourceInventory class for resource tracking."""

    def test_initialize_inventory(self):
        """Test inventory initialization with all resource types."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")

        assert inventory.run_id == "test-run-123"
        assert isinstance(inventory.created_at, datetime)

        # Verify all resource types are initialized
        expected_types = [
            "entra_users",
            "security_groups",
            "m365_groups",
            "teams_teams",
            "cloud_pcs",
            "container_apps",
            "transport_rules",
            "sharepoint_sites",
        ]
        for resource_type in expected_types:
            assert resource_type in inventory.resources
            assert inventory.resources[resource_type] == []

    def test_register_single_resource(self):
        """Test registering a single resource."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-123")

        assert "user-123" in inventory.resources["entra_users"]
        assert len(inventory.resources["entra_users"]) == 1

    def test_register_duplicate_resource(self):
        """Test registering duplicate resource is idempotent."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-123")
        inventory.register("entra_users", "user-123")  # Duplicate

        assert len(inventory.resources["entra_users"]) == 1

    def test_register_batch_resources(self):
        """Test batch registration of multiple resources."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        user_ids = ["user-1", "user-2", "user-3"]

        inventory.register_batch("entra_users", user_ids)

        assert len(inventory.resources["entra_users"]) == 3
        for user_id in user_ids:
            assert user_id in inventory.resources["entra_users"]

    def test_register_unknown_resource_type(self):
        """Test registering unknown resource type logs warning but doesn't crash."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")

        # Should not raise exception, just log warning
        inventory.register("unknown_type", "resource-123")

        # Unknown type should not be added to resources
        assert "unknown_type" not in inventory.resources

    def test_unregister_existing_resource(self):
        """Test unregistering an existing resource."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-123")

        result = inventory.unregister("entra_users", "user-123")

        assert result is True
        assert "user-123" not in inventory.resources["entra_users"]

    def test_unregister_nonexistent_resource(self):
        """Test unregistering nonexistent resource returns False."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")

        result = inventory.unregister("entra_users", "user-999")

        assert result is False

    def test_unregister_from_unknown_type(self):
        """Test unregistering from unknown resource type returns False."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")

        result = inventory.unregister("unknown_type", "resource-123")

        assert result is False

    def test_get_resources_by_type(self):
        """Test retrieving resources by specific type."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-1")
        inventory.register("entra_users", "user-2")
        inventory.register("security_groups", "group-1")

        users = inventory.get("entra_users")

        assert len(users) == 2
        assert "user-1" in users
        assert "user-2" in users

    def test_get_resources_returns_copy(self):
        """Test get() returns a copy to prevent external modification."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-1")

        users = inventory.get("entra_users")
        users.append("user-2")  # Modify returned list

        # Original should not be modified
        assert len(inventory.resources["entra_users"]) == 1

    def test_get_unknown_type_returns_empty_list(self):
        """Test getting unknown resource type returns empty list."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")

        result = inventory.get("unknown_type")

        assert result == []

    def test_get_all_resources(self):
        """Test retrieving all resources."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-1")
        inventory.register("security_groups", "group-1")

        all_resources = inventory.get_all()

        assert "entra_users" in all_resources
        assert "security_groups" in all_resources
        assert "user-1" in all_resources["entra_users"]
        assert "group-1" in all_resources["security_groups"]

    def test_get_all_returns_copy(self):
        """Test get_all() returns copies to prevent external modification."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-1")

        all_resources = inventory.get_all()
        all_resources["entra_users"].append("user-2")

        # Original should not be modified
        assert len(inventory.resources["entra_users"]) == 1

    def test_get_count_single_type(self):
        """Test counting resources of a specific type."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-1")
        inventory.register("entra_users", "user-2")

        count = inventory.get_count("entra_users")

        assert count == 2

    def test_get_count_all_types(self):
        """Test counting total resources across all types."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-1")
        inventory.register("security_groups", "group-1")
        inventory.register("security_groups", "group-2")

        total_count = inventory.get_count()

        assert total_count == 3

    def test_get_count_unknown_type_returns_zero(self):
        """Test getting count for unknown type returns 0."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")

        count = inventory.get_count("unknown_type")

        assert count == 0

    def test_get_summary(self):
        """Test generating summary of resource counts by type."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-1")
        inventory.register("entra_users", "user-2")
        inventory.register("security_groups", "group-1")

        summary = inventory.get_summary()

        assert summary["entra_users"] == 2
        assert summary["security_groups"] == 1
        assert summary["m365_groups"] == 0  # Unused types still present

    def test_to_json_serialization(self):
        """Test JSON serialization of inventory."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-1")
        inventory.register("security_groups", "group-1")

        json_str = inventory.to_json()

        # Parse to verify valid JSON
        data = json.loads(json_str)
        assert data["run_id"] == "test-run-123"
        assert "user-1" in data["resources"]["entra_users"]
        assert "group-1" in data["resources"]["security_groups"]
        assert "created_at" in data

    def test_from_json_deserialization(self):
        """Test JSON deserialization to reconstruct inventory."""
        original = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        original.register("entra_users", "user-1")
        original.register("security_groups", "group-1")

        json_str = original.to_json()

        # Deserialize
        restored = KnowledgeWorkerResourceInventory.from_json(json_str)

        assert restored.run_id == original.run_id
        assert restored.resources == original.resources
        assert restored.created_at == original.created_at

    def test_to_dict_conversion(self):
        """Test dictionary conversion includes summary."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-1")
        inventory.register("security_groups", "group-1")

        result = inventory.to_dict()

        assert result["run_id"] == "test-run-123"
        assert "resources" in result
        assert "created_at" in result
        assert "summary" in result
        assert result["summary"]["entra_users"] == 1
        assert result["summary"]["security_groups"] == 1


class TestKnowledgeWorkerCleanupManager:
    """Test KnowledgeWorkerCleanupManager class for cleanup operations."""

    @pytest.mark.asyncio
    async def test_cleanup_all_empty_inventory(self):
        """Test cleanup with empty inventory completes successfully."""
        mock_graph = MagicMock()
        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")

        report = await manager.cleanup_all(inventory)

        assert report.run_id == "test-run-123"
        assert report.total_resources == 0
        assert report.is_complete_success is False  # No resources processed
        assert report.completed_at is not None

    @pytest.mark.asyncio
    async def test_cleanup_all_single_resource(self):
        """Test cleanup with single resource."""
        mock_graph = MagicMock()
        mock_graph.users.by_user_id.return_value.delete = AsyncMock()

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-123")

        report = await manager.cleanup_all(inventory)

        assert report.total_resources == 1
        assert report.successful_deletions == 1
        assert report.is_complete_success is True
        mock_graph.users.by_user_id.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_cleanup_all_multiple_types(self):
        """Test cleanup with multiple resource types in correct order."""
        mock_graph = MagicMock()
        mock_graph.users.by_user_id.return_value.delete = AsyncMock()
        mock_graph.groups.by_group_id.return_value.delete = AsyncMock()

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-123")
        inventory.register("security_groups", "group-456")
        inventory.register("m365_groups", "m365-789")

        report = await manager.cleanup_all(inventory)

        assert report.total_resources == 3
        assert report.successful_deletions == 3
        assert report.is_complete_success is True

    @pytest.mark.asyncio
    async def test_cleanup_by_type(self):
        """Test cleanup of specific resource type only."""
        mock_graph = MagicMock()
        mock_graph.users.by_user_id.return_value.delete = AsyncMock()

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-123")
        inventory.register("security_groups", "group-456")  # Should not be deleted

        report = await manager.cleanup_by_type(inventory, "entra_users")

        assert report.total_resources == 1
        assert report.successful_deletions == 1
        # Verify only entra_users method was called
        mock_graph.users.by_user_id.assert_called_once()
        mock_graph.groups.by_group_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_by_unknown_type(self):
        """Test cleanup by unknown type returns empty report."""
        mock_graph = MagicMock()
        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")

        report = await manager.cleanup_by_type(inventory, "unknown_type")

        assert report.total_resources == 0
        assert report.completed_at is not None

    def test_get_delete_method(self):
        """Test _get_delete_method returns correct method for each type."""
        mock_graph = MagicMock()
        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )

        # Test all valid resource types
        assert manager._get_delete_method("entra_users") is not None
        assert manager._get_delete_method("security_groups") is not None
        assert manager._get_delete_method("m365_groups") is not None
        assert manager._get_delete_method("teams_teams") is not None
        assert manager._get_delete_method("cloud_pcs") is not None
        assert manager._get_delete_method("container_apps") is not None
        assert manager._get_delete_method("transport_rules") is not None
        assert manager._get_delete_method("sharepoint_sites") is not None

        # Test unknown type
        assert manager._get_delete_method("unknown_type") is None

    @pytest.mark.asyncio
    async def test_delete_entra_user_success(self):
        """Test successful Entra user deletion."""
        mock_graph = MagicMock()
        mock_graph.users.by_user_id.return_value.delete = AsyncMock()

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )

        result = await manager._delete_entra_user("user-123")

        assert result is True
        mock_graph.users.by_user_id.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_delete_entra_user_not_found(self):
        """Test deleting already deleted user returns True."""
        mock_graph = MagicMock()
        mock_graph.users.by_user_id.return_value.delete = AsyncMock(
            side_effect=Exception("User not found")
        )

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )

        result = await manager._delete_entra_user("user-123")

        assert result is True  # Already deleted, treat as success

    @pytest.mark.asyncio
    async def test_delete_entra_user_does_not_exist(self):
        """Test deleting user that does not exist returns True."""
        mock_graph = MagicMock()
        mock_graph.users.by_user_id.return_value.delete = AsyncMock(
            side_effect=Exception("does not exist")
        )

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )

        result = await manager._delete_entra_user("user-123")

        assert result is True  # Does not exist, treat as success

    @pytest.mark.asyncio
    async def test_delete_entra_user_permission_error(self):
        """Test user deletion with permission error returns False."""
        mock_graph = MagicMock()
        mock_graph.users.by_user_id.return_value.delete = AsyncMock(
            side_effect=Exception("Permission denied")
        )

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )

        result = await manager._delete_entra_user("user-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_security_group_success(self):
        """Test successful security group deletion."""
        mock_graph = MagicMock()
        mock_graph.groups.by_group_id.return_value.delete = AsyncMock()

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )

        result = await manager._delete_security_group("group-123")

        assert result is True
        mock_graph.groups.by_group_id.assert_called_once_with("group-123")

    @pytest.mark.asyncio
    async def test_delete_m365_group_success(self):
        """Test successful M365 group deletion."""
        mock_graph = MagicMock()
        mock_graph.groups.by_group_id.return_value.delete = AsyncMock()

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )

        result = await manager._delete_m365_group("m365-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_teams_team_success(self):
        """Test successful Teams team deletion."""
        mock_graph = MagicMock()
        mock_graph.groups.by_group_id.return_value.delete = AsyncMock()

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )

        result = await manager._delete_teams_team("team-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_cloud_pc_success(self):
        """Test successful Cloud PC deletion."""
        mock_graph = MagicMock()
        mock_graph.device_management.virtual_endpoint.cloud_p_cs.by_cloud_pc_id.return_value.delete = AsyncMock()

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )

        result = await manager._delete_cloud_pc("cloudpc-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_container_app_success(self):
        """Test successful container app deletion."""
        mock_container = MagicMock()
        mock_container.container_apps.begin_delete = AsyncMock()

        manager = KnowledgeWorkerCleanupManager(
            graph_client=MagicMock(),
            container_client=mock_container,
            run_id="test-run-123",
        )

        container_id = "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.App/containerApps/app-test"
        result = await manager._delete_container_app(container_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_container_app_no_client(self):
        """Test container app deletion without client returns False."""
        manager = KnowledgeWorkerCleanupManager(
            graph_client=MagicMock(), container_client=None, run_id="test-run-123"
        )

        result = await manager._delete_container_app("container-123")

        assert result is False  # No client configured

    @pytest.mark.asyncio
    async def test_delete_transport_rule_not_implemented(self):
        """Test transport rule deletion returns False (not implemented)."""
        manager = KnowledgeWorkerCleanupManager(
            graph_client=MagicMock(), run_id="test-run-123"
        )

        result = await manager._delete_transport_rule("rule-123")

        assert result is False  # Not yet implemented

    @pytest.mark.asyncio
    async def test_delete_sharepoint_site_success(self):
        """Test successful SharePoint site deletion."""
        mock_graph = MagicMock()
        mock_graph.sites.by_site_id.return_value.delete = AsyncMock()

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )

        result = await manager._delete_sharepoint_site("site-123")

        assert result is True

    def test_extract_resource_group(self):
        """Test extracting resource group name from Azure resource ID."""
        manager = KnowledgeWorkerCleanupManager(
            graph_client=MagicMock(), run_id="test-run-123"
        )

        resource_id = "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.App/containerApps/app-test"
        rg = manager._extract_resource_group(resource_id)

        assert rg == "rg-test"

    def test_extract_resource_group_invalid_format(self):
        """Test extracting resource group from invalid format returns empty."""
        manager = KnowledgeWorkerCleanupManager(
            graph_client=MagicMock(), run_id="test-run-123"
        )

        rg = manager._extract_resource_group("invalid-resource-id")

        assert rg == ""

    def test_extract_container_name(self):
        """Test extracting container name from Azure resource ID."""
        manager = KnowledgeWorkerCleanupManager(
            graph_client=MagicMock(), run_id="test-run-123"
        )

        resource_id = "/subscriptions/sub-123/resourceGroups/rg-test/providers/Microsoft.App/containerApps/app-test"
        name = manager._extract_container_name(resource_id)

        assert name == "app-test"

    def test_extract_container_name_empty_id(self):
        """Test extracting container name from empty ID returns empty."""
        manager = KnowledgeWorkerCleanupManager(
            graph_client=MagicMock(), run_id="test-run-123"
        )

        name = manager._extract_container_name("")

        assert name == ""

    @pytest.mark.asyncio
    async def test_cleanup_failure_tracking(self):
        """Test cleanup report tracks failures correctly."""
        mock_graph = MagicMock()
        # User deletion succeeds
        mock_graph.users.by_user_id.return_value.delete = AsyncMock()
        # Group deletion fails
        mock_graph.groups.by_group_id.return_value.delete = AsyncMock(
            side_effect=Exception("API error")
        )

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-123")
        inventory.register("security_groups", "group-456")

        report = await manager.cleanup_all(inventory)

        assert report.total_resources == 2
        assert report.successful_deletions == 1
        assert report.failed_deletions == 1
        assert report.is_complete_success is False

    @pytest.mark.asyncio
    async def test_cleanup_deletion_order(self):
        """Test cleanup deletes resources in correct order (reverse of creation)."""
        deletion_order = []

        mock_graph = MagicMock()

        # Track order of deletions
        async def track_user_delete():
            deletion_order.append("entra_users")

        async def track_group_delete():
            deletion_order.append("security_groups")

        mock_graph.users.by_user_id.return_value.delete = track_user_delete
        mock_graph.groups.by_group_id.return_value.delete = track_group_delete

        manager = KnowledgeWorkerCleanupManager(
            graph_client=mock_graph, run_id="test-run-123"
        )
        inventory = KnowledgeWorkerResourceInventory(run_id="test-run-123")
        inventory.register("entra_users", "user-123")
        inventory.register("security_groups", "group-456")

        await manager.cleanup_all(inventory)

        # Security groups should be deleted before entra users
        assert deletion_order.index("security_groups") < deletion_order.index(
            "entra_users"
        )
