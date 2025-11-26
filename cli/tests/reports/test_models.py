"""Unit tests for report data models."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError


class TestReportFilters:
    """Test ReportFilters data model."""

    def test_report_filters_valid_data(self):
        """Test ReportFilters accepts valid data."""
        from haymaker_cli.reports.models import ReportFilters

        filters = ReportFilters(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
            scenario_ids=["scenario-001", "scenario-002"],
            status=["completed", "failed"]
        )

        assert filters.scenario_ids == ["scenario-001", "scenario-002"]
        assert filters.status == ["completed", "failed"]

    def test_report_filters_optional_fields(self):
        """Test ReportFilters with optional fields omitted."""
        from haymaker_cli.reports.models import ReportFilters

        filters = ReportFilters()

        assert filters.start_date is None
        assert filters.end_date is None
        assert filters.scenario_ids is None or filters.scenario_ids == []
        assert filters.status is None or filters.status == []

    def test_report_filters_invalid_date_range(self):
        """Test ReportFilters rejects end_date before start_date."""
        from haymaker_cli.reports.models import ReportFilters

        with pytest.raises(ValidationError):
            ReportFilters(
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() - timedelta(days=7)  # Invalid
            )

    def test_report_filters_invalid_status(self):
        """Test ReportFilters validates status values."""
        from haymaker_cli.reports.models import ReportFilters

        with pytest.raises(ValidationError):
            ReportFilters(status=["invalid_status"])

    def test_report_filters_duration_range(self):
        """Test ReportFilters validates duration range."""
        from haymaker_cli.reports.models import ReportFilters

        filters = ReportFilters(
            min_duration_seconds=60,
            max_duration_seconds=3600
        )

        assert filters.min_duration_seconds == 60
        assert filters.max_duration_seconds == 3600

        # Invalid range
        with pytest.raises(ValidationError):
            ReportFilters(
                min_duration_seconds=3600,
                max_duration_seconds=60  # Invalid
            )

    def test_report_filters_to_dict(self):
        """Test ReportFilters serialization to dictionary."""
        from haymaker_cli.reports.models import ReportFilters

        filters = ReportFilters(
            start_date=datetime(2025, 1, 1),
            scenario_ids=["scenario-001"]
        )

        result = filters.dict()

        assert isinstance(result, dict)
        assert "start_date" in result
        assert "scenario_ids" in result


class TestReportMetadata:
    """Test ReportMetadata data model."""

    def test_report_metadata_valid_data(self):
        """Test ReportMetadata accepts valid data."""
        from haymaker_cli.reports.models import ReportMetadata

        metadata = ReportMetadata(
            title="Execution Report",
            generated_at=datetime.utcnow(),
            generated_by="test-user",
            report_type="summary",
            total_records=150
        )

        assert metadata.title == "Execution Report"
        assert metadata.report_type == "summary"
        assert metadata.total_records == 150

    def test_report_metadata_default_values(self):
        """Test ReportMetadata uses default values."""
        from haymaker_cli.reports.models import ReportMetadata

        metadata = ReportMetadata(
            title="Test Report",
            report_type="summary"
        )

        assert metadata.generated_at is not None
        assert isinstance(metadata.generated_at, datetime)

    def test_report_metadata_invalid_report_type(self):
        """Test ReportMetadata validates report type."""
        from haymaker_cli.reports.models import ReportMetadata

        with pytest.raises(ValidationError):
            ReportMetadata(
                title="Test Report",
                report_type="invalid_type"
            )

    def test_report_metadata_with_filters(self):
        """Test ReportMetadata includes filter information."""
        from haymaker_cli.reports.models import ReportMetadata, ReportFilters

        filters = ReportFilters(
            status=["completed"]
        )

        metadata = ReportMetadata(
            title="Test Report",
            report_type="summary",
            filters=filters
        )

        assert metadata.filters is not None
        assert metadata.filters.status == ["completed"]


class TestKPIData:
    """Test KPIData data model."""

    def test_kpi_data_valid_data(self):
        """Test KPIData accepts valid data."""
        from haymaker_cli.reports.models import KPIData

        kpi = KPIData(
            total_executions=150,
            successful_executions=120,
            failed_executions=25,
            running_executions=5,
            success_rate=80.0,
            avg_duration_seconds=287.5
        )

        assert kpi.total_executions == 150
        assert kpi.success_rate == 80.0

    def test_kpi_data_calculated_success_rate(self):
        """Test KPIData calculates success rate if not provided."""
        from haymaker_cli.reports.models import KPIData

        kpi = KPIData(
            total_executions=100,
            successful_executions=80,
            failed_executions=20
        )

        # Should auto-calculate success rate
        assert kpi.success_rate == 80.0

    def test_kpi_data_invalid_percentages(self):
        """Test KPIData validates percentage bounds."""
        from haymaker_cli.reports.models import KPIData

        with pytest.raises(ValidationError):
            KPIData(
                total_executions=100,
                success_rate=150.0  # Invalid: > 100
            )

        with pytest.raises(ValidationError):
            KPIData(
                total_executions=100,
                success_rate=-10.0  # Invalid: < 0
            )

    def test_kpi_data_with_agent_metrics(self):
        """Test KPIData includes agent-level metrics."""
        from haymaker_cli.reports.models import KPIData

        kpi = KPIData(
            total_executions=100,
            total_agents=1200,
            successful_agents=1000,
            failed_agents=200,
            agent_success_rate=83.33
        )

        assert kpi.total_agents == 1200
        assert kpi.agent_success_rate == 83.33

    def test_kpi_data_with_cost_metrics(self):
        """Test KPIData includes cost metrics."""
        from haymaker_cli.reports.models import KPIData

        kpi = KPIData(
            total_executions=100,
            total_cost_usd=456.78,
            avg_cost_per_execution=4.57
        )

        assert kpi.total_cost_usd == 456.78
        assert kpi.avg_cost_per_execution == 4.57

    def test_kpi_data_zero_executions(self):
        """Test KPIData handles zero executions gracefully."""
        from haymaker_cli.reports.models import KPIData

        kpi = KPIData(total_executions=0)

        assert kpi.success_rate == 0.0 or kpi.success_rate is None


class TestReportData:
    """Test ReportData data model."""

    def test_report_data_valid_data(self):
        """Test ReportData accepts valid data."""
        from haymaker_cli.reports.models import ReportData, ReportMetadata, KPIData

        metadata = ReportMetadata(
            title="Test Report",
            report_type="summary"
        )

        kpi = KPIData(total_executions=100)

        report = ReportData(
            metadata=metadata,
            kpi=kpi,
            executions=[],
            charts={}
        )

        assert report.metadata.title == "Test Report"
        assert report.kpi.total_executions == 100

    def test_report_data_with_executions(self):
        """Test ReportData includes execution records."""
        from haymaker_cli.reports.models import ReportData, ReportMetadata, KPIData
        from tests.fixtures.sample_data import sample_execution_data

        report = ReportData(
            metadata=ReportMetadata(title="Test", report_type="detailed"),
            kpi=KPIData(total_executions=5),
            executions=sample_execution_data(count=5)
        )

        assert len(report.executions) == 5

    def test_report_data_with_charts(self):
        """Test ReportData includes chart data."""
        from haymaker_cli.reports.models import ReportData, ReportMetadata, KPIData

        charts = {
            "timeline": {"x": [], "y": []},
            "status_distribution": {"labels": [], "values": []}
        }

        report = ReportData(
            metadata=ReportMetadata(title="Test", report_type="summary"),
            kpi=KPIData(total_executions=100),
            charts=charts
        )

        assert "timeline" in report.charts
        assert "status_distribution" in report.charts

    def test_report_data_to_dict(self):
        """Test ReportData serialization to dictionary."""
        from haymaker_cli.reports.models import ReportData, ReportMetadata, KPIData

        report = ReportData(
            metadata=ReportMetadata(title="Test", report_type="summary"),
            kpi=KPIData(total_executions=100),
            executions=[]
        )

        result = report.dict()

        assert isinstance(result, dict)
        assert "metadata" in result
        assert "kpi" in result
        assert "executions" in result


class TestScenarioReport:
    """Test ScenarioReport data model."""

    def test_scenario_report_valid_data(self):
        """Test ScenarioReport accepts valid data."""
        from haymaker_cli.reports.models import ScenarioReport

        report = ScenarioReport(
            scenario_id="scenario-001",
            scenario_name="Load Test",
            total_executions=50,
            successful_executions=40,
            failed_executions=10,
            success_rate=80.0,
            avg_duration_seconds=300.0
        )

        assert report.scenario_id == "scenario-001"
        assert report.success_rate == 80.0

    def test_scenario_report_comparison(self):
        """Test ScenarioReport supports comparison operations."""
        from haymaker_cli.reports.models import ScenarioReport

        report1 = ScenarioReport(
            scenario_id="s1",
            scenario_name="Test 1",
            total_executions=50,
            success_rate=80.0
        )

        report2 = ScenarioReport(
            scenario_id="s2",
            scenario_name="Test 2",
            total_executions=100,
            success_rate=90.0
        )

        # Should be sortable by success rate or execution count
        reports = sorted([report1, report2], key=lambda r: r.success_rate)
        assert reports[0].scenario_id == "s1"


class TestErrorSummary:
    """Test ErrorSummary data model."""

    def test_error_summary_valid_data(self):
        """Test ErrorSummary accepts valid data."""
        from haymaker_cli.reports.models import ErrorSummary

        summary = ErrorSummary(
            error_message="Connection timeout",
            count=15,
            affected_executions=["exec-001", "exec-002"],
            first_occurrence=datetime.utcnow() - timedelta(days=7),
            last_occurrence=datetime.utcnow()
        )

        assert summary.error_message == "Connection timeout"
        assert summary.count == 15
        assert len(summary.affected_executions) == 2

    def test_error_summary_sorting(self):
        """Test ErrorSummary supports sorting by count."""
        from haymaker_cli.reports.models import ErrorSummary

        error1 = ErrorSummary(
            error_message="Error A",
            count=5
        )

        error2 = ErrorSummary(
            error_message="Error B",
            count=15
        )

        errors = sorted([error1, error2], key=lambda e: e.count, reverse=True)
        assert errors[0].error_message == "Error B"
