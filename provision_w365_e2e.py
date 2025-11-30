#!/usr/bin/env python3
"""Complete Windows 365 + M365 E2E demonstration.

Demonstrates the full Knowledge Worker Activity Framework with Windows 365 Cloud PCs:
1. User and Teams provisioning (TeamsIntegration)
2. Cloud PC provisioning (Windows365CloudPCManager) - with graceful fallback
3. Activity simulation (knowledge worker agents)
4. Telemetry collection (M365TelemetryCollector)
5. Report generation (Console + JSON export)

Usage:
    python provision_w365_e2e.py --workers 2 --duration-minutes 30
    python provision_w365_e2e.py --workers 5 --duration-minutes 60 --skip-cloudpc
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

# Import framework components
from azure_haymaker.knowledge_worker.endpoints.cloud_pc import (
    Windows365CloudPCManager,
)
from azure_haymaker.knowledge_worker.identity.user_manager import EntraUserManager
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerConfig,
    WorkerIdentity,
    WorkerPersona,
)
from azure_haymaker.knowledge_worker.teams_integration import TeamsIntegration
from azure_haymaker.knowledge_worker.telemetry import M365TelemetryCollector

# Constants
TELEMETRY_LOOKBACK_HOURS = 24  # Look back 24 hours for telemetry data
MAX_CONSOLE_DISPLAY_WORKERS = 10  # Limit console output to first N workers for readability


def get_graph_client() -> GraphServiceClient:
    """Initialize Microsoft Graph API client from environment variables.

    Required environment variables:
        AZURE_TENANT_ID: Azure AD Tenant ID
        AZURE_CLIENT_ID: Service Principal Client ID
        AZURE_CLIENT_SECRET: Service Principal Client Secret

    Returns:
        Authenticated GraphServiceClient
    """
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    if not all([tenant_id, client_id, client_secret]):
        raise ValueError(
            "Missing required environment variables: "
            "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET"
        )

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    return GraphServiceClient(credentials=credential)


async def main(
    num_workers: int = 2,
    duration_minutes: int = 30,
    skip_cloudpc: bool = False,
) -> None:
    """Run complete E2E demonstration.

    Args:
        num_workers: Number of knowledge workers to provision
        duration_minutes: Duration to run activities (for simulation)
        skip_cloudpc: Skip Cloud PC provisioning (useful for testing)
    """
    run_id = f"w365-e2e-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    start_time = datetime.now(UTC)

    # Display banner
    print("\n" + "=" * 70)
    print("Windows 365 + M365 E2E Demonstration")
    print("=" * 70)
    print(f"Run ID: {run_id}")
    print(f"Workers: {num_workers} | Duration: {duration_minutes} min")
    print(f"Skip Cloud PC: {skip_cloudpc}")
    print("=" * 70 + "\n")

    # Phase 1: Initialize Graph API client
    print("\nPhase 1: Initializing Graph API client")
    try:
        graph_client = get_graph_client()
        print("  ✓ Graph API client initialized")
    except Exception as e:
        print(f"  ✗ Failed to initialize Graph client: {e}")
        sys.exit(1)

    # Phase 2: Provision users and Teams
    print("\nPhase 2: Provisioning users and Teams")
    teams_mgr = TeamsIntegration(graph_client, run_id)
    user_mgr = EntraUserManager(graph_client, run_id)

    # Create worker configs
    workers: list[WorkerIdentity] = []
    personas = list(WorkerPersona)

    print(f"  Provisioning {num_workers} users...")
    for i in range(num_workers):
        persona = personas[i % len(personas)]
        worker_config = WorkerConfig(
            worker_id=f"kw-{run_id[:8]}-{i:03d}",
            persona=persona,
            department=persona.name.lower(),
            endpoint_type=EndpointType.CLOUD_PC if not skip_cloudpc else EndpointType.CLI_CONTAINER,
        )

        try:
            # Create Entra user
            user = await user_mgr.create_user(
                worker_id=worker_config.worker_id,
                display_name=f"KW {persona.name.title()} {i:03d}",
                department=worker_config.department,
            )

            worker = WorkerIdentity(
                worker_id=worker_config.worker_id,
                display_name=user.display_name or worker_config.worker_id,
                user_principal_name=user.user_principal_name or "",
                entra_object_id=user.id or "",
                department=worker_config.department,
                persona=persona,
                endpoint_type=worker_config.endpoint_type,
                endpoint_id="",
                team_ids=[],
            )

            workers.append(worker)
            print(f"    [{i+1}/{num_workers}] Created user: {worker.worker_id}")

        except Exception as e:
            print(f"    ⚠ Failed to create user {worker_config.worker_id}: {e}")

    print(f"  ✓ Provisioned {len(workers)} users")

    # Create Teams
    try:
        team = await teams_mgr.create_team(
            team_name=f"HayMaker-{run_id[:8]}",
            description=f"Knowledge Worker team for run {run_id}",
            members=[w.entra_object_id for w in workers],
        )
        print(f"  ✓ Created team: {team.display_name}")

        # Update workers with team ID
        for worker in workers:
            worker.team_ids = [team.id]

    except Exception as e:
        print(f"  ⚠ Failed to create team: {e}")

    # Phase 3: Provision Cloud PCs
    if not skip_cloudpc:
        print("\nPhase 3: Provisioning Cloud PCs")
        cloudpc_mgr = Windows365CloudPCManager(graph_client, run_id)

        try:
            # Ensure provisioning policy exists
            policy_id = await cloudpc_mgr.ensure_provisioning_policy()
            print(f"  ✓ Provisioning policy ready: {policy_id}")

            # Provision Cloud PCs
            print(f"  Provisioning {len(workers)} Cloud PCs...")
            for i, worker in enumerate(workers):
                try:
                    cloud_pc_id = await cloudpc_mgr.provision_cloud_pc(
                        worker, policy_id
                    )
                    worker.endpoint_id = cloud_pc_id
                    print(f"    [{i+1}/{len(workers)}] Cloud PC: {cloud_pc_id}")
                except Exception as e:
                    print(f"    ⚠ Cloud PC provision failed for {worker.worker_id}: {e}")

            print(f"  ✓ Provisioned {len(workers)} Cloud PCs")

            # Check permission status
            perm_status = cloudpc_mgr.get_permission_status()
            if not perm_status["has_cloudpc_permission"]:
                print(
                    "  ⚠ CloudPC.ReadWrite.All permission not available - using mock provisioning"
                )
                print(f"    Fallback count: {perm_status['fallback_count']}")
            else:
                print("  ✓ Full Cloud PC permissions available")

        except Exception as e:
            print(f"  ✗ Cloud PC provisioning error: {e}")
            perm_status = None
    else:
        print("\nPhase 3: Skipping Cloud PC provisioning")
        perm_status = None

    # Phase 4: Simulate activities
    print(f"\nPhase 4: Simulating worker activities ({duration_minutes} min)")
    print("  In a real deployment, knowledge worker agents would run here.")
    print("  For this demo, we'll collect existing telemetry from M365.")
    print("  ✓ Activity simulation phase complete")

    # Phase 5: Collect telemetry
    print("\nPhase 5: Collecting telemetry")
    telemetry = M365TelemetryCollector(graph_client, run_id)

    try:
        # Collect telemetry with time window
        end_time = datetime.now(UTC)
        start_time_telemetry = end_time - timedelta(hours=TELEMETRY_LOOKBACK_HOURS)

        summary = await telemetry.get_run_summary(
            workers=workers,
            start_time=start_time_telemetry,
            end_time=end_time,
        )

        print(f"  ✓ Telemetry collected for {len(workers)} workers")
        print(
            f"    Emails: {summary['email_count']}, "
            f"Calendar: {summary['calendar_count']}, "
            f"Teams: {summary['teams_count']}"
        )

    except Exception as e:
        print(f"  ⚠ Telemetry collection error: {e}")
        summary = {
            "run_id": run_id,
            "total_workers": len(workers),
            "email_count": 0,
            "calendar_count": 0,
            "teams_count": 0,
            "by_worker": {},
            "error": str(e),
        }

    # Phase 6: Generate reports
    print("\nPhase 6: Generating reports")

    # Console report
    generate_console_report(workers, summary, perm_status)

    # JSON export
    json_path = export_json_summary(run_id, workers, summary, start_time)
    print(f"  ✓ JSON report exported: {json_path}")

    # Completion
    elapsed = (datetime.now(UTC) - start_time).total_seconds()
    print(f"\n✓ E2E demonstration complete! ({elapsed:.1f}s)\n")


def generate_console_report(
    workers: list[WorkerIdentity],
    summary: dict[str, Any],
    perm_status: dict[str, Any] | None,
) -> None:
    """Generate and display console report.

    Args:
        workers: List of provisioned workers
        summary: Telemetry summary data
        perm_status: Cloud PC permission status (None if skipped)
    """
    print("\n" + "=" * 70)
    print("RUN SUMMARY")
    print("=" * 70)

    # Workers summary
    print(f"\nProvisioned Workers ({len(workers)} total):")
    print("-" * 70)
    print(f"{'Worker ID':<25} {'Persona':<15} {'Department':<20}")
    print("-" * 70)
    for worker in workers[:MAX_CONSOLE_DISPLAY_WORKERS]:
        persona = worker.persona.name if worker.persona else "N/A"
        print(f"{worker.worker_id:<25} {persona:<15} {worker.department:<20}")
    if len(workers) > MAX_CONSOLE_DISPLAY_WORKERS:
        print(f"... and {len(workers) - MAX_CONSOLE_DISPLAY_WORKERS} more workers")

    # Telemetry summary
    print("\nTelemetry Summary:")
    print("-" * 70)
    print(f"  Total Workers:      {summary.get('total_workers', 0)}")
    print(f"  Email Messages:     {summary.get('email_count', 0)}")
    print(f"  Calendar Events:    {summary.get('calendar_count', 0)}")
    print(f"  Teams Messages:     {summary.get('teams_count', 0)}")

    # Permission status (if Cloud PC was used)
    if perm_status:
        print("\nCloud PC Permissions:")
        print("-" * 70)
        has_perm = perm_status.get("has_cloudpc_permission", False)
        status_str = "✓ Available" if has_perm else "⚠ Not Available (using mock)"
        print(f"  CloudPC.ReadWrite.All:  {status_str}")
        print(f"  Fallback Count:         {perm_status.get('fallback_count', 0)}")

    print("=" * 70)


def export_json_summary(
    run_id: str,
    workers: list[WorkerIdentity],
    summary: dict[str, Any],
    start_time: datetime,
) -> str:
    """Export run summary to JSON file.

    Args:
        run_id: Run identifier
        workers: List of provisioned workers
        summary: Telemetry summary data
        start_time: Run start time

    Returns:
        Path to exported JSON file
    """
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"{run_id}-summary.json"

    export_data = {
        "run_id": run_id,
        "start_time": start_time.isoformat(),
        "end_time": datetime.now(UTC).isoformat(),
        "workers": [
            {
                "worker_id": w.worker_id,
                "persona": w.persona.name if w.persona else None,
                "department": w.department,
                "endpoint_type": w.endpoint_type.value if w.endpoint_type else None,
                "endpoint_id": w.endpoint_id,
                "user_principal_name": w.user_principal_name,
            }
            for w in workers
        ],
        "telemetry_summary": summary,
    }

    with open(output_file, "w") as f:
        json.dump(export_data, f, indent=2)

    return str(output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Windows 365 + M365 E2E Demonstration"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of knowledge workers to provision (default: 2)",
    )
    parser.add_argument(
        "--duration-minutes",
        type=int,
        default=30,
        help="Duration to run activities in minutes (default: 30)",
    )
    parser.add_argument(
        "--skip-cloudpc",
        action="store_true",
        help="Skip Cloud PC provisioning (useful for testing without CloudPC permissions)",
    )

    args = parser.parse_args()

    try:
        asyncio.run(main(args.workers, args.duration_minutes, args.skip_cloudpc))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
