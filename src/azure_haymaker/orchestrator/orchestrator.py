"""Azure Durable Functions orchestrator for Azure HayMaker.

BACKWARD COMPATIBILITY FACADE
==============================
This module has been refactored into separate files to comply with the 300-line
philosophy limit. This file now serves as a backward-compatibility facade that
re-exports all functions from their new locations.

Original Structure (1065 lines - DEPRECATED):
- Timer trigger function
- Main orchestration function
- 8 activity functions

New Structure (compliant with 300-line limit):
- orchestrator_app.py: Shared FunctionApp instance (~42 lines)
- timer_trigger.py: Timer trigger function (~92 lines)
- workflow_orchestrator.py: Main orchestration function (~330 lines)
- activities/: Activity functions organized by phase
  - validation.py: Environment validation (~73 lines)
  - selection.py: Scenario selection (~70 lines)
  - provisioning.py: SP and container deployment (~200 lines)
  - monitoring.py: Agent status monitoring (~92 lines)
  - cleanup.py: Cleanup verification and forced cleanup (~234 lines)
  - reporting.py: Report generation (~109 lines)

Design Pattern: Facade Pattern
==============================
This facade maintains backward compatibility for existing imports while
enabling the new modular structure. All existing code continues to work
without modification.

Import Examples:
    from azure_haymaker.orchestrator.orchestrator import (
        app,
        haymaker_timer,
        orchestrate_haymaker_run,
        validate_environment_activity,
        # ... etc
    )

Migration Guide:
===============
For new code, prefer importing from the specific modules:

    # OLD (still works, but deprecated)
    from azure_haymaker.orchestrator.orchestrator import haymaker_timer

    # NEW (recommended)
    from azure_haymaker.orchestrator.timer_trigger import haymaker_timer

Related:
- Issue #48: Refactor orchestrator.py (1065 lines)
- Philosophy: Each module should be a self-contained "brick" < 300 lines
"""

# Import shared FunctionApp instance
# Import all activity functions
from azure_haymaker.orchestrator.activities.cleanup import (
    force_cleanup_activity,
    verify_cleanup_activity,
)
from azure_haymaker.orchestrator.activities.monitoring import (
    check_agent_status_activity,
)
from azure_haymaker.orchestrator.activities.provisioning import (
    create_service_principal_activity,
    deploy_container_app_activity,
)
from azure_haymaker.orchestrator.activities.reporting import (
    generate_report_activity,
)
from azure_haymaker.orchestrator.activities.selection import (
    select_scenarios_activity,
)
from azure_haymaker.orchestrator.activities.validation import (
    validate_environment_activity,
)
from azure_haymaker.orchestrator.orchestrator_app import app

# Import timer trigger
from azure_haymaker.orchestrator.timer_trigger import haymaker_timer

# Import main orchestration function
from azure_haymaker.orchestrator.workflow_orchestrator import (
    orchestrate_haymaker_run,
)

# Re-export all public functions for backward compatibility
__all__ = [
    # Shared FunctionApp instance
    "app",
    # Timer trigger
    "haymaker_timer",
    # Main orchestration function
    "orchestrate_haymaker_run",
    # Activity functions
    "validate_environment_activity",
    "select_scenarios_activity",
    "create_service_principal_activity",
    "deploy_container_app_activity",
    "check_agent_status_activity",
    "verify_cleanup_activity",
    "force_cleanup_activity",
    "generate_report_activity",
]
