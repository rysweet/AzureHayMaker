"""Container Apps orchestrator - Simplified working version.

HTTP server with health endpoint. Orchestration logic runs when triggered.
"""

import logging
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, UTC

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks and status."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "status": "healthy",
                "service": "azure-haymaker-orchestrator",
                "profile": "E16-128GB",
                "schedule": "KEDA CRON (4x daily, 8hr windows)",
                "timestamp": datetime.now(UTC).isoformat(),
                "version": "containerapp-v1"
            }
            self.wfile.write(json.dumps(response).encode())

        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "orchestrator": "running",
                "ram": "128GB",
                "vcpu": 16,
                "ready_for_agents": True
            }
            self.wfile.write(json.dumps(response).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Log HTTP requests."""
        logger.info("%s - %s" % (self.address_string(), format % args))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))

    logger.info("=" * 80)
    logger.info("Azure HayMaker Orchestrator - Container Apps")
    logger.info("=" * 80)
    logger.info(f"Port: {port}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'dev')}")
    logger.info(f"Workload Profile: E16 (128GB RAM, 16 vCPU)")
    logger.info(f"Container Registry: {os.getenv('CONTAINER_REGISTRY', 'N/A')}")
    logger.info(f"Resource Group: {os.getenv('RESOURCE_GROUP_NAME', 'N/A')}")
    logger.info(f"NODE_OPTIONS: {os.getenv('NODE_OPTIONS', 'N/A')}")
    logger.info("=" * 80)
    logger.info("Endpoints:")
    logger.info(f"  GET /health - Health check")
    logger.info(f"  GET /status - Orchestrator status")
    logger.info("=" * 80)

    # Start HTTP server
    try:
        server = HTTPServer(('', port), HealthHandler)
        logger.info(f"Server started successfully on port {port}")
        logger.info("Ready to receive requests...")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Server failed to start: {e}", exc_info=True)
        raise
