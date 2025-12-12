"""Workflow composition engine - combines bricks into executable workflows."""

import logging

from azure_haymaker.engineering_sim.bricks.base import (
    BrickContext,
    BrickExecutionError,
    BrickResult,
    BrickValidationError,
    WorkflowBrick,
)

logger = logging.getLogger(__name__)


class Workflow:
    """Composes multiple bricks into a sequential workflow.

    Args:
        name: Workflow name
        stop_on_failure: Whether to stop execution on first failure (default: True)
    """

    def __init__(self, name: str, stop_on_failure: bool = True):
        self.name = name
        self.bricks: list[WorkflowBrick] = []
        self.stop_on_failure = stop_on_failure

    def add_brick(self, brick: WorkflowBrick) -> "Workflow":
        """Add a brick to the workflow.

        Args:
            brick: WorkflowBrick to add

        Returns:
            Self for method chaining
        """
        self.bricks.append(brick)
        return self

    async def execute(self, context: BrickContext, stop_on_failure: bool = None) -> BrickResult:
        """Execute all bricks sequentially.

        Args:
            context: Initial workflow context
            stop_on_failure: Override default stop_on_failure behavior

        Returns:
            BrickResult with aggregated telemetry
        """
        # Use runtime parameter if provided, otherwise use instance default
        should_stop_on_failure = stop_on_failure if stop_on_failure is not None else self.stop_on_failure

        if not self.bricks:
            # Empty workflow returns success immediately
            return BrickResult(
                success=True,
                context=context,
                telemetry={"workflow": self.name, "bricks_executed": 0}
            )

        current_context = context
        aggregated_telemetry = {"workflow": self.name, "bricks": []}
        total_duration = 0.0

        for i, brick in enumerate(self.bricks):
            logger.info(f"Executing brick {i+1}/{len(self.bricks)}: {brick.name}")

            # Validate brick can execute with current context
            if not brick.validate(current_context):
                error_msg = f"Validation failed: Brick {brick.name}"
                logger.error(error_msg)

                if should_stop_on_failure:
                    return BrickResult(
                        success=False,
                        context=current_context,
                        telemetry=aggregated_telemetry,
                        error=error_msg,
                        duration_seconds=total_duration
                    )
                continue

            # Execute brick
            try:
                result = await brick.execute(current_context)

                # Update context for next brick
                current_context = result.context

                # Aggregate telemetry
                aggregated_telemetry["bricks"].append(result.telemetry)
                total_duration += result.duration_seconds

                # Handle brick failure
                if not result.success and should_stop_on_failure:
                    logger.error(f"Brick {brick.name} failed: {result.error}")
                    return BrickResult(
                        success=False,
                        context=current_context,
                        telemetry=aggregated_telemetry,
                        error=result.error,
                        duration_seconds=total_duration
                    )

            except (BrickExecutionError, BrickValidationError) as e:
                logger.error(f"Brick {brick.name} raised error: {e}")

                if should_stop_on_failure:
                    return BrickResult(
                        success=False,
                        context=current_context,
                        telemetry=aggregated_telemetry,
                        error=str(e),
                        duration_seconds=total_duration
                    )

        # All bricks completed successfully
        aggregated_telemetry["bricks_executed"] = len(self.bricks)

        return BrickResult(
            success=True,
            context=current_context,
            telemetry=aggregated_telemetry,
            duration_seconds=total_duration
        )

    def validate_all(self, context: BrickContext) -> list[str]:
        """Validate all bricks can execute with given context.

        Args:
            context: Context to validate

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []
        for brick in self.bricks:
            if not brick.validate(context):
                errors.append(f"{brick.name} validation failed")
        return errors

    def estimate_duration(self) -> float:
        """Estimate workflow duration in seconds.

        Returns:
            Estimated duration based on brick count (60s per brick)
        """
        # Rough estimate: 60 seconds per brick
        return len(self.bricks) * 60.0
