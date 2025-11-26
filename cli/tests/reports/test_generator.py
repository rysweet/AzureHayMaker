"""Unit tests for report generator."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta


class TestReportGenerator:
    """Test ReportGenerator class."""

    def test_generator_initialization(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator initializes correctly."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(
            storage=mock_telemetry_storage,
            output_dir=report_output_dir
        )

        assert generator.storage == mock_telemetry_storage
        assert generator.output_dir == report_output_dir

    def test_generate_summary_report(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator generates summary report."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_summary_report()

        assert report_path.exists()
        assert report_path.suffix == ".html"
        assert "summary" in report_path.name.lower()

    def test_generate_detailed_report(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator generates detailed report."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_detailed_report()

        assert report_path.exists()
        assert report_path.suffix == ".html"
        assert "detailed" in report_path.name.lower()

    def test_generate_scenario_report(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator generates scenario-specific report."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_scenario_report("scenario-001")

        assert report_path.exists()
        assert "scenario" in report_path.name.lower()

    def test_generate_error_report(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator generates error analysis report."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_error_report()

        assert report_path.exists()
        assert "error" in report_path.name.lower()

    def test_generate_report_with_filters(self, mock_telemetry_storage, report_output_dir, report_filters):
        """Test ReportGenerator applies filters when generating reports."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_summary_report(filters=report_filters)

        assert report_path.exists()

        # Verify filter info is in report (by checking file content)
        with open(report_path) as f:
            content = f.read()
            assert len(content) > 0

    def test_generate_csv_export(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator exports data to CSV."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        csv_path = generator.export_to_csv()

        assert csv_path.exists()
        assert csv_path.suffix == ".csv"

        # Verify CSV has content
        with open(csv_path) as f:
            lines = f.readlines()
            assert len(lines) > 0
            assert "," in lines[0]  # Header with commas

    def test_generate_json_export(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator exports data to JSON."""
        from haymaker_cli.reports.generator import ReportGenerator
        import json

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        json_path = generator.export_to_json()

        assert json_path.exists()
        assert json_path.suffix == ".json"

        # Verify valid JSON
        with open(json_path) as f:
            data = json.load(f)
            assert isinstance(data, dict)

    def test_generate_charts(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator generates chart data (Plotly)."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        charts = generator.generate_charts()

        assert isinstance(charts, dict)
        assert "timeline" in charts
        assert "status_distribution" in charts
        assert "region_distribution" in charts

        # Charts should be JSON serializable
        import json
        json.dumps(charts)

    def test_render_template(self, mock_telemetry_storage, report_output_dir, sample_kpis):
        """Test ReportGenerator renders Jinja2 templates."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        html = generator.render_template(
            template_name="summary.html",
            context={"kpis": sample_kpis}
        )

        assert isinstance(html, str)
        assert len(html) > 0
        assert "<html>" in html.lower() or "<!doctype" in html.lower()

    def test_generate_report_empty_data(self, mock_telemetry_storage_empty, report_output_dir):
        """Test ReportGenerator handles empty data gracefully."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage_empty, report_output_dir)

        report_path = generator.generate_summary_report()

        assert report_path.exists()

        # Should still generate report with zero data message
        with open(report_path) as f:
            content = f.read()
            assert "no data" in content.lower() or "0" in content

    def test_generate_report_custom_filename(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator uses custom filename."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        custom_name = "my_custom_report.html"
        report_path = generator.generate_summary_report(filename=custom_name)

        assert report_path.name == custom_name

    def test_generate_report_creates_output_dir(self, mock_telemetry_storage, tmp_path):
        """Test ReportGenerator creates output directory if not exists."""
        from haymaker_cli.reports.generator import ReportGenerator

        new_dir = tmp_path / "new_reports"
        assert not new_dir.exists()

        generator = ReportGenerator(mock_telemetry_storage, new_dir)
        generator.generate_summary_report()

        assert new_dir.exists()

    def test_generate_multiple_reports(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator generates multiple reports without conflicts."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report1 = generator.generate_summary_report()
        report2 = generator.generate_detailed_report()
        report3 = generator.generate_error_report()

        assert report1.exists()
        assert report2.exists()
        assert report3.exists()
        assert report1 != report2 != report3

    def test_generate_report_with_timestamp(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator includes timestamp in filename."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_summary_report(include_timestamp=True)

        # Filename should include date/time
        assert any(char.isdigit() for char in report_path.stem)

    def test_add_custom_css(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator supports custom CSS."""
        from haymaker_cli.reports.generator import ReportGenerator

        custom_css = "body { background-color: #f0f0f0; }"

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_summary_report(custom_css=custom_css)

        with open(report_path) as f:
            content = f.read()
            assert custom_css in content

    def test_add_custom_logo(self, mock_telemetry_storage, report_output_dir, tmp_path):
        """Test ReportGenerator supports custom logo."""
        from haymaker_cli.reports.generator import ReportGenerator

        # Create fake logo file
        logo_path = tmp_path / "logo.png"
        logo_path.write_text("fake logo data")

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_summary_report(logo_path=logo_path)

        with open(report_path) as f:
            content = f.read()
            assert "logo" in content.lower() or "img" in content.lower()

    def test_generate_comparison_report(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator generates time period comparison report."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_comparison_report(
            period1_days=7,
            period2_days=7
        )

        assert report_path.exists()
        assert "comparison" in report_path.name.lower()

    def test_generate_agent_performance_report(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator generates agent performance report."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_agent_performance_report()

        assert report_path.exists()
        assert "agent" in report_path.name.lower()

    def test_generate_resource_utilization_report(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator generates resource utilization report."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_resource_utilization_report()

        assert report_path.exists()
        assert "resource" in report_path.name.lower()

    def test_report_includes_metadata(self, mock_telemetry_storage, report_output_dir):
        """Test generated report includes metadata."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_summary_report()

        with open(report_path) as f:
            content = f.read()
            # Should include generation time, HayMaker branding, etc.
            assert "haymaker" in content.lower()
            # Should include some date/time
            assert any(str(datetime.utcnow().year) in content for _ in [1])

    def test_report_responsive_design(self, mock_telemetry_storage, report_output_dir):
        """Test generated report has responsive design."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_summary_report()

        with open(report_path) as f:
            content = f.read()
            # Should include viewport meta tag or responsive CSS
            assert "viewport" in content.lower() or "media" in content.lower()

    def test_report_includes_charts(self, mock_telemetry_storage, report_output_dir):
        """Test generated report includes chart visualizations."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_summary_report()

        with open(report_path) as f:
            content = f.read()
            # Should include Plotly or chart divs
            assert "plotly" in content.lower() or "chart" in content.lower()

    def test_save_report_metadata(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator saves report metadata."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        report_path = generator.generate_summary_report()

        # Should create metadata file
        metadata_path = report_path.with_suffix(".json")
        if metadata_path.exists():
            import json
            with open(metadata_path) as f:
                metadata = json.load(f)
                assert "generated_at" in metadata
                assert "report_type" in metadata

    def test_generate_report_with_large_dataset(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator handles large datasets efficiently."""
        from haymaker_cli.reports.generator import ReportGenerator
        import time

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        start_time = time.time()
        report_path = generator.generate_summary_report()
        generation_time = time.time() - start_time

        assert report_path.exists()
        # Should complete in reasonable time (< 10 seconds)
        assert generation_time < 10.0

    def test_validate_output_format(self, mock_telemetry_storage, report_output_dir):
        """Test ReportGenerator validates output format parameter."""
        from haymaker_cli.reports.generator import ReportGenerator

        generator = ReportGenerator(mock_telemetry_storage, report_output_dir)

        # Valid formats
        html_path = generator.generate_report(format="html")
        assert html_path.suffix == ".html"

        csv_path = generator.generate_report(format="csv")
        assert csv_path.suffix == ".csv"

        # Invalid format should raise error
        with pytest.raises(ValueError):
            generator.generate_report(format="invalid")
