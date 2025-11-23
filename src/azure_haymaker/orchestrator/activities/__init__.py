"""Activity functions for Azure HayMaker orchestrator.

This package contains all Durable Functions activity functions organized by phase:

- validation: Environment validation activity
- selection: Scenario selection activity
- provisioning: Service principal and container deployment activities
- monitoring: Agent status monitoring activity
- cleanup: Cleanup verification and forced cleanup activities
- reporting: Report generation activity

Design Pattern: Activity Function Organization
- Each phase has its own module
- All activities import shared app instance from orchestrator_app
- Activities are registered via decorators
- No circular imports

Import Structure:
    from azure_haymaker.orchestrator.activities import (
        validate_environment_activity,
        select_scenarios_activity,
        # etc.
    )

Note: Activity functions are registered via decorators, not exports.
The orchestration function references them by string name.
"""

# Import all activity modules to ensure decorators are registered
from azure_haymaker.orchestrator.activities import (
    cleanup,  # noqa: F401
    monitoring,  # noqa: F401
    provisioning,  # noqa: F401
    reporting,  # noqa: F401
    selection,  # noqa: F401
    validation,  # noqa: F401
)

# Activity functions are registered via @app.activity_trigger decorators
# and are called by name in the orchestration function.
# No need to explicitly export them.
__all__ = [
    "cleanup",
    "monitoring",
    "provisioning",
    "reporting",
    "selection",
    "validation",
]
