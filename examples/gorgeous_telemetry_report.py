"""Gorgeous telemetry report with Rich library visualization."""

import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

console = Console()


async def demo_gorgeous_report():
    """Demo of gorgeous telemetry report."""

    # Simulated data (replace with real M365TelemetryCollector)
    data = {
        "run_id": "kw-demo123",
        "worker_count": 50,
        "duration_hours": 4.2,
        "total_emails": 1234,
        "total_calendar_events": 287,
        "total_teams_messages": 678,
        "total_documents": 143,
        "by_department": {
            "engineering": {"workers": 16, "emails": 420, "teams": 312},
            "legal": {"workers": 10, "emails": 285, "teams": 145},
            "hr": {"workers": 8, "emails": 198, "teams": 98},
            "finance": {"workers": 8, "emails": 165, "teams": 67},
            "sales": {"workers": 8, "emails": 166, "teams": 56},
        },
    }

    # Title panel
    console.print(
        Panel.fit(
            "[bold cyan]Knowledge Worker Telemetry Report[/bold cyan]\n"
            f"[dim]Run ID: {data['run_id']} | Duration: {data['duration_hours']:.1f} hours[/dim]",
            border_style="cyan",
        )
    )

    console.print()

    # Summary table
    summary = Table(title="Activity Summary", show_header=True, header_style="bold magenta")
    summary.add_column("Metric", style="cyan")
    summary.add_column("Total", justify="right", style="green")
    summary.add_column("Per Worker", justify="right", style="yellow")

    summary.add_row("Workers Deployed", str(data["worker_count"]), "-")
    summary.add_row(
        "Emails Sent",
        f"{data['total_emails']:,}",
        f"{data['total_emails'] / data['worker_count']:.1f}",
    )
    summary.add_row(
        "Teams Messages",
        f"{data['total_teams_messages']:,}",
        f"{data['total_teams_messages'] / data['worker_count']:.1f}",
    )
    summary.add_row(
        "Calendar Events",
        f"{data['total_calendar_events']:,}",
        f"{data['total_calendar_events'] / data['worker_count']:.1f}",
    )
    summary.add_row(
        "Documents Created",
        f"{data['total_documents']:,}",
        f"{data['total_documents'] / data['worker_count']:.1f}",
    )

    console.print(summary)
    console.print()

    # Department breakdown
    dept_table = Table(title="Department Breakdown", show_header=True)
    dept_table.add_column("Department", style="cyan")
    dept_table.add_column("Workers", justify="right")
    dept_table.add_column("Emails", justify="right", style="green")
    dept_table.add_column("Teams Msgs", justify="right", style="blue")

    for dept, stats in data["by_department"].items():
        dept_table.add_row(
            dept.title(), str(stats["workers"]), str(stats["emails"]), str(stats["teams"])
        )

    console.print(dept_table)
    console.print()

    # Activity tree
    tree = Tree("📊 [bold]Activity Breakdown[/bold]")
    tree.add("📧 Email Operations").add(f"[green]{data['total_emails']:,} messages sent[/green]")
    tree.add("📅 Calendar Events").add(
        f"[blue]{data['total_calendar_events']:,} events created[/blue]"
    )
    tree.add("💬 Teams Activity").add(
        f"[magenta]{data['total_teams_messages']:,} messages posted[/magenta]"
    )
    tree.add("📄 Documents").add(f"[yellow]{data['total_documents']:,} files created[/yellow]")

    console.print(tree)
    console.print()

    # Cost panel
    console.print(
        Panel(
            "[bold]Cost Analysis[/bold]\n\n"
            "Cloud PCs (5): [green]$155/month[/green]\n"
            "CLI Containers (25): [green]$50/month[/green]\n"
            "[bold cyan]Total: $205/month[/bold cyan]\n\n"
            "[dim]Savings vs all Cloud PCs: $725/month (78%)[/dim]",
            title="💰 Monthly Cost",
            border_style="green",
        )
    )


if __name__ == "__main__":
    asyncio.run(demo_gorgeous_report())
