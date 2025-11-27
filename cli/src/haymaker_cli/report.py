"""Reporting commands for HayMaker CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console

from haymaker_cli.auth import create_auth_provider
from haymaker_cli.client import HayMakerClientError, SyncHayMakerClient
from haymaker_cli.config import load_cli_config
from haymaker_cli.report_generator import ReportGenerator

console = Console()


def get_client(ctx: click.Context) -> SyncHayMakerClient:
    """Get configured HayMaker client from context.

    Args:
        ctx: Click context

    Returns:
        Configured HayMaker client

    Raises:
        click.ClickException: If configuration is invalid
    """
    try:
        profile = ctx.obj["profile"]
        config = load_cli_config(profile)
        auth = create_auth_provider(config.auth.model_dump())
        return SyncHayMakerClient(config.endpoint, auth)
    except Exception as e:
        raise click.ClickException(f"Configuration error: {e}") from e


def handle_error(error: Exception):
    """Handle and display errors.

    Args:
        error: Exception to handle
    """
    if isinstance(error, HayMakerClientError):
        console.print(f"[red]Error:[/red] {error}", style="red")
        if error.status_code:
            console.print(f"[dim]Status Code: {error.status_code}[/dim]")
        if error.details:
            console.print(f"[dim]Details: {error.details}[/dim]")
    else:
        console.print(f"[red]Error:[/red] {error}", style="red")

    sys.exit(1)


@click.group()  # type: ignore[misc]  # Click decorators modify function signatures
def report():
    """Generate reports from orchestrator metrics."""


@report.command(name="summary")
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

        console.print(f"[cyan]Generating summary report...[/cyan]")
        console.print(f"[dim]Period: {period}[/dim]")
        if scenario:
            console.print(f"[dim]Scenario: {scenario}[/dim]")

        # Fetch metrics from orchestrator
        metrics = client.get_metrics(period=period, scenario=scenario)

        # Fetch additional data
        agents = client.list_agents(limit=100)
        resources = client.list_resources(scenario=scenario, limit=1000)

        # Generate report
        generator = ReportGenerator(client)
        output_path = Path(output)
        generator.generate_summary_report(
            metrics=metrics,
            agents=agents,
            resources=resources,
            output_path=output_path,
        )

        console.print(f"\n[green]Report generated successfully![/green]")
        console.print(f"[cyan]Output:[/cyan] {output_path.absolute()}")

    except Exception as e:
        handle_error(e)


@report.command(name="scenario")
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
        agents = client.list_agents(limit=100)
        scenario_agents = [a for a in agents if a.scenario == scenario_name]

        resources = client.list_resources(scenario=scenario_name, limit=1000)

        # Generate report
        generator = ReportGenerator(client)
        output_path = Path(output or f"{scenario_name}-report.html")
        generator.generate_scenario_report(
            scenario_name=scenario_name,
            metrics=metrics,
            agents=scenario_agents,
            resources=resources,
            output_path=output_path,
        )

        console.print(f"\n[green]Report generated successfully![/green]")
        console.print(f"[cyan]Output:[/cyan] {output_path.absolute()}")

    except Exception as e:
        handle_error(e)
