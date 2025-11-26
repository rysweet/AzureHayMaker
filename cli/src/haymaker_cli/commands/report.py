"""Report generation commands."""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


def get_storage_path(storage_dir: str | None) -> Path:
    """Get telemetry storage path from option or default with validation.

    Args:
        storage_dir: Optional storage directory path

    Returns:
        Validated storage path

    Raises:
        ValueError: If path is outside user's home directory
    """
    if storage_dir:
        storage_path = Path(storage_dir).resolve()

        # Ensure storage is within home directory for security
        try:
            storage_path.relative_to(Path.home())
        except ValueError:
            raise ValueError(
                f"Storage directory must be within home directory. Got: {storage_path}"
            )

        logger.info(f"Storage path validated: {storage_path}")
        return storage_path

    return Path.home() / ".haymaker" / "telemetry"


def get_output_dir_and_filename(output: str | None) -> tuple[Path, Optional[str]]:
    """Get output directory and filename from option or default with path traversal protection.

    Args:
        output: Optional output file path

    Returns:
        Tuple of (output directory, filename)

    Raises:
        ValueError: If path is invalid or outside allowed directory
    """
    if output:
        # Resolve to absolute path
        output_path = Path(output).resolve()

        # Define allowed base directories
        allowed_bases = [
            Path.home() / ".haymaker" / "reports",
            Path.cwd().resolve(),
        ]

        # Ensure output directory exists in one of the allowed bases
        is_valid = False
        for base in allowed_bases:
            try:
                output_path.relative_to(base)
                is_valid = True
                break
            except ValueError:
                continue

        if not is_valid:
            raise ValueError(
                f"Output path must be within current directory or ~/.haymaker/reports. "
                f"Got: {output_path}"
            )

        # Validate filename (alphanumeric, dots, dashes, underscores only)
        filename = output_path.name
        if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
            raise ValueError(
                f"Invalid filename: {filename}. "
                f"Only alphanumeric characters, dots, dashes, and underscores are allowed."
            )

        logger.info(f"Output validated: {output_path}")
        return output_path.parent, filename

    # Default to current directory
    return Path.cwd(), None


def validate_date_string(date_str: str) -> datetime:
    """Validate and parse date string.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If date format is invalid
    """
    try:
        parsed = datetime.fromisoformat(date_str)
        # Ensure date is not in the future
        if parsed > datetime.utcnow():
            raise ValueError(f"Date cannot be in the future: {date_str}")
        return parsed
    except ValueError as e:
        raise ValueError(f"Invalid date format (expected YYYY-MM-DD): {date_str}") from e


def validate_scenario_id(scenario_id: str) -> str:
    """Validate scenario ID.

    Args:
        scenario_id: Scenario identifier

    Returns:
        Validated scenario ID

    Raises:
        ValueError: If scenario ID is invalid
    """
    # Length limits
    if len(scenario_id) > 256:
        raise ValueError(f"Scenario ID too long (max 256 chars): {scenario_id}")

    # Character whitelist: alphanumeric, dashes, underscores, dots
    if not re.match(r'^[a-zA-Z0-9._-]+$', scenario_id):
        raise ValueError(
            f"Invalid scenario ID: {scenario_id}. "
            f"Only alphanumeric characters, dots, dashes, and underscores are allowed."
        )

    return scenario_id


@click.group()
def report():
    """Generate reports and view dashboards."""


@report.command()
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--start-date", help="Start date filter (YYYY-MM-DD)")
@click.option("--end-date", help="End date filter (YYYY-MM-DD)")
@click.option("--scenario", help="Filter by scenario ID")
@click.option("--status", multiple=True, help="Filter by status (can be used multiple times)")
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def summary(output: str | None, start_date: str | None, end_date: str | None,
            scenario: str | None, status: tuple, storage_dir: str | None):
    """Generate summary report with KPIs."""
    try:
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.reports.models import ReportFilters
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Setup storage and output
        storage = TelemetryStorage(get_storage_path(storage_dir))
        output_dir, filename = get_output_dir_and_filename(output)

        # Validate and create filters
        filters = None
        if any([start_date, end_date, scenario, status]):
            validated_start = validate_date_string(start_date) if start_date else None
            validated_end = validate_date_string(end_date) if end_date else None
            validated_scenario = validate_scenario_id(scenario) if scenario else None

            filters = ReportFilters(
                start_date=validated_start,
                end_date=validated_end,
                scenario_ids=[validated_scenario] if validated_scenario else None,
                status=list(status) if status else None,
            )

        # Generate report
        generator = ReportGenerator(storage, output_dir)

        console.print("[cyan]Generating summary report...[/cyan]")

        report_path = generator.generate_summary_report(filters=filters, filename=filename)

        console.print(f"[green]Report generated:[/green] {report_path}")

    except Exception as e:
        logger.error(f"Failed to generate summary report: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@report.command()
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--start-date", help="Start date filter (YYYY-MM-DD)")
@click.option("--end-date", help="End date filter (YYYY-MM-DD)")
@click.option("--scenario", help="Filter by scenario ID")
@click.option("--status", multiple=True, help="Filter by status")
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def detailed(output: str | None, start_date: str | None, end_date: str | None,
             scenario: str | None, status: tuple, storage_dir: str | None):
    """Generate detailed report with execution data."""
    try:
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.reports.models import ReportFilters
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Setup storage and output
        storage = TelemetryStorage(get_storage_path(storage_dir))
        output_dir, filename = get_output_dir_and_filename(output)

        # Validate and create filters
        filters = None
        if any([start_date, end_date, scenario, status]):
            validated_start = validate_date_string(start_date) if start_date else None
            validated_end = validate_date_string(end_date) if end_date else None
            validated_scenario = validate_scenario_id(scenario) if scenario else None

            filters = ReportFilters(
                start_date=validated_start,
                end_date=validated_end,
                scenario_ids=[validated_scenario] if validated_scenario else None,
                status=list(status) if status else None,
            )

        # Generate report
        generator = ReportGenerator(storage, output_dir)

        console.print("[cyan]Generating detailed report...[/cyan]")

        report_path = generator.generate_detailed_report(filters=filters, filename=filename)

        console.print(f"[green]Report generated:[/green] {report_path}")

    except Exception as e:
        logger.error(f"Failed to generate summary report: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@report.command()
@click.argument("scenario_id")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def scenario(scenario_id: str, output: str | None, storage_dir: str | None):
    """Generate scenario-specific report."""
    try:
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Validate scenario ID
        validated_scenario_id = validate_scenario_id(scenario_id)

        # Setup storage and output
        storage = TelemetryStorage(get_storage_path(storage_dir))
        output_dir, filename = get_output_dir_and_filename(output)

        # Generate report
        generator = ReportGenerator(storage, output_dir)

        console.print(f"[cyan]Generating scenario report for {validated_scenario_id}...[/cyan]")

        report_path = generator.generate_scenario_report(validated_scenario_id, filename=filename)

        console.print(f"[green]Report generated:[/green] {report_path}")

    except Exception as e:
        logger.error(f"Failed to generate summary report: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@report.command()
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def errors(output: str | None, storage_dir: str | None):
    """Generate error analysis report."""
    try:
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Setup storage and output
        storage = TelemetryStorage(get_storage_path(storage_dir))
        output_dir, filename = get_output_dir_and_filename(output)

        # Generate report
        generator = ReportGenerator(storage, output_dir)

        console.print("[cyan]Generating error analysis report...[/cyan]")

        report_path = generator.generate_error_report(filename=filename)

        console.print(f"[green]Report generated:[/green] {report_path}")

    except Exception as e:
        logger.error(f"Failed to generate summary report: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@report.command()
@click.option("--output", "-o", type=click.Path(), help="Output CSV file path")
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def export_csv(output: str | None, storage_dir: str | None):
    """Export data to CSV format."""
    try:
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Setup storage and output
        storage = TelemetryStorage(get_storage_path(storage_dir))
        output_dir, filename = get_output_dir_and_filename(output)

        # Generate export
        generator = ReportGenerator(storage, output_dir)

        console.print("[cyan]Exporting to CSV...[/cyan]")

        csv_path = generator.export_to_csv(filename=filename)

        console.print(f"[green]CSV exported:[/green] {csv_path}")

    except Exception as e:
        logger.error(f"Failed to generate summary report: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@report.command()
@click.option("--output", "-o", type=click.Path(), help="Output JSON file path")
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def export_json(output: str | None, storage_dir: str | None):
    """Export data to JSON format."""
    try:
        from haymaker_cli.reports.generator import ReportGenerator
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Setup storage and output
        storage = TelemetryStorage(get_storage_path(storage_dir))
        output_dir, filename = get_output_dir_and_filename(output)

        # Generate export
        generator = ReportGenerator(storage, output_dir)

        console.print("[cyan]Exporting to JSON...[/cyan]")

        json_path = generator.export_to_json(filename=filename)

        console.print(f"[green]JSON exported:[/green] {json_path}")

    except Exception as e:
        logger.error(f"Failed to generate summary report: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


# Dashboard command removed - will be added in v1.5 with full Textual implementation
# For now, users should use 'haymaker report summary' for viewing telemetry data
