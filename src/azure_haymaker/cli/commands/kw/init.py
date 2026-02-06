"""KW init command - Initialize Azure Entra app registration.

Creates an Azure Entra app registration with Microsoft Graph
permissions required for M365 operations.
"""

import os
import sys

import click

from ...constants import EXIT_ERROR

__all__ = ["init"]


@click.command()
@click.option(
    "--tenant-id",
    "-t",
    help="Azure tenant ID (auto-detected if not provided)",
)
@click.option(
    "--app-name",
    default="haymaker-knowledge-worker",
    help="Display name for the app registration",
)
@click.option(
    "--save-config",
    "-o",
    type=click.Path(),
    help="Save configuration to file (e.g., kw_config.env)",
)
@click.option(
    "--reuse-existing/--no-reuse-existing",
    default=True,
    help="Reuse existing app if found",
)
def init(
    tenant_id: str | None,
    app_name: str,
    save_config: str | None,
    reuse_existing: bool,
) -> None:
    """Initialize Knowledge Worker app registration.

    Creates an Azure Entra app registration with Microsoft Graph
    permissions required for M365 operations (Mail, Teams, Calendar, etc.).

    After running this command, you must grant admin consent by visiting
    the URL displayed in the output.

    Example:
        haymaker kw init --save-config kw_config.env
        source kw_config.env
    """
    from azure_haymaker.knowledge_worker.infrastructure.app_setup import setup_kw_app

    click.echo("Initializing Knowledge Worker app registration...")
    click.echo()

    try:
        config = setup_kw_app(
            tenant_id=tenant_id,
            app_name=app_name,
            reuse_existing=reuse_existing,
        )
    except RuntimeError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(EXIT_ERROR)

    # Display results
    click.echo("✅ App registration created successfully!")
    click.echo()
    click.echo(f"  App ID:        {config.app_id}")
    click.echo(f"  Tenant ID:     {config.tenant_id}")
    click.echo(f"  SP Object ID:  {config.sp_id}")
    click.echo()
    click.echo("⚠️  IMPORTANT: Grant admin consent by visiting:")
    click.echo(f"  {config.admin_consent_url}")
    click.echo()

    # Save config if requested - with secure file permissions
    if save_config:
        # Create file with secure permissions atomically (0o600 = owner read/write only)
        fd = os.open(save_config, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(config.to_env_string())
        click.echo(f"✅ Configuration saved to: {save_config}")
        click.echo(f"   Run: source {save_config}")
    else:
        click.echo("To save credentials, run with --save-config <file>")
