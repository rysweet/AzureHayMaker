"""Entry point for running orchestrator as a module in Container Apps.

Usage:
    python -m azure_haymaker.orchestrator

For Container Apps deployment with KEDA CRON scaling.
Provides HTTP health endpoint for container health checks.
"""

import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks."""

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
                "schedule": "KEDA CRON (00:00, 06:00, 12:00, 18:00 UTC)"
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))

    logger.info("=" * 80)
    logger.info("Azure HayMaker Orchestrator - Container Apps Mode")
    logger.info("=" * 80)
    logger.info(f"Port: {port}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'dev')}")
    logger.info(f"Workload Profile: E16 (128GB RAM, 16 vCPU)")
    logger.info(f"Schedule: KEDA CRON (00:00, 06:00, 12:00, 18:00 UTC)")
    logger.info(f"Scale: minReplicas=0, maxReplicas=1 (scale-to-zero)")
    logger.info("=" * 80)

    # Start HTTP server for health checks
    server = HTTPServer(('', port), HealthHandler)
    logger.info(f"Health check server started on port {port}")
    logger.info(f"Health endpoint: http://localhost:{port}/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down orchestrator...")
        server.shutdown()
