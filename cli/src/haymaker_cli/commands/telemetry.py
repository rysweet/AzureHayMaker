"""Telemetry collection commands."""

import asyncio
import logging
from pathlib import Path

import click
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


def get_storage_path(storage_dir: str | None) -> Path:
    """Get telemetry storage path from option or default with validation.

    Args:
        storage_dir: Optional storage directory path

    Returns:
        Validated storage path

    Raises:
        ValueError: If path is outside user's home directory
    """
    if storage_dir:
        storage_path = Path(storage_dir).resolve()

        # Ensure storage is within home directory for security
        try:
            storage_path.relative_to(Path.home())
        except ValueError:
            raise ValueError(
                f"Storage directory must be within home directory. Got: {storage_path}"
            )

        logger.info(f"Storage path validated: {storage_path}")
        return storage_path

    return Path.home() / ".haymaker" / "telemetry"


@click.group()
def telemetry():
    """Manage telemetry collection."""


@telemetry.command()
@click.option("--interval", default=300, type=int, help="Collection interval in seconds")
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def start(interval: int, storage_dir: str | None):
    """Start background telemetry collection."""
    try:
        from haymaker_cli.client import HayMakerClient
        from haymaker_cli.config import load_cli_config
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Load config
        config = load_cli_config()

        # Setup storage
        storage = TelemetryStorage(get_storage_path(storage_dir))

        # Create API client
        client = HayMakerClient(base_url=config.endpoint)

        # Create collector
        collector = TelemetryCollector(
            api_client=client,
            storage=storage,
            interval_seconds=interval,
        )

        # Start collection
        console.print("[cyan]Starting telemetry collection...[/cyan]")
        console.print(f"[dim]Interval: {interval}s[/dim]")
        console.print(f"[dim]Storage: {storage.storage_path}[/dim]")

        asyncio.run(collector.start_background())

        console.print("[green]Telemetry collection started![/green]")

    except Exception as e:
        logger.error(f"Telemetry command error: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@telemetry.command()
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def stop(storage_dir: str | None):
    """Stop background telemetry collection."""
    try:
        # Find and remove lock file
        lock_file = get_storage_path(storage_dir) / "telemetry.lock"

        if lock_file.exists():
            lock_file.unlink()
            console.print("[green]Telemetry collection stopped![/green]")
        else:
            console.print("[yellow]No telemetry collection running[/yellow]")

    except Exception as e:
        logger.error(f"Telemetry command error: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@telemetry.command()
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def status(storage_dir: str | None):
    """Show telemetry collection status."""
    try:
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Setup storage
        storage = TelemetryStorage(get_storage_path(storage_dir))

        # Check lock file
        lock_file = storage.storage_path / "telemetry.lock"
        is_running = lock_file.exists()

        console.print("[cyan]Telemetry Status[/cyan]\n")
        console.print(f"  Status: {'[green]Running[/green]' if is_running else '[dim]Stopped[/dim]'}")
        console.print(f"  Storage: {storage.storage_path}")

        # Get last sync time
        last_sync = storage.get_last_sync_time()
        if last_sync:
            console.print(f"  Last Sync: {last_sync}")
        else:
            console.print("  Last Sync: Never")

        # Get record counts
        executions = storage.load_executions()
        agents = storage.load_agents()
        console.print(f"\n  Records:")
        console.print(f"    Executions: {len(executions)}")
        console.print(f"    Agents: {len(agents)}")

    except Exception as e:
        logger.error(f"Telemetry command error: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@telemetry.command()
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def collect(storage_dir: str | None):
    """Manually trigger telemetry collection."""
    try:
        from haymaker_cli.client import HayMakerClient
        from haymaker_cli.config import load_cli_config
        from haymaker_cli.telemetry.collector import TelemetryCollector
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Load config
        config = load_cli_config()

        # Setup storage
        storage = TelemetryStorage(get_storage_path(storage_dir))

        # Create API client
        client = HayMakerClient(base_url=config.endpoint)

        # Create collector
        collector = TelemetryCollector(
            api_client=client,
            storage=storage,
        )

        # Collect once
        console.print("[cyan]Collecting telemetry data...[/cyan]")

        result = asyncio.run(collector.collect_once())

        if result.success:
            console.print("[green]Collection successful![/green]\n")
            console.print(f"  Executions: {result.executions_collected}")
            console.print(f"  Agents: {result.agents_collected}")
            console.print(f"  Resources: {result.resources_collected}")
            console.print(f"  Time: {result.collection_time_seconds:.2f}s")
        else:
            console.print(f"[red]Collection failed:[/red] {result.error_message}")

    except Exception as e:
        logger.error(f"Telemetry command error: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@telemetry.command()
@click.option("--days", default=30, type=int, help="Keep data newer than N days")
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def prune(days: int, storage_dir: str | None):
    """Prune old telemetry data."""
    try:
        from haymaker_cli.telemetry.storage import TelemetryStorage

        # Setup storage
        storage = TelemetryStorage(get_storage_path(storage_dir))

        console.print(f"[cyan]Pruning data older than {days} days...[/cyan]")

        # Prune data
        result = storage.prune_old_data(days)

        total_pruned = sum(result.values())
        console.print(f"[green]Pruned {total_pruned} old records[/green]")
        console.print(f"  Executions: {result['executions']}")
        console.print(f"  Agents: {result['agents']}")
        console.print(f"  Resources: {result['resources']}")

    except Exception as e:
        logger.error(f"Telemetry command error: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@telemetry.command()
@click.option("--storage-dir", type=click.Path(), help="Telemetry storage directory")
def config(storage_dir: str | None):
    """Show telemetry configuration."""
    try:
        from haymaker_cli.telemetry.config import TelemetryConfig

        # Load config
        config_file = Path.home() / ".haymaker" / "telemetry_config.yaml"

        if config_file.exists():
            telemetry_config = TelemetryConfig.load_from_file(config_file)
        else:
            telemetry_config = TelemetryConfig()

        console.print("[cyan]Telemetry Configuration[/cyan]\n")
        console.print(f"  Collection Interval: {telemetry_config.collection_interval_seconds}s")
        console.print(f"  Batch Size: {telemetry_config.batch_size}")
        console.print(f"  Retention Days: {telemetry_config.retention_days}")
        console.print(f"  Max File Size: {telemetry_config.max_file_size_mb}MB")
        console.print(f"  Storage Path: {telemetry_config.storage_path}")

    except Exception as e:
        logger.error(f"Telemetry command error: {e}", exc_info=True)
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
