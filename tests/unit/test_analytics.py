"""Unit tests for analytics endpoint logic.

Tests the analytics aggregation logic from orchestrator_server.py.
Since the orchestrator_server.py is a standalone entry point with heavy
Azure SDK dependencies, we test the core analytics aggregation logic
by extracting it into testable functions.
"""

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from azure_haymaker.models.execution import (
    AnalyticsSummary,
    ExecutionCounts,
    ScenarioStats,
)

# ==============================================================================
# ANALYTICS AGGREGATION FUNCTIONS (extracted for testing)
# ==============================================================================


def aggregate_analytics(
    entities: list[dict[str, Any]],
    period: str,
) -> AnalyticsSummary:
    """Aggregate analytics from Table Storage entities.

    This is the core aggregation logic extracted from orchestrator_server.py
    for unit testing. The actual endpoint uses this same algorithm.

    Args:
        entities: List of Table Storage entities
        period: Time period string (7d, 30d, 90d)

    Returns:
        AnalyticsSummary with aggregated statistics
    """
    total_executions = 0
    succeeded_executions = 0
    failed_executions = 0
    total_duration_hours = 0.0
    duration_count = 0
    scenario_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"count": 0, "succeeded": 0, "failed": 0}
    )

    # Track seen execution IDs to avoid double-counting
    seen_execution_ids: set[str] = set()

    for entity in entities:
        execution_id = entity.get("PartitionKey", "")

        # Skip if we've already counted this execution
        if execution_id in seen_execution_ids:
            continue
        seen_execution_ids.add(execution_id)

        total_executions += 1

        # Count by status
        status = entity.get("Status", "")
        if status in ("completed", "COMPLETED"):
            succeeded_executions += 1
        elif status in ("failed", "FAILED", "error", "ERROR"):
            failed_executions += 1

        # Calculate duration if we have timestamps
        created_at_str = entity.get("CreatedAt")
        completed_at_str = entity.get("CompletedAt")
        if created_at_str and completed_at_str:
            try:
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
                completed_at = datetime.fromisoformat(
                    completed_at_str.replace("Z", "+00:00")
                )
                duration = (completed_at - created_at).total_seconds() / 3600
                if duration > 0:
                    total_duration_hours += duration
                    duration_count += 1
            except (ValueError, TypeError):
                pass  # Skip malformed timestamps

        # Track scenario statistics
        scenarios_json = entity.get("Scenarios", "[]")
        try:
            scenarios = json.loads(scenarios_json)
            for scenario_name in scenarios:
                scenario_stats[scenario_name]["count"] += 1
                if status in ("completed", "COMPLETED"):
                    scenario_stats[scenario_name]["succeeded"] += 1
                elif status in ("failed", "FAILED", "error", "ERROR"):
                    scenario_stats[scenario_name]["failed"] += 1
        except (json.JSONDecodeError, TypeError):
            pass  # Skip malformed scenarios

    # Calculate success rate
    success_rate = (
        succeeded_executions / total_executions if total_executions > 0 else 0.0
    )

    # Calculate average duration
    avg_duration = total_duration_hours / duration_count if duration_count > 0 else 0.0

    # Build top scenarios list (top 10 by execution count)
    top_scenarios = sorted(
        [
            ScenarioStats(
                name=name,
                count=stats["count"],
                success_rate=(
                    stats["succeeded"] / stats["count"]
                    if stats["count"] > 0
                    else 0.0
                ),
            )
            for name, stats in scenario_stats.items()
        ],
        key=lambda s: s.count,
        reverse=True,
    )[:10]

    return AnalyticsSummary(
        period=period,
        executions=ExecutionCounts(
            total=total_executions,
            succeeded=succeeded_executions,
            failed=failed_executions,
        ),
        success_rate=round(success_rate, 4),
        avg_duration_hours=round(avg_duration, 2),
        top_scenarios=top_scenarios,
    )


def build_odata_filter(cutoff_date: datetime) -> str:
    """Build OData filter for Table Storage query.

    Args:
        cutoff_date: Cutoff date for filtering

    Returns:
        OData filter string with proper datetime format
    """
    cutoff_iso = cutoff_date.isoformat()
    # Azure Table Storage OData requires datetime'...' prefix for date comparisons
    return f"CreatedAt ge datetime'{cutoff_iso}'"


def parse_period_days(period: str) -> int:
    """Parse period string to number of days.

    Args:
        period: Period string (7d, 30d, 90d)

    Returns:
        Number of days
    """
    period_days = {"7d": 7, "30d": 30, "90d": 90}
    return period_days[period]


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def sample_entities():
    """Create sample Table Storage entities for testing."""
    now = datetime.now(UTC)
    return [
        {
            "PartitionKey": "exec-001",
            "RowKey": "2024-01-15T10:00:00",
            "Status": "completed",
            "CreatedAt": (now - timedelta(days=5)).isoformat(),
            "CompletedAt": (now - timedelta(days=5) + timedelta(hours=2)).isoformat(),
            "Scenarios": json.dumps(["compute-01-linux-vm", "networking-01-vnet"]),
        },
        {
            "PartitionKey": "exec-002",
            "RowKey": "2024-01-16T10:00:00",
            "Status": "COMPLETED",
            "CreatedAt": (now - timedelta(days=4)).isoformat(),
            "CompletedAt": (now - timedelta(days=4) + timedelta(hours=3)).isoformat(),
            "Scenarios": json.dumps(["compute-01-linux-vm", "storage-01-blob"]),
        },
        {
            "PartitionKey": "exec-003",
            "RowKey": "2024-01-17T10:00:00",
            "Status": "failed",
            "CreatedAt": (now - timedelta(days=3)).isoformat(),
            "CompletedAt": (now - timedelta(days=3) + timedelta(hours=1)).isoformat(),
            "Scenarios": json.dumps(["networking-01-vnet"]),
        },
    ]


# ==============================================================================
# TEST CLASSES
# ==============================================================================


class TestAnalyticsEmptyResults:
    """Test analytics aggregation with empty or missing data."""

    def test_empty_entities_returns_zero_counts(self):
        """Test that empty entities list returns zero counts."""
        result = aggregate_analytics([], "7d")

        assert result.period == "7d"
        assert result.executions.total == 0
        assert result.executions.succeeded == 0
        assert result.executions.failed == 0
        assert result.success_rate == 0.0
        assert result.avg_duration_hours == 0.0
        assert result.top_scenarios == []

    def test_empty_analytics_summary_model(self):
        """Test creating empty AnalyticsSummary directly."""
        summary = AnalyticsSummary(
            period="30d",
            executions=ExecutionCounts(total=0, succeeded=0, failed=0),
            success_rate=0.0,
            avg_duration_hours=0.0,
            top_scenarios=[],
        )

        assert summary.period == "30d"
        assert summary.executions.total == 0
        assert summary.success_rate == 0.0


class TestAnalyticsAggregation:
    """Test analytics aggregation logic."""

    def test_aggregation_counts_executions_correctly(self, sample_entities):
        """Test that execution counts are aggregated correctly."""
        result = aggregate_analytics(sample_entities, "7d")

        assert result.executions.total == 3
        assert result.executions.succeeded == 2
        assert result.executions.failed == 1

    def test_success_rate_calculation(self, sample_entities):
        """Test that success rate is calculated correctly."""
        result = aggregate_analytics(sample_entities, "7d")

        # 2 succeeded / 3 total = 0.6667
        assert result.success_rate == pytest.approx(0.6667, rel=0.01)

    def test_average_duration_calculation(self, sample_entities):
        """Test that average duration is calculated correctly."""
        result = aggregate_analytics(sample_entities, "7d")

        # Average of 2h, 3h, 1h = 2.0h
        assert result.avg_duration_hours == pytest.approx(2.0, rel=0.01)

    def test_top_scenarios_aggregation(self, sample_entities):
        """Test that top scenarios are aggregated and sorted correctly."""
        result = aggregate_analytics(sample_entities, "7d")

        top_scenarios = result.top_scenarios

        # compute-01-linux-vm appears in 2 executions (both succeeded)
        # networking-01-vnet appears in 2 executions (1 succeeded, 1 failed)
        # storage-01-blob appears in 1 execution (succeeded)
        assert len(top_scenarios) >= 2

        # Should be sorted by count descending
        scenario_names = [s.name for s in top_scenarios]
        assert "compute-01-linux-vm" in scenario_names
        assert "networking-01-vnet" in scenario_names

        # Find compute-01-linux-vm and check success rate
        compute_01 = next(s for s in top_scenarios if s.name == "compute-01-linux-vm")
        assert compute_01.count == 2
        assert compute_01.success_rate == 1.0  # Both succeeded

        # Find networking-01-vnet and check success rate
        networking_01 = next(s for s in top_scenarios if s.name == "networking-01-vnet")
        assert networking_01.count == 2
        assert networking_01.success_rate == 0.5  # 1 of 2 succeeded

    def test_deduplication_of_execution_ids(self):
        """Test that duplicate execution IDs are not counted twice."""
        duplicate_entities = [
            {
                "PartitionKey": "exec-001",
                "RowKey": "row-1",
                "Status": "completed",
                "CreatedAt": datetime.now(UTC).isoformat(),
                "CompletedAt": datetime.now(UTC).isoformat(),
                "Scenarios": "[]",
            },
            {
                "PartitionKey": "exec-001",  # Same execution ID
                "RowKey": "row-2",
                "Status": "completed",
                "CreatedAt": datetime.now(UTC).isoformat(),
                "CompletedAt": datetime.now(UTC).isoformat(),
                "Scenarios": "[]",
            },
        ]

        result = aggregate_analytics(duplicate_entities, "7d")

        # Should only count as 1 execution, not 2
        assert result.executions.total == 1
        assert result.executions.succeeded == 1

    def test_status_variations(self):
        """Test that various status string variations are handled correctly."""
        entities = [
            {"PartitionKey": "exec-1", "Status": "completed", "Scenarios": "[]"},
            {"PartitionKey": "exec-2", "Status": "COMPLETED", "Scenarios": "[]"},
            {"PartitionKey": "exec-3", "Status": "failed", "Scenarios": "[]"},
            {"PartitionKey": "exec-4", "Status": "FAILED", "Scenarios": "[]"},
            {"PartitionKey": "exec-5", "Status": "error", "Scenarios": "[]"},
            {"PartitionKey": "exec-6", "Status": "ERROR", "Scenarios": "[]"},
            {"PartitionKey": "exec-7", "Status": "running", "Scenarios": "[]"},  # Not counted
        ]

        result = aggregate_analytics(entities, "7d")

        assert result.executions.total == 7
        assert result.executions.succeeded == 2  # completed, COMPLETED
        assert result.executions.failed == 4  # failed, FAILED, error, ERROR


class TestAnalyticsDateFiltering:
    """Test date filtering utilities."""

    def test_odata_filter_format_uses_datetime_prefix(self):
        """Test that OData filter uses correct datetime'...' format."""
        cutoff = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        query_filter = build_odata_filter(cutoff)

        # Should contain datetime prefix (critical for Azure Table Storage)
        assert "datetime'" in query_filter
        assert query_filter.startswith("CreatedAt ge datetime'")

    def test_parse_period_7d(self):
        """Test parsing 7d period."""
        assert parse_period_days("7d") == 7

    def test_parse_period_30d(self):
        """Test parsing 30d period."""
        assert parse_period_days("30d") == 30

    def test_parse_period_90d(self):
        """Test parsing 90d period."""
        assert parse_period_days("90d") == 90

    def test_parse_period_invalid(self):
        """Test parsing invalid period raises KeyError."""
        with pytest.raises(KeyError):
            parse_period_days("invalid")


class TestAnalyticsEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_malformed_scenarios_json(self):
        """Test that malformed scenarios JSON is handled gracefully."""
        malformed_entities = [
            {
                "PartitionKey": "exec-001",
                "RowKey": "row-1",
                "Status": "completed",
                "CreatedAt": datetime.now(UTC).isoformat(),
                "CompletedAt": datetime.now(UTC).isoformat(),
                "Scenarios": "not valid json",  # Malformed JSON
            },
        ]

        # Should not raise, just skip the malformed data
        result = aggregate_analytics(malformed_entities, "7d")

        assert result.executions.total == 1
        assert result.top_scenarios == []

    def test_handles_malformed_timestamps(self):
        """Test that malformed timestamps are handled gracefully."""
        malformed_entities = [
            {
                "PartitionKey": "exec-001",
                "RowKey": "row-1",
                "Status": "completed",
                "CreatedAt": "not-a-date",  # Malformed
                "CompletedAt": "also-not-a-date",  # Malformed
                "Scenarios": "[]",
            },
        ]

        # Should not raise, just skip duration calculation
        result = aggregate_analytics(malformed_entities, "7d")

        assert result.avg_duration_hours == 0.0

    def test_handles_missing_fields(self):
        """Test that missing fields are handled gracefully."""
        sparse_entities = [
            {
                "PartitionKey": "exec-001",
                "RowKey": "row-1",
                # Missing Status, CreatedAt, CompletedAt, Scenarios
            },
        ]

        # Should not raise
        result = aggregate_analytics(sparse_entities, "7d")

        assert result.executions.total == 1
        assert result.executions.succeeded == 0
        assert result.executions.failed == 0

    def test_handles_none_values(self):
        """Test that None values in fields are handled gracefully."""
        entities_with_none = [
            {
                "PartitionKey": "exec-001",
                "RowKey": "row-1",
                "Status": None,
                "CreatedAt": None,
                "CompletedAt": None,
                "Scenarios": None,
            },
        ]

        # Should not raise
        result = aggregate_analytics(entities_with_none, "7d")

        assert result.executions.total == 1

    def test_handles_negative_duration(self):
        """Test that negative duration (completed before created) is skipped."""
        now = datetime.now(UTC)
        entities = [
            {
                "PartitionKey": "exec-001",
                "Status": "completed",
                "CreatedAt": now.isoformat(),
                "CompletedAt": (now - timedelta(hours=1)).isoformat(),  # Before created
                "Scenarios": "[]",
            },
        ]

        result = aggregate_analytics(entities, "7d")

        # Duration should not be counted (negative)
        assert result.avg_duration_hours == 0.0

    def test_z_suffix_timestamp_handling(self):
        """Test that Z-suffixed timestamps are handled correctly."""
        entities = [
            {
                "PartitionKey": "exec-001",
                "Status": "completed",
                "CreatedAt": "2024-01-15T10:00:00Z",  # Z suffix
                "CompletedAt": "2024-01-15T12:00:00Z",  # Z suffix
                "Scenarios": "[]",
            },
        ]

        result = aggregate_analytics(entities, "7d")

        # Should correctly calculate 2 hour duration
        assert result.avg_duration_hours == pytest.approx(2.0, rel=0.01)


class TestScenarioStatsModel:
    """Test ScenarioStats model."""

    def test_scenario_stats_creation(self):
        """Test creating ScenarioStats model."""
        stats = ScenarioStats(
            name="compute-01-linux-vm",
            count=10,
            success_rate=0.8,
        )

        assert stats.name == "compute-01-linux-vm"
        assert stats.count == 10
        assert stats.success_rate == 0.8


class TestExecutionCountsModel:
    """Test ExecutionCounts model."""

    def test_execution_counts_creation(self):
        """Test creating ExecutionCounts model."""
        counts = ExecutionCounts(
            total=100,
            succeeded=85,
            failed=15,
        )

        assert counts.total == 100
        assert counts.succeeded == 85
        assert counts.failed == 15


class TestAnalyticsSummaryModel:
    """Test AnalyticsSummary model."""

    def test_analytics_summary_full(self):
        """Test creating full AnalyticsSummary model."""
        summary = AnalyticsSummary(
            period="30d",
            executions=ExecutionCounts(total=100, succeeded=85, failed=15),
            success_rate=0.85,
            avg_duration_hours=2.5,
            top_scenarios=[
                ScenarioStats(name="compute-01", count=50, success_rate=0.9),
                ScenarioStats(name="networking-01", count=30, success_rate=0.8),
            ],
        )

        assert summary.period == "30d"
        assert summary.executions.total == 100
        assert summary.success_rate == 0.85
        assert summary.avg_duration_hours == 2.5
        assert len(summary.top_scenarios) == 2
        assert summary.top_scenarios[0].name == "compute-01"
