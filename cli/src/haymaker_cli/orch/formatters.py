"""Output formatters for orchestrator CLI commands.

This module provides Rich-based formatting for Container App information,
including status displays, revision tables, replica listings, and health checks.

Public API:
    - format_container_app_status: Format app status with revisions table
    - format_replicas: Format replicas as Rich table
    - format_logs: Format log entries with colored output
    - format_health_results: Format health check results with suggestions

Example:
    >>> from haymaker_cli.orch.formatters import format_container_app_status
    >>> from haymaker_cli.orch.models import ContainerAppInfo, RevisionInfo
    >>> app = ContainerAppInfo(
    ...     name="my-app",
    ...     resource_group="my-rg",
    ...     location="eastus",
    ...     provisioning_state="Succeeded",
    ...     running_status="Running"
    ... )
    >>> revisions = [
    ...     RevisionInfo(
    ...         name="my-app--rev1",
    ...         active=True,
    ...         traffic_weight=100,
    ...         replicas_count=2,
    ...         health_state="Healthy"
    ...     )
    ... ]
    >>> format_container_app_status(app, revisions)  # doctest: +SKIP
"""

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from haymaker_cli.formatters import format_datetime, format_json, format_yaml
from haymaker_cli.orch.models import (
    ContainerAppInfo,
    HealthCheckResult,
    ReplicaInfo,
    RevisionInfo,
)

console = Console()


def format_container_app_status(app: ContainerAppInfo, revisions: list[RevisionInfo]) -> str:
    """Format Container App status with revisions table.

    Creates a comprehensive status display showing the app's endpoint, state,
    and active revisions with traffic routing information.

    Args:
        app: Container app information
        revisions: List of revision information

    Returns:
        Empty string (output is printed directly to console)

    Example:
        >>> app = ContainerAppInfo(
        ...     name="orch-dev",
        ...     resource_group="haymaker-rg",
        ...     location="eastus",
        ...     provisioning_state="Succeeded",
        ...     running_status="Running",
        ...     latest_revision_fqdn="orch-dev.example.io"
        ... )
        >>> revisions = []
        >>> format_container_app_status(app, revisions)  # doctest: +SKIP
        ''
    """
    # Create header section
    header_table = Table.grid(padding=(0, 2))
    header_table.add_column(style="cyan", justify="right")
    header_table.add_column()

    # Endpoint
    if app.latest_revision_fqdn:
        endpoint = f"https://{app.latest_revision_fqdn}"
        header_table.add_row("Endpoint:", endpoint)

    # Status
    status_text = _format_status_badge(app.provisioning_state, app.running_status)
    header_table.add_row("Status:", status_text)

    # Location
    header_table.add_row("Location:", app.location)

    # Ingress
    if app.ingress_enabled:
        ingress_type = "External" if app.external_ingress else "Internal"
        port_info = f" (port {app.target_port})" if app.target_port else ""
        header_table.add_row("Ingress:", f"{ingress_type}{port_info}")

    # Scaling
    header_table.add_row("Replicas:", f"{app.min_replicas}-{app.max_replicas}")

    # Print header
    console.print(Panel(header_table, title=f"[bold]{app.name}[/bold]", border_style="blue"))

    # Active revisions table
    if revisions:
        console.print()
        revisions_table = Table(title="Active Revisions")
        revisions_table.add_column("NAME", style="cyan", no_wrap=True)
        revisions_table.add_column("TRAFFIC", justify="right")
        revisions_table.add_column("REPLICAS", justify="right")
        revisions_table.add_column("HEALTH")
        revisions_table.add_column("CREATED", justify="right")

        for revision in revisions:
            # Format traffic percentage
            traffic = f"{revision.traffic_weight}%" if revision.traffic_weight else "0%"

            # Format replicas count
            replicas = str(revision.replicas_count) if revision.replicas_count else "0"

            # Format health state
            health = _format_health_state(revision.health_state)

            # Format created timestamp
            created = format_datetime(revision.created_at)

            revisions_table.add_row(
                revision.name,
                traffic,
                replicas,
                health,
                created,
            )

        console.print(revisions_table)
    else:
        console.print("\n[dim]No active revisions found[/dim]")

    return ""


def format_replicas(replicas: list[ReplicaInfo]) -> str:
    """Format replicas as Rich table.

    Displays all replicas for a revision with their running state and creation time.

    Args:
        replicas: List of replica information

    Returns:
        Empty string (output is printed directly to console)

    Example:
        >>> replicas = [
        ...     ReplicaInfo(
        ...         name="replica-1",
        ...         running_state="Running",
        ...         created_at=None
        ...     )
        ... ]
        >>> format_replicas(replicas)  # doctest: +SKIP
        ''
    """
    if not replicas:
        console.print("[dim]No replicas found[/dim]")
        return ""

    table = Table(title=f"Replicas ({len(replicas)} total)")
    table.add_column("NAME", style="cyan")
    table.add_column("STATE")
    table.add_column("CREATED", justify="right")
    table.add_column("DETAILS")

    for replica in replicas:
        # Format running state
        state = _format_running_state(replica.running_state)

        # Format created timestamp
        created = format_datetime(replica.created_at)

        # Details
        details = replica.running_state_details or ""

        table.add_row(
            replica.name,
            state,
            created,
            details,
        )

    console.print(table)
    return ""


def format_logs(logs: list[dict], timestamps: bool = True) -> str:
    """Format log entries with colored output.

    Displays log entries with optional timestamps, colored by severity level.
    Supports standard Python logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Args:
        logs: List of log entries (each with 'timestamp', 'level', 'message' keys)
        timestamps: Whether to show timestamps (default: True)

    Returns:
        Empty string (output is printed directly to console)

    Example:
        >>> from datetime import datetime
        >>> logs = [
        ...     {
        ...         "timestamp": datetime.now(),
        ...         "level": "INFO",
        ...         "message": "Container started"
        ...     },
        ...     {
        ...         "timestamp": datetime.now(),
        ...         "level": "ERROR",
        ...         "message": "Connection failed"
        ...     }
        ... ]
        >>> format_logs(logs)  # doctest: +SKIP
        ''
    """
    if not logs:
        console.print("[dim]No logs found[/dim]")
        return ""

    level_colors = {
        "DEBUG": "dim",
        "INFO": "white",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red bold",
    }

    for log in logs:
        # Extract log fields
        timestamp = log.get("timestamp")
        level = log.get("level", "INFO")
        message = log.get("message", "")

        # Build output line
        parts = []

        if timestamps and timestamp:
            if isinstance(timestamp, datetime):
                ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                ts_str = str(timestamp)
            parts.append(f"[dim]{ts_str}[/dim]")

        level_style = level_colors.get(level, "white")
        parts.append(f"[{level_style}]{level:8}[/{level_style}]")
        parts.append(message)

        console.print(" ".join(parts))

    return ""


def format_health_results(results: list[dict], verbose: bool = False) -> str:
    """Format health check results with suggestions.

    Displays health check results in a color-coded table with actionable
    suggestions for any failed checks. Uses green (pass), yellow (warning),
    and red (fail) for visual clarity.

    Args:
        results: List of health check results with keys:
            - check_name: Name of the check
            - status: One of "PASS", "WARN", "FAIL"
            - message: Brief status message
            - details: Optional detailed information (shown if verbose)
            - suggestions: Optional list of actionable suggestions
        verbose: Show detailed information for each check (default: False)

    Returns:
        Empty string (output is printed directly to console)

    Example:
        >>> results = [
        ...     {
        ...         "check_name": "Container App Status",
        ...         "status": "PASS",
        ...         "message": "App is running",
        ...         "suggestions": []
        ...     },
        ...     {
        ...         "check_name": "HTTP Health Endpoint",
        ...         "status": "FAIL",
        ...         "message": "Connection refused",
        ...         "suggestions": ["Check if ingress is enabled", "Verify container port"]
        ...     }
        ... ]
        >>> format_health_results(results)  # doctest: +SKIP
        ''
    """
    if not results:
        console.print("[dim]No health check results[/dim]")
        return ""

    # Build results table
    table = Table(title="Health Check Results")
    table.add_column("CHECK", style="cyan")
    table.add_column("STATUS", justify="center")
    table.add_column("MESSAGE")

    all_suggestions = []

    for result in results:
        check_name = result.get("check_name", "Unknown")
        status = result.get("status", "UNKNOWN")
        message = result.get("message", "")
        details = result.get("details", {})
        suggestions = result.get("suggestions", [])

        # Format status with icon and color
        status_text = _format_check_status(status)

        # Add row
        table.add_row(check_name, status_text, message)

        # Show details if verbose
        if verbose and details:
            for key, value in details.items():
                table.add_row(f"  {key}", "", str(value))

        # Collect suggestions from failed checks
        if status == "FAIL" and suggestions:
            all_suggestions.extend(suggestions)

    console.print(table)

    # Show suggestions if any
    if all_suggestions:
        console.print("\n[yellow]Suggestions:[/yellow]")
        for suggestion in all_suggestions:
            console.print(f"  • {suggestion}")

    return ""


def format_health_check_result(result: HealthCheckResult, verbose: bool = False) -> str:
    """Format a single HealthCheckResult model.

    Converts the HealthCheckResult model to the format expected by
    format_health_results and displays it.

    Args:
        result: Health check result model
        verbose: Show detailed information (default: False)

    Returns:
        Empty string (output is printed directly to console)

    Example:
        >>> from datetime import datetime
        >>> result = HealthCheckResult(
        ...     app_name="my-app",
        ...     status="healthy",
        ...     provisioning_state="Succeeded",
        ...     running_status="Running",
        ...     total_replicas=2,
        ...     healthy_replicas=2
        ... )
        >>> format_health_check_result(result)  # doctest: +SKIP
        ''
    """
    # Convert to health check result format
    checks = []

    # Overall status check
    status_map = {
        "healthy": "PASS",
        "degraded": "WARN",
        "unhealthy": "FAIL",
        "unknown": "FAIL",
    }

    status = status_map.get(result.status, "FAIL")
    message = f"{result.provisioning_state}"
    if result.running_status:
        message += f" / {result.running_status}"

    checks.append({
        "check_name": "Container App Status",
        "status": status,
        "message": message,
        "details": result.details if verbose else {},
        "suggestions": _generate_suggestions(result),
    })

    # Replica health check
    if result.total_replicas > 0:
        if result.healthy_replicas == result.total_replicas:
            replica_status = "PASS"
            replica_msg = f"All {result.total_replicas} replicas healthy"
        elif result.healthy_replicas > 0:
            replica_status = "WARN"
            replica_msg = f"{result.healthy_replicas}/{result.total_replicas} replicas healthy"
        else:
            replica_status = "FAIL"
            replica_msg = "No healthy replicas"

        checks.append({
            "check_name": "Replica Health",
            "status": replica_status,
            "message": replica_msg,
            "details": {},
            "suggestions": [],
        })

    # Endpoint check
    if result.fqdn:
        checks.append({
            "check_name": "Endpoint",
            "status": "PASS",
            "message": f"https://{result.fqdn}",
            "details": {},
            "suggestions": [],
        })

    # Display any errors
    if result.errors:
        for error in result.errors:
            checks.append({
                "check_name": "Error",
                "status": "FAIL",
                "message": error,
                "details": {},
                "suggestions": [],
            })

    # Display any warnings
    if result.warnings:
        for warning in result.warnings:
            checks.append({
                "check_name": "Warning",
                "status": "WARN",
                "message": warning,
                "details": {},
                "suggestions": [],
            })

    return format_health_results(checks, verbose=verbose)


# Helper functions

def _format_status_badge(provisioning_state: str, running_status: str | None) -> Text:
    """Format provisioning and running status as colored badge.

    Args:
        provisioning_state: Provisioning state (Succeeded, Failed, etc.)
        running_status: Running status (Running, Stopped, etc.)

    Returns:
        Rich Text with appropriate color
    """
    if provisioning_state == "Succeeded" and running_status == "Running":
        return Text("Running", style="green")
    elif provisioning_state == "Failed":
        return Text("Failed", style="red")
    elif provisioning_state == "Succeeded" and running_status != "Running":
        return Text(running_status or "Stopped", style="yellow")
    else:
        return Text(provisioning_state, style="yellow")


def _format_health_state(health_state: str | None) -> Text:
    """Format health state with color.

    Args:
        health_state: Health state (Healthy, Unhealthy, None)

    Returns:
        Rich Text with appropriate color
    """
    if health_state == "Healthy":
        return Text("Healthy", style="green")
    elif health_state == "Unhealthy":
        return Text("Unhealthy", style="red")
    elif health_state is None or health_state == "None":
        return Text("None", style="dim")
    else:
        return Text(health_state, style="yellow")


def _format_running_state(running_state: str | None) -> Text:
    """Format running state with color.

    Args:
        running_state: Running state (Running, NotRunning, Unknown)

    Returns:
        Rich Text with appropriate color
    """
    if running_state == "Running":
        return Text("Running", style="green")
    elif running_state == "NotRunning":
        return Text("NotRunning", style="red")
    elif running_state is None:
        return Text("Unknown", style="dim")
    else:
        return Text(running_state, style="yellow")


def _format_check_status(status: str) -> Text:
    """Format check status with icon and color.

    Args:
        status: Status string (PASS, WARN, FAIL)

    Returns:
        Rich Text with icon and color
    """
    if status == "PASS":
        return Text("✓ PASS", style="green")
    elif status == "WARN":
        return Text("⚠ WARN", style="yellow")
    elif status == "FAIL":
        return Text("✗ FAIL", style="red")
    else:
        return Text(f"? {status}", style="dim")


def _generate_suggestions(result: HealthCheckResult) -> list[str]:
    """Generate actionable suggestions based on health check result.

    Args:
        result: Health check result

    Returns:
        List of suggestion strings
    """
    suggestions = []

    if result.status == "unhealthy":
        if result.provisioning_state == "Failed":
            suggestions.append("Check container logs for startup errors")
            suggestions.append("Verify container image is accessible")
            suggestions.append("Review resource limits and quotas")

        if result.running_status != "Running":
            suggestions.append("Check if the app was manually stopped")
            suggestions.append("Review scaling configuration")

        if result.total_replicas == 0:
            suggestions.append("Scale up the app (min_replicas may be 0)")
            suggestions.append("Check for recent deployment failures")

        if result.healthy_replicas == 0 and result.total_replicas > 0:
            suggestions.append("Check container health probes")
            suggestions.append("Review container logs for runtime errors")
            suggestions.append("Verify dependencies (databases, services) are accessible")

    elif result.status == "degraded":
        if result.healthy_replicas < result.total_replicas:
            suggestions.append("Some replicas are unhealthy - check logs for errors")
            suggestions.append("Consider restarting the revision")

    return suggestions


# Re-export common formatters for convenience
__all__ = [
    "format_container_app_status",
    "format_replicas",
    "format_logs",
    "format_health_results",
    "format_health_check_result",
    "format_json",
    "format_yaml",
]
