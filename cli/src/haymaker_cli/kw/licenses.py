"""E5 license management commands for Knowledge Worker CLI."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import click
from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient
from rich.console import Console
from rich.table import Table

console = Console()
logger = logging.getLogger(__name__)


def _get_graph_client():
    """Create Graph client from environment."""
    import os

    tenant_id = os.getenv("KW_TENANT_ID")
    app_id = os.getenv("KW_APP_ID")
    secret = os.getenv("KW_CLIENT_SECRET")

    if not all([tenant_id, app_id, secret]):
        console.print("[red]Missing credentials: KW_TENANT_ID, KW_APP_ID, KW_CLIENT_SECRET[/red]")
        raise click.Abort()

    credential = ClientSecretCredential(tenant_id, app_id, secret)
    return GraphServiceClient(credential)


@click.command()
@click.option("--show-users", is_flag=True, help="Show users with E5 licenses")
def list_licenses_command(show_users):
    """Show E5 license allocation and availability."""
    asyncio.run(_list_licenses(show_users))


async def _list_licenses(show_users):
    """Show E5 license status."""
    client = _get_graph_client()

    console.print("\n[bold]E5 License Status[/bold]\n")

    # Get E5 SKUs
    skus = await client.subscribed_skus.get()

    for sku in skus.value:
        if "E5" in sku.sku_part_number:
            total = sku.prepaid_units.enabled
            consumed = sku.consumed_units
            available = total - consumed

            table = Table()
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("SKU", sku.sku_part_number)
            table.add_row("Total", str(total))
            table.add_row("Consumed", str(consumed))
            table.add_row("Available", str(available))

            console.print(table)

            if show_users:
                console.print("\n[bold]Users with E5 Licenses:[/bold]\n")

                # Get all users
                users = await client.users.get()

                licensed_count = 0
                for user in users.value:
                    if user.assigned_licenses and len(user.assigned_licenses) > 0:
                        # Check if has E5 license
                        for license in user.assigned_licenses:
                            if str(license.sku_id) == str(sku.sku_id):
                                console.print(f"  • {user.user_principal_name}")
                                licensed_count += 1
                                break

                console.print(f"\n[cyan]Total users with {sku.sku_part_number}: {licensed_count}[/cyan]")


@click.command()
@click.option("--older-than", help="Reclaim from deployments older than (e.g., '24h', '7d')")
@click.option("--run-id", help="Reclaim from specific run ID")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
def reclaim_licenses_command(older_than, run_id, dry_run, yes):
    """Reclaim E5 licenses from old Knowledge Worker deployments."""
    asyncio.run(_reclaim_licenses(older_than, run_id, dry_run, yes))


async def _reclaim_licenses(older_than, run_id, dry_run, yes_flag):
    """Reclaim licenses by deleting old KW users."""
    client = _get_graph_client()

    # Get all KW users
    all_users = await client.users.get()
    kw_users = [u for u in all_users.value if u.user_principal_name and u.user_principal_name.startswith("kw-kw-")]

    if not kw_users:
        console.print("[yellow]No KW users found[/yellow]")
        return

    # Filter by age or run_id if specified
    users_to_delete = []

    if run_id:
        users_to_delete = [u for u in kw_users if run_id in u.user_principal_name]
    elif older_than:
        cutoff = _parse_time_delta(older_than)
        cutoff_date = datetime.now(UTC) - cutoff

        for user in kw_users:
            if user.created_date_time and user.created_date_time < cutoff_date:
                users_to_delete.append(user)
    else:
        users_to_delete = kw_users

    if not users_to_delete:
        console.print("[yellow]No users match criteria[/yellow]")
        return

    console.print(f"\n[bold]Found {len(users_to_delete)} KW users to delete:[/bold]\n")

    for user in users_to_delete[:10]:
        console.print(f"  • {user.user_principal_name}")

    if len(users_to_delete) > 10:
        console.print(f"  ... and {len(users_to_delete) - 10} more")

    if dry_run:
        console.print(f"\n[yellow]DRY RUN: Would delete {len(users_to_delete)} users[/yellow]")
        return

    if not yes_flag:
        confirm = click.confirm(f"\nDelete {len(users_to_delete)} users and reclaim licenses?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    console.print(f"\n[bold]Deleting {len(users_to_delete)} users...[/bold]\n")

    deleted = 0
    failed = 0

    for user in users_to_delete:
        try:
            await client.users.by_user_id(user.id).delete()
            console.print(f"[green]✓[/green] {user.user_principal_name}")
            deleted += 1
        except Exception as e:
            console.print(f"[red]✗[/red] {user.user_principal_name}: {str(e)[:60]}")
            failed += 1

    console.print(f"\n[bold green]✓ Deleted {deleted} users[/bold green]")
    if failed > 0:
        console.print(f"[bold red]✗ Failed: {failed}[/bold red]")

    console.print(f"\n[cyan]Reclaimed ~{deleted} E5 licenses[/cyan]")


def _parse_time_delta(time_str):
    """Parse time delta like '24h', '7d'."""
    if time_str.endswith("h"):
        hours = int(time_str[:-1])
        return timedelta(hours=hours)
    elif time_str.endswith("d"):
        days = int(time_str[:-1])
        return timedelta(days=days)
    else:
        raise ValueError(f"Invalid time format: {time_str}. Use '24h' or '7d'")
