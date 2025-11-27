"""Shared utilities for HayMaker CLI commands."""

import sys

import click
from rich.console import Console

from haymaker_cli.auth import create_auth_provider
from haymaker_cli.client import HayMakerClientError, SyncHayMakerClient
from haymaker_cli.config import load_cli_config

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
