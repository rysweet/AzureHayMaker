"""Output formatters for HayMaker CLI."""

import json
from datetime import datetime
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table
from rich.text import Text

from haymaker_cli.models import (
    AgentInfo,
    CleanupResponse,
    ExecutionResponse,
    ExecutionStatus,
    LogEntry,
    MetricsSummary,
    OrchestratorStatus,
    ResourceInfo,
)

console = Console()


def format_json(data: Any) -> str:
    """Format data as JSON.

    Args:
        data: Data to format (Pydantic model or dict)

    Returns:
        JSON string

    Example:
        >>> status = OrchestratorStatus(status="running", active_agents=5)
        >>> output = format_json(status)
        >>> "running" in output
        True
    """
    if hasattr(data, "model_dump"):
        # Pydantic model
        data_dict = data.model_dump(mode="json")
    elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
        # List of Pydantic models
        data_dict = [item.model_dump(mode="json") for item in data]
    else:
        data_dict = data

    return json.dumps(data_dict, indent=2, default=str)


def format_yaml(data: Any) -> str:
    """Format data as YAML.

    Args:
        data: Data to format (Pydantic model or dict)

    Returns:
        YAML string

    Example:
        >>> status = OrchestratorStatus(status="running", active_agents=5)
        >>> output = format_yaml(status)
        >>> "status: running" in output
        True
    """
    if hasattr(data, "model_dump"):
        # Pydantic model
        data_dict = data.model_dump(mode="json")
    elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
        # List of Pydantic models
        data_dict = [item.model_dump(mode="json") for item in data]
    else:
        data_dict = data

    return yaml.dump(data_dict, default_flow_style=False, sort_keys=False)


def format_datetime(dt: datetime | None) -> str:
    """Format datetime for display.

    Args:
        dt: Datetime to format

    Returns:
        Formatted datetime string or "(not set)"

    Example:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 11, 15, 10, 30, 0)
        >>> format_datetime(dt)
        '2025-11-15 10:30:00'
    """
    if dt is None:
        return "(not set)"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_status(status: str) -> Text:
    """Format status with color.

    Args:
        status: Status string

    Returns:
        Rich Text with color

    Example:
        >>> text = format_status("running")
        >>> text.plain
        'running'
    """
    colors = {
        "running": "blue",
        "completed": "green",
        "success": "green",
        "failed": "red",
        "error": "red",
        "queued": "yellow",
        "idle": "dim",
        "created": "green",
        "deleted": "dim",
    }

    color = colors.get(status.lower(), "white")
    return Text(status, style=color)


# Specific formatters for each data type


def format_orchestrator_status(status: OrchestratorStatus) -> str:
    """Format orchestrator status as table.

    Args:
        status: Orchestrator status

    Returns:
        Formatted table string
    """
    table = Table(title="Orchestrator Status", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Status", format_status(status.status))
    table.add_row("Current Run ID", status.current_run_id or "(none)")
    table.add_row("Phase", status.phase or "(none)")
    table.add_row("Active Agents", str(status.active_agents))
    table.add_row("Next Run", format_datetime(status.next_run))

    console.print(table)
    return ""


def format_metrics_summary(metrics: MetricsSummary) -> str:
    """Format metrics summary as table.

    Args:
        metrics: Metrics summary

    Returns:
        Formatted table string
    """
    # Summary table
    summary_table = Table(title=f"Execution Metrics (Period: {metrics.period})", show_header=False)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value")

    summary_table.add_row("Total Executions", str(metrics.total_executions))
    summary_table.add_row("Active Agents", str(metrics.active_agents))
    summary_table.add_row("Total Resources", str(metrics.total_resources))
    summary_table.add_row("Success Rate", f"{metrics.success_rate * 100:.1f}%")
    summary_table.add_row("Last Execution", format_datetime(metrics.last_execution))

    console.print(summary_table)

    # Scenario breakdown
    if metrics.scenarios:
        console.print()
        scenario_table = Table(title="Scenario Breakdown")
        scenario_table.add_column("Scenario", style="cyan")
        scenario_table.add_column("Total Runs", justify="right")
        scenario_table.add_column("Success", justify="right", style="green")
        scenario_table.add_column("Failed", justify="right", style="red")
        scenario_table.add_column("Success Rate", justify="right")
        scenario_table.add_column("Avg Duration", justify="right")

        for scenario in metrics.scenarios:
            success_rate = (
                scenario.success_count / scenario.run_count * 100 if scenario.run_count > 0 else 0
            )
            avg_duration = (
                f"{scenario.avg_duration_hours:.1f}h"
                if scenario.avg_duration_hours is not None
                else "N/A"
            )

            scenario_table.add_row(
                scenario.scenario_name,
                str(scenario.run_count),
                str(scenario.success_count),
                str(scenario.fail_count),
                f"{success_rate:.1f}%",
                avg_duration,
            )

        console.print(scenario_table)

    return ""


def format_agent_list(agents: list[AgentInfo]) -> str:
    """Format agent list as table.

    Args:
        agents: List of agents

    Returns:
        Formatted table string
    """
    if not agents:
        console.print("[dim]No agents found[/dim]")
        return ""

    table = Table(title=f"Agents ({len(agents)} total)")
    table.add_column("Agent ID", style="cyan")
    table.add_column("Scenario")
    table.add_column("Status")
    table.add_column("Started", justify="right")
    table.add_column("Completed", justify="right")
    table.add_column("Progress")

    for agent in agents:
        table.add_row(
            agent.agent_id,
            agent.scenario,
            format_status(agent.status),
            format_datetime(agent.started_at),
            format_datetime(agent.completed_at),
            agent.progress or "",
        )

    console.print(table)
    return ""


def format_resource_list(resources: list[ResourceInfo], group_by: str | None = None) -> str:
    """Format resource list as table.

    Args:
        resources: List of resources
        group_by: Optional grouping (type, scenario, execution_id)

    Returns:
        Formatted table string
    """
    if not resources:
        console.print("[dim]No resources found[/dim]")
        return ""

    if group_by == "type":
        # Group by resource type
        grouped: dict[str, list[ResourceInfo]] = {}
        for resource in resources:
            if resource.type not in grouped:
                grouped[resource.type] = []
            grouped[resource.type].append(resource)

        for resource_type, type_resources in grouped.items():
            table = Table(title=f"{resource_type} ({len(type_resources)} resources)")
            table.add_column("Name", style="cyan")
            table.add_column("Scenario")
            table.add_column("Status")
            table.add_column("Created", justify="right")

            for resource in type_resources:
                table.add_row(
                    resource.name,
                    resource.scenario,
                    format_status(resource.status),
                    format_datetime(resource.created_at),
                )

            console.print(table)
            console.print()

    else:
        # Single table
        table = Table(title=f"Resources ({len(resources)} total)")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Scenario")
        table.add_column("Status")
        table.add_column("Created", justify="right")

        for resource in resources:
            table.add_row(
                resource.name,
                resource.type,
                resource.scenario,
                format_status(resource.status),
                format_datetime(resource.created_at),
            )

        console.print(table)

    return ""


def format_execution_response(execution: ExecutionResponse) -> str:
    """Format execution response.

    Args:
        execution: Execution response

    Returns:
        Formatted string
    """
    table = Table(show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Execution ID", execution.execution_id)
    table.add_row("Status", format_status(execution.status))
    table.add_row("Status URL", execution.status_url)
    table.add_row("Created At", format_datetime(execution.created_at))

    console.print(table)
    return ""


def format_execution_status(execution: ExecutionStatus) -> str:
    """Format execution status.

    Args:
        execution: Execution status

    Returns:
        Formatted string
    """
    table = Table(title="Execution Status", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Execution ID", execution.execution_id)
    table.add_row("Scenario", execution.scenario_name)
    table.add_row("Status", format_status(execution.status))
    table.add_row("Created At", format_datetime(execution.created_at))
    table.add_row("Started At", format_datetime(execution.started_at))
    table.add_row("Completed At", format_datetime(execution.completed_at))

    if execution.agent_id:
        table.add_row("Agent ID", execution.agent_id)

    if execution.report_url:
        table.add_row("Report URL", execution.report_url)

    if execution.error:
        table.add_row("Error", Text(execution.error, style="red"))

    console.print(table)
    return ""


def format_cleanup_response(cleanup: CleanupResponse) -> str:
    """Format cleanup response.

    Args:
        cleanup: Cleanup response

    Returns:
        Formatted string
    """
    table = Table(title="Cleanup Status", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Cleanup ID", cleanup.cleanup_id)
    table.add_row("Status", format_status(cleanup.status))
    table.add_row("Resources Found", str(cleanup.resources_found))
    table.add_row("Resources Deleted", str(cleanup.resources_deleted))

    if cleanup.errors:
        table.add_row("Errors", str(len(cleanup.errors)))

    console.print(table)

    if cleanup.errors:
        console.print("\n[red]Errors:[/red]")
        for error in cleanup.errors:
            console.print(f"  - {error}")

    return ""


def format_log_entries(logs: list[LogEntry], follow: bool = False) -> str:
    """Format log entries with rich syntax highlighting.

    Args:
        logs: List of log entries
        follow: If True, use streaming format (no table borders)

    Returns:
        Formatted log output string
    """
    if not logs:
        if not follow:
            console.print("[dim]No logs found[/dim]")
        return ""

    if follow:
        # Streaming format (no borders, continuous output)
        level_colors = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red bold",
        }

        for log in logs:
            # Parse timestamp - handle both datetime objects and strings
            if isinstance(log.timestamp, str):
                try:
                    from datetime import datetime

                    # Convert UTC 'Z' suffix to timezone offset for ISO format parsing
                    timestamp_str: str = log.timestamp.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(timestamp_str)
                    time_str = dt.strftime("%H:%M:%S")
                except Exception:
                    time_str = log.timestamp[:8] if len(log.timestamp) >= 8 else log.timestamp
            else:
                time_str = log.timestamp.strftime("%H:%M:%S")

            level_color = level_colors.get(log.level, "white")

            # Print formatted log line
            console.print(
                f"[dim]{time_str}[/dim] [{level_color}]{log.level:8}[/{level_color}] {log.message}"
            )
    else:
        # Table format (default for tail mode)
        table = Table(title="Agent Logs", show_header=True, header_style="bold magenta")
        table.add_column("Timestamp", style="dim", width=20)
        table.add_column("Level", width=10)
        table.add_column("Message", width=80)

        level_colors = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red bold",
        }

        for log in logs:
            # Parse timestamp - handle both datetime objects and strings
            if isinstance(log.timestamp, str):
                timestamp_str = log.timestamp[:19] if len(log.timestamp) >= 19 else log.timestamp
            else:
                timestamp_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")

            level_style = level_colors.get(log.level, "white")

            table.add_row(timestamp_str, Text(log.level, style=level_style), log.message)

        console.print(table)

    return ""
