"""Engineering team simulation framework.

This module provides a compositional workflow engine for simulating
realistic software engineering team activities on GitHub, including:
- Commits
- Pull requests
- Code reviews
- CI/CD pipelines
- Merges

The framework follows the "brick philosophy" - small, composable,
self-contained components that can be combined into complex workflows.
"""

from azure_haymaker.engineering_sim.bricks.base import (
    BrickContext,
    BrickResult,
    WorkflowBrick,
    BrickExecutionError,
    BrickValidationError,
)

__all__ = [
    "BrickContext",
    "BrickResult",
    "WorkflowBrick",
    "BrickExecutionError",
    "BrickValidationError",
]
