"""Pytest fixtures for report tests."""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
from datetime import datetime, timedelta
import json

from tests.fixtures.sample_data import (
    sample_execution_data,
    sample_agent_data,
    sample_resource_data,
    sample_report_filters,
    sample_kpi_data
)


@pytest.fixture
def mock_telemetry_storage():
    """Mock telemetry storage for report generation tests."""
    storage = Mock()

    # Mock load_executions
    storage.load_executions = Mock(return_value=sample_execution_data(count=50))

    # Mock load_agents
    storage.load_agents = Mock(return_value=sample_agent_data("exec-001", count=100))

    # Mock load_resources
    storage.load_resources = Mock(return_value=sample_resource_data("exec-001", count=200))

    # Mock get_date_range
    storage.get_date_range = Mock(return_value={
        "earliest": (datetime.utcnow() - timedelta(days=30)).isoformat(),
        "latest": datetime.utcnow().isoformat()
    })

    return storage


@pytest.fixture
def mock_telemetry_storage_empty():
    """Mock telemetry storage with no data."""
    storage = Mock()

    storage.load_executions = Mock(return_value=[])
    storage.load_agents = Mock(return_value=[])
    storage.load_resources = Mock(return_value=[])
    storage.get_date_range = Mock(return_value={
        "earliest": None,
        "latest": None
    })

    return storage


@pytest.fixture
def report_filters():
    """Sample report filters for testing."""
    return sample_report_filters()


@pytest.fixture
def report_output_dir(tmp_path):
    """Create temporary report output directory."""
    output_dir = tmp_path / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def mock_jinja2_env():
    """Mock Jinja2 environment for template testing."""
    env = Mock()
    template = Mock()
    template.render = Mock(return_value="<html>Rendered Report</html>")
    env.get_template = Mock(return_value=template)
    return env


@pytest.fixture
def sample_kpis():
    """Sample KPI data for testing."""
    return sample_kpi_data()


@pytest.fixture
def mock_plotly():
    """Mock plotly for chart generation testing."""
    plotly = Mock()
    plotly.to_json = Mock(return_value='{"data": [], "layout": {}}')
    return plotly


@pytest.fixture
def report_metadata():
    """Sample report metadata for testing."""
    return {
        "title": "HayMaker Execution Report",
        "generated_at": datetime.utcnow().isoformat(),
        "generated_by": "test-user",
        "filters": sample_report_filters(),
        "data_range": {
            "start": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "end": datetime.utcnow().isoformat()
        },
        "total_records": 150
    }


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for export testing."""
    return [
        ["Execution ID", "Scenario", "Status", "Duration", "Agents"],
        ["exec-001", "Test Scenario 1", "completed", "300", "10"],
        ["exec-002", "Test Scenario 2", "failed", "150", "8"],
        ["exec-003", "Test Scenario 3", "running", "N/A", "12"]
    ]


@pytest.fixture
def sample_chart_data():
    """Sample chart data for visualization testing."""
    return {
        "execution_timeline": {
            "x": [(datetime.utcnow() - timedelta(days=i)).isoformat() for i in range(7)],
            "y": [10, 12, 15, 14, 18, 16, 20]
        },
        "status_distribution": {
            "labels": ["Completed", "Failed", "Running"],
            "values": [120, 25, 5]
        },
        "region_distribution": {
            "labels": ["eastus", "westus", "centralus"],
            "values": [620, 615, 610]
        },
        "duration_histogram": {
            "bins": [60, 120, 180, 240, 300, 360],
            "counts": [15, 35, 45, 30, 20, 5]
        }
    }


@pytest.fixture
def mock_report_generator_dependencies(mock_telemetry_storage, mock_jinja2_env, report_output_dir):
    """Bundle all report generator dependencies."""
    return {
        "storage": mock_telemetry_storage,
        "template_env": mock_jinja2_env,
        "output_dir": report_output_dir
    }
