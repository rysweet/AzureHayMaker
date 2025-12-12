#!/usr/bin/env python3
"""Deploy 5 Knowledge Workers - Basic Test (No AI)"""

import asyncio
import json
import os
import sys
from datetime import datetime, UTC
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient
from azure_haymaker.knowledge_worker import DeploymentConfig, KnowledgeWorkerOrchestrator

EVIDENCE_DIR = Path(__file__).parent / "evidence"
EVIDENCE_DIR.mkdir(exist_ok=True)

async def main():
    print("🏴‍☠️ Knowledge Worker Deployment - 5 Workers (Basic Test, No AI)")
    print("=" * 70)

    tenant_id = os.getenv("KW_TENANT_ID", "c7674d41-af6c-46f5-89a5-d41495d2151e")
    app_id = os.getenv("KW_APP_ID")
    client_secret = os.getenv("KW_CLIENT_SECRET")

    if not all([app_id, client_secret]):
        print("❌ Missing credentials")
        return 1

    print("\n1️⃣  Authenticating...")
    credential = ClientSecretCredential(tenant_id=tenant_id, client_id=app_id, client_secret=client_secret)
    graph_client = GraphServiceClient(credential)
    print("   ✅ Authenticated")

    print("\n2️⃣  Creating deployment...")
    config = DeploymentConfig(
        name=f"kw-5-basic-{datetime.now().strftime('%H%M')}",
        total_workers=5,
        tenant_domain="DefenderATEVET12.onmicrosoft.com",
        duration_hours=1,
        email_markers_enabled=True,
        marker_style="both",
        marker_format="TEST-RUN",
        departments={
            "engineering": {"count": 3, "endpoint_type": "cli_container", "activity": {"email_per_hour": 6}},
            "sales": {"count": 2, "endpoint_type": "cli_container", "activity": {"email_per_hour": 8}},
        },
    )

    orchestrator = KnowledgeWorkerOrchestrator(graph_client)
    run_id = orchestrator.create_deployment(config)
    print(f"   ✅ Run ID: {run_id}")

    print("\n3️⃣  Starting deployment...")
    success = await orchestrator.start_deployment(run_id)

    if success:
        print("\n✅ DEPLOYMENT SUCCESSFUL!")
        state = orchestrator.get_deployment(run_id)
        print(f"   Phase: {state.phase.value}")
        print(f"   Status: {state.status.value}")
        print(f"   Workers: {len(state.workers)}")
        (EVIDENCE_DIR / "run_id.txt").write_text(run_id)
        (EVIDENCE_DIR / "success.json").write_text(json.dumps({"run_id": run_id, "workers": len(state.workers), "success": True}, indent=2))
        return 0
    else:
        print("\n❌ DEPLOYMENT FAILED")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))
