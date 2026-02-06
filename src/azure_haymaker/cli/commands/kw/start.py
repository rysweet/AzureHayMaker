"""KW start command - Start or resume a deployment."""

import asyncio
import sys

import click

from ...constants import EXIT_ERROR
from ...utils.state import get_deployment_or_exit, get_state_manager


@click.command()
@click.option("--run-id", "-r", required=True, help="Deployment run ID")
def start(run_id: str) -> None:
    """Start or resume a deployment."""
    deployment = get_deployment_or_exit(run_id)

    if deployment.get("status") == "running":
        click.echo(f"Deployment {run_id} is already running.")
        return

    success = asyncio.run(_start_deployment(run_id))

    if success:
        click.echo(f"Deployment {run_id} started.")
    else:
        click.echo(f"Failed to start deployment {run_id}.")
        sys.exit(EXIT_ERROR)


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
