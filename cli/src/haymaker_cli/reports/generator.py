"""Report generation with templating for Azure HayMaker CLI."""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..telemetry.storage import TelemetryStorage
from .data import ReportDataProcessor
from .models import KPIData, ReportData, ReportFilters, ReportMetadata

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Report generator.

    Generates HTML, CSV, and JSON reports from telemetry data.
    """

    def __init__(self, storage: TelemetryStorage, output_dir: Path):
        """Initialize report generator.

        Args:
            storage: TelemetryStorage instance
            output_dir: Directory for report output
        """
        self.storage = storage
        self.output_dir = Path(output_dir)
        self.processor = ReportDataProcessor(storage)

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate_summary_report(
        self,
        filters: Optional[ReportFilters] = None,
        filename: Optional[str] = None,
        include_timestamp: bool = False,
    ) -> Path:
        """Generate summary report with KPIs.

        Args:
            filters: Optional filters to apply
            filename: Custom filename (default: auto-generated)
            include_timestamp: Include timestamp in filename

        Returns:
            Path to generated report
        """
        # Calculate KPIs and get data
        kpis = self.processor.calculate_kpis(filters)
        top_regions = self.processor.get_top_regions(filters, limit=5)
        top_scenarios = self.processor.get_top_scenarios(filters, limit=10)
        error_dist = self.processor.get_error_distribution(filters)
        timeline = self.processor.get_timeline_data(filters, granularity="day")
        status_dist = self.processor.get_status_distribution(filters)

        # Create metadata
        metadata = ReportMetadata(
            title="HayMaker Execution Summary",
            report_type="summary",
            filters=filters,
            total_records=kpis.get("total_executions", 0),
        )

        # Build context
        context = {
            "metadata": metadata,
            "kpis": kpis,
            "top_regions": top_regions,
            "top_scenarios": top_scenarios,
            "error_distribution": error_dist[:10],  # Top 10 errors
            "charts": {
                "timeline": timeline,
                "status_distribution": status_dist,
            },
        }

        # Generate filename
        if filename is None:
            filename = self._generate_filename("summary", include_timestamp)

        # Render template
        html = self.render_template("summary_report.html.jinja", context)

        # Write to file with secure permissions
        report_path = self.output_dir / filename
        fd = os.open(str(report_path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(html)
        except Exception:
            os.close(fd)
            raise

        logger.info(f"Summary report generated: {report_path}")
        return report_path

    def generate_detailed_report(
        self,
        filters: Optional[ReportFilters] = None,
        filename: Optional[str] = None,
        include_timestamp: bool = False,
    ) -> Path:
        """Generate detailed report with execution data.

        Args:
            filters: Optional filters to apply
            filename: Custom filename
            include_timestamp: Include timestamp in filename

        Returns:
            Path to generated report
        """
        # Get data
        kpis = self.processor.calculate_kpis(filters)
        filter_dict = self.processor._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)
        agents = self.storage.load_agents(filters=filter_dict)

        # Create metadata
        metadata = ReportMetadata(
            title="HayMaker Detailed Execution Report",
            report_type="detailed",
            filters=filters,
            total_records=len(executions),
        )

        # Build context
        context = {
            "metadata": metadata,
            "kpis": kpis,
            "executions": executions,
            "agents": agents,
        }

        # Generate filename
        if filename is None:
            filename = self._generate_filename("detailed", include_timestamp)

        # Render template
        html = self.render_template("detailed_report.html.jinja", context)

        # Write to file with secure permissions
        report_path = self.output_dir / filename
        fd = os.open(str(report_path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(html)
        except Exception:
            os.close(fd)
            raise

        logger.info(f"Detailed report generated: {report_path}")
        return report_path

    def generate_scenario_report(
        self,
        scenario_id: str,
        filters: Optional[ReportFilters] = None,
        filename: Optional[str] = None,
        include_timestamp: bool = False,
    ) -> Path:
        """Generate scenario-specific report.

        Args:
            scenario_id: Scenario identifier
            filters: Optional filters to apply
            filename: Custom filename
            include_timestamp: Include timestamp in filename

        Returns:
            Path to generated report
        """
        # Add scenario filter
        if filters is None:
            filters = ReportFilters(scenario_ids=[scenario_id])
        else:
            filters.scenario_ids = [scenario_id]

        # Get data
        kpis = self.processor.calculate_kpis(filters)
        filter_dict = self.processor._convert_filters(filters)
        executions = self.storage.load_executions(filters=filter_dict)
        timeline = self.processor.get_timeline_data(filters, granularity="day")

        # Get scenario name from first execution
        scenario_name = "Unknown Scenario"
        if executions:
            scenario_name = executions[0].get("scenario_name", scenario_id)

        # Create metadata
        metadata = ReportMetadata(
            title=f"HayMaker Scenario Report: {scenario_name}",
            report_type="scenario",
            filters=filters,
            total_records=len(executions),
        )

        # Build context
        context = {
            "metadata": metadata,
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "kpis": kpis,
            "executions": executions,
            "charts": {
                "timeline": timeline,
            },
        }

        # Generate filename
        if filename is None:
            filename = self._generate_filename(
                f"scenario_{scenario_id}", include_timestamp
            )

        # Render template
        html = self.render_template("scenario_report.html.jinja", context)

        # Write to file with secure permissions
        report_path = self.output_dir / filename
        fd = os.open(str(report_path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(html)
        except Exception:
            os.close(fd)
            raise

        logger.info(f"Scenario report generated: {report_path}")
        return report_path

    def generate_error_report(
        self,
        filters: Optional[ReportFilters] = None,
        filename: Optional[str] = None,
        include_timestamp: bool = False,
    ) -> Path:
        """Generate error analysis report.

        Args:
            filters: Optional filters to apply
            filename: Custom filename
            include_timestamp: Include timestamp in filename

        Returns:
            Path to generated report
        """
        # Get failure data
        failure_analysis = self.processor.get_failure_analysis(filters)
        error_dist = self.processor.get_error_distribution(filters)

        # Create metadata
        metadata = ReportMetadata(
            title="HayMaker Error Analysis Report",
            report_type="error",
            filters=filters,
            total_records=failure_analysis.get("total_failures", 0),
        )

        # Build context
        context = {
            "metadata": metadata,
            "failure_analysis": failure_analysis,
            "error_distribution": error_dist,
        }

        # Generate filename
        if filename is None:
            filename = self._generate_filename("errors", include_timestamp)

        # Render template
        html = self.render_template("error_report.html.jinja", context)

        # Write to file with secure permissions
        report_path = self.output_dir / filename
        fd = os.open(str(report_path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(html)
        except Exception:
            os.close(fd)
            raise

        logger.info(f"Error report generated: {report_path}")
        return report_path


    def export_to_csv(
        self,
        filters: Optional[ReportFilters] = None,
        filename: Optional[str] = None,
    ) -> Path:
        """Export data to CSV format.

        Args:
            filters: Optional filters to apply
            filename: Custom filename (default: executions.csv)

        Returns:
            Path to CSV file
        """
        # Get CSV data
        csv_data = self.processor.export_to_csv_format(filters)

        # Generate filename
        if filename is None:
            filename = f"executions_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

        csv_path = self.output_dir / filename

        # Write CSV with secure permissions
        fd = os.open(str(csv_path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(csv_data)
        except Exception:
            os.close(fd)
            raise

        logger.info(f"CSV exported: {csv_path}")
        return csv_path

    def export_to_json(
        self,
        filters: Optional[ReportFilters] = None,
        filename: Optional[str] = None,
    ) -> Path:
        """Export data to JSON format.

        Args:
            filters: Optional filters to apply
            filename: Custom filename (default: report_data.json)

        Returns:
            Path to JSON file
        """
        # Get data
        kpis = self.processor.calculate_kpis(filters)
        filter_dict = self.processor._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)
        agents = self.storage.load_agents(filters=filter_dict)

        # Build export data
        export_data = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "filters": filters.model_dump() if filters else None,
            },
            "kpis": kpis,
            "executions": executions,
            "agents": agents,
        }

        # Generate filename
        if filename is None:
            filename = f"report_data_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        json_path = self.output_dir / filename

        # Write JSON with secure permissions
        fd = os.open(str(json_path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(export_data, f, indent=2, default=str)
        except Exception:
            os.close(fd)
            raise

        logger.info(f"JSON exported: {json_path}")
        return json_path

    def generate_charts(
        self, filters: Optional[ReportFilters] = None
    ) -> Dict[str, Any]:
        """Generate chart data for Plotly.

        Args:
            filters: Optional filters to apply

        Returns:
            Dictionary of chart configurations
        """
        timeline = self.processor.get_timeline_data(filters, granularity="day")
        status_dist = self.processor.get_status_distribution(filters)
        region_dist = self.processor.get_region_distribution(filters)
        duration_hist = self.processor.get_duration_distribution(filters, bins=10)

        return {
            "timeline": {
                "type": "line",
                "data": {
                    "x": timeline["x"],
                    "y": timeline["y"],
                },
                "layout": {
                    "title": "Executions Over Time",
                    "xaxis": {"title": "Date"},
                    "yaxis": {"title": "Count"},
                },
            },
            "status_distribution": {
                "type": "pie",
                "data": {
                    "labels": status_dist["labels"],
                    "values": status_dist["values"],
                },
                "layout": {
                    "title": "Execution Status Distribution",
                },
            },
            "region_distribution": {
                "type": "bar",
                "data": {
                    "x": region_dist["labels"],
                    "y": region_dist["values"],
                },
                "layout": {
                    "title": "Agents by Region",
                    "xaxis": {"title": "Region"},
                    "yaxis": {"title": "Count"},
                },
            },
            "duration_histogram": {
                "type": "histogram",
                "data": {
                    "x": duration_hist["bins"],
                    "y": duration_hist["counts"],
                },
                "layout": {
                    "title": "Duration Distribution",
                    "xaxis": {"title": "Duration (seconds)"},
                    "yaxis": {"title": "Count"},
                },
            },
        }

    def render_template(
        self, template_name: str, context: Dict[str, Any]
    ) -> str:
        """Render Jinja2 template.

        Args:
            template_name: Name of template file
            context: Template context dictionary

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def _generate_filename(self, prefix: str, include_timestamp: bool = False) -> str:
        """Generate report filename.

        Args:
            prefix: Filename prefix
            include_timestamp: Include timestamp in filename

        Returns:
            Generated filename
        """
        if include_timestamp:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            return f"{prefix}_{timestamp}.html"
        return f"{prefix}.html"
