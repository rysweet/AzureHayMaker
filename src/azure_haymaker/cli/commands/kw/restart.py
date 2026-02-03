"""KW restart command - Restart a deployment."""

import asyncio
import sys

import click

from ...constants import EXIT_CANCELLED, EXIT_ERROR
from ...utils.state import get_deployment_or_exit, get_state_manager


@click.command()
@click.option("--run-id", "-r", required=True, help="Deployment run ID")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def restart(run_id: str, yes: bool) -> None:
    """Restart a deployment (stop then start)."""
    get_deployment_or_exit(run_id)

    if not yes and not click.confirm(f"Restart deployment {run_id}?"):
        click.echo("Aborted.")
        sys.exit(EXIT_CANCELLED)

    click.echo(f"Stopping deployment {run_id}...")
    asyncio.run(_stop_deployment(run_id))

    click.echo(f"Starting deployment {run_id}...")
    success = asyncio.run(_start_deployment(run_id))

    if success:
        click.echo(f"Deployment {run_id} restarted.")
    else:
        click.echo(f"Failed to restart deployment {run_id}.")
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


async def _start_deployment(run_id: str) -> bool:
    """Start a deployment (async implementation)."""
    state_manager = get_state_manager()
    deployment = state_manager.load_deployment(run_id)

    if deployment:
        state_manager.save_deployment(
            run_id=run_id,
            name=deployment.get("name", ""),
            phase="executing",
            status="running",
            worker_count=deployment.get("worker_count", 0),
        )
        return True

    return False
