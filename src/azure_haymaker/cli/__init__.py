"""Azure HayMaker CLI.

Command-line interface for managing Knowledge Worker deployments.
Provides lifecycle management commands: status, list, logs, start, stop, restart, cleanup.

Usage:
    haymaker kw status              # Show deployment status
    haymaker kw list                # List deployments
    haymaker kw logs --run-id ID    # View logs
    haymaker kw stop --run-id ID    # Stop deployment
    haymaker kw cleanup --run-id ID # Clean up resources

Addresses Issue #172: Add lifecycle management commands to haymaker kw CLI.
"""

import click

from .commands.kw import kw


@click.group()
@click.version_option(package_name="azure-haymaker")
def cli() -> None:
    """Azure HayMaker - Knowledge Worker simulation framework.

    Manage Knowledge Worker deployments with lifecycle commands.
    """
    pass


# Register command groups
cli.add_command(kw)


__all__ = ["cli"]
