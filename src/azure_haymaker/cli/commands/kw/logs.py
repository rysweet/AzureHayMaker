"""KW logs command - View deployment logs."""

import time
from typing import Any

import click

from ...constants import DEFAULT_LOG_LINES
from ...utils.state import get_deployment_or_exit, get_log_path


@click.command()
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
