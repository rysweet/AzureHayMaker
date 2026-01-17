"""CIPipelineBrick - Triggers CI pipeline runs.

Simulates triggering a CI/CD pipeline (GitHub Actions workflow),
generating appropriate telemetry.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Literal

from azure_haymaker.workflow_bricks.base import BrickBase
from azure_haymaker.workflow_bricks.clients.github_client import GitHubClient
from azure_haymaker.workflow_bricks.exceptions import BrickValidationError
from azure_haymaker.workflow_bricks.models import BrickContext, BrickResult

logger = logging.getLogger(__name__)

# Type alias for workflow status
WorkflowStatus = Literal["success", "failure", "cancelled", "skipped"]


class CIPipelineBrick(BrickBase):
    """Brick that triggers a CI pipeline run.

    Triggers a GitHub Actions workflow and optionally waits for
    completion or simulates a specific outcome.

    Attributes:
        workflow_name: Workflow file name (e.g., "ci.yml")
        trigger_ref: Git ref to trigger on (e.g., "refs/heads/main")
        inputs: Optional workflow inputs
        expected_status: Status to simulate in dry_run mode
        duration_seconds: Simulated duration in dry_run mode
        wait_for_completion: Whether to wait for actual completion

    Example:
        >>> brick = CIPipelineBrick(
        ...     workflow_name="ci.yml",
        ...     trigger_ref="refs/heads/feat/auth",
        ...     inputs={"run_integration": "true"},
        ... )
        >>> result = await brick.execute(context)
        >>> print(result.outputs["run_id"])
    """

    def __init__(
        self,
        workflow_name: str,
        trigger_ref: str,
        inputs: dict[str, str] | None = None,
        expected_status: WorkflowStatus = "success",
        duration_seconds: int = 60,
        wait_for_completion: bool = False,
    ) -> None:
        """Initialize CIPipelineBrick.

        Args:
            workflow_name: Workflow file name
            trigger_ref: Git ref to trigger on
            inputs: Optional workflow inputs
            expected_status: Status to simulate in dry_run
            duration_seconds: Simulated duration in dry_run
            wait_for_completion: Wait for actual workflow completion
        """
        super().__init__()
        self.workflow_name = workflow_name
        self.trigger_ref = trigger_ref
        self.inputs = inputs or {}
        self.expected_status = expected_status
        self.duration_seconds = duration_seconds
        self.wait_for_completion = wait_for_completion

    async def validate(self, context: BrickContext) -> bool:
        """Validate pipeline preconditions.

        Checks that:
        - Workflow name is provided
        - Trigger ref is specified

        Args:
            context: Execution context

        Returns:
            True if validation passes

        Raises:
            BrickValidationError: If validation fails
        """
        if not self.workflow_name or not self.workflow_name.strip():
            raise BrickValidationError("Workflow name required")

        if not self.trigger_ref:
            raise BrickValidationError("Trigger ref required")

        if not context.github_token:
            raise BrickValidationError("GitHub token required")

        return True

    async def execute(self, context: BrickContext) -> BrickResult:
        """Execute the pipeline trigger.

        In real mode, triggers workflow via GitHub API.
        In dry_run mode, simulates the pipeline run.

        Args:
            context: Execution context

        Returns:
            BrickResult with run_id and workflow_status in outputs
        """
        result = self._create_result()

        try:
            if context.dry_run:
                run_data = await self._execute_dry_run(context)
            else:
                run_data = await self._execute_real(context)

            result.outputs["run_id"] = run_data["run_id"]
            result.outputs["workflow_name"] = self.workflow_name
            result.outputs["workflow_status"] = run_data["status"]
            result.outputs["trigger_ref"] = self.trigger_ref

            # Update context metadata
            context.metadata["last_workflow_run_id"] = run_data["run_id"]
            context.metadata["last_workflow_status"] = run_data["status"]

            # Log telemetry
            self._log_telemetry(
                result=result,
                event_type="triggered",
                context=context,
                target=f"{context.full_repo_name}/{self.workflow_name}",
                details={
                    "run_id": run_data["run_id"],
                    "status": run_data["status"],
                    "trigger_ref": self.trigger_ref,
                    "inputs": self.inputs,
                },
            )

            result.mark_success()

        except Exception as e:
            logger.exception(f"Pipeline trigger failed: {e}")
            result.mark_failed(str(e))

        return result

    async def _execute_dry_run(self, context: BrickContext) -> dict[str, Any]:
        """Execute in dry run mode (no API calls).

        Simulates a workflow run with the configured expected status.

        Args:
            context: Execution context

        Returns:
            Simulated run data
        """
        # Generate fake but realistic run ID
        fake_id = (
            abs(hash(f"{context.full_repo_name}-{self.workflow_name}-{uuid.uuid4().hex}"))
            % 10000000000
        )

        logger.info(
            f"[DRY RUN] Would trigger workflow {self.workflow_name} on {context.full_repo_name}"
        )
        logger.info(f"[DRY RUN] Ref: {self.trigger_ref}")
        if self.inputs:
            logger.info(f"[DRY RUN] Inputs: {self.inputs}")
        logger.info(f"[DRY RUN] Simulating {self.expected_status} after ~{self.duration_seconds}s")

        # Simulate some execution time (scaled down for testing)
        if self.duration_seconds > 0:
            # Wait a fraction of the actual time for simulation
            await asyncio.sleep(min(self.duration_seconds / 10, 2))

        return {
            "run_id": fake_id,
            "status": self.expected_status,
        }

    async def _execute_real(self, context: BrickContext) -> dict[str, Any]:
        """Execute real workflow trigger via GitHub API.

        Args:
            context: Execution context

        Returns:
            Run data including run_id and status
        """
        client = self._get_client(context)

        # Trigger the workflow
        await client.trigger_workflow(
            context.repo_owner,
            context.repo_name,
            self.workflow_name,
            self.trigger_ref,
            self.inputs if self.inputs else None,
        )

        logger.info(f"Triggered workflow {self.workflow_name} on {context.full_repo_name}")

        # Give GitHub a moment to create the run
        await asyncio.sleep(2)

        # Try to get the run ID from recent runs
        # Extract branch from ref (e.g., "refs/heads/main" -> "main")
        branch = self.trigger_ref
        if branch.startswith("refs/heads/"):
            branch = branch[11:]

        runs = await client.get_workflow_runs(
            context.repo_owner,
            context.repo_name,
            self.workflow_name,
            branch=branch,
            per_page=1,
        )

        run_id = None
        status = "queued"

        if runs.get("workflow_runs"):
            latest_run = runs["workflow_runs"][0]
            run_id = latest_run["id"]
            status = latest_run.get("status", "queued")

            # Optionally wait for completion
            if self.wait_for_completion:
                status = await self._wait_for_completion(client, context, run_id)

        return {
            "run_id": run_id or 0,
            "status": status,
        }

    async def _wait_for_completion(
        self,
        client: GitHubClient,
        context: BrickContext,
        run_id: int,
        max_wait_seconds: int = 600,
        poll_interval: int = 10,
    ) -> str:
        """Wait for workflow run to complete.

        Args:
            client: GitHub client
            context: Execution context
            run_id: Workflow run ID
            max_wait_seconds: Maximum time to wait
            poll_interval: Seconds between status checks

        Returns:
            Final workflow status
        """
        import time

        start_time = time.time()
        terminal_statuses = {"completed", "cancelled", "failure", "success", "skipped"}

        while time.time() - start_time < max_wait_seconds:
            runs = await client.get_workflow_runs(
                context.repo_owner,
                context.repo_name,
                per_page=1,
            )

            if runs.get("workflow_runs"):
                for run in runs["workflow_runs"]:
                    if run["id"] == run_id:
                        status = run.get("status", "")
                        conclusion = run.get("conclusion", "")

                        if status == "completed":
                            return conclusion or "success"

                        if status in terminal_statuses:
                            return status

            logger.debug(f"Waiting for workflow {run_id} to complete...")
            await asyncio.sleep(poll_interval)

        logger.warning(f"Timeout waiting for workflow {run_id}")
        return "timeout"

    def _get_client(self, context: BrickContext) -> GitHubClient:
        """Get or create GitHub client from context.

        Args:
            context: Execution context

        Returns:
            GitHubClient instance
        """
        if context.github_client is not None:
            return context.github_client

        return GitHubClient(token=context.github_token)


__all__ = ["CIPipelineBrick"]
