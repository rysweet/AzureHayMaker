"""Unit tests for Worker models with WINDOWS_VM support.

This module tests the WorkerIdentity and EndpointType models with the new
WINDOWS_VM endpoint type added for Issue #120.

Tests cover:
- EndpointType.WINDOWS_VM enum value exists
- EndpointType.WINDOWS_VM serialization to/from JSON
- WorkerIdentity accepts WINDOWS_VM endpoint type
- WorkerIdentity validation with WINDOWS_VM
- Model serialization and deserialization

Uses pytest with pydantic models.
"""

import json

import pytest

from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerIdentity,
    WorkerPersona,
)

# ==============================================================================
# ENDPOINT TYPE ENUM TESTS
# ==============================================================================


class TestEndpointTypeEnum:
    """Tests for EndpointType enum with WINDOWS_VM."""

    def test_endpoint_type_windows_vm_exists(self):
        """Test EndpointType.WINDOWS_VM enum value exists."""
        assert hasattr(EndpointType, "WINDOWS_VM")
        assert EndpointType.WINDOWS_VM is not None

    def test_endpoint_type_windows_vm_value(self):
        """Test EndpointType.WINDOWS_VM has correct string value."""
        assert EndpointType.WINDOWS_VM.value == "windows_vm"

    def test_endpoint_type_all_values(self):
        """Test all endpoint types are present."""
        expected_types = {"CLOUD_PC", "CLI_CONTAINER", "WINDOWS_VM"}
        actual_types = {e.name for e in EndpointType}

        assert expected_types.issubset(
            actual_types
        ), f"Missing types: {expected_types - actual_types}"

    def test_endpoint_type_string_comparison(self):
        """Test EndpointType.WINDOWS_VM can be compared with strings."""
        assert EndpointType.WINDOWS_VM == "windows_vm"
        assert EndpointType.WINDOWS_VM != "cloud_pc"
        assert EndpointType.WINDOWS_VM != "cli_container"

    def test_endpoint_type_serialization(self):
        """Test EndpointType.WINDOWS_VM serializes to JSON correctly."""
        # Test direct enum serialization
        endpoint_type = EndpointType.WINDOWS_VM

        # Pydantic should serialize enum values
        serialized = endpoint_type.value
        assert serialized == "windows_vm"

    def test_endpoint_type_deserialization(self):
        """Test creating EndpointType.WINDOWS_VM from string."""
        endpoint_type = EndpointType("windows_vm")

        assert endpoint_type == EndpointType.WINDOWS_VM


# ==============================================================================
# WORKER IDENTITY WITH WINDOWS_VM TESTS
# ==============================================================================


class TestWorkerIdentityWithWindowsVM:
    """Tests for WorkerIdentity accepting WINDOWS_VM endpoint type."""

    def test_worker_identity_accepts_windows_vm(self):
        """Test WorkerIdentity can be created with WINDOWS_VM endpoint type."""
        worker = WorkerIdentity(
            worker_id="kw-test-001",
            display_name="Test Worker",
            user_principal_name="test@example.com",
            department="engineering",
            persona=WorkerPersona.ENGINEERING,
            endpoint_type=EndpointType.WINDOWS_VM,
            endpoint_id="vm-12345",
        )

        assert worker.endpoint_type == EndpointType.WINDOWS_VM
        assert worker.endpoint_id == "vm-12345"

    def test_worker_identity_windows_vm_from_string(self):
        """Test WorkerIdentity accepts 'windows_vm' string for endpoint_type."""
        worker = WorkerIdentity(
            worker_id="kw-test-002",
            display_name="Test Worker 2",
            user_principal_name="test2@example.com",
            department="operations",
            persona=WorkerPersona.OPERATIONS,
            endpoint_type="windows_vm",  # String instead of enum
            endpoint_id="vm-67890",
        )

        assert worker.endpoint_type == EndpointType.WINDOWS_VM

    def test_worker_identity_windows_vm_default(self):
        """Test WorkerIdentity defaults to CLI_CONTAINER, not WINDOWS_VM."""
        worker = WorkerIdentity(
            worker_id="kw-test-003",
            display_name="Test Worker 3",
            user_principal_name="test3@example.com",
            department="sales",
            persona=WorkerPersona.SALES,
        )

        # Default should be CLI_CONTAINER
        assert worker.endpoint_type == EndpointType.CLI_CONTAINER
        assert worker.endpoint_type != EndpointType.WINDOWS_VM

    def test_worker_identity_windows_vm_validation(self):
        """Test WorkerIdentity validates WINDOWS_VM endpoint type."""
        # Should not raise validation error
        worker = WorkerIdentity(
            worker_id="kw-test-004",
            display_name="Test Worker 4",
            user_principal_name="test4@example.com",
            department="hr",
            persona=WorkerPersona.HR,
            endpoint_type=EndpointType.WINDOWS_VM,
        )

        assert worker.endpoint_type == EndpointType.WINDOWS_VM

    def test_worker_identity_invalid_endpoint_type_raises_error(self):
        """Test WorkerIdentity rejects invalid endpoint type."""
        with pytest.raises((ValueError, Exception)):
            WorkerIdentity(
                worker_id="kw-test-005",
                display_name="Test Worker 5",
                user_principal_name="test5@example.com",
                department="marketing",
                persona=WorkerPersona.MARKETING,
                endpoint_type="invalid_type",
            )


# ==============================================================================
# WORKER IDENTITY SERIALIZATION TESTS
# ==============================================================================


class TestWorkerIdentitySerialization:
    """Tests for WorkerIdentity serialization with WINDOWS_VM."""

    def test_worker_identity_to_dict_with_windows_vm(self):
        """Test WorkerIdentity with WINDOWS_VM serializes to dict correctly."""
        worker = WorkerIdentity(
            worker_id="kw-test-006",
            display_name="Test Worker 6",
            user_principal_name="test6@example.com",
            department="finance",
            persona=WorkerPersona.FINANCE,
            endpoint_type=EndpointType.WINDOWS_VM,
            endpoint_id="vm-abc123",
        )

        worker_dict = worker.model_dump()

        assert worker_dict["endpoint_type"] == "windows_vm"
        assert worker_dict["endpoint_id"] == "vm-abc123"
        assert worker_dict["worker_id"] == "kw-test-006"

    def test_worker_identity_to_json_with_windows_vm(self):
        """Test WorkerIdentity with WINDOWS_VM serializes to JSON correctly."""
        worker = WorkerIdentity(
            worker_id="kw-test-007",
            display_name="Test Worker 7",
            user_principal_name="test7@example.com",
            department="legal",
            persona=WorkerPersona.LEGAL,
            endpoint_type=EndpointType.WINDOWS_VM,
            endpoint_id="vm-def456",
        )

        worker_json = worker.model_dump_json()
        parsed = json.loads(worker_json)

        assert parsed["endpoint_type"] == "windows_vm"
        assert parsed["endpoint_id"] == "vm-def456"

    def test_worker_identity_from_dict_with_windows_vm(self):
        """Test WorkerIdentity can be created from dict with WINDOWS_VM."""
        worker_data = {
            "worker_id": "kw-test-008",
            "display_name": "Test Worker 8",
            "user_principal_name": "test8@example.com",
            "department": "executive",
            "persona": "executive",
            "endpoint_type": "windows_vm",
            "endpoint_id": "vm-ghi789",
        }

        worker = WorkerIdentity(**worker_data)

        assert worker.endpoint_type == EndpointType.WINDOWS_VM
        assert worker.endpoint_id == "vm-ghi789"

    def test_worker_identity_from_json_with_windows_vm(self):
        """Test WorkerIdentity can be deserialized from JSON with WINDOWS_VM."""
        worker_json = json.dumps(
            {
                "worker_id": "kw-test-009",
                "display_name": "Test Worker 9",
                "user_principal_name": "test9@example.com",
                "department": "engineering",
                "persona": "engineering",
                "endpoint_type": "windows_vm",
                "endpoint_id": "vm-jkl012",
            }
        )

        worker = WorkerIdentity.model_validate_json(worker_json)

        assert worker.endpoint_type == EndpointType.WINDOWS_VM
        assert worker.endpoint_id == "vm-jkl012"


# ==============================================================================
# WORKER IDENTITY ENDPOINT TYPE UPDATE TESTS
# ==============================================================================


class TestWorkerIdentityEndpointTypeUpdate:
    """Tests for updating WorkerIdentity endpoint_type."""

    def test_update_endpoint_type_to_windows_vm(self):
        """Test WorkerIdentity endpoint_type can be updated to WINDOWS_VM."""
        worker = WorkerIdentity(
            worker_id="kw-test-010",
            display_name="Test Worker 10",
            user_principal_name="test10@example.com",
            department="operations",
            persona=WorkerPersona.OPERATIONS,
            endpoint_type=EndpointType.CLOUD_PC,  # Start with Cloud PC
            endpoint_id="cloudpc-123",
        )

        # Update to Windows VM (simulating fallback)
        worker.endpoint_type = EndpointType.WINDOWS_VM
        worker.endpoint_id = "vm-new-456"

        assert worker.endpoint_type == EndpointType.WINDOWS_VM
        assert worker.endpoint_id == "vm-new-456"

    def test_update_endpoint_type_from_windows_vm_to_container(self):
        """Test WorkerIdentity endpoint_type can be updated from WINDOWS_VM."""
        worker = WorkerIdentity(
            worker_id="kw-test-011",
            display_name="Test Worker 11",
            user_principal_name="test11@example.com",
            department="sales",
            persona=WorkerPersona.SALES,
            endpoint_type=EndpointType.WINDOWS_VM,
            endpoint_id="vm-789",
        )

        # Update to Container
        worker.endpoint_type = EndpointType.CLI_CONTAINER
        worker.endpoint_id = "container-999"

        assert worker.endpoint_type == EndpointType.CLI_CONTAINER
        assert worker.endpoint_id == "container-999"


# ==============================================================================
# WORKER IDENTITY COPY AND MODIFICATION TESTS
# ==============================================================================


class TestWorkerIdentityCopyWithWindowsVM:
    """Tests for copying WorkerIdentity with WINDOWS_VM."""

    def test_copy_worker_with_windows_vm(self):
        """Test WorkerIdentity with WINDOWS_VM can be copied."""
        worker = WorkerIdentity(
            worker_id="kw-test-012",
            display_name="Test Worker 12",
            user_principal_name="test12@example.com",
            department="hr",
            persona=WorkerPersona.HR,
            endpoint_type=EndpointType.WINDOWS_VM,
            endpoint_id="vm-copy-123",
        )

        worker_copy = worker.model_copy()

        assert worker_copy.endpoint_type == EndpointType.WINDOWS_VM
        assert worker_copy.endpoint_id == "vm-copy-123"
        assert worker_copy.worker_id == worker.worker_id

    def test_copy_and_update_endpoint_type(self):
        """Test copying WorkerIdentity and updating endpoint_type."""
        worker = WorkerIdentity(
            worker_id="kw-test-013",
            display_name="Test Worker 13",
            user_principal_name="test13@example.com",
            department="finance",
            persona=WorkerPersona.FINANCE,
            endpoint_type=EndpointType.CLOUD_PC,
            endpoint_id="cloudpc-999",
        )

        # Copy with different endpoint type
        worker_copy = worker.model_copy(
            update={
                "endpoint_type": EndpointType.WINDOWS_VM,
                "endpoint_id": "vm-updated-456",
            }
        )

        assert worker_copy.endpoint_type == EndpointType.WINDOWS_VM
        assert worker_copy.endpoint_id == "vm-updated-456"
        # Original unchanged
        assert worker.endpoint_type == EndpointType.CLOUD_PC


# ==============================================================================
# MULTIPLE WORKER IDENTITIES TESTS
# ==============================================================================


class TestMultipleWorkersWithDifferentEndpoints:
    """Tests for multiple workers with different endpoint types."""

    def test_mixed_endpoint_types_in_list(self):
        """Test list of workers with mixed endpoint types including WINDOWS_VM."""
        workers = [
            WorkerIdentity(
                worker_id=f"kw-test-{i:03d}",
                display_name=f"Test Worker {i}",
                user_principal_name=f"test{i}@example.com",
                department="engineering",
                persona=WorkerPersona.ENGINEERING,
                endpoint_type=endpoint_type,
                endpoint_id=f"{endpoint_type.value}-{i}",
            )
            for i, endpoint_type in enumerate(
                [
                    EndpointType.CLOUD_PC,
                    EndpointType.WINDOWS_VM,
                    EndpointType.CLI_CONTAINER,
                    EndpointType.WINDOWS_VM,
                ]
            )
        ]

        assert len(workers) == 4
        assert workers[0].endpoint_type == EndpointType.CLOUD_PC
        assert workers[1].endpoint_type == EndpointType.WINDOWS_VM
        assert workers[2].endpoint_type == EndpointType.CLI_CONTAINER
        assert workers[3].endpoint_type == EndpointType.WINDOWS_VM

    def test_filter_workers_by_windows_vm(self):
        """Test filtering workers by WINDOWS_VM endpoint type."""
        workers = [
            WorkerIdentity(
                worker_id=f"kw-test-{i:03d}",
                display_name=f"Test Worker {i}",
                user_principal_name=f"test{i}@example.com",
                department="engineering",
                persona=WorkerPersona.ENGINEERING,
                endpoint_type=endpoint_type,
                endpoint_id=f"{endpoint_type.value}-{i}",
            )
            for i, endpoint_type in enumerate(
                [
                    EndpointType.CLOUD_PC,
                    EndpointType.WINDOWS_VM,
                    EndpointType.CLI_CONTAINER,
                    EndpointType.WINDOWS_VM,
                    EndpointType.CLOUD_PC,
                ]
            )
        ]

        windows_vm_workers = [w for w in workers if w.endpoint_type == EndpointType.WINDOWS_VM]

        assert len(windows_vm_workers) == 2
        assert all(w.endpoint_type == EndpointType.WINDOWS_VM for w in windows_vm_workers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
