"""KW status command - Display deployment status."""

from typing import Any

import click

from ...constants import DEFAULT_OUTPUT_FORMAT
from ...utils.output import format_json, format_status_line
from ...utils.state import get_deployment_or_exit, get_state_manager


@click.command()
@click.option("--run-id", "-r", help="Specific deployment run ID")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json"]),
    default=DEFAULT_OUTPUT_FORMAT,
    help="Output format",
)
def status(run_id: str | None, output_format: str) -> None:
    """Display deployment status.

    Shows status of all deployments or a specific one.
    """
    state_manager = get_state_manager()

    if run_id:
        _show_single_status(run_id, output_format)
    else:
        _show_all_status(state_manager, output_format)


def _show_single_status(run_id: str, output_format: str) -> None:
    """Show status for a single deployment."""
    deployment = get_deployment_or_exit(run_id)

    if output_format == "json":
        click.echo(format_json([deployment]))
    else:
        click.echo(
            format_status_line(
                deployment["run_id"],
                deployment.get("status", "unknown"),
                deployment.get("phase", "unknown"),
            )
        )
        click.echo(f"  Workers: {deployment.get('worker_count', 0)}")
        click.echo(f"  Started: {deployment.get('started_at', 'N/A')}")


def _show_all_status(state_manager: Any, output_format: str) -> None:
    """Show status for all deployments."""
    deployments = state_manager.list_deployments()

    if not deployments:
        click.echo("No deployments found.")
        return

    if output_format == "json":
        click.echo(format_json(deployments))
    else:
        for deployment in deployments:
            click.echo(
                format_status_line(
                    deployment["run_id"],
                    deployment.get("status", "unknown"),
                    deployment.get("phase", "unknown"),
                )
            )
