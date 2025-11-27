"""HTML report generator for HayMaker metrics."""

from datetime import datetime
from pathlib import Path

from haymaker_cli.client import SyncHayMakerClient
from haymaker_cli.models import AgentInfo, MetricsSummary, ResourceInfo


class ReportGenerator:
    """Generate HTML reports from orchestrator metrics.

    Uses the orchestrator's get_metrics() API to fetch aggregated data
    and renders it as HTML reports.

    Example:
        >>> client = SyncHayMakerClient("https://api.example.com", auth)
        >>> generator = ReportGenerator(client)
        >>> generator.generate_summary_report(...)  # doctest: +SKIP
    """

    def __init__(self, client: SyncHayMakerClient):
        """Initialize report generator.

        Args:
            client: Configured HayMaker client
        """
        self.client = client

    def generate_summary_report(
        self,
        metrics: MetricsSummary,
        agents: list[AgentInfo],
        resources: list[ResourceInfo],
        output_path: Path,
    ) -> None:
        """Generate summary report HTML.

        Args:
            metrics: Metrics summary from orchestrator
            agents: List of agent information
            resources: List of resource information
            output_path: Output file path
        """
        # Calculate additional stats
        running_agents = len([a for a in agents if a.status == "running"])
        completed_agents = len([a for a in agents if a.status == "completed"])
        failed_agents = len([a for a in agents if a.status == "failed"])

        active_resources = len([r for r in resources if r.status == "created"])
        deleted_resources = len([r for r in resources if r.status == "deleted"])

        # Group resources by type
        resources_by_type: dict[str, int] = {}
        for resource in resources:
            if resource.status == "created":
                resources_by_type[resource.type] = resources_by_type.get(resource.type, 0) + 1

        # Generate HTML
        html = self._render_summary_html(
            metrics=metrics,
            running_agents=running_agents,
            completed_agents=completed_agents,
            failed_agents=failed_agents,
            active_resources=active_resources,
            deleted_resources=deleted_resources,
            resources_by_type=resources_by_type,
        )

        # Write to file
        output_path.write_text(html)

    def generate_scenario_report(
        self,
        scenario_name: str,
        metrics: MetricsSummary,
        agents: list[AgentInfo],
        resources: list[ResourceInfo],
        output_path: Path,
    ) -> None:
        """Generate scenario-specific report HTML.

        Args:
            scenario_name: Name of the scenario
            metrics: Metrics summary from orchestrator
            agents: List of agent information for this scenario
            resources: List of resource information for this scenario
            output_path: Output file path
        """
        # Find scenario metrics
        scenario_metrics = None
        for sm in metrics.scenarios:
            if sm.scenario_name == scenario_name:
                scenario_metrics = sm
                break

        # Calculate stats
        running_agents = len([a for a in agents if a.status == "running"])
        completed_agents = len([a for a in agents if a.status == "completed"])
        failed_agents = len([a for a in agents if a.status == "failed"])

        active_resources = len([r for r in resources if r.status == "created"])

        # Group resources by type
        resources_by_type: dict[str, int] = {}
        for resource in resources:
            if resource.status == "created":
                resources_by_type[resource.type] = resources_by_type.get(resource.type, 0) + 1

        # Generate HTML
        html = self._render_scenario_html(
            scenario_name=scenario_name,
            scenario_metrics=scenario_metrics,
            metrics=metrics,
            running_agents=running_agents,
            completed_agents=completed_agents,
            failed_agents=failed_agents,
            active_resources=active_resources,
            resources_by_type=resources_by_type,
            agents=agents,
            resources=resources,
        )

        # Write to file
        output_path.write_text(html)

    def _render_summary_html(
        self,
        metrics: MetricsSummary,
        running_agents: int,
        completed_agents: int,
        failed_agents: int,
        active_resources: int,
        deleted_resources: int,
        resources_by_type: dict[str, int],
    ) -> str:
        """Render summary report HTML.

        Args:
            metrics: Metrics summary
            running_agents: Number of running agents
            completed_agents: Number of completed agents
            failed_agents: Number of failed agents
            active_resources: Number of active resources
            deleted_resources: Number of deleted resources
            resources_by_type: Resources grouped by type

        Returns:
            HTML string
        """
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Build scenario rows
        scenario_rows = ""
        for scenario in metrics.scenarios:
            success_rate = (
                (scenario.success_count / scenario.run_count * 100)
                if scenario.run_count > 0
                else 0.0
            )
            avg_duration = (
                f"{scenario.avg_duration_hours:.2f}h"
                if scenario.avg_duration_hours is not None
                else "N/A"
            )

            scenario_rows += f"""
                <tr>
                    <td>{scenario.scenario_name}</td>
                    <td>{scenario.run_count}</td>
                    <td>{scenario.success_count}</td>
                    <td>{scenario.fail_count}</td>
                    <td>{success_rate:.1f}%</td>
                    <td>{avg_duration}</td>
                </tr>
            """

        # Build resources by type rows
        resource_type_rows = ""
        for resource_type, count in sorted(resources_by_type.items()):
            resource_type_rows += f"""
                <tr>
                    <td>{resource_type}</td>
                    <td>{count}</td>
                </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HayMaker Summary Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        .header .subtitle {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .kpi-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .kpi-card .label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
        }}
        .kpi-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .kpi-card.success .value {{ color: #10b981; }}
        .kpi-card.danger .value {{ color: #ef4444; }}
        .kpi-card.warning .value {{ color: #f59e0b; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .section h2 {{
            margin-top: 0;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background-color: #f9fafb;
            font-weight: 600;
            color: #374151;
        }}
        tr:hover {{
            background-color: #f9fafb;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>HayMaker Summary Report</h1>
        <div class="subtitle">Period: {metrics.period} | Generated: {now}</div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">Total Executions</div>
            <div class="value">{metrics.total_executions}</div>
        </div>
        <div class="kpi-card success">
            <div class="label">Success Rate</div>
            <div class="value">{metrics.success_rate * 100:.1f}%</div>
        </div>
        <div class="kpi-card">
            <div class="label">Active Agents</div>
            <div class="value">{running_agents}</div>
        </div>
        <div class="kpi-card">
            <div class="label">Active Resources</div>
            <div class="value">{active_resources}</div>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card success">
            <div class="label">Completed Agents</div>
            <div class="value">{completed_agents}</div>
        </div>
        <div class="kpi-card danger">
            <div class="label">Failed Agents</div>
            <div class="value">{failed_agents}</div>
        </div>
        <div class="kpi-card">
            <div class="label">Total Resources</div>
            <div class="value">{metrics.total_resources}</div>
        </div>
        <div class="kpi-card">
            <div class="label">Deleted Resources</div>
            <div class="value">{deleted_resources}</div>
        </div>
    </div>

    <div class="section">
        <h2>Scenario Metrics</h2>
        <table>
            <thead>
                <tr>
                    <th>Scenario</th>
                    <th>Total Runs</th>
                    <th>Successful</th>
                    <th>Failed</th>
                    <th>Success Rate</th>
                    <th>Avg Duration</th>
                </tr>
            </thead>
            <tbody>
                {scenario_rows}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Resources by Type</h2>
        <table>
            <thead>
                <tr>
                    <th>Resource Type</th>
                    <th>Active Count</th>
                </tr>
            </thead>
            <tbody>
                {resource_type_rows}
            </tbody>
        </table>
    </div>

    <div class="footer">
        Generated by HayMaker CLI | {now}
    </div>
</body>
</html>"""

    def _render_scenario_html(
        self,
        scenario_name: str,
        scenario_metrics: any,
        metrics: MetricsSummary,
        running_agents: int,
        completed_agents: int,
        failed_agents: int,
        active_resources: int,
        resources_by_type: dict[str, int],
        agents: list[AgentInfo],
        resources: list[ResourceInfo],
    ) -> str:
        """Render scenario report HTML.

        Args:
            scenario_name: Scenario name
            scenario_metrics: Scenario-specific metrics
            metrics: Overall metrics summary
            running_agents: Number of running agents
            completed_agents: Number of completed agents
            failed_agents: Number of failed agents
            active_resources: Number of active resources
            resources_by_type: Resources grouped by type
            agents: List of agents for this scenario
            resources: List of resources for this scenario

        Returns:
            HTML string
        """
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Scenario metrics
        run_count = scenario_metrics.run_count if scenario_metrics else 0
        success_count = scenario_metrics.success_count if scenario_metrics else 0
        fail_count = scenario_metrics.fail_count if scenario_metrics else 0
        success_rate = (success_count / run_count * 100) if run_count > 0 else 0.0
        avg_duration = (
            f"{scenario_metrics.avg_duration_hours:.2f}h"
            if scenario_metrics and scenario_metrics.avg_duration_hours is not None
            else "N/A"
        )

        # Build agent rows
        agent_rows = ""
        for agent in sorted(agents, key=lambda a: a.started_at, reverse=True)[:20]:
            status_color = {
                "running": "#f59e0b",
                "completed": "#10b981",
                "failed": "#ef4444",
            }.get(agent.status, "#6b7280")

            completed_str = (
                agent.completed_at.strftime("%Y-%m-%d %H:%M:%S")
                if agent.completed_at
                else "Running..."
            )

            agent_rows += f"""
                <tr>
                    <td>{agent.agent_id}</td>
                    <td><span style="color: {status_color}; font-weight: bold;">{agent.status}</span></td>
                    <td>{agent.started_at.strftime("%Y-%m-%d %H:%M:%S")}</td>
                    <td>{completed_str}</td>
                    <td>{agent.progress or "-"}</td>
                </tr>
            """

        # Build resource rows
        resource_rows = ""
        for resource in sorted(resources, key=lambda r: r.created_at, reverse=True)[:50]:
            status_color = {
                "created": "#10b981",
                "deleted": "#6b7280",
                "error": "#ef4444",
            }.get(resource.status, "#6b7280")

            deleted_str = (
                resource.deleted_at.strftime("%Y-%m-%d %H:%M:%S")
                if resource.deleted_at
                else "-"
            )

            resource_rows += f"""
                <tr>
                    <td>{resource.name}</td>
                    <td>{resource.type}</td>
                    <td><span style="color: {status_color}; font-weight: bold;">{resource.status}</span></td>
                    <td>{resource.created_at.strftime("%Y-%m-%d %H:%M:%S")}</td>
                    <td>{deleted_str}</td>
                </tr>
            """

        # Build resources by type rows
        resource_type_rows = ""
        for resource_type, count in sorted(resources_by_type.items()):
            resource_type_rows += f"""
                <tr>
                    <td>{resource_type}</td>
                    <td>{count}</td>
                </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HayMaker Scenario Report - {scenario_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        .header .subtitle {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .kpi-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .kpi-card .label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
        }}
        .kpi-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .kpi-card.success .value {{ color: #10b981; }}
        .kpi-card.danger .value {{ color: #ef4444; }}
        .kpi-card.warning .value {{ color: #f59e0b; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .section h2 {{
            margin-top: 0;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background-color: #f9fafb;
            font-weight: 600;
            color: #374151;
        }}
        tr:hover {{
            background-color: #f9fafb;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Scenario Report: {scenario_name}</h1>
        <div class="subtitle">Period: {metrics.period} | Generated: {now}</div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">Total Runs</div>
            <div class="value">{run_count}</div>
        </div>
        <div class="kpi-card success">
            <div class="label">Success Rate</div>
            <div class="value">{success_rate:.1f}%</div>
        </div>
        <div class="kpi-card">
            <div class="label">Avg Duration</div>
            <div class="value">{avg_duration}</div>
        </div>
        <div class="kpi-card">
            <div class="label">Active Resources</div>
            <div class="value">{active_resources}</div>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card success">
            <div class="label">Successful Runs</div>
            <div class="value">{success_count}</div>
        </div>
        <div class="kpi-card danger">
            <div class="label">Failed Runs</div>
            <div class="value">{fail_count}</div>
        </div>
        <div class="kpi-card warning">
            <div class="label">Running Agents</div>
            <div class="value">{running_agents}</div>
        </div>
        <div class="kpi-card">
            <div class="label">Total Agents</div>
            <div class="value">{len(agents)}</div>
        </div>
    </div>

    <div class="section">
        <h2>Recent Agents (Last 20)</h2>
        <table>
            <thead>
                <tr>
                    <th>Agent ID</th>
                    <th>Status</th>
                    <th>Started At</th>
                    <th>Completed At</th>
                    <th>Progress</th>
                </tr>
            </thead>
            <tbody>
                {agent_rows}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Resources by Type</h2>
        <table>
            <thead>
                <tr>
                    <th>Resource Type</th>
                    <th>Active Count</th>
                </tr>
            </thead>
            <tbody>
                {resource_type_rows}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Recent Resources (Last 50)</h2>
        <table>
            <thead>
                <tr>
                    <th>Resource Name</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Created At</th>
                    <th>Deleted At</th>
                </tr>
            </thead>
            <tbody>
                {resource_rows}
            </tbody>
        </table>
    </div>

    <div class="footer">
        Generated by HayMaker CLI | {now}
    </div>
</body>
</html>"""
