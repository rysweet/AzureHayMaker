"""Tests for worker_registry module.

Comprehensive unit tests for the WorkerRegistry class including:
- Worker registration and unregistration
- Worker lookup operations
- UPN retrieval
- Department filtering
- Random recipient selection
- Registry queries
- Cleanup operations
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity, WorkerPersona
from azure_haymaker.knowledge_worker.worker_registry import WorkerRegistry

if TYPE_CHECKING:
    pass


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_workers() -> list[WorkerIdentity]:
    """Create sample worker identities for testing."""
    return [
        WorkerIdentity(
            worker_id="kw-eng-001",
            display_name="Alice Engineer",
            user_principal_name="alice@tenant.onmicrosoft.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        ),
        WorkerIdentity(
            worker_id="kw-eng-002",
            display_name="Bob Engineer",
            user_principal_name="bob@tenant.onmicrosoft.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        ),
        WorkerIdentity(
            worker_id="kw-hr-001",
            display_name="Carol HR",
            user_principal_name="carol@tenant.onmicrosoft.com",
            department="hr",
            persona=WorkerPersona.HR,
        ),
        WorkerIdentity(
            worker_id="kw-sales-001",
            display_name="Dave Sales",
            user_principal_name="dave@tenant.onmicrosoft.com",
            department="sales",
            persona=WorkerPersona.SALES,
        ),
        WorkerIdentity(
            worker_id="kw-exec-001",
            display_name="Eve Executive",
            user_principal_name="eve@tenant.onmicrosoft.com",
            department="executive",
            persona=WorkerPersona.EXECUTIVE,
        ),
    ]


@pytest.fixture
def populated_registry(sample_workers: list[WorkerIdentity]) -> WorkerRegistry:
    """Create a registry populated with sample workers."""
    registry = WorkerRegistry(run_id="kw-test-12345")
    for worker in sample_workers:
        registry.register(worker)
    return registry


@pytest.fixture
def empty_registry() -> WorkerRegistry:
    """Create an empty registry."""
    return WorkerRegistry(run_id="kw-empty-00000")


# =============================================================================
# UNIT TESTS - Registry Creation
# =============================================================================


class TestRegistryCreation:
    """Tests for WorkerRegistry creation."""

    def test_create_empty_registry(self) -> None:
        """Test creating an empty registry."""
        registry = WorkerRegistry(run_id="kw-abc12345")

        assert registry.run_id == "kw-abc12345"
        assert registry.worker_count == 0

    def test_registry_run_id_stored(self) -> None:
        """Test that run_id is stored correctly."""
        registry = WorkerRegistry(run_id="kw-xyz98765")

        assert registry.run_id == "kw-xyz98765"


# =============================================================================
# UNIT TESTS - Worker Registration
# =============================================================================


class TestWorkerRegistration:
    """Tests for worker registration operations."""

    def test_register_single_worker(self, empty_registry: WorkerRegistry) -> None:
        """Test registering a single worker."""
        worker = WorkerIdentity(
            worker_id="kw-eng-001",
            display_name="Test Worker",
            user_principal_name="test@tenant.onmicrosoft.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        )

        empty_registry.register(worker)

        assert empty_registry.worker_count == 1
        assert empty_registry.get("kw-eng-001") is not None

    def test_register_multiple_workers(
        self, empty_registry: WorkerRegistry, sample_workers: list[WorkerIdentity]
    ) -> None:
        """Test registering multiple workers."""
        for worker in sample_workers:
            empty_registry.register(worker)

        assert empty_registry.worker_count == len(sample_workers)

    def test_register_duplicate_worker_overwrites(self, empty_registry: WorkerRegistry) -> None:
        """Test registering a worker with same ID overwrites existing."""
        worker1 = WorkerIdentity(
            worker_id="kw-eng-001",
            display_name="Original Name",
            user_principal_name="original@tenant.onmicrosoft.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        )
        worker2 = WorkerIdentity(
            worker_id="kw-eng-001",  # Same ID
            display_name="Updated Name",
            user_principal_name="updated@tenant.onmicrosoft.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        )

        empty_registry.register(worker1)
        empty_registry.register(worker2)

        assert empty_registry.worker_count == 1
        assert empty_registry.get("kw-eng-001").display_name == "Updated Name"


# =============================================================================
# UNIT TESTS - Worker Unregistration
# =============================================================================


class TestWorkerUnregistration:
    """Tests for worker unregistration operations."""

    def test_unregister_existing_worker(self, populated_registry: WorkerRegistry) -> None:
        """Test unregistering an existing worker."""
        initial_count = populated_registry.worker_count

        populated_registry.unregister("kw-eng-001")

        assert populated_registry.worker_count == initial_count - 1
        assert populated_registry.get("kw-eng-001") is None

    def test_unregister_nonexistent_worker(self, populated_registry: WorkerRegistry) -> None:
        """Test unregistering a non-existent worker does nothing."""
        initial_count = populated_registry.worker_count

        populated_registry.unregister("nonexistent-worker")

        assert populated_registry.worker_count == initial_count

    def test_unregister_all_workers(
        self, populated_registry: WorkerRegistry, sample_workers: list[WorkerIdentity]
    ) -> None:
        """Test unregistering all workers."""
        for worker in sample_workers:
            populated_registry.unregister(worker.worker_id)

        assert populated_registry.worker_count == 0


# =============================================================================
# UNIT TESTS - Worker Lookup
# =============================================================================


class TestWorkerLookup:
    """Tests for worker lookup operations."""

    def test_get_existing_worker(self, populated_registry: WorkerRegistry) -> None:
        """Test getting an existing worker by ID."""
        worker = populated_registry.get("kw-eng-001")

        assert worker is not None
        assert worker.worker_id == "kw-eng-001"
        assert worker.display_name == "Alice Engineer"

    def test_get_nonexistent_worker(self, populated_registry: WorkerRegistry) -> None:
        """Test getting a non-existent worker returns None."""
        worker = populated_registry.get("nonexistent-worker")

        assert worker is None

    def test_get_from_empty_registry(self, empty_registry: WorkerRegistry) -> None:
        """Test getting from empty registry returns None."""
        worker = empty_registry.get("any-worker")

        assert worker is None


# =============================================================================
# UNIT TESTS - Get All Workers
# =============================================================================


class TestGetAllWorkers:
    """Tests for getting all workers."""

    def test_get_all_workers(
        self, populated_registry: WorkerRegistry, sample_workers: list[WorkerIdentity]
    ) -> None:
        """Test getting all registered workers."""
        workers = populated_registry.get_all_workers()

        assert len(workers) == len(sample_workers)
        worker_ids = {w.worker_id for w in workers}
        expected_ids = {w.worker_id for w in sample_workers}
        assert worker_ids == expected_ids

    def test_get_all_workers_empty_registry(self, empty_registry: WorkerRegistry) -> None:
        """Test getting all workers from empty registry."""
        workers = empty_registry.get_all_workers()

        assert len(workers) == 0
        assert workers == []


# =============================================================================
# UNIT TESTS - Get All UPNs
# =============================================================================


class TestGetAllUPNs:
    """Tests for getting all user principal names."""

    def test_get_all_upns(self, populated_registry: WorkerRegistry) -> None:
        """Test getting all UPNs."""
        upns = populated_registry.get_all_upns()

        assert len(upns) == 5
        assert "alice@tenant.onmicrosoft.com" in upns
        assert "bob@tenant.onmicrosoft.com" in upns
        assert "carol@tenant.onmicrosoft.com" in upns

    def test_get_all_upns_empty_registry(self, empty_registry: WorkerRegistry) -> None:
        """Test getting UPNs from empty registry."""
        upns = empty_registry.get_all_upns()

        assert upns == []

    def test_get_all_upns_excludes_empty(self, empty_registry: WorkerRegistry) -> None:
        """Test that workers with empty UPN are excluded."""
        worker_with_upn = WorkerIdentity(
            worker_id="kw-eng-001",
            display_name="Worker With UPN",
            user_principal_name="worker@tenant.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        )
        worker_without_upn = WorkerIdentity(
            worker_id="kw-eng-002",
            display_name="Worker Without UPN",
            user_principal_name="",  # Empty UPN
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
        )

        empty_registry.register(worker_with_upn)
        empty_registry.register(worker_without_upn)

        upns = empty_registry.get_all_upns()

        assert len(upns) == 1
        assert "worker@tenant.com" in upns


# =============================================================================
# UNIT TESTS - Department Filtering
# =============================================================================


class TestDepartmentFiltering:
    """Tests for department-based worker filtering."""

    def test_get_workers_by_department(self, populated_registry: WorkerRegistry) -> None:
        """Test filtering workers by department."""
        engineering_workers = populated_registry.get_workers_by_department("engineering")

        assert len(engineering_workers) == 2
        for worker in engineering_workers:
            assert worker.department.lower() == "engineering"

    def test_get_workers_by_department_case_insensitive(
        self, populated_registry: WorkerRegistry
    ) -> None:
        """Test department filtering is case-insensitive."""
        workers_lower = populated_registry.get_workers_by_department("engineering")
        workers_upper = populated_registry.get_workers_by_department("ENGINEERING")
        workers_mixed = populated_registry.get_workers_by_department("EnGiNeErInG")

        assert len(workers_lower) == len(workers_upper) == len(workers_mixed)

    def test_get_workers_nonexistent_department(self, populated_registry: WorkerRegistry) -> None:
        """Test filtering by non-existent department returns empty."""
        workers = populated_registry.get_workers_by_department("nonexistent")

        assert workers == []

    def test_get_workers_by_department_single_match(
        self, populated_registry: WorkerRegistry
    ) -> None:
        """Test filtering with single worker in department."""
        hr_workers = populated_registry.get_workers_by_department("hr")

        assert len(hr_workers) == 1
        assert hr_workers[0].worker_id == "kw-hr-001"


# =============================================================================
# UNIT TESTS - Random Recipients
# =============================================================================


class TestRandomRecipients:
    """Tests for random recipient selection."""

    def test_get_random_recipients_single(self, populated_registry: WorkerRegistry) -> None:
        """Test getting a single random recipient."""
        recipients = populated_registry.get_random_recipients(
            exclude="kw-eng-001",
            count=1,
        )

        assert len(recipients) == 1
        assert "alice@tenant.onmicrosoft.com" not in recipients

    def test_get_random_recipients_multiple(self, populated_registry: WorkerRegistry) -> None:
        """Test getting multiple random recipients."""
        recipients = populated_registry.get_random_recipients(
            exclude="kw-eng-001",
            count=3,
        )

        assert len(recipients) == 3
        assert "alice@tenant.onmicrosoft.com" not in recipients

    def test_get_random_recipients_excludes_self(self, populated_registry: WorkerRegistry) -> None:
        """Test that excluded worker is never in results."""
        # Run multiple times to test randomness
        for _ in range(10):
            recipients = populated_registry.get_random_recipients(
                exclude="kw-eng-001",
                count=4,
            )
            assert "alice@tenant.onmicrosoft.com" not in recipients

    def test_get_random_recipients_more_than_available(
        self, populated_registry: WorkerRegistry
    ) -> None:
        """Test requesting more recipients than available."""
        # Excluding one worker, only 4 candidates remain
        recipients = populated_registry.get_random_recipients(
            exclude="kw-eng-001",
            count=10,  # More than available
        )

        assert len(recipients) == 4  # Returns all available

    def test_get_random_recipients_empty_registry(self, empty_registry: WorkerRegistry) -> None:
        """Test getting recipients from empty registry."""
        recipients = empty_registry.get_random_recipients(
            exclude="any-worker",
            count=1,
        )

        assert recipients == []


# =============================================================================
# UNIT TESTS - Random Recipients from Department
# =============================================================================


class TestRandomRecipientsFromDepartment:
    """Tests for department-specific random recipient selection."""

    def test_get_random_recipients_from_department(
        self, populated_registry: WorkerRegistry
    ) -> None:
        """Test getting random recipients from specific department."""
        recipients = populated_registry.get_random_recipients_from_department(
            exclude="kw-eng-001",
            department="engineering",
            count=1,
        )

        assert len(recipients) == 1
        assert recipients[0] == "bob@tenant.onmicrosoft.com"

    def test_get_random_recipients_department_excludes_self(
        self, populated_registry: WorkerRegistry
    ) -> None:
        """Test department recipients excludes sender."""
        recipients = populated_registry.get_random_recipients_from_department(
            exclude="kw-eng-002",
            department="engineering",
            count=1,
        )

        assert len(recipients) == 1
        assert "bob@tenant.onmicrosoft.com" not in recipients

    def test_get_random_recipients_nonexistent_department(
        self, populated_registry: WorkerRegistry
    ) -> None:
        """Test getting recipients from non-existent department."""
        recipients = populated_registry.get_random_recipients_from_department(
            exclude="kw-eng-001",
            department="nonexistent",
            count=1,
        )

        assert recipients == []

    def test_get_random_recipients_department_case_insensitive(
        self, populated_registry: WorkerRegistry
    ) -> None:
        """Test department name is case-insensitive."""
        recipients_lower = populated_registry.get_random_recipients_from_department(
            exclude="kw-eng-001",
            department="engineering",
            count=1,
        )
        recipients_upper = populated_registry.get_random_recipients_from_department(
            exclude="kw-eng-001",
            department="ENGINEERING",
            count=1,
        )

        # Both should return the same single candidate (bob)
        assert recipients_lower == recipients_upper


# =============================================================================
# UNIT TESTS - Worker Count Property
# =============================================================================


class TestWorkerCount:
    """Tests for worker_count property."""

    def test_worker_count_empty(self, empty_registry: WorkerRegistry) -> None:
        """Test worker count on empty registry."""
        assert empty_registry.worker_count == 0

    def test_worker_count_after_registration(
        self, empty_registry: WorkerRegistry, sample_workers: list[WorkerIdentity]
    ) -> None:
        """Test worker count increases after registration."""
        for i, worker in enumerate(sample_workers):
            empty_registry.register(worker)
            assert empty_registry.worker_count == i + 1

    def test_worker_count_after_unregistration(self, populated_registry: WorkerRegistry) -> None:
        """Test worker count decreases after unregistration."""
        initial_count = populated_registry.worker_count

        populated_registry.unregister("kw-eng-001")
        assert populated_registry.worker_count == initial_count - 1

        populated_registry.unregister("kw-hr-001")
        assert populated_registry.worker_count == initial_count - 2


# =============================================================================
# INTEGRATION TESTS - Full Workflow
# =============================================================================


class TestRegistryIntegration:
    """Integration tests for registry workflows."""

    def test_full_lifecycle(self) -> None:
        """Test complete registry lifecycle."""
        # Create registry
        registry = WorkerRegistry(run_id="kw-lifecycle-test")
        assert registry.worker_count == 0

        # Register workers
        workers = [
            WorkerIdentity(
                worker_id=f"kw-test-{i:03d}",
                display_name=f"Test Worker {i}",
                user_principal_name=f"worker{i}@tenant.com",
                department="testing",
                persona=WorkerPersona.ENGINEERING,
            )
            for i in range(5)
        ]

        for worker in workers:
            registry.register(worker)
        assert registry.worker_count == 5

        # Query workers
        all_workers = registry.get_all_workers()
        assert len(all_workers) == 5

        all_upns = registry.get_all_upns()
        assert len(all_upns) == 5

        testing_workers = registry.get_workers_by_department("testing")
        assert len(testing_workers) == 5

        # Get random recipients
        recipients = registry.get_random_recipients(
            exclude="kw-test-000",
            count=2,
        )
        assert len(recipients) == 2
        assert "worker0@tenant.com" not in recipients

        # Unregister some workers
        registry.unregister("kw-test-000")
        registry.unregister("kw-test-001")
        assert registry.worker_count == 3

        # Verify lookup
        assert registry.get("kw-test-000") is None
        assert registry.get("kw-test-002") is not None

    def test_cross_department_communication(self, populated_registry: WorkerRegistry) -> None:
        """Test simulating cross-department email recipients."""
        # Engineering worker wants to email HR
        hr_recipients = populated_registry.get_random_recipients_from_department(
            exclude="kw-eng-001",
            department="hr",
            count=1,
        )

        assert len(hr_recipients) == 1
        assert hr_recipients[0] == "carol@tenant.onmicrosoft.com"

        # HR worker wants to email Engineering
        eng_recipients = populated_registry.get_random_recipients_from_department(
            exclude="kw-hr-001",
            department="engineering",
            count=2,
        )

        assert len(eng_recipients) == 2
        assert "carol@tenant.onmicrosoft.com" not in eng_recipients
