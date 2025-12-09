"""HTTP API endpoints for meta-orchestrator management.

This module provides REST API endpoints for starting and monitoring
multi-tenant meta-orchestrations.

Endpoints:
- POST /api/v1/meta/execute: Start multi-tenant orchestration
- GET /api/v1/meta/status/{instance_id}: Get orchestration status

Phase 2: Orchestrator Integration
"""

import json
import logging
from datetime import datetime
from uuid import uuid4

import azure.functions as func
from azure.durable_functions import DurableOrchestrationClient

from azure_haymaker.orchestrator.models.tenant_config import MetaOrchestratorConfig
from azure_haymaker.orchestrator.orchestrator_app import app

logger = logging.getLogger(__name__)


@app.route(route="api/v1/meta/execute", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_meta_orchestration(
    req: func.HttpRequest, client: DurableOrchestrationClient
) -> func.HttpResponse:
    """Start multi-tenant meta-orchestration.

    Request body:
        {
            "meta_config": {...},  // MetaOrchestratorConfig (nested or flat)
            "tenant_names": ["tenant-a", "tenant-b"],  // Optional: specific tenants only
            "run_all": true  // Optional: run all enabled tenants (default)
        }

    Response (202 Accepted):
        {
            "meta_run_id": "meta-abc123",
            "instance_id": "meta-abc123",
            "status_query_url": "/api/v1/meta/status/meta-abc123",
            "tenants": ["tenant-a", "tenant-b"]
        }

    Response (400 Bad Request):
        {
            "error": "Missing meta_config in request body"
        }

    Response (500 Internal Server Error):
        {
            "error": "Failed to start orchestration: ..."
        }
    """
    try:
        # Parse request
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON in request body"}),
                status_code=400,
                mimetype="application/json",
            )

        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Empty request body"}),
                status_code=400,
                mimetype="application/json",
            )

        # Validate meta_config present
        meta_config_dict = req_body.get("meta_config")
        if not meta_config_dict:
            return func.HttpResponse(
                json.dumps({"error": "Missing meta_config in request body"}),
                status_code=400,
                mimetype="application/json",
            )

        # Generate meta run ID
        meta_run_id = f"meta-{uuid4().hex[:12]}"

        # Load and validate meta config
        try:
            # Handle both nested and flat structure
            if "meta_orchestrator" in meta_config_dict:
                # Nested structure - flatten it
                flat_config = {**meta_config_dict["meta_orchestrator"]}
                flat_config["target_tenants"] = meta_config_dict.get("target_tenants", [])
                meta_config = MetaOrchestratorConfig(**flat_config)
            else:
                # Already flat
                meta_config = MetaOrchestratorConfig(**meta_config_dict)
        except Exception as e:
            logger.error(f"Failed to parse meta_config: {e}")
            return func.HttpResponse(
                json.dumps({"error": f"Invalid meta_config: {str(e)}"}),
                status_code=400,
                mimetype="application/json",
            )

        # Filter tenants if specific names provided
        tenant_names = req_body.get("tenant_names")
        if tenant_names:
            original_count = len(meta_config.target_tenants)
            meta_config.target_tenants = [
                t for t in meta_config.target_tenants if t.name in tenant_names
            ]
            logger.info(
                f"Filtered tenants from {original_count} to {len(meta_config.target_tenants)}"
            )

        # Validate at least one tenant enabled
        enabled_tenants = [t for t in meta_config.target_tenants if t.enabled]
        if not enabled_tenants:
            return func.HttpResponse(
                json.dumps({"error": "No enabled tenants found in configuration"}),
                status_code=400,
                mimetype="application/json",
            )

        # Prepare orchestration input
        orchestration_input = {
            "meta_run_id": meta_run_id,
            "meta_config": meta_config.model_dump(),
            "started_at": datetime.utcnow().isoformat(),
        }

        # Start meta-orchestration
        instance_id = await client.start_new(
            "orchestrate_multi_tenant_run", client_input=orchestration_input
        )

        logger.info(
            f"Started meta-orchestration {instance_id} for {len(meta_config.target_tenants)} tenants"
        )

        # Return status
        response = {
            "meta_run_id": meta_run_id,
            "instance_id": instance_id,
            "status_query_url": f"/api/v1/meta/status/{instance_id}",
            "tenants": [t.name for t in meta_config.target_tenants],
            "enabled_tenants": [t.name for t in enabled_tenants],
        }

        return func.HttpResponse(
            json.dumps(response), status_code=202, mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Failed to start meta-orchestration: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}), status_code=500, mimetype="application/json"
        )


@app.route(route="api/v1/meta/status/{instance_id}", methods=["GET"])
@app.durable_client_input(client_name="client")
async def get_meta_orchestration_status(
    req: func.HttpRequest, client: DurableOrchestrationClient
) -> func.HttpResponse:
    """Get status of a meta-orchestration.

    URL Parameters:
        instance_id: Meta-orchestration instance ID

    Response (200 OK):
        {
            "instance_id": "meta-abc123",
            "runtime_status": "Running",
            "created_time": "2025-12-09T12:00:00Z",
            "last_updated_time": "2025-12-09T12:15:00Z",
            "output": {...}  // Meta-report (when completed)
        }

    Response (404 Not Found):
        {
            "error": "Meta-orchestration not found: meta-abc123"
        }
    """
    try:
        # Get instance ID from route
        instance_id = req.route_params.get("instance_id")

        if not instance_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing instance_id parameter"}),
                status_code=400,
                mimetype="application/json",
            )

        # Get orchestration status
        status = await client.get_status(instance_id)

        if not status:
            return func.HttpResponse(
                json.dumps({"error": f"Meta-orchestration not found: {instance_id}"}),
                status_code=404,
                mimetype="application/json",
            )

        # Format response
        response = {
            "instance_id": status.instance_id,
            "runtime_status": status.runtime_status.name if status.runtime_status else "Unknown",
            "created_time": status.created_time.isoformat() if status.created_time else None,
            "last_updated_time": (
                status.last_updated_time.isoformat() if status.last_updated_time else None
            ),
        }

        # Include output if completed
        if status.output:
            response["output"] = status.output

        return func.HttpResponse(
            json.dumps(response), status_code=200, mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Failed to get meta-orchestration status: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}), status_code=500, mimetype="application/json"
        )
