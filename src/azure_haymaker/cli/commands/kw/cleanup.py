"""KW cleanup command - Clean up deployment resources."""

import sys
from typing import Any

import click

from ...constants import EXIT_CANCELLED
from ...utils.state import (
    filter_deployments_by_age,
    get_deployment_or_exit,
    get_state_manager,
    parse_duration,
)


@click.command()
@click.option("--run-id", "-r", help="Specific deployment to clean up")
@click.option("--all", "cleanup_all", is_flag=True, help="Clean up all deployments")
@click.option("--older-than", help="Clean up deployments older than duration (e.g., 24h, 7d)")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def cleanup(
    run_id: str | None,
    cleanup_all: bool,
    older_than: str | None,
    dry_run: bool,
    yes: bool,
) -> None:
    """Clean up deployment resources.

    Must specify one of: --run-id, --all, or --older-than.
    """
    if not run_id and not cleanup_all and not older_than:
        raise click.UsageError("Must specify one of: --run-id, --all, or --older-than")

    state_manager = get_state_manager()

    # Determine deployments to clean up
    if run_id:
        deployments = [get_deployment_or_exit(run_id)]
    elif older_than:
        duration = parse_duration(older_than)
        all_deployments = state_manager.list_deployments()
        deployments = filter_deployments_by_age(all_deployments, duration)
    else:  # cleanup_all
        deployments = state_manager.list_deployments()

    if not deployments:
        click.echo("No deployments to clean up.")
        return

    # Show what will be cleaned up
    click.echo(f"Deployments to clean up ({len(deployments)}):")
    for deployment in deployments:
        click.echo(f"  - {deployment['run_id']}: {deployment.get('name', 'N/A')}")

    if dry_run:
        click.echo("\n[Dry run] No resources were deleted.")
        return

    # Confirm
    if not yes and not click.confirm(f"Clean up {len(deployments)} deployment(s)?"):
        click.echo("Aborted.")
        sys.exit(EXIT_CANCELLED)

    # Perform cleanup
    for deployment in deployments:
        _cleanup_single_deployment(state_manager, deployment["run_id"])

    click.echo(f"Cleaned up {len(deployments)} deployment(s).")


def _cleanup_single_deployment(state_manager: Any, run_id: str) -> None:
    """Clean up a single deployment."""
    click.echo(f"Cleaning up {run_id}...")

    # Delete workers
    worker_count = state_manager.delete_workers(run_id)
    click.echo(f"  Deleted {worker_count} worker(s)")

    # Delete deployment state
    state_manager.delete_deployment(run_id)
    click.echo("  Deleted deployment state")
