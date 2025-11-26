"""Unit tests for telemetry data models."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError


class TestExecutionRecord:
    """Test ExecutionRecord data model."""

    def test_execution_record_valid_data(self):
        """Test ExecutionRecord accepts valid data."""
        from haymaker_cli.telemetry.models import ExecutionRecord

        data = {
            "id": "exec-001",
            "scenario_id": "scenario-001",
            "scenario_name": "Load Test",
            "status": "completed",
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow() + timedelta(minutes=5),
            "duration_seconds": 300,
            "total_agents": 10,
            "successful_agents": 8,
            "failed_agents": 2
        }

        record = ExecutionRecord(**data)

        assert record.id == "exec-001"
        assert record.scenario_name == "Load Test"
        assert record.status == "completed"
        assert record.duration_seconds == 300
        assert record.total_agents == 10

    def test_execution_record_optional_fields(self):
        """Test ExecutionRecord with optional fields omitted."""
        from haymaker_cli.telemetry.models import ExecutionRecord

        data = {
            "id": "exec-001",
            "scenario_id": "scenario-001",
            "scenario_name": "Load Test",
            "status": "running",
            "started_at": datetime.utcnow(),
            "total_agents": 10
        }

        record = ExecutionRecord(**data)

        assert record.completed_at is None
        assert record.duration_seconds is None
        assert record.error_message is None
        assert record.metadata is None or record.metadata == {}

    def test_execution_record_invalid_status(self):
        """Test ExecutionRecord rejects invalid status values."""
        from haymaker_cli.telemetry.models import ExecutionRecord

        data = {
            "id": "exec-001",
            "scenario_id": "scenario-001",
            "scenario_name": "Load Test",
            "status": "invalid_status",  # Invalid
            "started_at": datetime.utcnow(),
            "total_agents": 10
        }

        with pytest.raises(ValidationError):
            ExecutionRecord(**data)

    def test_execution_record_negative_agents(self):
        """Test ExecutionRecord rejects negative agent counts."""
        from haymaker_cli.telemetry.models import ExecutionRecord

        data = {
            "id": "exec-001",
            "scenario_id": "scenario-001",
            "scenario_name": "Load Test",
            "status": "completed",
            "started_at": datetime.utcnow(),
            "total_agents": -5  # Invalid
        }

        with pytest.raises(ValidationError):
            ExecutionRecord(**data)

    def test_execution_record_to_dict(self):
        """Test ExecutionRecord serialization to dictionary."""
        from haymaker_cli.telemetry.models import ExecutionRecord

        now = datetime.utcnow()
        data = {
            "id": "exec-001",
            "scenario_id": "scenario-001",
            "scenario_name": "Load Test",
            "status": "completed",
            "started_at": now,
            "total_agents": 10
        }

        record = ExecutionRecord(**data)
        result = record.dict()

        assert isinstance(result, dict)
        assert result["id"] == "exec-001"
        assert result["status"] == "completed"

    def test_execution_record_from_json(self):
        """Test ExecutionRecord deserialization from JSON."""
        from haymaker_cli.telemetry.models import ExecutionRecord

        json_data = {
            "id": "exec-001",
            "scenario_id": "scenario-001",
            "scenario_name": "Load Test",
            "status": "completed",
            "started_at": "2025-01-01T12:00:00",
            "total_agents": 10
        }

        record = ExecutionRecord.parse_obj(json_data)

        assert record.id == "exec-001"
        assert isinstance(record.started_at, datetime)


class TestAgentRecord:
    """Test AgentRecord data model."""

    def test_agent_record_valid_data(self):
        """Test AgentRecord accepts valid data."""
        from haymaker_cli.telemetry.models import AgentRecord

        data = {
            "id": "agent-001",
            "execution_id": "exec-001",
            "vm_name": "vm-haymaker-01",
            "region": "eastus",
            "status": "completed",
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow() + timedelta(minutes=2),
            "duration_seconds": 120,
            "exit_code": 0
        }

        record = AgentRecord(**data)

        assert record.id == "agent-001"
        assert record.vm_name == "vm-haymaker-01"
        assert record.region == "eastus"
        assert record.exit_code == 0

    def test_agent_record_failed_status(self):
        """Test AgentRecord with failed status and error message."""
        from haymaker_cli.telemetry.models import AgentRecord

        data = {
            "id": "agent-001",
            "execution_id": "exec-001",
            "vm_name": "vm-haymaker-01",
            "region": "eastus",
            "status": "failed",
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow() + timedelta(minutes=1),
            "duration_seconds": 60,
            "exit_code": 1,
            "error_message": "Script execution failed",
            "stdout_lines": 150,
            "stderr_lines": 25
        }

        record = AgentRecord(**data)

        assert record.status == "failed"
        assert record.exit_code == 1
        assert record.error_message == "Script execution failed"
        assert record.stderr_lines == 25

    def test_agent_record_running_status(self):
        """Test AgentRecord with running status (no completion)."""
        from haymaker_cli.telemetry.models import AgentRecord

        data = {
            "id": "agent-001",
            "execution_id": "exec-001",
            "vm_name": "vm-haymaker-01",
            "region": "eastus",
            "status": "running",
            "started_at": datetime.utcnow()
        }

        record = AgentRecord(**data)

        assert record.status == "running"
        assert record.completed_at is None
        assert record.duration_seconds is None
        assert record.exit_code is None

    def test_agent_record_invalid_region(self):
        """Test AgentRecord validation for region format."""
        from haymaker_cli.telemetry.models import AgentRecord

        data = {
            "id": "agent-001",
            "execution_id": "exec-001",
            "vm_name": "vm-haymaker-01",
            "region": "",  # Empty region should fail
            "status": "completed",
            "started_at": datetime.utcnow()
        }

        with pytest.raises(ValidationError):
            AgentRecord(**data)


class TestResourceRecord:
    """Test ResourceRecord data model."""

    def test_resource_record_valid_data(self):
        """Test ResourceRecord accepts valid data."""
        from haymaker_cli.telemetry.models import ResourceRecord

        data = {
            "id": "resource-001",
            "execution_id": "exec-001",
            "agent_id": "agent-001",
            "vm_name": "vm-haymaker-01",
            "timestamp": datetime.utcnow(),
            "cpu_percent": 45.5,
            "memory_percent": 62.3,
            "disk_io_read_mb": 150.0,
            "disk_io_write_mb": 75.0,
            "network_sent_mb": 25.0,
            "network_recv_mb": 50.0
        }

        record = ResourceRecord(**data)

        assert record.id == "resource-001"
        assert record.cpu_percent == 45.5
        assert record.memory_percent == 62.3
        assert record.disk_io_read_mb == 150.0

    def test_resource_record_percentage_bounds(self):
        """Test ResourceRecord validates percentage bounds (0-100)."""
        from haymaker_cli.telemetry.models import ResourceRecord

        # Test invalid CPU percentage
        data = {
            "id": "resource-001",
            "execution_id": "exec-001",
            "agent_id": "agent-001",
            "vm_name": "vm-haymaker-01",
            "timestamp": datetime.utcnow(),
            "cpu_percent": 150.0,  # Invalid: > 100
            "memory_percent": 62.3
        }

        with pytest.raises(ValidationError):
            ResourceRecord(**data)

        # Test invalid memory percentage
        data["cpu_percent"] = 45.5
        data["memory_percent"] = -10.0  # Invalid: < 0

        with pytest.raises(ValidationError):
            ResourceRecord(**data)

    def test_resource_record_negative_io(self):
        """Test ResourceRecord rejects negative I/O values."""
        from haymaker_cli.telemetry.models import ResourceRecord

        data = {
            "id": "resource-001",
            "execution_id": "exec-001",
            "agent_id": "agent-001",
            "vm_name": "vm-haymaker-01",
            "timestamp": datetime.utcnow(),
            "cpu_percent": 45.5,
            "memory_percent": 62.3,
            "disk_io_read_mb": -50.0  # Invalid
        }

        with pytest.raises(ValidationError):
            ResourceRecord(**data)

    def test_resource_record_optional_fields(self):
        """Test ResourceRecord with optional network fields omitted."""
        from haymaker_cli.telemetry.models import ResourceRecord

        data = {
            "id": "resource-001",
            "execution_id": "exec-001",
            "agent_id": "agent-001",
            "vm_name": "vm-haymaker-01",
            "timestamp": datetime.utcnow(),
            "cpu_percent": 45.5,
            "memory_percent": 62.3
        }

        record = ResourceRecord(**data)

        assert record.cpu_percent == 45.5
        assert record.disk_io_read_mb is None or record.disk_io_read_mb == 0.0


class TestCollectionResult:
    """Test CollectionResult data model."""

    def test_collection_result_success(self):
        """Test CollectionResult for successful collection."""
        from haymaker_cli.telemetry.models import CollectionResult

        result = CollectionResult(
            success=True,
            executions_collected=10,
            agents_collected=100,
            resources_collected=500,
            collection_time_seconds=2.5
        )

        assert result.success is True
        assert result.executions_collected == 10
        assert result.error_message is None

    def test_collection_result_failure(self):
        """Test CollectionResult for failed collection."""
        from haymaker_cli.telemetry.models import CollectionResult

        result = CollectionResult(
            success=False,
            executions_collected=0,
            agents_collected=0,
            resources_collected=0,
            collection_time_seconds=0.1,
            error_message="API connection failed"
        )

        assert result.success is False
        assert result.error_message == "API connection failed"

    def test_collection_result_partial_success(self):
        """Test CollectionResult for partial collection (some data, some errors)."""
        from haymaker_cli.telemetry.models import CollectionResult

        result = CollectionResult(
            success=True,
            executions_collected=5,
            agents_collected=0,
            resources_collected=0,
            collection_time_seconds=1.2,
            error_message="Agent collection timed out"
        )

        assert result.success is True
        assert result.executions_collected == 5
        assert result.agents_collected == 0
        assert result.error_message is not None
