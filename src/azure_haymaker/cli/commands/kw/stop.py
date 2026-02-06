"""KW stop command - Stop a running deployment."""

import asyncio
import sys

import click

from ...constants import EXIT_CANCELLED, EXIT_ERROR
from ...utils.state import get_deployment_or_exit, get_state_manager


@click.command()
@click.option("--run-id", "-r", required=True, help="Deployment run ID")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def stop(run_id: str, yes: bool) -> None:
    """Stop a running deployment."""
    deployment = get_deployment_or_exit(run_id)

    if deployment.get("status") != "running":
        click.echo(f"Deployment {run_id} is not running (status: {deployment.get('status')})")
        sys.exit(EXIT_ERROR)

    if not yes and not click.confirm(f"Stop deployment {run_id}?"):
        click.echo("Aborted.")
        sys.exit(EXIT_CANCELLED)

    success = asyncio.run(_stop_deployment(run_id))

    if success:
        click.echo(f"Deployment {run_id} stopped.")
    else:
        click.echo(f"Failed to stop deployment {run_id}.")
        sys.exit(EXIT_ERROR)


async def _stop_deployment(run_id: str) -> bool:
    """Stop a deployment (async implementation)."""
    state_manager = get_state_manager()
    deployment = state_manager.load_deployment(run_id)

    if deployment:
        state_manager.save_deployment(
            run_id=run_id,
            name=deployment.get("name", ""),
            phase="stopped",
            status="stopped",
            worker_count=deployment.get("worker_count", 0),
            completed_at=None,
        )
        return True

    return False
