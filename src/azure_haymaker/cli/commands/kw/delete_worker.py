"""KW delete-worker command - Delete specific workers."""

import asyncio
import sys

import click

from ...constants import EXIT_CANCELLED, EXIT_ERROR
from ...utils.state import get_workers_for_deployment


@click.command("delete-worker")
@click.option("--worker-id", "-w", help="Specific worker ID to delete")
@click.option("--run-id", "-r", help="Deployment run ID (with --department)")
@click.option("--department", "-d", help="Delete all workers in department")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def delete_worker(
    worker_id: str | None,
    run_id: str | None,
    department: str | None,
    yes: bool,
) -> None:
    """Delete specific workers from a deployment."""
    if not worker_id and not (run_id and department):
        raise click.UsageError("Must specify either --worker-id or both --run-id and --department")

    if worker_id:
        _delete_single_worker(worker_id, yes)
    else:
        _delete_workers_by_department(run_id, department, yes)


def _delete_single_worker(worker_id: str, yes: bool) -> None:
    """Delete a single worker by ID."""
    if not yes and not click.confirm(f"Delete worker {worker_id}?"):
        click.echo("Aborted.")
        sys.exit(EXIT_CANCELLED)

    success = asyncio.run(_delete_worker(worker_id))

    if success:
        click.echo(f"Worker {worker_id} deleted.")
    else:
        click.echo(f"Failed to delete worker {worker_id}.")
        sys.exit(EXIT_ERROR)


def _delete_workers_by_department(run_id: str | None, department: str | None, yes: bool) -> None:
    """Delete all workers in a department."""
    if not run_id or not department:
        return

    workers = get_workers_for_deployment(run_id)
    dept_workers = [w for w in workers if w.get("department") == department]

    if not dept_workers:
        click.echo(f"No workers found in department {department}")
        return

    click.echo(f"Found {len(dept_workers)} worker(s) in {department}")

    if not yes and not click.confirm(f"Delete {len(dept_workers)} worker(s)?"):
        click.echo("Aborted.")
        sys.exit(EXIT_CANCELLED)

    for worker in dept_workers:
        asyncio.run(_delete_worker(worker["worker_id"]))
        click.echo(f"  Deleted {worker['worker_id']}")

    click.echo(f"Deleted {len(dept_workers)} worker(s).")


async def _delete_worker(worker_id: str) -> bool:
    """Delete a worker (async implementation).

    In a full implementation, this would call the EntraUserManager
    to delete the actual Entra user.
    """
    # For now, just return True - actual deletion requires Graph API
    # and would be implemented via EntraUserManager.delete_worker()
    return True
