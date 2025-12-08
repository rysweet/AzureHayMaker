"""Base framework for workflow bricks.

This module defines the core abstractions for the brick-based workflow engine:
- BrickContext: Immutable context threading between bricks
- BrickResult: Result wrapper with telemetry
- WorkflowBrick: Abstract base class for all bricks
- Custom exceptions for error handling

Following the brick philosophy: small, composable, self-contained components.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Optional


class BrickExecutionError(Exception):
    """Exception raised when brick execution fails."""
    pass


class BrickValidationError(Exception):
    """Exception raised when brick validation fails."""
    pass


@dataclass(frozen=True)
class BrickContext:
    """Immutable context for workflow execution.

    Context threads through bricks, accumulating state as the workflow progresses.
    Each brick receives a context and returns an updated context via BrickResult.

    Args:
        team_id: Identifier for the team executing the workflow
        sprint_id: Identifier for the sprint
        repo_name: GitHub repository name
        branch_name: Git branch name (optional)
        pr_number: Pull request number (optional)
        commit_sha: Commit SHA (optional)
        base_branch: Base branch for PRs (default: "main")
        metadata: Additional metadata dict (default: empty dict)
    """
    team_id: str
    sprint_id: str
    repo_name: str
    branch_name: Optional[str] = None
    pr_number: Optional[int] = None
    commit_sha: Optional[str] = None
    base_branch: str = "main"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure metadata is never None."""
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

    def update(self, **kwargs: Any) -> "BrickContext":
        """Create new context with updated fields.

        Follows immutable pattern - returns new instance with updates,
        original context is unchanged.

        Args:
            **kwargs: Fields to update

        Returns:
            New BrickContext with updated fields

        Example:
            >>> context = BrickContext(team_id="alpha", sprint_id="s1", repo_name="api")
            >>> updated = context.update(branch_name="feature/auth")
            >>> assert context.branch_name is None
            >>> assert updated.branch_name == "feature/auth"
        """
        return replace(self, **kwargs)


@dataclass
class BrickResult:
    """Result of brick execution.

    Wraps execution result with:
    - Success status
    - Updated context (for threading)
    - Telemetry data
    - Optional error message
    - Execution duration

    Args:
        success: Whether execution succeeded
        context: Updated context after brick execution
        telemetry: Dict of telemetry data (metrics, metadata, etc.)
        error: Optional error message if execution failed
        duration_seconds: Execution time in seconds (default: 0.0)
    """
    success: bool
    context: BrickContext
    telemetry: Dict[str, Any]
    error: Optional[str] = None
    duration_seconds: float = 0.0

    def merge_telemetry(self, other: "BrickResult") -> "BrickResult":
        """Merge telemetry from another result.

        Creates new result with combined telemetry. Later keys overwrite
        earlier keys on conflict.

        Args:
            other: Another BrickResult to merge telemetry from

        Returns:
            New BrickResult with merged telemetry

        Example:
            >>> result1 = BrickResult(success=True, context=ctx, telemetry={"a": 1})
            >>> result2 = BrickResult(success=True, context=ctx, telemetry={"b": 2})
            >>> merged = result1.merge_telemetry(result2)
            >>> assert merged.telemetry == {"a": 1, "b": 2}
        """
        merged_telemetry = {**self.telemetry, **other.telemetry}
        return BrickResult(
            success=self.success and other.success,
            context=other.context,  # Use most recent context
            telemetry=merged_telemetry,
            error=self.error or other.error,
            duration_seconds=self.duration_seconds + other.duration_seconds
        )


class WorkflowBrick(ABC):
    """Abstract base class for workflow bricks.

    Bricks are composable units of work that:
    - Receive a BrickContext
    - Perform some action (commit, PR, review, etc.)
    - Return a BrickResult with updated context

    Subclasses must implement execute(). They may optionally override:
    - validate() for pre-execution validation
    - name property for custom naming

    Example:
        >>> class MyBrick(WorkflowBrick):
        ...     async def execute(self, context: BrickContext) -> BrickResult:
        ...         # Do work here
        ...         updated_context = context.update(branch_name="feature/x")
        ...         return BrickResult(
        ...             success=True,
        ...             context=updated_context,
        ...             telemetry={"action": "my_action"}
        ...         )
    """

    @abstractmethod
    async def execute(self, context: BrickContext) -> BrickResult:
        """Execute the brick's work.

        This is the core method that performs the brick's action.
        Must be implemented by all concrete bricks.

        Args:
            context: Current workflow context

        Returns:
            BrickResult with updated context and telemetry

        Raises:
            BrickExecutionError: If execution fails
        """
        pass

    def validate(self, context: BrickContext) -> bool:
        """Validate that context has required fields for execution.

        Default implementation returns True. Override in subclasses
        to enforce preconditions.

        Args:
            context: Current workflow context

        Returns:
            True if context is valid for this brick

        Raises:
            BrickValidationError: If validation fails with specific error

        Example:
            >>> class CommitBrick(WorkflowBrick):
            ...     def validate(self, context: BrickContext) -> bool:
            ...         return context.branch_name is not None
        """
        return True

    @property
    def name(self) -> str:
        """Brick name (defaults to class name).

        Returns:
            Human-readable brick name
        """
        return self.__class__.__name__

    def __repr__(self) -> str:
        """String representation of brick.

        Returns:
            Readable representation including brick name
        """
        return f"{self.name}()"
