"""Azure Functions entry point for Azure HayMaker orchestrator.

This module exposes the Azure Functions from the orchestrator module
to the Azure Functions runtime.
"""

# Import and expose the Function App instance from orchestrator
from azure_haymaker.orchestrator import app

# Export the app so Azure Functions runtime can find it
__all__ = ["app"]
