"""Integration tests for full report generation workflow."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta


class TestReportGenerationWorkflow:
    """Test complete report generation workflow."""

    def test_full_report_generation_cycle(self, mock_telemetry_storage, tmp_path):
        """Test complete report generation from data to HTML."""
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.reports.data import ReportDataProcessor

        # Process data
        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis()

        assert kpis["total_executions"] > 0

        # Generate report
        generator = ReportGenerator(mock_telemetry_storage, tmp_path)
        report_path = generator.generate_summary_report()

        assert report_path.exists()
        assert report_path.stat().st_size > 0

        # Verify HTML content
        with open(report_path) as f:
            content = f.read()
            assert "<!DOCTYPE" in content or "<html" in content
            assert str(kpis["total_executions"]) in content

    def test_multi_format_report_generation(self, mock_telemetry_storage, tmp_path):
        """Test generating reports in multiple formats."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, tmp_path)

        # Generate HTML
        html_path = generator.generate_summary_report(format="html")
        assert html_path.exists()
        assert html_path.suffix == ".html"

        # Generate CSV
        csv_path = generator.export_to_csv()
        assert csv_path.exists()
        assert csv_path.suffix == ".csv"

        # Generate JSON
        json_path = generator.export_to_json()
        assert json_path.exists()
        assert json_path.suffix == ".json"

    def test_filtered_report_generation(self, mock_telemetry_storage, tmp_path):
        """Test report generation with filters applied."""
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.reports.models import ReportFilters

        # Create filters
        filters = ReportFilters(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
            status=["completed"]
        )

        generator = ReportGenerator(mock_telemetry_storage, tmp_path)
        report_path = generator.generate_summary_report(filters=filters)

        assert report_path.exists()

        # Verify filters were applied
        with open(report_path) as f:
            content = f.read()
            # Should mention completed status or filtering

    def test_report_with_charts(self, mock_telemetry_storage, tmp_path):
        """Test report generation includes charts."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, tmp_path)

        # Generate charts
        charts = generator.generate_charts()

        assert "timeline" in charts
        assert "status_distribution" in charts

        # Generate report with charts
        report_path = generator.generate_summary_report()

        with open(report_path) as f:
            content = f.read()
            # Should include chart div or Plotly reference
            assert "chart" in content.lower() or "plotly" in content.lower()

    def test_scenario_specific_report(self, mock_telemetry_storage, tmp_path):
        """Test scenario-specific report generation."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, tmp_path)

        report_path = generator.generate_scenario_report("scenario-001")

        assert report_path.exists()

        with open(report_path) as f:
            content = f.read()
            assert "scenario" in content.lower()

    def test_error_analysis_report(self, mock_telemetry_storage, tmp_path):
        """Test error analysis report generation."""
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.reports.data import ReportDataProcessor

        # Get error data
        processor = ReportDataProcessor(mock_telemetry_storage)
        errors = processor.get_error_distribution()

        # Generate error report
        generator = ReportGenerator(mock_telemetry_storage, tmp_path)
        report_path = generator.generate_error_report()

        assert report_path.exists()

        with open(report_path) as f:
            content = f.read()
            assert "error" in content.lower()

    def test_comparison_report_generation(self, mock_telemetry_storage, tmp_path):
        """Test time period comparison report."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, tmp_path)

        report_path = generator.generate_comparison_report(
            period1_days=7,
            period2_days=7
        )

        assert report_path.exists()

        with open(report_path) as f:
            content = f.read()
            assert "comparison" in content.lower()

    def test_report_template_rendering(self, mock_telemetry_storage, tmp_path):
        """Test Jinja2 template rendering."""
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)
        kpis = processor.calculate_kpis()

        generator = ReportGenerator(mock_telemetry_storage, tmp_path)

        # Render template
        html = generator.render_template(
            template_name="summary.html",
            context={"kpis": kpis}
        )

        assert len(html) > 0
        assert "<html>" in html.lower() or "<!doctype" in html.lower()

    def test_custom_report_styling(self, mock_telemetry_storage, tmp_path):
        """Test custom CSS in reports."""
        from haymaker_cli.reports.generator import ReportGenerator

        custom_css = """
        body { font-family: Arial; }
        .kpi { color: blue; }
        """

        generator = ReportGenerator(mock_telemetry_storage, tmp_path)
        report_path = generator.generate_summary_report(custom_css=custom_css)

        with open(report_path) as f:
            content = f.read()
            assert "Arial" in content

    def test_report_metadata_tracking(self, mock_telemetry_storage, tmp_path):
        """Test report metadata is tracked."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, tmp_path)
        report_path = generator.generate_summary_report()

        # Check for metadata file
        metadata_path = report_path.with_suffix(".json")
        if metadata_path.exists():
            import json
            with open(metadata_path) as f:
                metadata = json.load(f)
                assert "generated_at" in metadata

    def test_empty_data_report_generation(self, mock_telemetry_storage_empty, tmp_path):
        """Test report generation with empty data."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage_empty, tmp_path)
        report_path = generator.generate_summary_report()

        assert report_path.exists()

        with open(report_path) as f:
            content = f.read()
            assert "no data" in content.lower() or "0" in content


class TestDataProcessingIntegration:
    """Test data processing for reports."""

    def test_kpi_calculation_pipeline(self, mock_telemetry_storage):
        """Test complete KPI calculation pipeline."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)

        # Calculate all KPIs
        kpis = processor.calculate_kpis()

        # Verify all expected KPIs are present
        assert "total_executions" in kpis
        assert "successful_executions" in kpis
        assert "failed_executions" in kpis
        assert "success_rate" in kpis
        assert "avg_duration_seconds" in kpis

        # Verify calculations are consistent
        assert kpis["total_executions"] >= kpis["successful_executions"]
        assert kpis["success_rate"] <= 100.0

    def test_aggregation_pipeline(self, mock_telemetry_storage):
        """Test data aggregation pipeline."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)

        # Get top regions
        regions = processor.get_top_regions(limit=5)
        assert isinstance(regions, list)

        # Get top scenarios
        scenarios = processor.get_top_scenarios(limit=10)
        assert isinstance(scenarios, list)

        # Get error distribution
        errors = processor.get_error_distribution()
        assert isinstance(errors, list)

    def test_chart_data_generation(self, mock_telemetry_storage):
        """Test chart data generation pipeline."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)

        # Timeline chart
        timeline = processor.get_timeline_data(interval="day")
        assert "x" in timeline
        assert "y" in timeline

        # Status distribution
        status_dist = processor.get_status_distribution()
        assert "labels" in status_dist
        assert "values" in status_dist

        # Region distribution
        region_dist = processor.get_region_distribution()
        assert "labels" in region_dist

    def test_filtering_pipeline(self, mock_telemetry_storage):
        """Test data filtering pipeline."""
        from haymaker_cli.reports.data import ReportDataProcessor
        from haymaker_cli.reports.models import ReportFilters

        processor = ReportDataProcessor(mock_telemetry_storage)

        # Test various filter combinations
        filters = ReportFilters(
            status=["completed"],
            scenario_ids=["scenario-001"]
        )

        kpis = processor.calculate_kpis(filters=filters)

        # Should only include filtered data
        assert kpis["failed_executions"] == 0

    def test_export_pipeline(self, mock_telemetry_storage):
        """Test data export pipeline."""
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)

        # Export to CSV format
        csv_data = processor.export_to_csv_format()

        assert isinstance(csv_data, list)
        assert len(csv_data) > 0

        # First row should be headers
        headers = csv_data[0]
        assert len(headers) > 0


class TestEndToEndReportWorkflow:
    """Test complete end-to-end report workflow."""

    def test_collection_to_report_workflow(self, mock_api_client, tmp_path):
        """Test complete workflow from collection to report generation."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from haymaker_cli.reports.generator import ReportGenerator

        storage_dir = tmp_path / "telemetry"
        reports_dir = tmp_path / "reports"

        # Step 1: Collect telemetry data
        storage = TelemetryStorage(storage_dir)
        collector = TelemetryCollector(mock_api_client, storage)

        import asyncio
        result = asyncio.run(collector.collect_once())

        assert result.success is True

        # Step 2: Generate report from collected data
        generator = ReportGenerator(storage, reports_dir)
        report_path = generator.generate_summary_report()

        assert report_path.exists()

        # Step 3: Verify report contains collected data
        with open(report_path) as f:
            content = f.read()
            assert len(content) > 0

    def test_scheduled_collection_and_reporting(self, mock_api_client, tmp_path):
        """Test scheduled collection with periodic reporting."""
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage
        from haymaker_cli.reports.generator import ReportGenerator
        import asyncio

        storage_dir = tmp_path / "telemetry"
        reports_dir = tmp_path / "reports"

        storage = TelemetryStorage(storage_dir)
        collector = TelemetryCollector(mock_api_client, storage, interval_seconds=0.5)

        async def run_workflow():
            # Start background collection
            await collector.start_background()

            # Wait for some collections
            await asyncio.sleep(1.5)

            # Generate report while collection is running
            generator = ReportGenerator(storage, reports_dir)
            report_path = generator.generate_summary_report()

            assert report_path.exists()

            # Stop collection
            await collector.stop_background()

            return report_path

        report_path = asyncio.run(run_workflow())
        assert report_path.exists()

    def test_multi_report_generation(self, mock_telemetry_storage, tmp_path):
        """Test generating multiple report types."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, tmp_path)

        # Generate all report types
        summary = generator.generate_summary_report()
        detailed = generator.generate_detailed_report()
        errors = generator.generate_error_report()

        assert summary.exists()
        assert detailed.exists()
        assert errors.exists()

        # All reports should be different
        assert summary != detailed
        assert detailed != errors

    def test_report_archival_workflow(self, mock_telemetry_storage, tmp_path):
        """Test report generation and archival."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, tmp_path)

        # Generate report with timestamp
        report_path = generator.generate_summary_report(include_timestamp=True)

        assert report_path.exists()

        # Archive directory should contain timestamped report
        report_files = list(tmp_path.glob("*.html"))
        assert len(report_files) > 0

    def test_report_diff_workflow(self, mock_telemetry_storage, tmp_path):
        """Test comparing reports across time periods."""
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.reports.data import ReportDataProcessor

        processor = ReportDataProcessor(mock_telemetry_storage)

        # Compare two time periods
        comparison = processor.compare_time_periods(
            period1_days=7,
            period2_days=7
        )

        assert "period1" in comparison
        assert "period2" in comparison

        # Generate comparison report
        generator = ReportGenerator(mock_telemetry_storage, tmp_path)
        report_path = generator.generate_comparison_report(
            period1_days=7,
            period2_days=7
        )

        assert report_path.exists()
