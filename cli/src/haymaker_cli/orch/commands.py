"""Click CLI commands for orchestrator management (haymaker orch).

This module provides the main CLI command group for managing Azure Container Apps
used by the HayMaker orchestrator. Commands include status monitoring, replica
management, log viewing, and health checks.

Commands:
    - haymaker orch status: Show orchestrator status and revisions
    - haymaker orch replicas: Show replica information with follow mode
    - haymaker orch logs: Display container logs with tail/follow options
    - haymaker orch health: Run health checks with optional deep mode

Example:
    >>> # Show orchestrator status
    >>> haymaker orch status --format table

    >>> # Follow replica status
    >>> haymaker orch replicas --revision my-app--rev1 --follow

    >>> # View logs with timestamps
    >>> haymaker orch logs --revision my-app--rev1 --timestamps --follow

    >>> # Run deep health checks
    >>> haymaker orch health --deep --verbose
"""

import asyncio
import sys
import time
from typing import Any

import click
from rich.console import Console

from haymaker_cli.orch.client import ContainerAppsClient
from haymaker_cli.orch.config import load_orchestrator_config
from haymaker_cli.orch.formatters import (
    format_container_app_status,
    format_health_check_result,
    format_json,
    format_logs,
    format_replicas,
    format_yaml,
)
from haymaker_cli.orch.health import run_health_checks
from haymaker_cli.orch.models import ApiError, ConfigError, NetworkError, ServerError

console = Console()


def handle_orch_error(e: Exception) -> None:
    """Handle orchestrator command errors with appropriate exit codes.

    Maps exception types to exit codes:
    - ConfigError: exit code 1 (configuration issues)
    - NetworkError: exit code 2 (network connectivity)
    - ApiError: exit code 3 (Azure API errors)
    - ServerError: exit code 4 (Azure 5xx errors)
    - Other exceptions: exit code 1 (generic error)

    Args:
        e: Exception to handle

    Example:
        >>> try:
        ...     raise ConfigError("Missing subscription ID")
        ... except Exception as e:
        ...     handle_orch_error(e)  # doctest: +SKIP
    """
    if isinstance(e, ConfigError):
        console.print(f"[red]Configuration error:[/red] {e}", style="red")
        if e.details:
            console.print(f"[dim]Details: {e.details}[/dim]")
        sys.exit(1)
    elif isinstance(e, NetworkError):
        console.print(f"[red]Network error:[/red] {e}", style="red")
        if e.details:
            console.print(f"[dim]Details: {e.details}[/dim]")
        sys.exit(2)
    elif isinstance(e, ApiError):
        console.print(f"[red]API error:[/red] {e}", style="red")
        if e.details:
            console.print(f"[dim]Details: {e.details}[/dim]")
        sys.exit(3)
    elif isinstance(e, ServerError):
        console.print(f"[red]Server error:[/red] {e}", style="red")
        if e.details:
            console.print(f"[dim]Details: {e.details}[/dim]")
        sys.exit(4)
    else:
        console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(1)


def format_output(data: Any, format_type: str, table_formatter=None) -> None:
    """Format and print output based on format type.

    Args:
        data: Data to format
        format_type: Output format ("table", "json", "yaml")
        table_formatter: Optional function for table formatting

    Example:
        >>> format_output({"key": "value"}, "json")  # doctest: +SKIP
    """
    if format_type == "json":
        console.print(format_json(data))
    elif format_type == "yaml":
        console.print(format_yaml(data))
    else:  # table
        if table_formatter:
            table_formatter(data)
        else:
            # Fallback to JSON if no table formatter provided
            console.print(format_json(data))


@click.group()
def orch():
    """Manage Azure Container Apps orchestrator.

    Commands for monitoring and managing the HayMaker orchestrator
    deployed on Azure Container Apps. Includes status checks, replica
    management, log viewing, and health monitoring.

    Example:
        haymaker orch status
        haymaker orch replicas --revision my-app--rev1
        haymaker orch logs --follow
        haymaker orch health --deep
    """


@orch.command()
@click.option(
    "--app-name",
    help="Container app name (default: from config)",
)
@click.option(
    "--subscription-id",
    help="Azure subscription ID (default: from config or env)",
)
@click.option(
    "--resource-group",
    help="Azure resource group (default: from config or env)",
)
@click.option(
    "--revision",
    help="Show specific revision only",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information",
)
@click.pass_context
def status(
    ctx: click.Context,
    app_name: str | None,
    subscription_id: str | None,
    resource_group: str | None,
    revision: str | None,
    output_format: str,
    verbose: bool,
):
    """Show orchestrator status and revisions.

    Displays the current status of the Container App including:
    - Endpoint URL
    - Overall provisioning and running status
    - Active revisions with traffic weights
    - Replica counts and health state

    Examples:
        # Show status with default config
        haymaker orch status

        # Show specific revision
        haymaker orch status --revision my-app--rev1

        # Output as JSON
        haymaker orch status --format json

        # Show detailed information
        haymaker orch status --verbose
    """
    try:
        # Load configuration
        config = load_orchestrator_config(
            subscription_id=subscription_id,
            resource_group=resource_group,
            container_app_name=app_name,
        )

        # Use app name from config if not specified
        final_app_name = app_name or config.container_app_name
        if not final_app_name:
            raise ConfigError(
                "Container app name not specified. Provide via --app-name or configure with:\n"
                "haymaker config set orchestrator.container_app_name <name>",
                details={"missing_field": "container_app_name"},
            )

        # Create client
        client = ContainerAppsClient(config.subscription_id, config.resource_group)

        # Get app info and revisions
        async def get_status_data():
            app = await client.get_container_app(final_app_name)
            revisions = await client.list_revisions(final_app_name)

            # Filter to active revisions unless specific revision requested
            if revision:
                revisions = [r for r in revisions if r.name == revision]
                if not revisions:
                    raise ApiError(
                        f"Revision not found: {revision}",
                        details={"revision": revision},
                    )
            else:
                revisions = [r for r in revisions if r.active]

            return app, revisions

        # Run async operation
        app_info, revision_list = asyncio.run(get_status_data())

        # Format and display output
        if output_format == "json":
            data = {
                "app": app_info.model_dump(mode="json"),
                "revisions": [r.model_dump(mode="json") for r in revision_list],
            }
            console.print(format_json(data))
        elif output_format == "yaml":
            data = {
                "app": app_info.model_dump(mode="json"),
                "revisions": [r.model_dump(mode="json") for r in revision_list],
            }
            console.print(format_yaml(data))
        else:  # table
            format_container_app_status(app_info, revision_list)

            if verbose:
                console.print("\n[cyan]Configuration:[/cyan]")
                console.print(f"  Subscription ID: {config.subscription_id}")
                console.print(f"  Resource Group:  {config.resource_group}")
                console.print(f"  Container App:   {final_app_name}")

    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted by user[/dim]")
        sys.exit(0)
    except Exception as e:
        handle_orch_error(e)


@orch.command()
@click.option(
    "--app-name",
    help="Container app name (default: from config)",
)
@click.option(
    "--subscription-id",
    help="Azure subscription ID (default: from config or env)",
)
@click.option(
    "--resource-group",
    help="Azure resource group (default: from config or env)",
)
@click.option(
    "--revision",
    required=True,
    help="Revision name to show replicas for",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow replica status (poll continuously)",
)
@click.option(
    "--interval",
    default=5,
    type=int,
    help="Polling interval in seconds for follow mode (default: 5)",
)
@click.pass_context
def replicas(
    ctx: click.Context,
    app_name: str | None,
    subscription_id: str | None,
    resource_group: str | None,
    revision: str,
    output_format: str,
    follow: bool,
    interval: int,
):
    """Show replica information for a revision.

    Lists all replicas for the specified revision with their running state,
    creation time, and any state details. Supports follow mode for continuous
    monitoring.

    Examples:
        # Show replicas for a revision
        haymaker orch replicas --revision my-app--rev1

        # Follow replica status (updates every 5 seconds)
        haymaker orch replicas --revision my-app--rev1 --follow

        # Custom polling interval
        haymaker orch replicas --revision my-app--rev1 --follow --interval 10

        # Output as JSON
        haymaker orch replicas --revision my-app--rev1 --format json
    """
    try:
        # Load configuration
        config = load_orchestrator_config(
            subscription_id=subscription_id,
            resource_group=resource_group,
            container_app_name=app_name,
        )

        # Use app name from config if not specified
        final_app_name = app_name or config.container_app_name
        if not final_app_name:
            raise ConfigError(
                "Container app name not specified. Provide via --app-name or configure with:\n"
                "haymaker config set orchestrator.container_app_name <name>",
                details={"missing_field": "container_app_name"},
            )

        # Create client
        client = ContainerAppsClient(config.subscription_id, config.resource_group)

        if follow:
            console.print(f"[dim]Following replicas for revision {revision}...[/dim]")
            console.print(f"[dim]Polling every {interval} seconds[/dim]")
            console.print("[dim]Press Ctrl+C to stop[/dim]\n")

            try:
                while True:
                    # Get replica info
                    async def get_replicas():
                        return await client.list_replicas(final_app_name, revision)

                    replica_list = asyncio.run(get_replicas())

                    # Clear screen and show current state
                    console.clear()
                    console.print(f"[cyan]Replicas for {revision}[/cyan]")
                    console.print(f"[dim]Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")

                    if output_format == "json":
                        console.print(format_json([r.model_dump(mode="json") for r in replica_list]))
                    elif output_format == "yaml":
                        console.print(format_yaml([r.model_dump(mode="json") for r in replica_list]))
                    else:  # table
                        format_replicas(replica_list)

                    # Wait for next interval
                    time.sleep(interval)

            except KeyboardInterrupt:
                console.print("\n[dim]Stopped following replicas[/dim]")
                sys.exit(0)

        else:
            # One-time display
            async def get_replicas():
                return await client.list_replicas(final_app_name, revision)

            replica_list = asyncio.run(get_replicas())

            if output_format == "json":
                console.print(format_json([r.model_dump(mode="json") for r in replica_list]))
            elif output_format == "yaml":
                console.print(format_yaml([r.model_dump(mode="json") for r in replica_list]))
            else:  # table
                format_replicas(replica_list)

    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted by user[/dim]")
        sys.exit(0)
    except Exception as e:
        handle_orch_error(e)


@orch.command()
@click.option(
    "--app-name",
    help="Container app name (default: from config)",
)
@click.option(
    "--subscription-id",
    help="Azure subscription ID (default: from config or env)",
)
@click.option(
    "--resource-group",
    help="Azure resource group (default: from config or env)",
)
@click.option(
    "--revision",
    help="Filter logs by revision name",
)
@click.option(
    "--replica",
    help="Filter logs by replica name",
)
@click.option(
    "--tail",
    default=100,
    type=int,
    help="Number of recent log lines to show (default: 100)",
)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow logs (stream new entries)",
)
@click.option(
    "--timestamps",
    "-t",
    is_flag=True,
    help="Show timestamps",
)
@click.option(
    "--since",
    help="Show logs since duration (e.g., 5m, 1h, 30s)",
)
@click.option(
    "--container",
    help="Filter by container name",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format",
)
@click.pass_context
def logs(
    ctx: click.Context,
    app_name: str | None,
    subscription_id: str | None,
    resource_group: str | None,
    revision: str | None,
    replica: str | None,
    tail: int,
    follow: bool,
    timestamps: bool,
    since: str | None,
    container: str | None,
    output_format: str,
):
    """Display container logs.

    Shows logs from container replicas with various filtering options.
    Supports following logs in real-time and filtering by revision,
    replica, or container name.

    Note: This command currently provides a placeholder implementation.
    Full log streaming requires Azure Monitor integration which can be
    added in a future enhancement.

    Examples:
        # Show recent logs
        haymaker orch logs

        # Follow logs in real-time
        haymaker orch logs --follow

        # Show logs with timestamps
        haymaker orch logs --timestamps

        # Filter by revision
        haymaker orch logs --revision my-app--rev1

        # Show last 50 lines and follow
        haymaker orch logs --tail 50 --follow

        # Filter by time duration
        haymaker orch logs --since 1h
    """
    try:
        # Load configuration
        config = load_orchestrator_config(
            subscription_id=subscription_id,
            resource_group=resource_group,
            container_app_name=app_name,
        )

        # Use app name from config if not specified
        final_app_name = app_name or config.container_app_name
        if not final_app_name:
            raise ConfigError(
                "Container app name not specified. Provide via --app-name or configure with:\n"
                "haymaker config set orchestrator.container_app_name <name>",
                details={"missing_field": "container_app_name"},
            )

        # Note: Full log streaming requires Azure Monitor Log Analytics workspace integration
        # For now, we'll provide a helpful message
        console.print("[yellow]Log streaming not yet implemented.[/yellow]")
        console.print("\n[cyan]To view logs, use one of these methods:[/cyan]")
        console.print("1. Azure Portal:")
        console.print(f"   https://portal.azure.com/#@/resource/subscriptions/{config.subscription_id}"
                     f"/resourceGroups/{config.resource_group}/providers/Microsoft.App"
                     f"/containerApps/{final_app_name}/logs")
        console.print("\n2. Azure CLI:")

        cmd_parts = [
            "az containerapp logs show",
            f"--name {final_app_name}",
            f"--resource-group {config.resource_group}",
        ]

        if revision:
            cmd_parts.append(f"--revision {revision}")
        if replica:
            cmd_parts.append(f"--replica {replica}")
        if container:
            cmd_parts.append(f"--container {container}")
        if follow:
            cmd_parts.append("--follow")
        if tail:
            cmd_parts.append(f"--tail {tail}")

        console.print(f"   {' '.join(cmd_parts)}")

        console.print("\n3. Azure Monitor Log Analytics:")
        console.print("   Query the ContainerAppConsoleLogs table for detailed logs")

        console.print("\n[dim]Log streaming will be implemented in a future update.[/dim]")

    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted by user[/dim]")
        sys.exit(0)
    except Exception as e:
        handle_orch_error(e)


@orch.command()
@click.option(
    "--app-name",
    help="Container app name (default: from config)",
)
@click.option(
    "--subscription-id",
    help="Azure subscription ID (default: from config or env)",
)
@click.option(
    "--resource-group",
    help="Azure resource group (default: from config or env)",
)
@click.option(
    "--revision",
    help="Check specific revision only",
)
@click.option(
    "--deep",
    is_flag=True,
    help="Run deep health checks including HTTP endpoint tests",
)
@click.option(
    "--timeout",
    default=30,
    type=int,
    help="Timeout in seconds for health checks (default: 30)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed check information",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.pass_context
def health(
    ctx: click.Context,
    app_name: str | None,
    subscription_id: str | None,
    resource_group: str | None,
    revision: str | None,
    deep: bool,
    timeout: int,
    verbose: bool,
    output_format: str,
):
    """Run health checks on the orchestrator.

    Performs comprehensive health checks including:
    - Container App provisioning and running status
    - Replica health across active revisions
    - Endpoint connectivity (DNS and TCP)
    - HTTP health endpoint checks (with --deep flag)

    Returns actionable suggestions for any failed checks.

    Examples:
        # Basic health check
        haymaker orch health

        # Deep health check with HTTP endpoint test
        haymaker orch health --deep

        # Show detailed check information
        haymaker orch health --verbose

        # Check specific revision
        haymaker orch health --revision my-app--rev1

        # Custom timeout and verbose output
        haymaker orch health --deep --timeout 60 --verbose

        # Output as JSON
        haymaker orch health --format json
    """
    try:
        # Load configuration
        config = load_orchestrator_config(
            subscription_id=subscription_id,
            resource_group=resource_group,
            container_app_name=app_name,
        )

        # Use app name from config if not specified
        final_app_name = app_name or config.container_app_name
        if not final_app_name:
            raise ConfigError(
                "Container app name not specified. Provide via --app-name or configure with:\n"
                "haymaker config set orchestrator.container_app_name <name>",
                details={"missing_field": "container_app_name"},
            )

        # Create client
        client = ContainerAppsClient(config.subscription_id, config.resource_group)

        # Run health checks
        console.print(f"[cyan]Running health checks for {final_app_name}...[/cyan]")
        if deep:
            console.print("[dim]Deep mode: Including HTTP endpoint checks[/dim]")
        console.print()

        async def perform_health_checks():
            return await run_health_checks(
                client=client,
                app_name=final_app_name,
                deep=deep,
                timeout=timeout,
            )

        # Run checks
        check_results = asyncio.run(perform_health_checks())

        # Format and display results
        if output_format == "json":
            console.print(format_json(check_results))
        elif output_format == "yaml":
            console.print(format_yaml(check_results))
        else:  # table
            from haymaker_cli.orch.formatters import format_health_results
            format_health_results(check_results, verbose=verbose)

        # Exit with error code if any checks failed
        failed_checks = [r for r in check_results if r.get("status") == "FAIL"]
        if failed_checks:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted by user[/dim]")
        sys.exit(0)
    except Exception as e:
        handle_orch_error(e)


__all__ = ["orch", "status", "replicas", "logs", "health"]
