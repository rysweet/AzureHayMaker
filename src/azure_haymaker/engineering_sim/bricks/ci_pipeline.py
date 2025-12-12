"""CIPipelineBrick - Simulates CI/CD pipeline execution."""

import logging
import random
import time
from datetime import datetime

from azure_haymaker.engineering_sim.bricks.base import (
    BrickContext,
    BrickExecutionError,
    BrickResult,
    WorkflowBrick,
)

logger = logging.getLogger(__name__)


class CIPipelineBrick(WorkflowBrick):
    """Simulates a CI/CD pipeline run.

    Args:
        github_client: Optional GitHubClient (not used, for consistency)
        pipeline_name: Name of pipeline (default: "ci")
        test_suite: Test suite to run (default: "full")
        failure_rate: Probability of pipeline failure 0.0-1.0 (default: 0.0)
        duration_seconds: Simulated pipeline duration (default: random 30-120s)
    """

    def __init__(
        self,
        github_client=None,  # Optional, for consistency with other bricks
        pipeline_name: str = "ci",
        workflow_name: str | None = None,  # Alias for pipeline_name
        test_suite: str = "full",
        failure_rate: float = 0.0,
        failure_probability: float | None = None,  # Alias for failure_rate
        duration_seconds: float | None = None,
        test_count_range: tuple | None = None  # Optional test count range
    ):
        self.github_client = github_client
        self.pipeline_name = workflow_name or pipeline_name
        self.test_suite = test_suite
        self.failure_rate = failure_probability if failure_probability is not None else failure_rate
        self.duration_seconds = duration_seconds
        self.test_count_range = test_count_range or (50, 150)

    def validate(self, context: BrickContext) -> bool:
        """Validate that context has commit_sha or pr_number."""
        return context.commit_sha is not None or context.pr_number is not None

    async def execute(self, context: BrickContext) -> BrickResult:
        """Simulate CI/CD pipeline execution.

        Args:
            context: Current workflow context

        Returns:
            BrickResult with pipeline telemetry

        Raises:
            BrickExecutionError: If pipeline execution fails
        """
        start_time = time.time()

        try:
            if not self.validate(context):
                raise BrickExecutionError(
                    "CIPipelineBrick requires commit_sha or pr_number in context"
                )

            # Determine pipeline duration
            duration = self.duration_seconds or random.uniform(30, 120)

            # Simulate pipeline execution (don't actually wait)
            # In real simulation, you might await asyncio.sleep(duration)

            # Determine if pipeline succeeds or fails
            failed = random.random() < self.failure_rate

            if failed:
                status = "failure"
                conclusion = "failure"
                tests_passed = random.randint(50, 90)
                tests_failed = random.randint(1, 5)
                tests_total = tests_passed + tests_failed
            else:
                status = "success"
                conclusion = "success"
                min_tests, max_tests = self.test_count_range
                tests_total = random.randint(min_tests, max_tests)
                tests_passed = tests_total
                tests_failed = 0

            # Build telemetry
            telemetry = {
                "brick_type": "ci_pipeline",
                "pipeline_name": self.pipeline_name,
                "test_suite": self.test_suite,
                "status": status,
                "conclusion": conclusion,
                "tests_total": tests_total,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat(),
            }

            # Update context metadata with CI status
            updated_metadata = {**context.metadata, "ci_status": status, "ci_passed": not failed}
            updated_context = context.update(metadata=updated_metadata)

            if failed:
                logger.warning(
                    f"CI pipeline {self.pipeline_name} FAILED: "
                    f"{tests_failed}/{tests_total} tests failed"
                )
                return BrickResult(
                    success=False,
                    context=updated_context,
                    telemetry=telemetry,
                    error=f"CI pipeline failed: {tests_failed} test(s) failed",
                    duration_seconds=duration
                )
            else:
                logger.info(
                    f"CI pipeline {self.pipeline_name} passed: "
                    f"{tests_passed}/{tests_total} tests"
                )
                return BrickResult(
                    success=True,
                    context=updated_context,
                    telemetry=telemetry,
                    duration_seconds=duration
                )

        except BrickExecutionError:
            raise

        except Exception as e:
            duration = time.time() - start_time
            raise BrickExecutionError(
                f"Unexpected error in CIPipelineBrick: {str(e)}"
            ) from e
