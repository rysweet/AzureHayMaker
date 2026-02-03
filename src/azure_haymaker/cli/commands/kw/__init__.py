"""Knowledge Worker CLI commands.

Provides lifecycle management commands for KW deployments:
- init: Initialize Azure Entra app registration
- deploy: Create a new deployment
- status: Display deployment status
- list: List all deployments
- logs: View deployment logs
- start: Start a deployment
- stop: Stop a deployment
- restart: Restart a deployment
- cleanup: Clean up deployment resources
- delete-worker: Delete specific workers

Each command is a self-contained module following the brick philosophy.
Addresses Issue #22: Refactor long CLI methods.
Addresses Issue #172: Add lifecycle management commands.
"""

import click

from .cleanup import cleanup
from .delete_worker import delete_worker
from .deploy import deploy
from .init import init
from .list import list_deployments
from .logs import logs
from .restart import restart
from .start import start
from .status import status
from .stop import stop


@click.group()
def kw() -> None:
    """Knowledge Worker lifecycle management commands.

    Manage KW deployments: init, deploy, status, logs, start, stop, cleanup.
    """
    pass


# Register all commands
kw.add_command(status)
kw.add_command(list_deployments, name="list")
kw.add_command(logs)
kw.add_command(stop)
kw.add_command(start)
kw.add_command(restart)
kw.add_command(cleanup)
kw.add_command(delete_worker, name="delete-worker")
kw.add_command(init)
kw.add_command(deploy)

__all__ = ["kw"]
