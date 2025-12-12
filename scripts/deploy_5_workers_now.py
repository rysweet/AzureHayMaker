#!/usr/bin/env python3
"""Deploy 5 Knowledge Workers with AI Limericks - Evidence Collection Script

This script deploys 5 workers, captures REAL evidence, and saves it for PowerPoint creation.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, UTC
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient
from azure_haymaker.knowledge_worker import DeploymentConfig, KnowledgeWorkerOrchestrator
from azure_haymaker.knowledge_worker.content import EmailGenerationConfig

# Evidence collection directory
EVIDENCE_DIR = Path(__file__).parent / "evidence"
EVIDENCE_DIR.mkdir(exist_ok=True)

async def main():
    print("🏴‍☠️ Knowledge Worker Deployment - 5 Workers with AI Limericks")
    print("=" * 70)

    # Get credentials
    tenant_id = os.getenv("KW_TENANT_ID", "c7674d41-af6c-46f5-89a5-d41495d2151e")
    app_id = os.getenv("KW_APP_ID")
    client_secret = os.getenv("KW_CLIENT_SECRET")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not all([app_id, client_secret]):
        print("❌ Missing credentials: KW_APP_ID, KW_CLIENT_SECRET")
        return 1

    if not anthropic_key:
        print("⚠️  ANTHROPIC_API_KEY not set - will use fallback email generation")

    # Setup Graph client
    print("\n1️⃣  Authenticating with Microsoft Graph...")
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=app_id,
        client_secret=client_secret,
    )
    graph_client = GraphServiceClient(credential)
    print("   ✅ Authenticated")

    # Create deployment config
    print("\n2️⃣  Creating deployment configuration...")
    config = DeploymentConfig(
        name=f"kw-5-test-{datetime.now().strftime('%Y%m%d-%H%M')}",
        total_workers=5,
        tenant_domain="DefenderATEVET12.onmicrosoft.com",
        duration_hours=1,

        # Email markers
        email_markers_enabled=True,
        marker_style="both",
        marker_format="TEST-RUN",

        # AI generation
        email_generation=EmailGenerationConfig(
            enabled=bool(anthropic_key),
            directive="Include a humorous limerick about working in the age of AI in your email signature"
        ),

        # Departments
        departments={
            "engineering": {
                "count": 3,
                "endpoint_type": "cli_container",
                "activity": {
                    "email_per_hour": 6,
                    "teams_messages_per_hour": 10,
                },
            },
            "sales": {
                "count": 2,
                "endpoint_type": "cli_container",
                "activity": {
                    "email_per_hour": 8,
                    "teams_messages_per_hour": 8,
                },
            },
        },
    )

    print(f"   Name: {config.name}")
    print(f"   Workers: {config.total_workers}")
    print(f"   Departments: engineering (3), sales (2)")
    print(f"   AI Generation: {config.email_generation.enabled}")
    print(f"   Email Markers: {config.email_markers_enabled}")

    # Save config to evidence
    config_evidence = {
        "name": config.name,
        "total_workers": config.total_workers,
        "departments": config.departments,
        "ai_enabled": config.email_generation.enabled,
        "directive": config.email_generation.directive,
        "markers_enabled": config.email_markers_enabled,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    (EVIDENCE_DIR / "01_deployment_config.json").write_text(json.dumps(config_evidence, indent=2))

    # Create orchestrator
    print("\n3️⃣  Initializing Knowledge Worker Orchestrator...")
    orchestrator = KnowledgeWorkerOrchestrator(graph_client)
    print("   ✅ Orchestrator initialized")

    # Create deployment
    print("\n4️⃣  Creating deployment...")
    run_id = orchestrator.create_deployment(config)
    print(f"   ✅ Deployment created: {run_id}")

    # Save run ID
    (EVIDENCE_DIR / "02_run_id.txt").write_text(run_id)

    # Start deployment
    print("\n5️⃣  Starting deployment (this will take a few minutes)...")
    print("   Phase 1: Setup (security groups, transport rules)")
    print("   Phase 2: Provision (create users, assign licenses)")
    print("   Phase 3: Execute (run M365 activities)")

    try:
        success = await orchestrator.start_deployment(run_id)

        if success:
            print("\n✅ DEPLOYMENT STARTED SUCCESSFULLY!")

            # Get deployment state
            state = orchestrator.get_deployment(run_id)
            print(f"\n📊 Deployment Status:")
            print(f"   Run ID: {run_id}")
            print(f"   Phase: {state.phase.value}")
            print(f"   Status: {state.status.value}")
            print(f"   Workers: {len(state.workers)}")

            # Save state to evidence
            state_evidence = {
                "run_id": run_id,
                "phase": state.phase.value,
                "status": state.status.value,
                "worker_count": len(state.workers),
                "workers": [
                    {
                        "worker_id": w.worker_config.worker_id,
                        "department": w.worker_config.department,
                        "endpoint_type": w.worker_config.endpoint_type,
                    }
                    for w in state.workers
                ],
                "timestamp": datetime.now(UTC).isoformat(),
            }
            (EVIDENCE_DIR / "03_deployment_state.json").write_text(json.dumps(state_evidence, indent=2))

            print(f"\n📁 Evidence saved to: {EVIDENCE_DIR}/")
            print("   - 01_deployment_config.json")
            print("   - 02_run_id.txt")
            print("   - 03_deployment_state.json")

            return 0
        else:
            print("\n❌ Deployment failed to start")
            return 1

    except Exception as e:
        print(f"\n❌ Deployment error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
