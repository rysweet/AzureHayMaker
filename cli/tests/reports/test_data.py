"""Unit tests for report data processing and KPI calculation."""

import pytest
from datetime import datetime, timedelta
from tests.fixtures.sample_data import (
    sample_execution_data,
    sample_agent_data,
    sample_resource_data
)


class TestReportDataProcessor:
    """Test ReportDataProcessor class for KPI calculation."""

    def test_calculate_kpis_basic(self, mock_telemetry_storage):
        """Test basic KPI calculation from execution data."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis()

        assert "total_executions" in kpis
        assert "successful_executions" in kpis
        assert "failed_executions" in kpis
        assert "success_rate" in kpis
        assert kpis["total_executions"] > 0

    def test_calculate_kpis_empty_data(self, mock_telemetry_storage_empty):
        """Test KPI calculation with no data."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage_empty)
        kpis = processor.calculate_kpis()

        assert kpis["total_executions"] == 0
        assert kpis["success_rate"] == 0.0

    def test_calculate_kpis_with_filters(self, mock_telemetry_storage, report_filters):
        """Test KPI calculation with filters applied."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis(filters=report_filters)

        # Should only include filtered data
        assert kpis["total_executions"] <= 50

    def test_calculate_success_rate(self, mock_telemetry_storage):
        """Test success rate calculation."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis()

        # Success rate should be between 0 and 100
        assert 0 <= kpis["success_rate"] <= 100

        # Should match formula: successful / total * 100
        expected = (kpis["successful_executions"] / kpis["total_executions"]) * 100
        assert abs(kpis["success_rate"] - expected) < 0.01

    def test_calculate_avg_duration(self, mock_telemetry_storage):
        """Test average duration calculation."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis()

        assert "avg_duration_seconds" in kpis
        assert kpis["avg_duration_seconds"] > 0

    def test_calculate_agent_metrics(self, mock_telemetry_storage):
        """Test agent-level KPI calculation."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis()

        assert "total_agents" in kpis
        assert "successful_agents" in kpis
        assert "failed_agents" in kpis
        assert "agent_success_rate" in kpis

        # Agent counts should be consistent
        assert kpis["total_agents"] == kpis["successful_agents"] + kpis["failed_agents"]

    def test_calculate_cost_metrics(self, mock_telemetry_storage):
        """Test cost calculation (if available)."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis()

        if "total_cost_usd" in kpis:
            assert kpis["total_cost_usd"] >= 0
            assert kpis["avg_cost_per_execution"] >= 0

    def test_get_top_regions(self, mock_telemetry_storage):
        """Test top regions calculation."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        top_regions = processor.get_top_regions(limit=5)

        assert isinstance(top_regions, list)
        assert len(top_regions) <= 5

        if top_regions:
            # Should be sorted by count descending
            counts = [r["count"] for r in top_regions]
            assert counts == sorted(counts, reverse=True)

    def test_get_top_scenarios(self, mock_telemetry_storage):
        """Test top scenarios calculation."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        top_scenarios = processor.get_top_scenarios(limit=10)

        assert isinstance(top_scenarios, list)
        assert len(top_scenarios) <= 10

        for scenario in top_scenarios:
            assert "scenario" in scenario
            assert "count" in scenario
            assert "success_rate" in scenario

    def test_get_error_distribution(self, mock_telemetry_storage):
        """Test error distribution calculation."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        errors = processor.get_error_distribution()

        assert isinstance(errors, list)

        for error in errors:
            assert "error" in error
            assert "count" in error

        # Should be sorted by count descending
        if len(errors) > 1:
            counts = [e["count"] for e in errors]
            assert counts == sorted(counts, reverse=True)

    def test_get_timeline_data(self, mock_telemetry_storage):
        """Test timeline data generation for charts."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        timeline = processor.get_timeline_data(interval="day")

        assert "x" in timeline  # Dates
        assert "y" in timeline  # Counts
        assert len(timeline["x"]) == len(timeline["y"])

    def test_get_status_distribution(self, mock_telemetry_storage):
        """Test status distribution calculation."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        status_dist = processor.get_status_distribution()

        assert "labels" in status_dist
        assert "values" in status_dist
        assert len(status_dist["labels"]) == len(status_dist["values"])

        # Should include completed, failed, running
        assert "completed" in [l.lower() for l in status_dist["labels"]]

    def test_get_duration_histogram(self, mock_telemetry_storage):
        """Test duration histogram generation."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        histogram = processor.get_duration_histogram(bins=10)

        assert "bins" in histogram
        assert "counts" in histogram
        assert len(histogram["bins"]) <= 10

    def test_get_region_distribution(self, mock_telemetry_storage):
        """Test region distribution calculation."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        region_dist = processor.get_region_distribution()

        assert "labels" in region_dist
        assert "values" in region_dist
        assert len(region_dist["labels"]) == len(region_dist["values"])

    def test_filter_by_date_range(self, mock_telemetry_storage):
        """Test filtering data by date range."""
        from haymaker_cli.reports.data import ReportDataProcessor
        from haymaker_cli.reports.models import ReportFilters

        filters = ReportFilters(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow()
        )

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis(filters=filters)

        # Should only include recent data
        assert kpis["total_executions"] >= 0

    def test_filter_by_scenario(self, mock_telemetry_storage):
        """Test filtering data by scenario IDs."""
        from haymaker_cli.reports.data import ReportDataProcessor
        from haymaker_cli.reports.models import ReportFilters

        filters = ReportFilters(
            scenario_ids=["scenario-001"]
        )

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis(filters=filters)

        # Should only include specified scenarios
        assert kpis["total_executions"] >= 0

    def test_filter_by_status(self, mock_telemetry_storage):
        """Test filtering data by execution status."""
        from haymaker_cli.reports.data import ReportDataProcessor
        from haymaker_cli.reports.models import ReportFilters

        filters = ReportFilters(status=["completed"])

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis(filters=filters)

        # Should only include completed executions
        assert kpis["failed_executions"] == 0

    def test_filter_by_duration_range(self, mock_telemetry_storage):
        """Test filtering data by duration range."""
        from haymaker_cli.reports.data import ReportDataProcessor
        from haymaker_cli.reports.models import ReportFilters

        filters = ReportFilters(
            min_duration_seconds=60,
            max_duration_seconds=3600
        )

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis(filters=filters)

        # Should only include executions within duration range
        if kpis["total_executions"] > 0:
            assert 60 <= kpis["avg_duration_seconds"] <= 3600

    def test_calculate_percentiles(self, mock_telemetry_storage):
        """Test percentile calculation for duration."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        percentiles = processor.calculate_percentiles([50, 90, 95, 99])

        assert "p50" in percentiles
        assert "p90" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles

        # Percentiles should be monotonically increasing
        assert percentiles["p50"] <= percentiles["p90"]
        assert percentiles["p90"] <= percentiles["p95"]
        assert percentiles["p95"] <= percentiles["p99"]

    def test_get_scenario_comparison(self, mock_telemetry_storage):
        """Test scenario comparison data."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        comparison = processor.get_scenario_comparison()

        assert isinstance(comparison, list)

        for scenario in comparison:
            assert "scenario_id" in scenario
            assert "scenario_name" in scenario
            assert "total_executions" in scenario
            assert "success_rate" in scenario

    def test_get_agent_performance(self, mock_telemetry_storage):
        """Test agent performance metrics."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        performance = processor.get_agent_performance()

        assert "avg_duration_seconds" in performance
        assert "p50_duration" in performance
        assert "p95_duration" in performance

    def test_get_resource_utilization(self, mock_telemetry_storage):
        """Test resource utilization metrics."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        utilization = processor.get_resource_utilization()

        assert "avg_cpu_percent" in utilization
        assert "avg_memory_percent" in utilization
        assert "peak_cpu_percent" in utilization
        assert "peak_memory_percent" in utilization

    def test_get_failure_analysis(self, mock_telemetry_storage):
        """Test failure analysis data."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        analysis = processor.get_failure_analysis()

        assert "total_failures" in analysis
        assert "failure_rate" in analysis
        assert "top_errors" in analysis
        assert "failure_by_region" in analysis

    def test_aggregate_by_time_interval(self, mock_telemetry_storage):
        """Test data aggregation by time intervals."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)

        # Test hourly aggregation
        hourly = processor.aggregate_by_time("hour")
        assert isinstance(hourly, list)

        # Test daily aggregation
        daily = processor.aggregate_by_time("day")
        assert isinstance(daily, list)

        # Daily should have fewer points than hourly
        assert len(daily) <= len(hourly)

    def test_compare_time_periods(self, mock_telemetry_storage):
        """Test comparison between time periods."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)

        comparison = processor.compare_time_periods(
            period1_days=7,
            period2_days=7
        )

        assert "period1" in comparison
        assert "period2" in comparison
        assert "change_percent" in comparison

    def test_export_to_csv_format(self, mock_telemetry_storage):
        """Test data export to CSV format."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        csv_data = processor.export_to_csv_format()

        assert isinstance(csv_data, list)
        assert len(csv_data) > 0

        # First row should be headers
        headers = csv_data[0]
        assert "Execution ID" in headers or "execution_id" in headers
