"""Workflow composition engine.

Composes multiple bricks into sequential workflows with
shared context and error handling.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from azure_haymaker.workflow_bricks.models import BrickContext, BrickResult, BrickStatus

if TYPE_CHECKING:
    from azure_haymaker.workflow_bricks.base import BrickBase

logger = logging.getLogger(__name__)


class Workflow:
    """Composes multiple bricks into a sequential workflow.

    Executes bricks in order, passing context between them.
    Stops on first failure unless configured otherwise.

    Attributes:
        name: Workflow name for logging and telemetry
        steps: List of bricks to execute in order
        stop_on_failure: Whether to stop on first failure

    Example:
        >>> workflow = Workflow(
        ...     name="feature-development",
        ...     steps=[
        ...         CommitBrick(message="feat: Add feature", ...),
        ...         PullRequestBrick(title="feat: Feature", ...),
        ...         CodeReviewBrick(pr_number=None, reviewer="bob", ...),
        ...         MergeBrick(pr_number=None, merge_method="squash"),
        ...     ],
        ... )
        >>> results = await workflow.execute(context)
        >>> assert all(r.status == BrickStatus.SUCCESS for r in results)
    """

    def __init__(
        self,
        name: str,
        steps: list[BrickBase],
        stop_on_failure: bool = True,
    ) -> None:
        """Initialize Workflow.

        Args:
            name: Workflow name
            steps: List of bricks to execute
            stop_on_failure: Stop on first failure (default True)
        """
        self.name = name
        self.steps = steps
        self.stop_on_failure = stop_on_failure

    async def execute(self, context: BrickContext) -> list[BrickResult]:
        """Execute all workflow steps in sequence.

        Each brick receives the shared context, which may be
        updated by previous bricks (e.g., pr_number set by
        PullRequestBrick for use by CodeReviewBrick).

        Args:
            context: Shared execution context

        Returns:
            List of BrickResult from each step
        """
        results: list[BrickResult] = []

        logger.info(f"Starting workflow '{self.name}' with {len(self.steps)} steps")

        for i, brick in enumerate(self.steps):
            step_num = i + 1
            logger.info(f"[{self.name}] Step {step_num}/{len(self.steps)}: {brick.name}")

            try:
                # Run the brick with shared context
                result = await brick.run(context)
                results.append(result)

                if result.status == BrickStatus.FAILED:
                    logger.error(
                        f"[{self.name}] Step {step_num} ({brick.name}) failed: {result.error}"
                    )
                    if self.stop_on_failure:
                        logger.info(f"[{self.name}] Stopping workflow due to failure")
                        break
                elif result.status == BrickStatus.SKIPPED:
                    logger.warning(
                        f"[{self.name}] Step {step_num} ({brick.name}) skipped: {result.error}"
                    )
                else:
                    logger.info(
                        f"[{self.name}] Step {step_num} ({brick.name}) completed successfully"
                    )

            except Exception as e:
                logger.exception(
                    f"[{self.name}] Step {step_num} ({brick.name}) raised exception: {e}"
                )
                # Create a failed result for the exception
                error_result = BrickResult(
                    status=BrickStatus.FAILED,
                    brick_name=brick.name,
                    error=str(e),
                )
                error_result.mark_failed(str(e))
                results.append(error_result)

                if self.stop_on_failure:
                    break

        # Log final summary
        succeeded = sum(1 for r in results if r.status == BrickStatus.SUCCESS)
        failed = sum(1 for r in results if r.status == BrickStatus.FAILED)
        skipped = sum(1 for r in results if r.status == BrickStatus.SKIPPED)

        logger.info(
            f"[{self.name}] Workflow complete: "
            f"{succeeded} succeeded, {failed} failed, {skipped} skipped"
        )

        return results

    def __repr__(self) -> str:
        """Return string representation."""
        step_names = [s.name for s in self.steps]
        return f"Workflow(name={self.name!r}, steps={step_names})"


__all__ = ["Workflow"]
