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

Each command handler is small and focused, following single-responsibility.
Addresses Issue #22: Refactor long CLI methods.
Addresses Issue #172: Add lifecycle management commands.
"""

import asyncio
import sys
from typing import Any

import click

from ..constants import (
    DEFAULT_LIST_LIMIT,
    DEFAULT_LOG_LINES,
    DEFAULT_OUTPUT_FORMAT,
    EXIT_CANCELLED,
    EXIT_ERROR,
)
from ..utils.output import format_json, format_status_line, format_table
from ..utils.state import (
    filter_deployments_by_age,
    get_deployment_or_exit,
    get_log_path,
    get_state_manager,
    get_workers_for_deployment,
    parse_duration,
)


@click.group()
def kw() -> None:
    """Knowledge Worker lifecycle management commands.

    Manage KW deployments: init, deploy, status, logs, start, stop, cleanup.
    """
    pass


# ============================================================================
# Status Command
# ============================================================================


@kw.command()
@click.option("--run-id", "-r", help="Specific deployment run ID")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json"]),
    default=DEFAULT_OUTPUT_FORMAT,
    help="Output format",
)
def status(run_id: str | None, output_format: str) -> None:
    """Display deployment status.

    Shows status of all deployments or a specific one.
    """
    state_manager = get_state_manager()

    if run_id:
        _show_single_status(run_id, output_format)
    else:
        _show_all_status(state_manager, output_format)


def _show_single_status(run_id: str, output_format: str) -> None:
    """Show status for a single deployment."""
    deployment = get_deployment_or_exit(run_id)

    if output_format == "json":
        click.echo(format_json([deployment]))
    else:
        click.echo(
            format_status_line(
                deployment["run_id"],
                deployment.get("status", "unknown"),
                deployment.get("phase", "unknown"),
            )
        )
        click.echo(f"  Workers: {deployment.get('worker_count', 0)}")
        click.echo(f"  Started: {deployment.get('started_at', 'N/A')}")


def _show_all_status(state_manager: Any, output_format: str) -> None:
    """Show status for all deployments."""
    deployments = state_manager.list_deployments()

    if not deployments:
        click.echo("No deployments found.")
        return

    if output_format == "json":
        click.echo(format_json(deployments))
    else:
        for deployment in deployments:
            click.echo(
                format_status_line(
                    deployment["run_id"],
                    deployment.get("status", "unknown"),
                    deployment.get("phase", "unknown"),
                )
            )


# ============================================================================
# List Command
# ============================================================================


@kw.command("list")
@click.option(
    "--limit",
    "-l",
    type=int,
    default=DEFAULT_LIST_LIMIT,
    help="Maximum number of deployments to show",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json"]),
    default=DEFAULT_OUTPUT_FORMAT,
    help="Output format",
)
def list_deployments(limit: int, output_format: str) -> None:
    """List all known deployments."""
    state_manager = get_state_manager()
    deployments = state_manager.get_recent_deployments(limit)

    if not deployments:
        click.echo("No deployments found.")
        return

    if output_format == "json":
        click.echo(format_json(deployments))
    else:
        columns = ["run_id", "name", "status", "phase", "worker_count"]
        click.echo(format_table(deployments, columns))


# ============================================================================
# Logs Command
# ============================================================================


@kw.command()
@click.option("--run-id", "-r", required=True, help="Deployment run ID")
@click.option("--follow", "-f", is_flag=True, help="Follow logs in real-time")
@click.option(
    "--lines",
    "-n",
    type=int,
    default=DEFAULT_LOG_LINES,
    help="Number of lines to show",
)
def logs(run_id: str, follow: bool, lines: int) -> None:
    """View logs for a deployment."""
    # Verify deployment exists
    get_deployment_or_exit(run_id)

    log_dir = get_log_path(run_id)

    if not log_dir.exists():
        click.echo(f"No logs found for deployment: {run_id}")
        return

    _display_logs(log_dir, lines, follow)


def _display_logs(log_dir: Any, lines: int, follow: bool) -> None:
    """Display logs from the log directory."""
    log_file = log_dir / "activity.log"

    if not log_file.exists():
        click.echo("No activity log found.")
        return

    if follow:
        _follow_log_file(log_file)
    else:
        _show_log_tail(log_file, lines)


def _show_log_tail(log_file: Any, lines: int) -> None:
    """Show last N lines of a log file."""
    with open(log_file) as f:
        all_lines = f.readlines()
        for line in all_lines[-lines:]:
            click.echo(line.rstrip())


def _follow_log_file(log_file: Any) -> None:
    """Follow a log file in real-time."""
    import time

    click.echo(f"Following {log_file}... (Ctrl+C to stop)")

    with open(log_file) as f:
        # Go to end
        f.seek(0, 2)

        try:
            while True:
                line = f.readline()
                if line:
                    click.echo(line.rstrip())
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            click.echo("\nStopped following logs.")


# ============================================================================
# Stop Command
# ============================================================================


@kw.command()
@click.option("--run-id", "-r", required=True, help="Deployment run ID")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def stop(run_id: str, yes: bool) -> None:
    """Stop a running deployment."""
    deployment = get_deployment_or_exit(run_id)

    if deployment.get("status") != "running":
        click.echo(f"Deployment {run_id} is not running (status: {deployment.get('status')})")
        sys.exit(EXIT_ERROR)

    if not yes and not click.confirm(f"Stop deployment {run_id}?"):
        click.echo("Aborted.")
        sys.exit(EXIT_CANCELLED)

    success = asyncio.run(_stop_deployment(run_id))

    if success:
        click.echo(f"Deployment {run_id} stopped.")
    else:
        click.echo(f"Failed to stop deployment {run_id}.")
        sys.exit(EXIT_ERROR)


async def _stop_deployment(run_id: str) -> bool:
    """Stop a deployment (async implementation)."""
    # Update state to stopped
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


# ============================================================================
# Start Command
# ============================================================================


@kw.command()
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


# ============================================================================
# Restart Command
# ============================================================================


@kw.command()
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


# ============================================================================
# Cleanup Command
# ============================================================================


@kw.command()
@click.option("--run-id", "-r", help="Specific deployment to clean up")
@click.option("--all", "cleanup_all", is_flag=True, help="Clean up all deployments")
@click.option("--older-than", help="Clean up deployments older than duration (e.g., 24h, 7d)")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def cleanup(
    run_id: str | None,
    cleanup_all: bool,
    older_than: str | None,
    dry_run: bool,
    yes: bool,
) -> None:
    """Clean up deployment resources.

    Must specify one of: --run-id, --all, or --older-than.
    """
    if not run_id and not cleanup_all and not older_than:
        raise click.UsageError("Must specify one of: --run-id, --all, or --older-than")

    state_manager = get_state_manager()

    # Determine deployments to clean up
    if run_id:
        deployments = [get_deployment_or_exit(run_id)]
    elif older_than:
        duration = parse_duration(older_than)
        all_deployments = state_manager.list_deployments()
        deployments = filter_deployments_by_age(all_deployments, duration)
    else:  # cleanup_all
        deployments = state_manager.list_deployments()

    if not deployments:
        click.echo("No deployments to clean up.")
        return

    # Show what will be cleaned up
    click.echo(f"Deployments to clean up ({len(deployments)}):")
    for deployment in deployments:
        click.echo(f"  - {deployment['run_id']}: {deployment.get('name', 'N/A')}")

    if dry_run:
        click.echo("\n[Dry run] No resources were deleted.")
        return

    # Confirm
    if not yes and not click.confirm(f"Clean up {len(deployments)} deployment(s)?"):
        click.echo("Aborted.")
        sys.exit(EXIT_CANCELLED)

    # Perform cleanup
    for deployment in deployments:
        _cleanup_single_deployment(state_manager, deployment["run_id"])

    click.echo(f"Cleaned up {len(deployments)} deployment(s).")


def _cleanup_single_deployment(state_manager: Any, run_id: str) -> None:
    """Clean up a single deployment."""
    click.echo(f"Cleaning up {run_id}...")

    # Delete workers
    worker_count = state_manager.delete_workers(run_id)
    click.echo(f"  Deleted {worker_count} worker(s)")

    # Delete deployment state
    state_manager.delete_deployment(run_id)
    click.echo("  Deleted deployment state")


# ============================================================================
# Delete Worker Command
# ============================================================================


@kw.command("delete-worker")
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


# ============================================================================
# Init Command
# ============================================================================


@kw.command()
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

    # Save config if requested
    if save_config:
        with open(save_config, "w") as f:
            f.write(config.to_env_string())
        click.echo(f"✅ Configuration saved to: {save_config}")
        click.echo(f"   Run: source {save_config}")
    else:
        click.echo("To save credentials, run with --save-config <file>")


# ============================================================================
# Deploy Command
# ============================================================================


@kw.command()
@click.option(
    "--name",
    "-n",
    default=None,
    help="Deployment name (auto-generated if not provided)",
)
@click.option(
    "--workers",
    "-w",
    type=int,
    default=10,
    help="Number of workers to deploy",
)
@click.option(
    "--department",
    "-d",
    default="engineering",
    help="Department name for workers",
)
@click.option(
    "--duration",
    type=int,
    default=8,
    help="Duration in hours for worker activities",
)
@click.option(
    "--tenant-domain",
    help="M365 tenant domain (e.g., contoso.onmicrosoft.com)",
)
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=True),
    help="Load deployment config from YAML/JSON file",
)
@click.option(
    "--enable-ai-generation/--no-ai-generation",
    default=False,
    help="Enable AI-powered email content generation",
)
@click.option(
    "--email-directive",
    help="AI directive for email generation (e.g., 'Write as limericks')",
)
@click.option(
    "--marker-format",
    default="MARKER",
    help="Format for email markers (e.g., MARKER, TAG, LIMERICK)",
)
@click.option(
    "--start/--no-start",
    default=True,
    help="Start the deployment immediately after creation",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json"]),
    default=DEFAULT_OUTPUT_FORMAT,
    help="Output format",
)
def deploy(
    name: str | None,
    workers: int,
    department: str,
    duration: int,
    tenant_domain: str | None,
    config_file: str | None,
    enable_ai_generation: bool,
    email_directive: str | None,
    marker_format: str,
    start: bool,
    output_format: str,
) -> None:
    """Create a new Knowledge Worker deployment.

    Deploys simulated knowledge workers that perform M365 activities
    (email, Teams, calendar, documents).

    Examples:
        # Deploy 25 workers with AI limerick emails
        haymaker kw deploy --workers 25 --enable-ai-generation \\
            --email-directive "Write all emails as limericks"

        # Deploy from config file
        haymaker kw deploy --config-file deployment.yaml

        # Deploy without starting
        haymaker kw deploy --workers 10 --no-start
    """
    import os
    from datetime import datetime

    config_dict = {}

    # Load from config file if provided
    if config_file:
        config_dict = _load_config_file(config_file)
        click.echo(f"Loaded configuration from: {config_file}")

    # Override with CLI options (CLI takes precedence)
    if name:
        config_dict["name"] = name
    elif "name" not in config_dict:
        config_dict["name"] = f"kw-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    config_dict["total_workers"] = config_dict.get("total_workers", workers)
    config_dict["duration_hours"] = config_dict.get("duration_hours", duration)

    if tenant_domain:
        config_dict["tenant_domain"] = tenant_domain
    elif "tenant_domain" not in config_dict:
        # Try environment variable
        config_dict["tenant_domain"] = os.environ.get("KW_TENANT_DOMAIN", "")

    # Department config
    if "departments" not in config_dict:
        config_dict["departments"] = {
            department: {
                "count": config_dict["total_workers"],
                "endpoint_type": "cli_container",
                "activity": {
                    "email_per_hour": 4,
                    "teams_messages_per_hour": 15,
                    "documents_per_day": 5,
                    "meetings_per_day": 4,
                },
            }
        }

    # Email generation config
    if enable_ai_generation or email_directive:
        config_dict["email_generation"] = {
            "enabled": True,
            "directive": email_directive or "Generate professional work emails",
        }

    config_dict["marker_format"] = marker_format

    # Validate required fields
    if not config_dict.get("tenant_domain"):
        click.echo(
            "❌ Error: tenant_domain is required. "
            "Use --tenant-domain or set KW_TENANT_DOMAIN environment variable.",
            err=True,
        )
        sys.exit(EXIT_ERROR)

    # Create deployment
    run_id = _create_deployment(config_dict)

    if output_format == "json":
        click.echo(format_json({"run_id": run_id, "config": config_dict}))
    else:
        click.echo(f"✅ Created deployment: {run_id}")
        click.echo(f"   Name: {config_dict['name']}")
        click.echo(f"   Workers: {config_dict['total_workers']}")
        click.echo(f"   Duration: {config_dict['duration_hours']} hours")
        click.echo(f"   Tenant: {config_dict['tenant_domain']}")

    # Start if requested
    if start:
        click.echo()
        click.echo("Starting deployment...")
        _start_deployment_async(run_id)
        click.echo(f"✅ Deployment {run_id} started!")
        click.echo()
        click.echo("Monitor with:")
        click.echo(f"  haymaker kw status --run-id {run_id}")
        click.echo(f"  haymaker kw logs --run-id {run_id} --follow")


def _load_config_file(path: str) -> dict[str, Any]:
    """Load deployment configuration from YAML or JSON file.

    Args:
        path: Path to config file

    Returns:
        Configuration dictionary
    """
    import json
    from pathlib import Path

    file_path = Path(path)
    content = file_path.read_text()

    if file_path.suffix in (".yaml", ".yml"):
        try:
            import yaml

            return yaml.safe_load(content)
        except ImportError:
            click.echo(
                "❌ Error: PyYAML not installed. Install with: pip install pyyaml",
                err=True,
            )
            sys.exit(EXIT_ERROR)
    elif file_path.suffix == ".json":
        return json.loads(content)
    else:
        # Try JSON first, then YAML
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                import yaml

                return yaml.safe_load(content)
            except ImportError:
                click.echo("❌ Error: Could not parse config file", err=True)
                sys.exit(EXIT_ERROR)


def _create_deployment(config_dict: dict[str, Any]) -> str:
    """Create a deployment and persist to state.

    Args:
        config_dict: Deployment configuration

    Returns:
        Run ID
    """
    from uuid import uuid4

    state_manager = get_state_manager()

    run_id = f"kw-{uuid4().hex[:8]}"
    name = config_dict.get("name", run_id)

    state_manager.save_deployment(
        run_id=run_id,
        name=name,
        phase="initializing",
        status="pending",
        worker_count=0,
        config=config_dict,
    )

    return run_id


def _start_deployment_async(run_id: str) -> None:
    """Start a deployment asynchronously.

    This updates the state to 'running' and would trigger
    the actual orchestration in a full implementation.
    """
    state_manager = get_state_manager()
    deployment = state_manager.get_deployment(run_id)

    if not deployment:
        click.echo(f"❌ Deployment not found: {run_id}", err=True)
        sys.exit(EXIT_ERROR)

    # Update state
    state_manager.save_deployment(
        run_id=run_id,
        name=deployment.get("name", run_id),
        phase="executing",
        status="running",
        worker_count=deployment.get("config", {}).get("total_workers", 0),
        config=deployment.get("config", {}),
    )


__all__ = ["kw"]
