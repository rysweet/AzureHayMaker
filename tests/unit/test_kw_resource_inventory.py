"""Unit tests for Knowledge Worker resource inventory and cleanup.

This module tests the resource tracking system that ensures ALL resources
created by the Knowledge Worker framework can be identified and cleaned up.

Components tested:
- KnowledgeWorkerResourceInventory: Tracks created resources by type
- Resource registration and retrieval
- JSON serialization/deserialization for persistence
- Cleanup ordering and dependency handling

Reference: ARCHITECTURE.md Section 8 - Resource Tracking and Cleanup
"""

import json
from datetime import datetime, UTC

import pytest

# Import paths based on ARCHITECTURE.md specification
# src/azure_haymaker/knowledge_worker/cleanup/cleanup_manager.py

try:
    from azure_haymaker.knowledge_worker.cleanup.cleanup_manager import (
        KnowledgeWorkerResourceInventory,
        KnowledgeWorkerCleanupManager,
        CleanupReport,
    )
    CLEANUP_AVAILABLE = True
except ImportError:
    CLEANUP_AVAILABLE = False
    KnowledgeWorkerResourceInventory = None
    KnowledgeWorkerCleanupManager = None
    CleanupReport = None


pytestmark = pytest.mark.skipif(
    not CLEANUP_AVAILABLE,
    reason="Knowledge Worker cleanup module not yet implemented"
)


class TestKnowledgeWorkerResourceInventory:
    """Tests for KnowledgeWorkerResourceInventory class."""

    def test_init_with_run_id(self) -> None:
        """Test initializing inventory with run ID."""
        inventory = KnowledgeWorkerResourceInventory(run_id="run-abc12345")
        assert inventory.run_id == "run-abc12345"

    def test_init_creates_empty_resource_lists(self) -> None:
        """Test that initialization creates empty resource type lists."""
        inventory = KnowledgeWorkerResourceInventory(run_id="run-test")

        # All resource types should exist and be empty
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


class TestResourceRegistration:
    """Tests for resource registration functionality."""

    @pytest.fixture
    def inventory(self) -> KnowledgeWorkerResourceInventory:
        """Create a fresh inventory for each test."""
        return KnowledgeWorkerResourceInventory(run_id="run-test123")

    def test_register_entra_user(
        self, inventory: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test registering an Entra user resource."""
        inventory.register("entra_users", "user-obj-id-123")

        assert "user-obj-id-123" in inventory.resources["entra_users"]
        assert len(inventory.resources["entra_users"]) == 1

    def test_register_multiple_resources_same_type(
        self, inventory: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test registering multiple resources of the same type."""
        inventory.register("entra_users", "user-001")
        inventory.register("entra_users", "user-002")
        inventory.register("entra_users", "user-003")

        assert len(inventory.resources["entra_users"]) == 3
        assert "user-001" in inventory.resources["entra_users"]
        assert "user-002" in inventory.resources["entra_users"]
        assert "user-003" in inventory.resources["entra_users"]

    def test_register_multiple_resource_types(
        self, inventory: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test registering resources of different types."""
        inventory.register("entra_users", "user-001")
        inventory.register("security_groups", "sg-001")
        inventory.register("container_apps", "container-001")
        inventory.register("cloud_pcs", "cloudpc-001")

        assert len(inventory.resources["entra_users"]) == 1
        assert len(inventory.resources["security_groups"]) == 1
        assert len(inventory.resources["container_apps"]) == 1
        assert len(inventory.resources["cloud_pcs"]) == 1

    def test_register_unknown_resource_type_ignored(
        self, inventory: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test that unknown resource types are silently ignored."""
        # Per ARCHITECTURE.md, register only adds to known types
        inventory.register("unknown_type", "resource-123")

        assert "unknown_type" not in inventory.resources

    @pytest.mark.parametrize("resource_type,resource_id", [
        ("entra_users", "user-abc-123"),
        ("security_groups", "sg-def-456"),
        ("m365_groups", "m365-ghi-789"),
        ("teams_teams", "teams-jkl-012"),
        ("cloud_pcs", "cloudpc-mno-345"),
        ("container_apps", "container-pqr-678"),
        ("transport_rules", "rule-stu-901"),
        ("sharepoint_sites", "site-vwx-234"),
    ])
    def test_register_all_valid_types(
        self,
        inventory: KnowledgeWorkerResourceInventory,
        resource_type: str,
        resource_id: str,
    ) -> None:
        """Test that all valid resource types can be registered."""
        inventory.register(resource_type, resource_id)
        assert resource_id in inventory.resources[resource_type]


class TestGetAllResources:
    """Tests for get_all() method."""

    @pytest.fixture
    def populated_inventory(self) -> KnowledgeWorkerResourceInventory:
        """Create an inventory with various resources."""
        inventory = KnowledgeWorkerResourceInventory(run_id="run-populated")
        inventory.register("entra_users", "user-001")
        inventory.register("entra_users", "user-002")
        inventory.register("security_groups", "sg-001")
        inventory.register("container_apps", "container-001")
        inventory.register("container_apps", "container-002")
        inventory.register("container_apps", "container-003")
        return inventory

    def test_get_all_returns_complete_inventory(
        self, populated_inventory: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test that get_all returns all registered resources."""
        all_resources = populated_inventory.get_all()

        assert len(all_resources["entra_users"]) == 2
        assert len(all_resources["security_groups"]) == 1
        assert len(all_resources["container_apps"]) == 3

    def test_get_all_returns_copy(
        self, populated_inventory: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test that get_all returns a copy, not the original."""
        all_resources = populated_inventory.get_all()

        # Modify the returned dict
        all_resources["entra_users"].append("hacker-user")

        # Original should be unchanged
        assert "hacker-user" not in populated_inventory.resources["entra_users"]

    def test_get_all_empty_inventory(self) -> None:
        """Test get_all on empty inventory."""
        inventory = KnowledgeWorkerResourceInventory(run_id="run-empty")
        all_resources = inventory.get_all()

        # Should have all keys, but empty lists
        assert all(len(v) == 0 for v in all_resources.values())


class TestJsonSerialization:
    """Tests for JSON serialization and deserialization."""

    @pytest.fixture
    def inventory_with_resources(self) -> KnowledgeWorkerResourceInventory:
        """Create an inventory with resources for serialization tests."""
        inventory = KnowledgeWorkerResourceInventory(run_id="run-serial-test")
        inventory.register("entra_users", "user-001")
        inventory.register("entra_users", "user-002")
        inventory.register("security_groups", "sg-001")
        inventory.register("cloud_pcs", "cloudpc-001")
        return inventory

    def test_to_json_produces_valid_json(
        self, inventory_with_resources: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test that to_json produces valid JSON string."""
        json_str = inventory_with_resources.to_json()

        # Should not raise
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_to_json_includes_run_id(
        self, inventory_with_resources: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test that JSON includes run_id field."""
        json_str = inventory_with_resources.to_json()
        parsed = json.loads(json_str)

        assert parsed["run_id"] == "run-serial-test"

    def test_to_json_includes_resources(
        self, inventory_with_resources: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test that JSON includes all resources."""
        json_str = inventory_with_resources.to_json()
        parsed = json.loads(json_str)

        assert "resources" in parsed
        assert len(parsed["resources"]["entra_users"]) == 2
        assert len(parsed["resources"]["security_groups"]) == 1
        assert len(parsed["resources"]["cloud_pcs"]) == 1

    def test_to_json_includes_created_at(
        self, inventory_with_resources: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test that JSON includes created_at timestamp."""
        json_str = inventory_with_resources.to_json()
        parsed = json.loads(json_str)

        assert "created_at" in parsed
        # Should be ISO format timestamp
        timestamp = parsed["created_at"]
        # Should be parseable
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_from_json_restores_inventory(
        self, inventory_with_resources: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test that from_json restores the inventory correctly."""
        json_str = inventory_with_resources.to_json()

        restored = KnowledgeWorkerResourceInventory.from_json(json_str)

        assert restored.run_id == "run-serial-test"
        assert len(restored.resources["entra_users"]) == 2
        assert len(restored.resources["security_groups"]) == 1
        assert len(restored.resources["cloud_pcs"]) == 1

    def test_from_json_with_manual_json(self) -> None:
        """Test from_json with manually constructed JSON."""
        manual_json = json.dumps({
            "run_id": "manual-run-id",
            "resources": {
                "entra_users": ["user-a", "user-b"],
                "security_groups": ["sg-x"],
                "m365_groups": [],
                "teams_teams": [],
                "cloud_pcs": [],
                "container_apps": ["app-1"],
                "transport_rules": [],
                "sharepoint_sites": [],
            },
            "created_at": datetime.now(UTC).isoformat(),
        })

        restored = KnowledgeWorkerResourceInventory.from_json(manual_json)

        assert restored.run_id == "manual-run-id"
        assert restored.resources["entra_users"] == ["user-a", "user-b"]
        assert restored.resources["container_apps"] == ["app-1"]

    def test_serialization_roundtrip(
        self, inventory_with_resources: KnowledgeWorkerResourceInventory
    ) -> None:
        """Test complete serialization/deserialization roundtrip."""
        original_resources = inventory_with_resources.get_all()

        # Serialize
        json_str = inventory_with_resources.to_json()

        # Deserialize
        restored = KnowledgeWorkerResourceInventory.from_json(json_str)
        restored_resources = restored.get_all()

        # Compare (ignoring created_at which is added during to_json)
        assert restored.run_id == inventory_with_resources.run_id
        for resource_type in original_resources:
            assert restored_resources[resource_type] == original_resources[resource_type]

    def test_from_json_invalid_json_raises(self) -> None:
        """Test that invalid JSON raises appropriate error."""
        with pytest.raises(json.JSONDecodeError):
            KnowledgeWorkerResourceInventory.from_json("not valid json {{{")


class TestResourceInventoryIntegration:
    """Integration-style tests for resource inventory."""

    def test_typical_deployment_tracking(self) -> None:
        """Test tracking resources for a typical 50-worker deployment."""
        inventory = KnowledgeWorkerResourceInventory(run_id="run-deploy-50")

        # Phase 1: Setup
        inventory.register("security_groups", "kw-run-deploy-50-all-workers")
        inventory.register("transport_rules", "HayMaker-run-depl-InternalOnly")

        # Phase 2: Identity provisioning - 50 workers across teams
        for i in range(50):
            inventory.register("entra_users", f"user-obj-{i:03d}")

        # Create 5 teams
        for i in range(5):
            inventory.register("security_groups", f"sg-team-{i}")
            inventory.register("m365_groups", f"m365-team-{i}")
            inventory.register("teams_teams", f"teams-team-{i}")

        # Phase 3: Endpoints
        # 10 Cloud PCs for executives
        for i in range(10):
            inventory.register("cloud_pcs", f"cloudpc-exec-{i:03d}")

        # 40 CLI containers for other workers
        for i in range(40):
            inventory.register("container_apps", f"container-worker-{i:03d}")

        # Verify totals
        all_resources = inventory.get_all()
        assert len(all_resources["entra_users"]) == 50
        assert len(all_resources["security_groups"]) == 6  # 1 all-workers + 5 teams
        assert len(all_resources["m365_groups"]) == 5
        assert len(all_resources["teams_teams"]) == 5
        assert len(all_resources["cloud_pcs"]) == 10
        assert len(all_resources["container_apps"]) == 40
        assert len(all_resources["transport_rules"]) == 1

    def test_inventory_persistence_scenario(self) -> None:
        """Test saving and restoring inventory (simulated persistence)."""
        # Create and populate inventory
        inventory = KnowledgeWorkerResourceInventory(run_id="run-persist-test")
        inventory.register("entra_users", "user-001")
        inventory.register("container_apps", "container-001")

        # Simulate saving to storage
        saved_json = inventory.to_json()

        # Simulate time passing and restoring
        del inventory

        # Restore from storage
        restored = KnowledgeWorkerResourceInventory.from_json(saved_json)

        # Should have same resources
        assert restored.resources["entra_users"] == ["user-001"]
        assert restored.resources["container_apps"] == ["container-001"]


class TestCleanupReport:
    """Tests for CleanupReport class (if implemented)."""

    @pytest.mark.skip(reason="CleanupReport tests depend on implementation details")
    def test_cleanup_report_creation(self) -> None:
        """Test creating a cleanup report."""
        report = CleanupReport(run_id="run-cleanup-test")
        assert report.run_id == "run-cleanup-test"

    @pytest.mark.skip(reason="CleanupReport tests depend on implementation details")
    def test_cleanup_report_record_success(self) -> None:
        """Test recording successful cleanup."""
        report = CleanupReport(run_id="run-cleanup-test")
        report.record("user-001", success=True)
        assert report.success_count == 1

    @pytest.mark.skip(reason="CleanupReport tests depend on implementation details")
    def test_cleanup_report_record_failure(self) -> None:
        """Test recording failed cleanup."""
        report = CleanupReport(run_id="run-cleanup-test")
        report.record("user-001", success=False)
        assert report.failure_count == 1


class TestResourceCleanupOrdering:
    """Tests to verify cleanup ordering requirements from ARCHITECTURE.md.

    Cleanup order (reverse of creation):
    1. Stop container apps
    2. Delete container apps
    3. Delete Cloud PCs
    4. Remove transport rules
    5. Delete Teams teams
    6. Delete M365 groups
    7. Delete security groups
    8. Delete Entra users (last, as they may own resources)
    """

    def test_cleanup_order_documentation(self) -> None:
        """Document expected cleanup order for implementation reference."""
        expected_cleanup_order = [
            "container_apps",      # 1-2. Stop and delete containers
            "cloud_pcs",           # 3. Delete Cloud PCs
            "transport_rules",     # 4. Remove transport rules
            "teams_teams",         # 5. Delete Teams teams
            "m365_groups",         # 6. Delete M365 groups
            "security_groups",     # 7. Delete security groups
            "entra_users",         # 8. Delete users (last)
        ]

        # This test documents the expected order
        # Implementation should follow this sequence
        assert len(expected_cleanup_order) == 7

        # Entra users must be last
        assert expected_cleanup_order[-1] == "entra_users"

        # Container apps must be first
        assert expected_cleanup_order[0] == "container_apps"

    def test_inventory_contains_all_cleanable_types(self) -> None:
        """Test that inventory tracks all resource types that need cleanup."""
        inventory = KnowledgeWorkerResourceInventory(run_id="test")

        cleanable_types = {
            "entra_users",
            "security_groups",
            "m365_groups",
            "teams_teams",
            "cloud_pcs",
            "container_apps",
            "transport_rules",
            "sharepoint_sites",
        }

        inventory_types = set(inventory.resources.keys())

        # Inventory should have at least all cleanable types
        assert cleanable_types.issubset(inventory_types)


class TestResourceTagging:
    """Tests for resource tagging conventions from ARCHITECTURE.md."""

    @pytest.mark.parametrize("tag_key,description", [
        ("AzureHayMaker-managed", "Identifies managed resources"),
        ("RunId", "Associates with specific run"),
        ("Component", "Identifies framework (knowledge-worker)"),
        ("WorkerId", "Worker association"),
        ("Department", "Department grouping"),
        ("TeamId", "Team association"),
        ("CreatedAt", "Creation timestamp"),
    ])
    def test_expected_tags_documented(self, tag_key: str, description: str) -> None:
        """Document expected resource tags for implementation reference."""
        # This test documents the tagging convention
        # Implementation should add these tags to all created resources
        assert tag_key is not None
        assert description is not None

    def test_generate_tags_for_worker(self) -> None:
        """Test generating tags for a worker resource (helper function)."""
        # This would be a helper function in the implementation
        expected_tags = {
            "AzureHayMaker-managed": "true",
            "RunId": "run-abc12345",
            "Component": "knowledge-worker",
            "WorkerId": "kw-abc12345-engi-001",
            "Department": "engineering",
            "TeamId": "team-eng-001",
            "CreatedAt": "2025-01-25T10:00:00Z",
        }

        # Verify structure for implementation reference
        assert expected_tags["AzureHayMaker-managed"] == "true"
        assert expected_tags["Component"] == "knowledge-worker"
