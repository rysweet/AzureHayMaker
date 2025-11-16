"""Unit tests for metrics API."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from azure_haymaker.orchestrator.metrics_api import (
    MetricsSummary,
    ScenarioMetrics,
    parse_period,
    query_cosmos_metrics,
)


def test_parse_period_valid():
    """Test parsing valid period strings."""
    assert parse_period("7d") == timedelta(days=7)
    assert parse_period("30d") == timedelta(days=30)
    assert parse_period("90d") == timedelta(days=90)


def test_parse_period_invalid():
    """Test parsing invalid period strings."""
    with pytest.raises(ValueError, match="Invalid period format"):
        parse_period("invalid")

    with pytest.raises(ValueError, match="Invalid period format"):
        parse_period("7w")

    with pytest.raises(ValueError, match="Invalid period format"):
        parse_period("30")


@pytest.mark.asyncio
async def test_query_cosmos_metrics_empty():
    """Test querying metrics with no results."""
    mock_container = MagicMock()
    mock_container.query_items.return_value = []

    mock_database = MagicMock()
    mock_database.get_container_client.return_value = mock_container

    mock_client = MagicMock()
    mock_client.get_database_client.return_value = mock_database

    start_time = datetime.now(UTC) - timedelta(days=7)

    result = await query_cosmos_metrics(
        mock_client,
        "test_db",
        "test_container",
        start_time,
    )

    assert result["total_executions"] == 0
    assert result["success_count"] == 0
    assert result["success_rate"] == 0.0
    assert result["last_execution"] is None
    assert result["scenario_metrics"] == []


@pytest.mark.asyncio
async def test_query_cosmos_metrics_with_data():
    """Test querying metrics with sample data."""
    now = datetime.now(UTC)
    start_time = now - timedelta(hours=2)
    end_time = now

    mock_items = [
        {
            "scenario_name": "compute-01",
            "status": "completed",
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "execution_id": "exec-1",
        },
        {
            "scenario_name": "compute-01",
            "status": "completed",
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "execution_id": "exec-2",
        },
        {
            "scenario_name": "compute-02",
            "status": "failed",
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "execution_id": "exec-3",
        },
    ]

    mock_container = MagicMock()
    mock_container.query_items.return_value = mock_items

    mock_database = MagicMock()
    mock_database.get_container_client.return_value = mock_container

    mock_client = MagicMock()
    mock_client.get_database_client.return_value = mock_database

    result = await query_cosmos_metrics(
        mock_client,
        "test_db",
        "test_container",
        start_time - timedelta(hours=1),
    )

    assert result["total_executions"] == 3
    assert result["success_count"] == 2
    assert result["success_rate"] == pytest.approx(2 / 3, rel=0.01)
    assert result["last_execution"] is not None
    assert len(result["scenario_metrics"]) == 2

    # Check scenario metrics
    compute_01 = next(m for m in result["scenario_metrics"] if m.scenario_name == "compute-01")
    assert compute_01.run_count == 2
    assert compute_01.success_count == 2
    assert compute_01.fail_count == 0

    compute_02 = next(m for m in result["scenario_metrics"] if m.scenario_name == "compute-02")
    assert compute_02.run_count == 1
    assert compute_02.success_count == 0
    assert compute_02.fail_count == 1


@pytest.mark.asyncio
async def test_query_cosmos_metrics_with_scenario_filter():
    """Test querying metrics with scenario filter."""
    now = datetime.now(UTC)
    start_time = now - timedelta(hours=1)

    mock_items = [
        {
            "scenario_name": "compute-01",
            "status": "completed",
            "started_at": start_time.isoformat(),
            "completed_at": now.isoformat(),
            "execution_id": "exec-1",
        },
    ]

    mock_container = MagicMock()
    mock_container.query_items.return_value = mock_items

    mock_database = MagicMock()
    mock_database.get_container_client.return_value = mock_container

    mock_client = MagicMock()
    mock_client.get_database_client.return_value = mock_database

    result = await query_cosmos_metrics(
        mock_client,
        "test_db",
        "test_container",
        start_time,
        scenario_filter="compute-01",
    )

    assert result["total_executions"] == 1
    assert len(result["scenario_metrics"]) == 1
    assert result["scenario_metrics"][0].scenario_name == "compute-01"


def test_scenario_metrics_model():
    """Test ScenarioMetrics model validation."""
    metrics = ScenarioMetrics(
        scenario_name="test",
        run_count=10,
        success_count=8,
        fail_count=2,
        avg_duration_hours=2.5,
    )

    assert metrics.scenario_name == "test"
    assert metrics.run_count == 10
    assert metrics.success_count == 8
    assert metrics.fail_count == 2
    assert metrics.avg_duration_hours == 2.5


def test_metrics_summary_model():
    """Test MetricsSummary model validation."""
    summary = MetricsSummary(
        total_executions=100,
        active_agents=5,
        total_resources=250,
        success_rate=0.95,
        period="7d",
    )

    assert summary.total_executions == 100
    assert summary.active_agents == 5
    assert summary.total_resources == 250
    assert summary.success_rate == 0.95
    assert summary.period == "7d"
    assert summary.scenarios == []


def test_metrics_summary_with_scenarios():
    """Test MetricsSummary with scenario data."""
    scenario1 = ScenarioMetrics(
        scenario_name="compute-01",
        run_count=50,
        success_count=48,
        fail_count=2,
    )
    scenario2 = ScenarioMetrics(
        scenario_name="compute-02",
        run_count=50,
        success_count=47,
        fail_count=3,
    )

    summary = MetricsSummary(
        total_executions=100,
        active_agents=5,
        total_resources=250,
        success_rate=0.95,
        period="30d",
        scenarios=[scenario1, scenario2],
    )

    assert len(summary.scenarios) == 2
    assert summary.scenarios[0].scenario_name == "compute-01"
    assert summary.scenarios[1].scenario_name == "compute-02"
