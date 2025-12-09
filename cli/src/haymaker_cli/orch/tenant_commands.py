"""CLI commands for multi-tenant orchestration management.

This module provides CLI commands for managing target tenants in cross-tenant
orchestration, allowing users to add, list, update, and remove tenant configurations.

Commands:
    - haymaker orch tenant add: Add a new target tenant
    - haymaker orch tenant list: List all configured tenants
    - haymaker orch tenant status: Show status for specific tenant
    - haymaker orch tenant update: Update tenant configuration
    - haymaker orch tenant remove: Remove tenant from configuration

Example:
    >>> # Add a new tenant
    >>> haymaker orch tenant add prod-east \\
    ...     --tenant-id 12345678-1234-1234-1234-123456789012 \\
    ...     --subscription-id 87654321-4321-4321-4321-210987654321 \\
    ...     --resource-group haymaker-prod-rg

    >>> # List all tenants
    >>> haymaker orch tenant list

    >>> # Show tenant status
    >>> haymaker orch tenant status prod-east

    >>> # Update tenant
    >>> haymaker orch tenant update prod-east --enabled

    >>> # Remove tenant
    >>> haymaker orch tenant remove prod-east --confirm
"""

import sys

import click
from rich.console import Console
from rich.table import Table

from haymaker_cli.orch.formatters import format_json, format_yaml
from haymaker_cli.orch.tenant_config_utils import (
    TenantConfigError,
    add_tenant_to_config,
    get_tenant_config_path,
    list_tenant_configs,
    load_tenant_config,
    remove_tenant_from_config,
    update_tenant_in_config,
)

console = Console()


def format_tenant_list(tenants: list[dict], format_type: str = "table") -> None:
    """Format and display tenant list.

    Args:
        tenants: List of tenant configurations
        format_type: Output format ("table", "json", "yaml")
    """
    if format_type == "json":
        console.print(format_json(tenants))
    elif format_type == "yaml":
        console.print(format_yaml(tenants))
    else:  # table
        if not tenants:
            console.print("[dim]No tenants configured[/dim]")
            return

        table = Table(title=f"Configured Tenants ({len(tenants)} total)")
        table.add_column("Name", style="cyan")
        table.add_column("Display Name")
        table.add_column("Tenant ID", style="dim")
        table.add_column("Region")
        table.add_column("Scenarios", justify="right")
        table.add_column("Status")

        for tenant in tenants:
            status = "[green]Enabled[/green]" if tenant.get("enabled", True) else "[dim]Disabled[/dim]"
            scenario_count = len(tenant.get("scenarios", []))

            table.add_row(
                tenant["name"],
                tenant.get("display_name", tenant["name"]),
                tenant["tenant_id"][:8] + "...",  # Abbreviated
                tenant.get("region", "N/A"),
                str(scenario_count),
                status,
            )

        console.print(table)


def format_tenant_status(tenant: dict, format_type: str = "table") -> None:
    """Format and display detailed tenant status.

    Args:
        tenant: Tenant configuration
        format_type: Output format ("table", "json", "yaml")
    """
    if format_type == "json":
        console.print(format_json(tenant))
    elif format_type == "yaml":
        console.print(format_yaml(tenant))
    else:  # table
        table = Table(title=f"Tenant: {tenant['name']}", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Name", tenant["name"])
        table.add_row("Display Name", tenant.get("display_name", tenant["name"]))
        if tenant.get("description"):
            table.add_row("Description", tenant["description"])

        table.add_row("Tenant ID", tenant["tenant_id"])
        table.add_row("Subscription ID", tenant["subscription_id"])
        table.add_row("Region", tenant.get("region", "N/A"))
        table.add_row("Resource Group", tenant.get("resource_group_name", "N/A"))

        status = "[green]Enabled[/green]" if tenant.get("enabled", True) else "[dim]Disabled[/dim]"
        table.add_row("Status", status)

        # Scenarios
        scenarios = tenant.get("scenarios", [])
        if scenarios:
            table.add_row("Scenarios", ", ".join(scenarios))
        else:
            table.add_row("Scenarios", "[dim](none configured)[/dim]")

        # Schedule
        schedule = tenant.get("schedule")
        if schedule and schedule.get("cron"):
            table.add_row("Schedule", schedule["cron"])
            if schedule.get("timezone"):
                table.add_row("Timezone", schedule["timezone"])

        # Limits
        limits = tenant.get("limits", {})
        if limits:
            max_workers = limits.get("max_knowledge_workers", "unlimited")
            max_concurrent = limits.get("max_concurrent_scenarios", "unlimited")
            table.add_row("Max Workers", str(max_workers))
            table.add_row("Max Concurrent Scenarios", str(max_concurrent))

        console.print(table)


@click.group(name="tenant")
def tenant_group():
    """Manage multi-tenant orchestration configuration.

    Commands for adding, listing, updating, and removing target tenant
    configurations for cross-tenant orchestration.

    Example:
        haymaker orch tenant add prod-east --tenant-id ... --subscription-id ...
        haymaker orch tenant list
        haymaker orch tenant status prod-east
    """


@tenant_group.command(name="add")
@click.argument("tenant_name")
@click.option("--tenant-id", required=True, help="Azure tenant ID (UUID)")
@click.option("--subscription-id", required=True, help="Azure subscription ID (UUID)")
@click.option("--region", default="eastus", help="Azure region (default: eastus)")
@click.option("--resource-group", required=True, help="Resource group name")
@click.option(
    "--keyvault-prefix",
    required=True,
    help="Key Vault secret prefix for tenant credentials"
)
@click.option("--display-name", help="Human-readable display name")
@click.option("--description", help="Tenant description")
@click.option(
    "--scenarios",
    multiple=True,
    help="Scenario identifiers (can be specified multiple times)"
)
@click.option("--schedule", help="Cron schedule expression (e.g., '0 */6 * * *')")
@click.option("--enabled/--disabled", default=True, help="Enable tenant (default: enabled)")
@click.option(
    "--max-workers",
    type=int,
    help="Maximum knowledge workers"
)
@click.option(
    "--max-concurrent",
    type=int,
    help="Maximum concurrent scenarios"
)
def add_tenant(
    tenant_name,
    tenant_id,
    subscription_id,
    region,
    resource_group,
    keyvault_prefix,
    display_name,
    description,
    scenarios,
    schedule,
    enabled,
    max_workers,
    max_concurrent,
):
    """Add a new target tenant to configuration.

    Creates a new tenant configuration with the specified settings. The tenant
    will be added to the meta-orchestrator configuration file.

    Example:
        haymaker orch tenant add prod-east \\
            --tenant-id 12345678-1234-1234-1234-123456789012 \\
            --subscription-id 87654321-4321-4321-4321-210987654321 \\
            --region eastus \\
            --resource-group haymaker-prod-rg \\
            --keyvault-prefix prod-east \\
            --scenarios compute-01 --scenarios storage-02 \\
            --schedule "0 */6 * * *" \\
            --max-workers 100

    Required:
        TENANT_NAME: Unique identifier for the tenant (alphanumeric + hyphens)
        --tenant-id: Azure tenant UUID
        --subscription-id: Azure subscription UUID
        --resource-group: Resource group name for deployments
        --keyvault-prefix: Key Vault secret prefix for credentials

    Optional:
        --region: Azure region (default: eastus)
        --display-name: Human-readable name
        --description: Tenant description
        --scenarios: Scenario identifiers to execute
        --schedule: Cron schedule expression
        --enabled/--disabled: Enable tenant (default: enabled)
        --max-workers: Maximum knowledge workers limit
        --max-concurrent: Maximum concurrent scenarios limit
    """
    try:
        # Build tenant configuration
        tenant_config = {
            "name": tenant_name,
            "display_name": display_name or tenant_name,
            "tenant_id": tenant_id,
            "subscription_id": subscription_id,
            "region": region,
            "resource_group_name": resource_group,
            "credentials": {
                "keyvault_secret_prefix": keyvault_prefix
            },
            "enabled": enabled,
            "scenarios": list(scenarios) if scenarios else [],
        }

        if description:
            tenant_config["description"] = description

        if schedule:
            tenant_config["schedule"] = {
                "cron": schedule,
                "enabled": True
            }

        # Build limits if specified
        limits = {}
        if max_workers is not None:
            limits["max_knowledge_workers"] = max_workers
        if max_concurrent is not None:
            limits["max_concurrent_scenarios"] = max_concurrent
        if limits:
            tenant_config["limits"] = limits

        # Add tenant to configuration
        add_tenant_to_config(tenant_config)

        console.print(f"[green]✓[/green] Tenant '{tenant_name}' added successfully")
        console.print(f"[dim]Configuration saved to: {get_tenant_config_path()}[/dim]")

        # Show created tenant details
        console.print()
        format_tenant_status(tenant_config, "table")

    except TenantConfigError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", err=True)
        sys.exit(1)


@tenant_group.command(name="list")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format"
)
@click.option(
    "--filter-enabled/--filter-all",
    default=False,
    help="Show only enabled tenants"
)
def list_tenants(output_format, filter_enabled):
    """List all configured tenants.

    Displays a table of all configured target tenants with their basic
    information including name, tenant ID, region, and status.

    Example:
        # List all tenants
        haymaker orch tenant list

        # List only enabled tenants
        haymaker orch tenant list --filter-enabled

        # Output as JSON
        haymaker orch tenant list --format json
    """
    try:
        tenants = list_tenant_configs()

        if filter_enabled:
            tenants = [t for t in tenants if t.get("enabled", True)]

        format_tenant_list(tenants, output_format)

        if output_format == "table":
            config_path = get_tenant_config_path()
            console.print(f"\n[dim]Configuration: {config_path}[/dim]")

    except TenantConfigError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", err=True)
        sys.exit(1)


@tenant_group.command(name="status")
@click.argument("tenant_name")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format"
)
def tenant_status(tenant_name, output_format):
    """Show detailed status for a specific tenant.

    Displays comprehensive information about a tenant including its
    configuration, enabled scenarios, schedule, and resource limits.

    Example:
        haymaker orch tenant status prod-east
        haymaker orch tenant status prod-east --format json
    """
    try:
        config = load_tenant_config()
        tenants = config.get("target_tenants", [])

        tenant = next((t for t in tenants if t["name"] == tenant_name), None)
        if not tenant:
            console.print(f"[red]Error:[/red] Tenant '{tenant_name}' not found", err=True)
            console.print("\n[dim]Available tenants:[/dim]")
            for t in tenants:
                console.print(f"  - {t['name']}")
            sys.exit(1)

        format_tenant_status(tenant, output_format)

    except TenantConfigError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", err=True)
        sys.exit(1)


@tenant_group.command(name="update")
@click.argument("tenant_name")
@click.option("--display-name", help="Update display name")
@click.option("--description", help="Update description")
@click.option("--region", help="Update region")
@click.option("--resource-group", help="Update resource group")
@click.option("--enabled/--disabled", default=None, help="Enable/disable tenant")
@click.option("--schedule", help="Update cron schedule expression")
@click.option("--max-workers", type=int, help="Update maximum knowledge workers")
@click.option("--max-concurrent", type=int, help="Update maximum concurrent scenarios")
@click.option(
    "--add-scenario",
    multiple=True,
    help="Add scenario (can be specified multiple times)"
)
@click.option(
    "--remove-scenario",
    multiple=True,
    help="Remove scenario (can be specified multiple times)"
)
def update_tenant(
    tenant_name,
    display_name,
    description,
    region,
    resource_group,
    enabled,
    schedule,
    max_workers,
    max_concurrent,
    add_scenario,
    remove_scenario,
):
    """Update tenant configuration.

    Updates one or more configuration values for an existing tenant.
    Only specified options will be updated; others remain unchanged.

    Example:
        # Enable a tenant
        haymaker orch tenant update prod-east --enabled

        # Update schedule
        haymaker orch tenant update prod-east --schedule "0 */12 * * *"

        # Add scenarios
        haymaker orch tenant update prod-east \\
            --add-scenario compute-03 --add-scenario storage-04

        # Update resource limits
        haymaker orch tenant update prod-east \\
            --max-workers 200 --max-concurrent 20
    """
    try:
        # Build updates dictionary with only specified values
        updates = {}

        if display_name is not None:
            updates["display_name"] = display_name
        if description is not None:
            updates["description"] = description
        if region is not None:
            updates["region"] = region
        if resource_group is not None:
            updates["resource_group_name"] = resource_group
        if enabled is not None:
            updates["enabled"] = enabled
        if schedule is not None:
            updates["schedule"] = {"cron": schedule, "enabled": True}

        # Update limits
        if max_workers is not None or max_concurrent is not None:
            limits = {}
            if max_workers is not None:
                limits["max_knowledge_workers"] = max_workers
            if max_concurrent is not None:
                limits["max_concurrent_scenarios"] = max_concurrent
            updates["limits"] = limits

        # Handle scenario additions/removals
        if add_scenario or remove_scenario:
            # Load current scenarios
            config = load_tenant_config()
            tenants = config.get("target_tenants", [])
            tenant = next((t for t in tenants if t["name"] == tenant_name), None)

            if not tenant:
                console.print(f"[red]Error:[/red] Tenant '{tenant_name}' not found", err=True)
                sys.exit(1)

            current_scenarios = set(tenant.get("scenarios", []))

            # Add new scenarios
            for scenario in add_scenario:
                current_scenarios.add(scenario)

            # Remove scenarios
            for scenario in remove_scenario:
                current_scenarios.discard(scenario)

            updates["scenarios"] = list(current_scenarios)

        if not updates:
            console.print("[yellow]No updates specified[/yellow]")
            console.print("Use --help to see available options")
            sys.exit(0)

        # Apply updates
        update_tenant_in_config(tenant_name, updates)

        console.print(f"[green]✓[/green] Tenant '{tenant_name}' updated successfully")

        # Show updated tenant
        console.print()
        config = load_tenant_config()
        tenants = config.get("target_tenants", [])
        tenant = next((t for t in tenants if t["name"] == tenant_name), None)
        if tenant:
            format_tenant_status(tenant, "table")

    except TenantConfigError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", err=True)
        sys.exit(1)


@tenant_group.command(name="remove")
@click.argument("tenant_name")
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt"
)
def remove_tenant(tenant_name, confirm):
    """Remove tenant from configuration.

    Removes a tenant configuration from the meta-orchestrator. This does
    not delete any Azure resources; it only removes the tenant from the
    orchestration configuration.

    Example:
        # Remove with confirmation prompt
        haymaker orch tenant remove prod-east

        # Remove without confirmation
        haymaker orch tenant remove prod-east --confirm

    WARNING: This action cannot be undone. The tenant configuration will
    be permanently removed from the orchestration system.
    """
    try:
        # Check if tenant exists
        config = load_tenant_config()
        tenants = config.get("target_tenants", [])
        tenant = next((t for t in tenants if t["name"] == tenant_name), None)

        if not tenant:
            console.print(f"[red]Error:[/red] Tenant '{tenant_name}' not found", err=True)
            console.print("\n[dim]Available tenants:[/dim]")
            for t in tenants:
                console.print(f"  - {t['name']}")
            sys.exit(1)

        # Confirmation prompt
        if not confirm:
            console.print(f"[yellow]Warning:[/yellow] You are about to remove tenant '{tenant_name}'")
            console.print("\n[dim]Current configuration:[/dim]")
            format_tenant_status(tenant, "table")
            console.print()

            if not click.confirm("Are you sure you want to remove this tenant?", default=False):
                console.print("[dim]Operation cancelled[/dim]")
                sys.exit(0)

        # Remove tenant
        remove_tenant_from_config(tenant_name)

        console.print(f"[green]✓[/green] Tenant '{tenant_name}' removed successfully")

    except TenantConfigError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", err=True)
        sys.exit(1)


__all__ = [
    "tenant_group",
    "add_tenant",
    "list_tenants",
    "tenant_status",
    "update_tenant",
    "remove_tenant",
]
