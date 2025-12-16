"""Reporting commands for HayMaker CLI."""

from pathlib import Path

import click
from rich.console import Console

from haymaker_cli.cli_utils import get_client, handle_error
from haymaker_cli.report_generator import ReportGenerator

console = Console()

# Constants for API limits
DEFAULT_AGENT_LIMIT = 100
DEFAULT_RESOURCE_LIMIT = 1000


@click.group()  # type: ignore[misc]  # Click decorators modify function signatures
def report():
    """Generate reports from orchestrator metrics."""


@report.command(name="summary")  # type: ignore[misc]
@click.option(
    "--period",
    default="30d",
    type=click.Choice(["7d", "30d", "90d"], case_sensitive=False),
    help="Time period for report (default: 30d)",
)
@click.option("--scenario", help="Filter by scenario name")
@click.option(
    "--output",
    "-o",
    default="report.html",
    type=click.Path(),
    help="Output file path (default: report.html)",
)
@click.pass_context
def summary(ctx: click.Context, period: str, scenario: str | None, output: str):
    """Generate summary report in HTML format.

    Example:
        haymaker report summary
        haymaker report summary --period 90d
        haymaker report summary --scenario compute-01 --output compute-report.html
    """
    try:
        client = get_client(ctx)

        console.print("[cyan]Generating summary report...[/cyan]")
        console.print(f"[dim]Period: {period}[/dim]")
        if scenario:
            console.print(f"[dim]Scenario: {scenario}[/dim]")

        # Fetch metrics from orchestrator
        metrics = client.get_metrics(period=period, scenario=scenario)

        # Fetch additional data
        agents = client.list_agents(limit=DEFAULT_AGENT_LIMIT)
        resources = client.list_resources(scenario=scenario, limit=DEFAULT_RESOURCE_LIMIT)

        # Generate report
        generator = ReportGenerator()
        output_path = Path(output)
        generator.generate_summary_report(
            metrics=metrics,
            agents=agents,
            resources=resources,
            output_path=output_path,
        )

        console.print("\n[green]Report generated successfully![/green]")
        console.print(f"[cyan]Output:[/cyan] {output_path.absolute()}")

    except Exception as e:
        handle_error(e)


@report.command(name="scenario")  # type: ignore[misc]
@click.argument("scenario_name")
@click.option(
    "--period",
    default="30d",
    type=click.Choice(["7d", "30d", "90d"], case_sensitive=False),
    help="Time period for report (default: 30d)",
)
@click.option(
    "--output",
    "-o",
    help="Output file path (default: {scenario}-report.html)",
)
@click.pass_context
def scenario(ctx: click.Context, scenario_name: str, period: str, output: str | None):
    """Generate detailed report for a specific scenario.

    Example:
        haymaker report scenario compute-01
        haymaker report scenario compute-01 --period 90d
    """
    try:
        client = get_client(ctx)

        console.print(f"[cyan]Generating scenario report for:[/cyan] {scenario_name}")
        console.print(f"[dim]Period: {period}[/dim]")

        # Fetch scenario metrics
        metrics = client.get_metrics(period=period, scenario=scenario_name)

        # Fetch scenario-specific data
        agents = client.list_agents(limit=DEFAULT_AGENT_LIMIT)
        scenario_agents = [a for a in agents if a.scenario == scenario_name]

        resources = client.list_resources(scenario=scenario_name, limit=DEFAULT_RESOURCE_LIMIT)

        # Generate report
        generator = ReportGenerator()
        output_path = Path(output or f"{scenario_name}-report.html")
        generator.generate_scenario_report(
            scenario_name=scenario_name,
            metrics=metrics,
            agents=scenario_agents,
            resources=resources,
            output_path=output_path,
        )

        console.print("\n[green]Report generated successfully![/green]")
        console.print(f"[cyan]Output:[/cyan] {output_path.absolute()}")

    except Exception as e:
        handle_error(e)
