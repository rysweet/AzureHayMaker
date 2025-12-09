"""Test data for cross-tenant orchestration tests."""

from datetime import datetime, timezone
from uuid import uuid4


def sample_execution_run():
    """Sample execution run data."""
    return {
        "run_id": str(uuid4()),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress",
        "tenants": ["tenant-a", "tenant-b"],
    }


def sample_resource_event():
    """Sample resource creation event."""
    return {
        "event_type": "resource_created",
        "resource_id": f"/subscriptions/{uuid4()}/resourceGroups/test-rg/providers/Microsoft.Compute/virtualMachines/test-vm",
        "resource_type": "Microsoft.Compute/virtualMachines",
        "resource_name": "test-vm",
        "tenant_id": str(uuid4()),
        "scenario_name": "compute-01-linux-vm-web-server",
        "run_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tags": {"ManagedBy": "HayMaker", "Environment": "Test"},
    }


def sample_blob_data(tenant_id: str):
    """Sample blob data with tenant prefix."""
    return {
        "tenant_id": tenant_id,
        "data": "test blob content",
        "path": f"{tenant_id}/test-file.txt",
    }


def sample_table_entity(tenant_id: str, run_id: str):
    """Sample Table Storage entity with tenant partition key."""
    return {
        "PartitionKey": f"{tenant_id}#{run_id}",
        "RowKey": str(uuid4()),
        "tenant_id": tenant_id,
        "run_id": run_id,
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def sample_cosmos_document(tenant_id: str):
    """Sample Cosmos DB document with tenant_id field."""
    return {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "type": "execution_log",
        "data": "test document",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def sample_orchestration_status():
    """Sample orchestration status."""
    return {
        "instance_id": str(uuid4()),
        "status": "running",
        "tenant_name": "customer-a",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "phase": "provisioning",
        "scenarios_total": 5,
        "scenarios_completed": 2,
        "scenarios_running": 3,
        "scenarios_failed": 0,
    }


def sample_meta_report():
    """Sample meta-orchestration report."""
    return {
        "run_id": str(uuid4()),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "total_tenants": 3,
        "succeeded_tenants": 2,
        "failed_tenants": 1,
        "tenants": [
            {
                "name": "tenant-a",
                "status": "completed",
                "scenarios_completed": 5,
                "scenarios_failed": 0,
            },
            {
                "name": "tenant-b",
                "status": "completed",
                "scenarios_completed": 3,
                "scenarios_failed": 0,
            },
            {
                "name": "tenant-c",
                "status": "failed",
                "scenarios_completed": 1,
                "scenarios_failed": 2,
                "error": "Authentication failed",
            },
        ],
    }
