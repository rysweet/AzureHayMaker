"""KW list command - List all deployments."""

import click

from ...constants import DEFAULT_LIST_LIMIT, DEFAULT_OUTPUT_FORMAT
from ...utils.output import format_json, format_table
from ...utils.state import get_state_manager


@click.command("list")
@click.option(
    "--limit",
    "-l",
    type=int,
    default=DEFAULT_LIST_LIMIT,
    help="Maximum number of deployments to show",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json"]),
    default=DEFAULT_OUTPUT_FORMAT,
    help="Output format",
)
def list_deployments(limit: int, output_format: str) -> None:
    """List all known deployments."""
    state_manager = get_state_manager()
    deployments = state_manager.get_recent_deployments(limit)

    if not deployments:
        click.echo("No deployments found.")
        return

    if output_format == "json":
        click.echo(format_json(deployments))
    else:
        columns = ["run_id", "name", "status", "phase", "worker_count"]
        click.echo(format_table(deployments, columns))
