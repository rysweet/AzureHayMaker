#!/usr/bin/env python3
"""Azure HayMaker Resource Cleanup Tool.

Identifies and removes duplicate Azure resources to reduce costs.
This tool supports both dry-run and live cleanup modes.

Target State:
- 1 Key Vault (yow3ex)
- 1 Service Bus (yow3ex)
- 1 Storage Account (yow3ex)
- 1 VM (orchestrator)

Monthly Savings: ~$3,164 (77% cost reduction)

Usage:
    python scripts/resource-cleanup.py --dry-run    # Preview changes
    python scripts/resource-cleanup.py --execute    # Execute cleanup
    python scripts/resource-cleanup.py --status     # Show current state
"""

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Azure resource types to manage."""

    KEY_VAULT = "keyvault"
    SERVICE_BUS = "servicebus"
    FUNCTION_APP = "functionapp"
    STORAGE_ACCOUNT = "storage"


@dataclass
class ResourceInfo:
    """Information about an Azure resource."""

    name: str
    resource_type: ResourceType
    location: str = ""
    sku: str = ""
    tags: dict[str, str] = field(default_factory=dict)
    estimated_monthly_cost: float = 0.0


@dataclass
class CleanupPlan:
    """Plan for resource cleanup."""

    keep: list[ResourceInfo] = field(default_factory=list)
    delete: list[ResourceInfo] = field(default_factory=list)
    total_monthly_savings: float = 0.0


# Cost estimates per resource type (USD/month)
COST_ESTIMATES = {
    ResourceType.KEY_VAULT: 0.03,  # Per vault minimum
    ResourceType.SERVICE_BUS: 10.0,  # Standard tier
    ResourceType.FUNCTION_APP: 73.0,  # Consumption plan average
    ResourceType.STORAGE_ACCOUNT: 20.0,  # Standard LRS average
}


def run_az_command(command: list[str]) -> tuple[bool, str]:
    """Execute an Azure CLI command and return result.

    Args:
        command: Azure CLI command as list of strings

    Returns:
        Tuple of (success, output/error message)
    """
    try:
        result = subprocess.run(
            ["az"] + command,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out after 120 seconds"
    except FileNotFoundError:
        return False, "Azure CLI (az) not found. Please install Azure CLI."


def get_resources(
    resource_group: str,
    resource_type: ResourceType,
    keep_pattern: str,
) -> CleanupPlan:
    """Get resources and categorize them for cleanup.

    Args:
        resource_group: Azure resource group name
        resource_type: Type of resources to query
        keep_pattern: Pattern to identify resources to keep

    Returns:
        CleanupPlan with resources categorized
    """
    plan = CleanupPlan()
    cost_per_resource = COST_ESTIMATES.get(resource_type, 0.0)

    # Build the appropriate az command based on resource type
    if resource_type == ResourceType.KEY_VAULT:
        cmd = [
            "keyvault",
            "list",
            "-g",
            resource_group,
            "--query",
            "[].{name:name, location:location}",
            "-o",
            "json",
        ]
    elif resource_type == ResourceType.SERVICE_BUS:
        cmd = [
            "servicebus",
            "namespace",
            "list",
            "-g",
            resource_group,
            "--query",
            "[].{name:name, location:location, sku:sku.name}",
            "-o",
            "json",
        ]
    elif resource_type == ResourceType.FUNCTION_APP:
        cmd = [
            "functionapp",
            "list",
            "-g",
            resource_group,
            "--query",
            "[].{name:name, location:location, state:state}",
            "-o",
            "json",
        ]
    elif resource_type == ResourceType.STORAGE_ACCOUNT:
        cmd = [
            "storage",
            "account",
            "list",
            "-g",
            resource_group,
            "--query",
            "[].{name:name, location:location, sku:sku.name}",
            "-o",
            "json",
        ]
    else:
        return plan

    success, output = run_az_command(cmd)
    if not success:
        logger.error(f"Failed to list {resource_type.value}: {output}")
        return plan

    try:
        resources = json.loads(output) if output else []
    except json.JSONDecodeError:
        logger.error(f"Failed to parse {resource_type.value} response")
        return plan

    for res in resources:
        info = ResourceInfo(
            name=res.get("name", ""),
            resource_type=resource_type,
            location=res.get("location", ""),
            sku=res.get("sku", ""),
            estimated_monthly_cost=cost_per_resource,
        )

        if keep_pattern in info.name:
            plan.keep.append(info)
        else:
            plan.delete.append(info)
            plan.total_monthly_savings += cost_per_resource

    return plan


def delete_resource(
    resource_group: str,
    resource: ResourceInfo,
    dry_run: bool = True,
) -> bool:
    """Delete a single Azure resource.

    Args:
        resource_group: Azure resource group name
        resource: Resource to delete
        dry_run: If True, only simulate deletion

    Returns:
        True if deletion successful (or dry run), False otherwise
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would delete {resource.resource_type.value}: {resource.name}")
        return True

    # Build delete command based on resource type
    if resource.resource_type == ResourceType.KEY_VAULT:
        cmd = ["keyvault", "delete", "--name", resource.name, "-g", resource_group]
    elif resource.resource_type == ResourceType.SERVICE_BUS:
        cmd = [
            "servicebus",
            "namespace",
            "delete",
            "--name",
            resource.name,
            "-g",
            resource_group,
            "--yes",
        ]
    elif resource.resource_type == ResourceType.FUNCTION_APP:
        cmd = ["functionapp", "delete", "--name", resource.name, "-g", resource_group, "--yes"]
    elif resource.resource_type == ResourceType.STORAGE_ACCOUNT:
        cmd = ["storage", "account", "delete", "--name", resource.name, "-g", resource_group, "--yes"]
    else:
        logger.warning(f"Unknown resource type: {resource.resource_type}")
        return False

    logger.info(f"Deleting {resource.resource_type.value}: {resource.name}...")
    success, output = run_az_command(cmd)

    if success:
        logger.info(f"Successfully deleted: {resource.name}")
        return True
    else:
        logger.error(f"Failed to delete {resource.name}: {output}")
        return False


def execute_cleanup(
    resource_group: str,
    keep_pattern: str,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Execute the full cleanup process.

    Args:
        resource_group: Azure resource group name
        keep_pattern: Pattern to identify resources to keep
        dry_run: If True, only simulate cleanup

    Returns:
        Summary of cleanup results
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "resource_group": resource_group,
        "keep_pattern": keep_pattern,
        "dry_run": dry_run,
        "resources_kept": [],
        "resources_deleted": [],
        "resources_failed": [],
        "total_monthly_savings": 0.0,
    }

    # Process each resource type in dependency order
    # Delete Function Apps first (they depend on other resources)
    # Delete Service Bus after Function Apps
    # Delete Storage Accounts
    # Delete Key Vaults last (they may have soft delete)
    resource_order = [
        ResourceType.FUNCTION_APP,
        ResourceType.SERVICE_BUS,
        ResourceType.STORAGE_ACCOUNT,
        ResourceType.KEY_VAULT,
    ]

    for resource_type in resource_order:
        logger.info(f"\nProcessing {resource_type.value}...")
        plan = get_resources(resource_group, resource_type, keep_pattern)

        for resource in plan.keep:
            results["resources_kept"].append(
                {
                    "name": resource.name,
                    "type": resource.resource_type.value,
                    "monthly_cost": resource.estimated_monthly_cost,
                }
            )
            logger.info(f"  KEEP: {resource.name}")

        for resource in plan.delete:
            success = delete_resource(resource_group, resource, dry_run)
            if success:
                results["resources_deleted"].append(
                    {
                        "name": resource.name,
                        "type": resource.resource_type.value,
                        "monthly_cost": resource.estimated_monthly_cost,
                    }
                )
                results["total_monthly_savings"] += resource.estimated_monthly_cost
            else:
                results["resources_failed"].append(
                    {
                        "name": resource.name,
                        "type": resource.resource_type.value,
                    }
                )

    return results


def print_status(resource_group: str, keep_pattern: str) -> None:
    """Print current resource status.

    Args:
        resource_group: Azure resource group name
        keep_pattern: Pattern to identify resources to keep
    """
    print("\n" + "=" * 60)
    print("Azure HayMaker - Resource Status")
    print("=" * 60)
    print(f"Resource Group: {resource_group}")
    print(f"Keep Pattern: {keep_pattern}")
    print("=" * 60)

    total_cost = 0.0
    total_savings_potential = 0.0

    for resource_type in ResourceType:
        plan = get_resources(resource_group, resource_type, keep_pattern)
        type_cost = sum(r.estimated_monthly_cost for r in plan.keep)
        type_savings = sum(r.estimated_monthly_cost for r in plan.delete)
        total_cost += type_cost + type_savings
        total_savings_potential += type_savings

        print(f"\n{resource_type.value.upper()}:")
        print(f"  Keep ({len(plan.keep)}):")
        for r in plan.keep:
            print(f"    - {r.name} (${r.estimated_monthly_cost:.2f}/mo)")
        print(f"  Delete ({len(plan.delete)}):")
        for r in plan.delete:
            print(f"    - {r.name} (${r.estimated_monthly_cost:.2f}/mo)")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Current Monthly Cost:    ${total_cost:.2f}")
    print(f"Potential Savings:       ${total_savings_potential:.2f}")
    print(f"Cost After Cleanup:      ${total_cost - total_savings_potential:.2f}")
    print(f"Savings Percentage:      {(total_savings_potential/total_cost*100) if total_cost > 0 else 0:.1f}%")
    print("=" * 60)


def print_results(results: dict[str, Any]) -> None:
    """Print cleanup results summary.

    Args:
        results: Cleanup results dictionary
    """
    print("\n" + "=" * 60)
    print("CLEANUP RESULTS")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if results['dry_run'] else 'EXECUTED'}")
    print(f"Timestamp: {results['timestamp']}")
    print("-" * 60)
    print(f"Resources Kept:    {len(results['resources_kept'])}")
    print(f"Resources Deleted: {len(results['resources_deleted'])}")
    print(f"Resources Failed:  {len(results['resources_failed'])}")
    print("-" * 60)
    print(f"Monthly Savings:   ${results['total_monthly_savings']:.2f}")
    print("=" * 60)

    if results["resources_failed"]:
        print("\nFailed Resources:")
        for r in results["resources_failed"]:
            print(f"  - {r['type']}: {r['name']}")

    if not results["dry_run"]:
        print("\nCleanup complete! Review Azure portal to confirm.")


def main() -> int:
    """Main entry point for resource cleanup.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = argparse.ArgumentParser(
        description="Azure HayMaker Resource Cleanup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/resource-cleanup.py --status         # Show current resources
    python scripts/resource-cleanup.py --dry-run       # Preview cleanup
    python scripts/resource-cleanup.py --execute       # Execute cleanup

WARNING: --execute will permanently delete resources!
        """,
    )

    parser.add_argument(
        "--resource-group",
        "-g",
        default="haymaker-dev-rg",
        help="Azure resource group (default: haymaker-dev-rg)",
    )
    parser.add_argument(
        "--keep-pattern",
        "-k",
        default="yow3ex",
        help="Pattern for resources to keep (default: yow3ex)",
    )

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--status",
        "-s",
        action="store_true",
        help="Show current resource status",
    )
    action_group.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Preview cleanup without making changes",
    )
    action_group.add_argument(
        "--execute",
        "-e",
        action="store_true",
        help="Execute cleanup (DESTRUCTIVE)",
    )

    args = parser.parse_args()

    # Check Azure CLI is available
    success, _ = run_az_command(["--version"])
    if not success:
        print("Error: Azure CLI not available. Please install and login first.")
        print("  Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        print("  Login: az login")
        return 1

    # Check Azure authentication
    success, output = run_az_command(["account", "show"])
    if not success:
        print("Error: Not logged into Azure. Please run 'az login' first.")
        return 1

    if args.status:
        print_status(args.resource_group, args.keep_pattern)
        return 0

    if args.execute:
        print("\n" + "!" * 60)
        print("WARNING: This will PERMANENTLY DELETE Azure resources!")
        print("!" * 60)
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Cancelled.")
            return 0

    results = execute_cleanup(
        resource_group=args.resource_group,
        keep_pattern=args.keep_pattern,
        dry_run=args.dry_run,
    )

    print_results(results)

    if results["resources_failed"]:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
