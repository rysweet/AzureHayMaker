"""Main CLI entry point for HayMaker CLI."""

import sys
import time
from typing import Any

import click
from rich.console import Console

from haymaker_cli.auth import create_auth_provider
from haymaker_cli.client import HayMakerClientError, SyncHayMakerClient
from haymaker_cli.config import (
    get_config_value,
    list_config,
    load_cli_config,
    set_config_value,
)
from haymaker_cli.formatters import (
    format_agent_list,
    format_cleanup_response,
    format_execution_response,
    format_execution_status,
    format_json,
    format_log_entries,
    format_metrics_summary,
    format_orchestrator_status,
    format_resource_list,
    format_yaml,
)
from haymaker_cli.orch.commands import orch

console = Console()


@click.group()
@click.option(
    "--profile",
    default="default",
    help="Configuration profile to use",
    envvar="HAYMAKER_PROFILE",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, profile: str, output_format: str, verbose: bool):
    """Azure HayMaker CLI - Manage orchestrator operations.

    Examples:
        haymaker status
        haymaker metrics --period 30d
        haymaker deploy --scenario compute-01
    """
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    ctx.obj["format"] = output_format
    ctx.obj["verbose"] = verbose


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


def handle_output(ctx: click.Context, data: Any, formatter_func=None):
    """Handle output formatting based on context.

    Args:
        ctx: Click context
        data: Data to output
        formatter_func: Optional formatter function for table output
    """
    output_format = ctx.obj["format"]

    try:
        if output_format == "json":
            click.echo(format_json(data))
        elif output_format == "yaml":
            click.echo(format_yaml(data))
        else:  # table
            if formatter_func:
                formatter_func(data)
            else:
                click.echo(format_json(data))
    except Exception as e:
        raise click.ClickException(f"Output formatting error: {e}") from e


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


# Status command


@cli.command()  # type: ignore[misc]  # Click decorators modify function signatures
@click.pass_context
def status(ctx: click.Context):
    """Show current orchestrator status.

    Example:
        haymaker status
        haymaker status --format json
    """
    try:
        client = get_client(ctx)
        status_data = client.get_status()
        handle_output(ctx, status_data, format_orchestrator_status)
    except Exception as e:
        handle_error(e)


# Metrics command


@cli.command()  # type: ignore[misc]  # Click decorators modify function signatures
@click.option(
    "--period",
    default="7d",
    type=click.Choice(["7d", "30d", "90d"], case_sensitive=False),
    help="Time period for metrics",
)
@click.option("--scenario", help="Filter by scenario name")
@click.pass_context
def metrics(ctx: click.Context, period: str, scenario: str | None):
    """Show execution metrics.

    Example:
        haymaker metrics
        haymaker metrics --period 30d
        haymaker metrics --scenario compute-01
    """
    try:
        client = get_client(ctx)
        metrics_data = client.get_metrics(period=period, scenario=scenario)
        handle_output(ctx, metrics_data, format_metrics_summary)
    except Exception as e:
        handle_error(e)


# Agents command group


# Orchestrator command group

# Register orch command group from orch.commands module
cli.add_command(orch)


# Agents command group


@cli.group()  # type: ignore[misc]  # Click decorators modify function signatures
def agents():
    """Manage and view agents."""


@agents.command(name="list")
@click.option(
    "--status",
    type=click.Choice(["running", "completed", "failed"], case_sensitive=False),
    help="Filter by status",
)
@click.option("--limit", default=100, type=int, help="Maximum number of results")
@click.pass_context
def agents_list(ctx: click.Context, status: str | None, limit: int):
    """List all agents.

    Example:
        haymaker agents list
        haymaker agents list --status running
    """
    try:
        client = get_client(ctx)
        agents_data = client.list_agents(status=status, limit=limit)
        handle_output(ctx, agents_data, format_agent_list)
    except Exception as e:
        handle_error(e)


# Logs command


@cli.command()  # type: ignore[misc]  # Click decorators modify function signatures
@click.option("--agent-id", required=True, help="Agent ID to view logs for")
@click.option("--tail", default=100, type=int, help="Number of recent log entries")
@click.option("--follow", "-f", is_flag=True, help="Follow logs (stream new entries)")
@click.pass_context
def logs(ctx: click.Context, agent_id: str, tail: int, follow: bool):
    """View agent logs.

    Example:
        haymaker logs --agent-id agent-123
        haymaker logs --agent-id agent-123 --follow
        haymaker logs --agent-id agent-123 --tail 50
    """
    try:
        client = get_client(ctx)

        if follow:
            console.print(f"[dim]Following logs for agent {agent_id}...[/dim]")
            console.print("[dim]Press Ctrl+C to stop[/dim]\n")

            seen_ids = set()

            try:
                while True:
                    logs_data = client.get_agent_logs(agent_id, tail=tail, follow=False)

                    # Filter out logs we've already seen
                    new_logs = [
                        log for log in logs_data if f"{log.timestamp}-{log.message}" not in seen_ids
                    ]

                    if new_logs:
                        format_log_entries(new_logs)
                        for log in new_logs:
                            seen_ids.add(f"{log.timestamp}-{log.message}")

                    time.sleep(2)  # Poll every 2 seconds

            except KeyboardInterrupt:
                console.print("\n[dim]Stopped following logs[/dim]")
                return

        else:
            logs_data = client.get_agent_logs(agent_id, tail=tail, follow=False)
            handle_output(ctx, logs_data, format_log_entries)

    except Exception as e:
        handle_error(e)


# Resources command group


@cli.group()  # type: ignore[misc]  # Click decorators modify function signatures
def resources():
    """Manage and view resources."""


@resources.command(name="list")
@click.option("--execution-id", help="Filter by execution ID")
@click.option("--scenario", help="Filter by scenario name")
@click.option(
    "--status",
    type=click.Choice(["created", "deleted"], case_sensitive=False),
    help="Filter by status",
)
@click.option(
    "--group-by",
    type=click.Choice(["type", "scenario", "execution"], case_sensitive=False),
    help="Group results by field",
)
@click.option("--limit", default=100, type=int, help="Maximum number of results")
@click.pass_context
def resources_list(
    ctx: click.Context,
    execution_id: str | None,
    scenario: str | None,
    status: str | None,
    group_by: str | None,
    limit: int,
):
    """List all resources.

    Example:
        haymaker resources list
        haymaker resources list --scenario compute-01
        haymaker resources list --group-by type
    """
    try:
        client = get_client(ctx)
        resources_data = client.list_resources(
            execution_id=execution_id,
            scenario=scenario,
            status=status,
            limit=limit,
        )

        if ctx.obj["format"] == "table":
            format_resource_list(resources_data, group_by=group_by)
        else:
            handle_output(ctx, resources_data)

    except Exception as e:
        handle_error(e)


# Cleanup command


@cli.command()  # type: ignore[misc]  # Click decorators modify function signatures
@click.option("--execution-id", help="Cleanup specific execution")
@click.option("--scenario", help="Cleanup specific scenario")
@click.option("--dry-run", is_flag=True, help="Show what would be cleaned without deleting")
@click.confirmation_option(prompt="Are you sure you want to cleanup resources?")
@click.pass_context
def cleanup(
    ctx: click.Context,
    execution_id: str | None,
    scenario: str | None,
    dry_run: bool,
):
    """Trigger cleanup of resources.

    Example:
        haymaker cleanup --dry-run
        haymaker cleanup --execution-id exec-123
        haymaker cleanup --scenario compute-01
    """
    try:
        client = get_client(ctx)

        if dry_run:
            console.print("[yellow]Dry run mode - no resources will be deleted[/yellow]\n")

        cleanup_data = client.trigger_cleanup(
            execution_id=execution_id,
            scenario=scenario,
            dry_run=dry_run,
        )

        handle_output(ctx, cleanup_data, format_cleanup_response)

    except Exception as e:
        handle_error(e)


# Deploy command


@cli.command()  # type: ignore[misc]  # Click decorators modify function signatures
@click.option("--scenario", required=True, help="Scenario name to execute")
@click.option("--wait", is_flag=True, help="Wait for execution to complete")
@click.option(
    "--poll-interval", default=30, type=int, help="Polling interval in seconds (default: 30)"
)
@click.pass_context
def deploy(ctx: click.Context, scenario: str, wait: bool, poll_interval: int):
    """Deploy scenario on-demand.

    Example:
        haymaker deploy --scenario compute-01-linux-vm-web-server
        haymaker deploy --scenario compute-01 --wait
    """
    try:
        client = get_client(ctx)

        # Submit execution
        console.print(f"[cyan]Submitting execution for scenario:[/cyan] {scenario}")
        execution = client.execute_scenario(scenario)

        handle_output(ctx, execution, format_execution_response)

        if wait:
            console.print("\n[dim]Waiting for execution to complete...[/dim]")
            console.print(f"[dim]Execution ID: {execution.execution_id}[/dim]")
            console.print(f"[dim]Polling every {poll_interval} seconds[/dim]")
            console.print("[dim]Press Ctrl+C to stop waiting[/dim]\n")

            try:
                dots = 0
                while True:
                    status_data = client.get_execution_status(execution.execution_id)

                    if status_data.status in ["completed", "failed"]:
                        console.print()
                        format_execution_status(status_data)

                        if status_data.status == "completed":
                            console.print("\n[green]Execution completed successfully![/green]")
                        else:
                            console.print("\n[red]Execution failed![/red]")
                            if status_data.error:
                                console.print(f"[red]Error: {status_data.error}[/red]")
                            sys.exit(1)

                        break

                    # Show progress
                    dots = (dots + 1) % 4
                    progress = "." * dots
                    console.print(
                        f"\r[dim]Status: {status_data.status}{progress:4}[/dim]",
                        end="",
                    )

                    time.sleep(poll_interval)

            except KeyboardInterrupt:
                console.print("\n\n[dim]Stopped waiting. Execution continues in background.[/dim]")
                console.print(
                    f"[dim]Check status with: haymaker status --execution-id {execution.execution_id}[/dim]"
                )

    except Exception as e:
        handle_error(e)


# Config command group


@cli.group()  # type: ignore[misc]  # Click decorators modify function signatures
def config():
    """Manage CLI configuration."""


@config.command(name="set")
@click.argument("key")
@click.argument("value")
@click.option("--profile", default="default", help="Profile name")
def config_set(key: str, value: str, profile: str):
    """Set configuration value.

    Example:
        haymaker config set endpoint https://haymaker.azurewebsites.net
        haymaker config set api-key your-api-key
    """
    try:
        set_config_value(key, value, profile)
        console.print(f"[green]Configuration updated:[/green] {key} = {value}")
        console.print(f"[dim]Profile: {profile}[/dim]")
    except Exception as e:
        handle_error(e)


@config.command(name="get")
@click.argument("key")
@click.option("--profile", default="default", help="Profile name")
def config_get(key: str, profile: str):
    """Get configuration value.

    Example:
        haymaker config get endpoint
    """
    try:
        value = get_config_value(key, profile)
        if value:
            click.echo(value)
        else:
            console.print(f"[yellow]Configuration key not found:[/yellow] {key}")
    except Exception as e:
        handle_error(e)


@config.command(name="list")
@click.option("--profile", default="default", help="Profile name")
def config_list(profile: str):
    """List all configuration values.

    Example:
        haymaker config list
    """
    try:
        config_data = list_config(profile)

        if not config_data:
            console.print(f"[yellow]No configuration found for profile:[/yellow] {profile}")
            return

        console.print(f"[cyan]Configuration for profile:[/cyan] {profile}\n")

        for key, value in config_data.items():
            # Mask sensitive values
            if ("key" in key.lower() or "secret" in key.lower()) and value and value != "(not set)":
                value = "*" * 8 + value[-4:] if len(value) > 4 else "****"

            console.print(f"  {key:20} = {value}")

    except Exception as e:
        handle_error(e)


def main():
    """Main entry point for CLI."""
    cli()  # type: ignore[call-arg]  # Click modifies function signature


if __name__ == "__main__":
    main()
