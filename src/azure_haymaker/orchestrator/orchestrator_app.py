"""Azure Functions app instance for Azure HayMaker orchestrator.

This module creates a single FunctionApp instance that is imported by all
other orchestrator modules (timer trigger, workflow orchestrator, activities).

IMPORTANT: This module must be imported first to avoid circular dependencies.
All decorators (@app.timer_trigger, @app.orchestration_trigger, etc.)
reference this app instance.

Design Pattern: Shared Application Instance
- Create app ONCE in this module
- Import app from here in all other modules
- Prevents circular import issues
- Ensures all functions registered on same app instance

Example:
    from azure_haymaker.orchestrator.orchestrator_app import app

    @app.timer_trigger(schedule="0 0 * * * *", arg_name="timer")
    def my_timer(timer):
        pass
"""

import logging

import azure.functions as func

logger = logging.getLogger(__name__)

# =============================================================================
# SHARED FUNCTION APP INSTANCE
# =============================================================================
# This is the ONLY place where FunctionApp() is instantiated.
# All other modules import this instance.
#
# Azure Functions requires all functions to be registered on the same app
# instance. Creating multiple instances will cause registration failures.
# =============================================================================

app = func.FunctionApp()

logger.info("Azure Functions app instance created: %s", app)
