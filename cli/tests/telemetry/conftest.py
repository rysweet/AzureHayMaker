"""Pytest fixtures for telemetry tests."""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
from pathlib import Path
from datetime import datetime
import json

from tests.fixtures.sample_data import (
    sample_execution_data,
    sample_agent_data,
    sample_resource_data,
    sample_telemetry_config
)


@pytest.fixture
def mock_api_client():
    """Mock API client for testing telemetry collection."""
    client = AsyncMock()

    # Mock get_executions
    client.get_executions = AsyncMock(return_value={
        "executions": sample_execution_data(count=5),
        "total": 5,
        "page": 1,
        "page_size": 100
    })

    # Mock get_agents
    client.get_agents = AsyncMock(return_value={
        "agents": sample_agent_data("exec-001", count=10),
        "total": 10,
        "page": 1,
        "page_size": 100
    })

    # Mock get_resources
    client.get_resources = AsyncMock(return_value={
        "resources": sample_resource_data("exec-001", count=10),
        "total": 10,
        "page": 1,
        "page_size": 100
    })

    # Mock health check
    client.health_check = AsyncMock(return_value={"status": "healthy"})

    return client


@pytest.fixture
def mock_api_client_error():
    """Mock API client that raises errors for testing error handling."""
    client = AsyncMock()

    # Simulate API errors
    client.get_executions = AsyncMock(side_effect=Exception("API connection failed"))
    client.get_agents = AsyncMock(side_effect=Exception("API connection failed"))
    client.get_resources = AsyncMock(side_effect=Exception("API connection failed"))
    client.health_check = AsyncMock(side_effect=Exception("API connection failed"))

    return client


@pytest.fixture
def mock_api_client_empty():
    """Mock API client that returns empty data."""
    client = AsyncMock()

    client.get_executions = AsyncMock(return_value={
        "executions": [],
        "total": 0,
        "page": 1,
        "page_size": 100
    })

    client.get_agents = AsyncMock(return_value={
        "agents": [],
        "total": 0,
        "page": 1,
        "page_size": 100
    })

    client.get_resources = AsyncMock(return_value={
        "resources": [],
        "total": 0,
        "page": 1,
        "page_size": 100
    })

    client.health_check = AsyncMock(return_value={"status": "healthy"})

    return client


@pytest.fixture
def telemetry_config(tmp_path):
    """Sample telemetry configuration for testing."""
    config = sample_telemetry_config()
    config["storage_path"] = str(tmp_path)
    return config


@pytest.fixture
def telemetry_storage_dir(tmp_path):
    """Create temporary telemetry storage directory."""
    storage_dir = tmp_path / "telemetry"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def sample_telemetry_files(telemetry_storage_dir):
    """Create sample telemetry files for testing."""
    # Create executions file
    executions_file = telemetry_storage_dir / "executions.jsonl"
    with open(executions_file, "w") as f:
        for execution in sample_execution_data(count=10):
            f.write(json.dumps(execution) + "\n")

    # Create agents file
    agents_file = telemetry_storage_dir / "agents.jsonl"
    with open(agents_file, "w") as f:
        for agent in sample_agent_data("exec-001", count=20):
            f.write(json.dumps(agent) + "\n")

    # Create resources file
    resources_file = telemetry_storage_dir / "resources.jsonl"
    with open(resources_file, "w") as f:
        for resource in sample_resource_data("exec-001", count=30):
            f.write(json.dumps(resource) + "\n")

    return {
        "executions": executions_file,
        "agents": agents_file,
        "resources": resources_file
    }


@pytest.fixture
def mock_lock_file(tmp_path):
    """Mock lock file for testing background collection."""
    lock_file = tmp_path / "telemetry.lock"
    return lock_file


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing."""
    mock_dt = Mock()
    mock_dt.utcnow.return_value = datetime(2025, 1, 1, 12, 0, 0)
    return mock_dt


@pytest.fixture
def corrupted_telemetry_file(telemetry_storage_dir):
    """Create corrupted telemetry file for error testing."""
    corrupted_file = telemetry_storage_dir / "executions.jsonl"
    with open(corrupted_file, "w") as f:
        f.write('{"valid": "json"}\n')
        f.write('invalid json line\n')
        f.write('{"another": "valid"}\n')
    return corrupted_file


@pytest.fixture
def large_telemetry_dataset(telemetry_storage_dir):
    """Create large telemetry dataset for performance testing."""
    executions_file = telemetry_storage_dir / "executions.jsonl"
    with open(executions_file, "w") as f:
        for i in range(10000):
            execution = sample_execution_data(count=1, offset_minutes=i * 10)[0]
            execution["id"] = f"exec-{i + 1:05d}"
            f.write(json.dumps(execution) + "\n")
    return executions_file


@pytest.fixture
async def mock_background_task():
    """Mock asyncio task for background collection testing."""
    task = AsyncMock()
    task.done.return_value = False
    task.cancel = Mock()
    return task
