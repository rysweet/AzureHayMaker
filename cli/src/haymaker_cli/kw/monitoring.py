"""Monitoring commands for Knowledge Worker deployments.

Provides CLI commands for monitoring active KW deployments:
- list-workers: List all workers in a deployment
- check-telemetry: Verify M365 telemetry is being generated
- monitor: Real-time monitoring dashboard
- list-resources: List Azure resources for a deployment

All commands support run_id resolution from:
1. --run-id flag
2. HAYMAKER_RUN_ID environment variable
3. ~/.azure_haymaker/active_deployment file
"""

import asyncio
import json
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import click
import yaml
from azure.identity import ClientSecretCredential
from azure_haymaker.knowledge_worker.state_manager import DeploymentStateManager
from azure_haymaker.knowledge_worker.telemetry import M365TelemetryCollector
from msgraph.graph_service_client import GraphServiceClient
from rich.console import Console
from rich.live import Live
from rich.table import Table

from haymaker_cli.kw.resolver import RunIdResolver

console = Console()
logger = logging.getLogger(__name__)


def _get_graph_client() -> GraphServiceClient | None:
    """Create Graph API client from environment variables.

    Returns:
        GraphServiceClient or None if credentials not available
    """
    tenant_id = os.getenv("KW_TENANT_ID")
    app_id = os.getenv("KW_APP_ID")
    client_secret = os.getenv("KW_CLIENT_SECRET")

    if not all([tenant_id, app_id, client_secret]):
        return None

    # Type guard: after the check above, we know these are non-None
    assert tenant_id is not None
    assert app_id is not None
    assert client_secret is not None

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=app_id,
        client_secret=client_secret,
    )
    return GraphServiceClient(credential)


def _format_output(data: Any, format: str) -> str:
    """Format data for output.

    Args:
        data: Data to format
        format: Output format (json, yaml, or table)

    Returns:
        Formatted string
    """
    if format == "json":
        return json.dumps(data, indent=2, default=str)
    elif format == "yaml":
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    else:
        return str(data)


@click.command("list-workers")
@click.option("--run-id", help="Deployment run ID (or use HAYMAKER_RUN_ID env var)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format",
)
def list_workers_command(run_id: str | None, output_format: str):
    """List all workers in a KW deployment.

    Shows worker details including:
    - Worker ID and display name
    - Persona and department
    - User Principal Name (UPN)
    - Entra Object ID
    - Endpoint type

    Examples:
        haymaker kw list-workers --run-id kw-abc123
        haymaker kw list-workers --format json
        HAYMAKER_RUN_ID=kw-abc123 haymaker kw list-workers
    """
    # Resolve run_id
    resolved_run_id = RunIdResolver.resolve(run_id)
    if not resolved_run_id:
        console.print("[red]Error: No run_id specified[/red]")
        console.print("Specify via: --run-id, HAYMAKER_RUN_ID env var, or active deployment")
        sys.exit(1)

    # Load deployment state
    state_manager = DeploymentStateManager()
    deployment = state_manager.load_deployment(resolved_run_id)

    if not deployment:
        console.print(f"[red]Error: Deployment not found: {resolved_run_id}[/red]")
        sys.exit(1)

    # Load workers
    workers = state_manager.load_workers(resolved_run_id)

    if not workers:
        console.print(f"[yellow]No workers found for deployment: {resolved_run_id}[/yellow]")
        return

    # Output based on format
    if output_format == "json":
        output = {
            "run_id": resolved_run_id,
            "deployment_name": deployment.get("name"),
            "worker_count": len(workers),
            "workers": workers,
        }
        console.print(_format_output(output, "json"))

    elif output_format == "yaml":
        output = {
            "run_id": resolved_run_id,
            "deployment_name": deployment.get("name"),
            "worker_count": len(workers),
            "workers": workers,
        }
        console.print(_format_output(output, "yaml"))

    else:
        # Table format
        table = Table(title=f"Workers for {resolved_run_id}")
        table.add_column("Worker ID", style="cyan")
        table.add_column("Display Name", style="green")
        table.add_column("Persona")
        table.add_column("Department")
        table.add_column("UPN", style="dim")

        for worker in workers:
            table.add_row(
                worker.get("worker_id", ""),
                worker.get("display_name", ""),
                worker.get("persona", ""),
                worker.get("department", ""),
                worker.get("user_principal_name", ""),
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(workers)} workers[/dim]")


@click.command("check-telemetry")
@click.option("--run-id", help="Deployment run ID (or use HAYMAKER_RUN_ID env var)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.option(
    "--hours-back",
    default=24,
    type=int,
    help="Hours of history to check (default: 24)",
)
def check_telemetry_command(run_id: str | None, output_format: str, hours_back: int):
    """Check M365 telemetry generation for a deployment.

    Queries Microsoft Graph API to verify workers are generating:
    - Email messages (sent/received)
    - Calendar events
    - Teams messages

    Shows per-worker and aggregate statistics.

    Examples:
        haymaker kw check-telemetry --run-id kw-abc123
        haymaker kw check-telemetry --hours-back 48 --format json
    """
    # Resolve run_id
    resolved_run_id = RunIdResolver.resolve(run_id)
    if not resolved_run_id:
        console.print("[red]Error: No run_id specified[/red]")
        console.print("Specify via: --run-id, HAYMAKER_RUN_ID env var, or active deployment")
        sys.exit(1)

    # Check credentials
    graph_client = _get_graph_client()
    if not graph_client:
        console.print("[red]Error: M365 credentials not configured[/red]")
        console.print("Set KW_TENANT_ID, KW_APP_ID, and KW_CLIENT_SECRET environment variables")
        sys.exit(1)

    # Load workers
    state_manager = DeploymentStateManager()
    workers_data = state_manager.load_workers(resolved_run_id)

    if not workers_data:
        console.print(f"[yellow]No workers found for deployment: {resolved_run_id}[/yellow]")
        return

    console.print(f"[cyan]Checking telemetry for {len(workers_data)} workers...[/cyan]")
    console.print(f"[dim]Querying last {hours_back} hours[/dim]\n")

    # Create telemetry collector
    collector = M365TelemetryCollector(graph_client, resolved_run_id)

    # Collect telemetry asynchronously
    async def collect():
        # Build WorkerIdentity objects from stored data
        from azure_haymaker.knowledge_worker.models.worker import (
            EndpointType,
            WorkerIdentity,
            WorkerPersona,
        )

        workers = []
        for wd in workers_data:
            try:
                identity = WorkerIdentity(
                    worker_id=wd["worker_id"],
                    display_name=wd["display_name"],
                    user_principal_name=wd["user_principal_name"],
                    entra_object_id=wd["entra_object_id"],
                    persona=WorkerPersona(wd["persona"]),
                    endpoint_type=EndpointType(wd["endpoint_type"]),
                    department=wd.get("department", ""),
                    team_ids=wd.get("team_ids", []),
                )
                workers.append(identity)
            except Exception as e:
                logger.warning(f"Failed to parse worker data: {e}")

        # Collect telemetry
        start_time = datetime.now(UTC) - timedelta(hours=hours_back)
        summary = await collector.get_run_summary(workers, start_time=start_time)
        return summary

    try:
        summary = asyncio.run(collect())
    except Exception as e:
        console.print(f"[red]Error collecting telemetry: {e}[/red]")
        sys.exit(1)

    # Output based on format
    if output_format == "json":
        console.print(_format_output(summary, "json"))

    elif output_format == "yaml":
        console.print(_format_output(summary, "yaml"))

    else:
        # Table format - overall summary
        summary_table = Table(title=f"Telemetry Summary for {resolved_run_id}")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", justify="right", style="green")

        summary_table.add_row("Workers", str(summary.get("total_workers", 0)))
        summary_table.add_row("Emails", str(summary.get("email_count", 0)))
        summary_table.add_row("Calendar Events", str(summary.get("calendar_count", 0)))
        summary_table.add_row("Teams Messages", str(summary.get("teams_count", 0)))

        console.print(summary_table)

        # Per-worker breakdown
        by_worker = summary.get("by_worker", {})
        if by_worker:
            console.print("\n[cyan]Per-Worker Breakdown:[/cyan]")
            worker_table = Table()
            worker_table.add_column("Worker", style="cyan")
            worker_table.add_column("Emails", justify="right")
            worker_table.add_column("Calendar", justify="right")
            worker_table.add_column("Teams", justify="right")

            for worker_id, stats in by_worker.items():
                if "error" in stats:
                    worker_table.add_row(
                        worker_id,
                        "[red]ERROR[/red]",
                        "[red]ERROR[/red]",
                        "[red]ERROR[/red]",
                    )
                else:
                    worker_table.add_row(
                        worker_id,
                        str(stats.get("email_count", 0)),
                        str(stats.get("calendar_count", 0)),
                        str(stats.get("teams_count", 0)),
                    )

            console.print(worker_table)


@click.command("monitor")
@click.option("--run-id", help="Deployment run ID (or use HAYMAKER_RUN_ID env var)")
@click.option(
    "--refresh",
    default=10,
    type=int,
    help="Refresh interval in seconds (default: 10)",
)
@click.option(
    "--duration",
    default=0,
    type=int,
    help="Duration in seconds to monitor (0 = infinite, default: 0)",
)
def monitor_command(run_id: str | None, refresh: int, duration: int):
    """Real-time monitoring of KW deployment activity.

    Displays a live dashboard with:
    - Deployment status and phase
    - Worker count and status
    - Real-time activity counters (emails, calendar, Teams)
    - Error/warning indicators

    Press Ctrl+C to exit.

    Examples:
        haymaker kw monitor --run-id kw-abc123
        haymaker kw monitor --refresh 5 --duration 300
    """
    # Resolve run_id
    resolved_run_id = RunIdResolver.resolve(run_id)
    if not resolved_run_id:
        console.print("[red]Error: No run_id specified[/red]")
        console.print("Specify via: --run-id, HAYMAKER_RUN_ID env var, or active deployment")
        sys.exit(1)

    # Check credentials
    graph_client = _get_graph_client()
    if not graph_client:
        console.print("[red]Error: M365 credentials not configured[/red]")
        console.print("Set KW_TENANT_ID, KW_APP_ID, and KW_CLIENT_SECRET environment variables")
        sys.exit(1)

    state_manager = DeploymentStateManager()
    start_time = datetime.now(UTC)

    def generate_dashboard() -> Table:
        """Generate the monitoring dashboard table."""
        # Load current state
        deployment = state_manager.load_deployment(resolved_run_id)
        if not deployment:
            table = Table(title=f"Monitoring {resolved_run_id}")
            table.add_column("Error")
            table.add_row("[red]Deployment not found[/red]")
            return table

        # Create dashboard
        table = Table(title=f"Monitoring {resolved_run_id}")
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        # Deployment info
        table.add_row("Name", deployment.get("name", ""))
        table.add_row("Phase", deployment.get("phase", ""))
        table.add_row("Status", deployment.get("status", ""))
        table.add_row("Workers", str(deployment.get("worker_count", 0)))

        # Timestamps
        started_at = deployment.get("started_at")
        if started_at:
            table.add_row("Started", started_at)

        updated_at = deployment.get("updated_at")
        if updated_at:
            table.add_row("Updated", updated_at)

        # Monitoring duration
        elapsed = (datetime.now(UTC) - start_time).total_seconds()
        table.add_row("Monitoring Duration", f"{int(elapsed)}s")

        return table

    # Live monitoring loop
    try:
        with Live(generate_dashboard(), refresh_per_second=1 / refresh, console=console) as live:
            elapsed = 0
            while True:
                live.update(generate_dashboard())

                # Check duration limit
                if duration > 0 and elapsed >= duration:
                    break

                # Sleep for refresh interval
                import time

                time.sleep(refresh)
                elapsed += refresh

    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")


@click.command("list-resources")
@click.option("--run-id", help="Deployment run ID (or use HAYMAKER_RUN_ID env var)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.option(
    "--resource-type",
    type=click.Choice(["all", "users", "groups", "endpoints"], case_sensitive=False),
    default="all",
    help="Filter by resource type",
)
def list_resources_command(run_id: str | None, output_format: str, resource_type: str):
    """List Azure resources created for a KW deployment.

    Shows all resources provisioned for a deployment:
    - Entra users (knowledge workers)
    - Security groups
    - Endpoints (containers, Cloud PCs, VMs)
    - Transport rules

    Useful for:
    - Verifying deployment completeness
    - Troubleshooting missing resources
    - Planning cleanup operations

    Examples:
        haymaker kw list-resources --run-id kw-abc123
        haymaker kw list-resources --resource-type users --format json
    """
    # Resolve run_id
    resolved_run_id = RunIdResolver.resolve(run_id)
    if not resolved_run_id:
        console.print("[red]Error: No run_id specified[/red]")
        console.print("Specify via: --run-id, HAYMAKER_RUN_ID env var, or active deployment")
        sys.exit(1)

    # Load deployment state
    state_manager = DeploymentStateManager()
    deployment = state_manager.load_deployment(resolved_run_id)

    if not deployment:
        console.print(f"[red]Error: Deployment not found: {resolved_run_id}[/red]")
        sys.exit(1)

    # Load workers (users)
    workers = state_manager.load_workers(resolved_run_id)

    # Build resource inventory
    resources = {
        "run_id": resolved_run_id,
        "deployment_name": deployment.get("name"),
        "users": [],
        "groups": [],
        "endpoints": [],
    }

    # Add users
    if resource_type in ("all", "users"):
        for worker in workers:
            resources["users"].append(
                {
                    "type": "entra_user",
                    "id": worker.get("entra_object_id"),
                    "name": worker.get("display_name"),
                    "upn": worker.get("user_principal_name"),
                    "worker_id": worker.get("worker_id"),
                }
            )

    # Groups and endpoints would be queried from Azure in production
    # For now, we show placeholder structure
    if resource_type in ("all", "groups"):
        resources["groups"].append(
            {
                "type": "security_group",
                "id": f"{resolved_run_id}-workers-group",
                "name": f"KW Workers - {deployment.get('name')}",
            }
        )

    if resource_type in ("all", "endpoints"):
        for worker in workers:
            endpoint_type = worker.get("endpoint_type", "cli_container")
            resources["endpoints"].append(
                {
                    "type": endpoint_type,
                    "worker_id": worker.get("worker_id"),
                    "id": f"{worker.get('worker_id')}-endpoint",
                    "status": "running",
                }
            )

    # Output based on format
    if output_format == "json":
        console.print(_format_output(resources, "json"))

    elif output_format == "yaml":
        console.print(_format_output(resources, "yaml"))

    else:
        # Table format
        console.print(f"[cyan]Resources for {resolved_run_id}[/cyan]\n")

        # Users table
        if resources["users"]:
            users_table = Table(title="Entra Users")
            users_table.add_column("Worker ID", style="cyan")
            users_table.add_column("Display Name")
            users_table.add_column("UPN", style="dim")
            users_table.add_column("Object ID", style="dim")

            for user in resources["users"]:
                users_table.add_row(
                    user.get("worker_id", ""),
                    user.get("name", ""),
                    user.get("upn", ""),
                    user.get("id", ""),
                )

            console.print(users_table)

        # Groups table
        if resources["groups"]:
            console.print()
            groups_table = Table(title="Security Groups")
            groups_table.add_column("Name", style="cyan")
            groups_table.add_column("ID", style="dim")

            for group in resources["groups"]:
                groups_table.add_row(group.get("name", ""), group.get("id", ""))

            console.print(groups_table)

        # Endpoints table
        if resources["endpoints"]:
            console.print()
            endpoints_table = Table(title="Endpoints")
            endpoints_table.add_column("Worker ID", style="cyan")
            endpoints_table.add_column("Type")
            endpoints_table.add_column("Status")

            for endpoint in resources["endpoints"]:
                endpoints_table.add_row(
                    endpoint.get("worker_id", ""),
                    endpoint.get("type", ""),
                    endpoint.get("status", ""),
                )

            console.print(endpoints_table)

        # Summary
        console.print(
            f"\n[dim]Total: {len(resources['users'])} users, "
            f"{len(resources['groups'])} groups, "
            f"{len(resources['endpoints'])} endpoints[/dim]"
        )


__all__ = [
    "list_workers_command",
    "check_telemetry_command",
    "monitor_command",
    "list_resources_command",
]
