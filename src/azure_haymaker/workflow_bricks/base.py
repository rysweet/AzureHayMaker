"""Base class for workflow bricks.

Provides the abstract base class that all bricks inherit from,
defining the standard lifecycle: validate -> execute -> cleanup.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from azure_haymaker.workflow_bricks.models import BrickContext, BrickResult, BrickStatus

logger = logging.getLogger(__name__)


class BrickBase(ABC):
    """Abstract base class for workflow bricks.

    All bricks inherit from this class and implement the standard lifecycle:
    1. validate(context) - Check preconditions before execution
    2. execute(context) - Perform the main action
    3. cleanup(context, result) - Optional post-execution cleanup

    The run() method orchestrates this lifecycle and handles errors.

    Attributes:
        name: Human-readable name of the brick (auto-generated from class name)

    Example:
        >>> class MyBrick(BrickBase):
        ...     async def validate(self, context: BrickContext) -> bool:
        ...         return True
        ...
        ...     async def execute(self, context: BrickContext) -> BrickResult:
        ...         result = self._create_result()
        ...         result.mark_success({"output": "value"})
        ...         return result
        ...
        >>> brick = MyBrick()
        >>> result = await brick.run(context)
    """

    def __init__(self) -> None:
        """Initialize the brick."""
        # Auto-generate name from class name
        self._name = self.__class__.__name__

    @property
    def name(self) -> str:
        """Get the brick name."""
        return self._name

    def _create_result(self) -> BrickResult:
        """Create a new BrickResult for this brick.

        Returns:
            A new BrickResult with pending status.
        """
        return BrickResult(
            status=BrickStatus.PENDING,
            brick_name=self.name,
            started_at=datetime.now(UTC),
        )

    @abstractmethod
    async def validate(self, context: BrickContext) -> bool:
        """Validate preconditions for execution.

        This method should check that all required data is present
        and the context is valid for this brick's operation.

        Args:
            context: The execution context.

        Returns:
            True if validation passes.

        Raises:
            BrickValidationError: If validation fails.
        """
        ...

    @abstractmethod
    async def execute(self, context: BrickContext) -> BrickResult:
        """Execute the brick's main action.

        This method performs the actual work of the brick.
        It should create a BrickResult, perform the action,
        and mark the result as success or failure.

        Args:
            context: The execution context.

        Returns:
            BrickResult with the execution outcome.
        """
        ...

    async def cleanup(self, context: BrickContext, result: BrickResult) -> None:
        """Optional cleanup after execution.

        Override this method to perform any cleanup needed after
        the brick executes, regardless of success or failure.

        Args:
            context: The execution context.
            result: The execution result.
        """
        # Default implementation does nothing - subclasses can override
        _ = (context, result)  # Mark as intentionally unused

    async def run(self, context: BrickContext) -> BrickResult:
        """Run the complete brick lifecycle.

        Orchestrates validate -> execute -> cleanup and handles errors.

        Args:
            context: The execution context.

        Returns:
            BrickResult with the execution outcome.
        """
        result = self._create_result()

        try:
            # Validation
            logger.debug(f"Validating {self.name}")
            await self.validate(context)

            # Execution
            logger.info(f"Executing {self.name}")
            result = await self.execute(context)

        except Exception as e:
            logger.exception(f"{self.name} failed: {e}")
            result.mark_failed(str(e))

        finally:
            # Cleanup always runs
            try:
                await self.cleanup(context, result)
            except Exception as cleanup_error:
                logger.warning(f"{self.name} cleanup failed: {cleanup_error}")

        return result

    def _log_telemetry(
        self,
        result: BrickResult,
        event_type: str,
        context: BrickContext,
        target: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add telemetry event to result.

        Helper method to add telemetry events with consistent formatting.

        Args:
            result: The brick result to add telemetry to.
            event_type: Type of event (e.g., "commit.created").
            context: The execution context.
            target: What the action was performed on.
            details: Additional event details.
        """
        result.add_telemetry(
            event_type=f"brick.{self.name.lower()}.{event_type}",
            actor=context.actor,
            target=target,
            details={
                "tenant_id": context.tenant_id,
                "team_id": context.team_id,
                "repo": context.full_repo_name,
                "dry_run": context.dry_run,
                **(details or {}),
            },
        )


__all__ = ["BrickBase"]
