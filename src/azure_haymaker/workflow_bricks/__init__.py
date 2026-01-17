"""Workflow Bricks - Software Engineering Team Simulation.

Self-contained, composable components for simulating realistic
software engineering team activities including commits, pull requests,
code reviews, CI pipelines, and merges.

This module implements Proposal D: Compositional Workflow Engine
from Issue #145, following the Brick Philosophy where each component
has ONE clear responsibility.

Public API (the "studs"):
    BrickBase: Abstract base class for all bricks
    BrickContext: Execution context passed to each brick
    BrickResult: Standard result from brick execution
    BrickStatus: Enum for brick status (SUCCESS, FAILED, SKIPPED, PENDING)

    CommitBrick: Creates git commits
    PullRequestBrick: Creates pull requests
    CodeReviewBrick: Submits code reviews
    CIPipelineBrick: Triggers CI pipelines
    MergeBrick: Merges pull requests

    GitHubClient: Async client for GitHub API
    Workflow: Composes bricks into workflows

Example:
    >>> from azure_haymaker.workflow_bricks import (
    ...     BrickContext,
    ...     CommitBrick,
    ...     PullRequestBrick,
    ...     CodeReviewBrick,
    ...     MergeBrick,
    ...     Workflow,
    ... )
    >>>
    >>> context = BrickContext(
    ...     tenant_id="tenant-1",
    ...     team_id="team-alpha",
    ...     repo_owner="my-org",
    ...     repo_name="my-repo",
    ...     branch_name="feat/auth",
    ...     actor="alice@example.com",
    ...     github_token="ghp_...",
    ... )
    >>>
    >>> workflow = Workflow(
    ...     name="feature-workflow",
    ...     steps=[
    ...         CommitBrick(
    ...             message="feat: Add auth",
    ...             files=["src/auth.py"],
    ...             author_name="Alice",
    ...             author_email="alice@example.com",
    ...         ),
    ...         PullRequestBrick(
    ...             title="feat: Add authentication",
    ...             body="Implements user auth",
    ...             base_branch="main",
    ...             head_branch="feat/auth",
    ...         ),
    ...         CodeReviewBrick(
    ...             pr_number=None,  # Uses metadata from PR brick
    ...             reviewer="bob",
    ...             action="approve",
    ...         ),
    ...         MergeBrick(
    ...             pr_number=None,
    ...             merge_method="squash",
    ...         ),
    ...     ],
    ... )
    >>>
    >>> # results = await workflow.execute(context)
"""

# Base classes
from azure_haymaker.workflow_bricks.base import BrickBase

# Core bricks
from azure_haymaker.workflow_bricks.bricks import (
    CIPipelineBrick,
    CodeReviewBrick,
    CommitBrick,
    MergeBrick,
    PullRequestBrick,
)

# Clients
from azure_haymaker.workflow_bricks.clients import GitHubClient

# Composers
from azure_haymaker.workflow_bricks.composers import Workflow

# Exceptions
from azure_haymaker.workflow_bricks.exceptions import (
    BrickError,
    BrickExecutionError,
    BrickTimeoutError,
    BrickValidationError,
)

# Models
from azure_haymaker.workflow_bricks.models import (
    BrickContext,
    BrickResult,
    BrickStatus,
    TelemetryEvent,
)

__all__ = [
    # Base
    "BrickBase",
    # Models
    "BrickContext",
    "BrickResult",
    "BrickStatus",
    "TelemetryEvent",
    # Bricks
    "CommitBrick",
    "PullRequestBrick",
    "CodeReviewBrick",
    "CIPipelineBrick",
    "MergeBrick",
    # Clients
    "GitHubClient",
    # Composers
    "Workflow",
    # Exceptions
    "BrickError",
    "BrickValidationError",
    "BrickExecutionError",
    "BrickTimeoutError",
]
