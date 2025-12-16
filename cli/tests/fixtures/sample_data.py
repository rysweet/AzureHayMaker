"""Sample test data for telemetry and reporting tests."""

from datetime import datetime, timedelta
from typing import Any


def sample_execution_data(count: int = 5, offset_minutes: int = 0) -> list[dict[str, Any]]:
    """Generate sample execution data for testing.

    Args:
        count: Number of execution records to generate
        offset_minutes: Time offset in minutes from now

    Returns:
        List of execution record dictionaries
    """
    base_time = datetime.utcnow() - timedelta(minutes=offset_minutes)

    executions = []
    for i in range(count):
        execution_time = base_time + timedelta(minutes=i * 10)
        executions.append(
            {
                "id": f"exec-{i + 1:03d}",
                "scenario_id": f"scenario-{(i % 3) + 1}",
                "scenario_name": f"Test Scenario {(i % 3) + 1}",
                "status": ["completed", "failed", "running"][i % 3],
                "started_at": execution_time.isoformat(),
                "completed_at": (execution_time + timedelta(minutes=5)).isoformat()
                if i % 3 != 2
                else None,
                "duration_seconds": 300 if i % 3 != 2 else None,
                "total_agents": 10 + i,
                "successful_agents": 8 + i if i % 3 == 0 else 5,
                "failed_agents": 2 if i % 3 == 1 else 0,
                "error_message": "Connection timeout" if i % 3 == 1 else None,
                "metadata": {"user": "test-user", "trigger": "manual", "environment": "test"},
            }
        )

    return executions


def sample_agent_data(execution_id: str, count: int = 10) -> list[dict[str, Any]]:
    """Generate sample agent data for testing.

    Args:
        execution_id: Execution ID to associate agents with
        count: Number of agent records to generate

    Returns:
        List of agent record dictionaries
    """
    base_time = datetime.utcnow()

    agents = []
    for i in range(count):
        agent_time = base_time + timedelta(seconds=i * 30)
        agents.append(
            {
                "id": f"agent-{i + 1:03d}",
                "execution_id": execution_id,
                "vm_name": f"vm-haymaker-{i + 1:02d}",
                "region": ["eastus", "westus", "centralus"][i % 3],
                "status": ["completed", "failed", "running"][i % 3],
                "started_at": agent_time.isoformat(),
                "completed_at": (agent_time + timedelta(seconds=120)).isoformat()
                if i % 3 != 2
                else None,
                "duration_seconds": 120 if i % 3 != 2 else None,
                "exit_code": 0 if i % 3 == 0 else (1 if i % 3 == 1 else None),
                "error_message": "Script failed" if i % 3 == 1 else None,
                "stdout_lines": 150 + i * 10,
                "stderr_lines": 5 if i % 3 == 1 else 0,
            }
        )

    return agents


def sample_resource_data(execution_id: str, count: int = 10) -> list[dict[str, Any]]:
    """Generate sample resource usage data for testing.

    Args:
        execution_id: Execution ID to associate resources with
        count: Number of resource records to generate

    Returns:
        List of resource record dictionaries
    """
    base_time = datetime.utcnow()

    resources = []
    for i in range(count):
        resource_time = base_time + timedelta(seconds=i * 30)
        resources.append(
            {
                "id": f"resource-{i + 1:03d}",
                "execution_id": execution_id,
                "agent_id": f"agent-{i + 1:03d}",
                "vm_name": f"vm-haymaker-{i + 1:02d}",
                "timestamp": resource_time.isoformat(),
                "cpu_percent": 45.5 + i * 2.1,
                "memory_percent": 62.3 + i * 1.5,
                "disk_io_read_mb": 150.0 + i * 10.0,
                "disk_io_write_mb": 75.0 + i * 5.0,
                "network_sent_mb": 25.0 + i * 2.0,
                "network_recv_mb": 50.0 + i * 3.0,
            }
        )

    return resources


def sample_telemetry_config() -> dict[str, Any]:
    """Generate sample telemetry configuration for testing.

    Returns:
        Telemetry configuration dictionary
    """
    return {
        "enabled": True,
        "storage_path": "/tmp/haymaker/telemetry",
        "collection_interval_seconds": 300,
        "retention_days": 30,
        "max_file_size_mb": 100,
        "compress_old_files": True,
        "api_timeout_seconds": 30,
        "batch_size": 100,
    }


def sample_report_filters() -> dict[str, Any]:
    """Generate sample report filter configuration for testing.

    Returns:
        Report filter dictionary
    """
    return {
        "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "scenario_ids": ["scenario-001", "scenario-002"],
        "status": ["completed", "failed"],
        "min_duration_seconds": 60,
        "max_duration_seconds": 3600,
    }


def sample_kpi_data() -> dict[str, Any]:
    """Generate sample KPI data for testing report generation.

    Returns:
        KPI data dictionary
    """
    return {
        "total_executions": 150,
        "successful_executions": 120,
        "failed_executions": 25,
        "running_executions": 5,
        "success_rate": 80.0,
        "avg_duration_seconds": 287.5,
        "avg_agents_per_execution": 12.3,
        "total_agents": 1845,
        "successful_agents": 1523,
        "failed_agents": 322,
        "agent_success_rate": 82.5,
        "total_cost_usd": 456.78,
        "avg_cost_per_execution": 3.05,
        "top_regions": [
            {"region": "eastus", "count": 620},
            {"region": "westus", "count": 615},
            {"region": "centralus", "count": 610},
        ],
        "top_scenarios": [
            {"scenario": "Load Test", "count": 50, "success_rate": 85.0},
            {"scenario": "Stress Test", "count": 45, "success_rate": 78.0},
            {"scenario": "Endurance Test", "count": 40, "success_rate": 82.5},
        ],
        "error_distribution": [
            {"error": "Connection timeout", "count": 15},
            {"error": "Resource exhausted", "count": 8},
            {"error": "Authentication failed", "count": 2},
        ],
    }


def sample_empty_data() -> dict[str, Any]:
    """Generate empty data structure for testing edge cases.

    Returns:
        Empty data dictionary
    """
    return {"executions": [], "agents": [], "resources": []}


def sample_large_dataset(executions: int = 1000) -> dict[str, Any]:
    """Generate large dataset for performance testing.

    Args:
        executions: Number of executions to generate

    Returns:
        Large data dictionary
    """
    return {
        "executions": sample_execution_data(count=executions),
        "agents": [
            agent
            for i in range(min(executions, 100))  # Limit for memory
            for agent in sample_agent_data(f"exec-{i + 1:03d}", count=10)
        ],
        "resources": [
            resource
            for i in range(min(executions, 100))  # Limit for memory
            for resource in sample_resource_data(f"exec-{i + 1:03d}", count=10)
        ],
    }
