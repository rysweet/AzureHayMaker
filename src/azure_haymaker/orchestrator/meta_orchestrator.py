"""Phase 3 Meta-Orchestrator for multi-tenant parallel execution.

This module provides the MetaOrchestrator for executing orchestration runs
across multiple tenants in parallel. It uses a FanOutController pattern
to manage parallelism with configurable limits.

Architecture:
    MetaOrchestrator
    ├── validate_tenants() → checks tenant IDs against registry
    ├── execute() → creates FanOutController, aggregates results
    └── FanOutController
        ├── _semaphore: asyncio.Semaphore(max_parallelism)
        ├── execute() → spawns async tasks for each tenant
        └── _execute_for_tenant() → calls run_orchestration(tenant_config=...)

Usage:
    >>> from azure_haymaker.orchestrator.meta_orchestrator import (
    ...     MetaOrchestrator, MetaExecutionRequest, FailureMode
    ... )
    >>> request = MetaExecutionRequest(
    ...     tenant_ids=["tenant-1", "tenant-2"],
    ...     scenarios=["compute-01-linux-vm"],
    ...     failure_mode=FailureMode.CONTINUE,
    ... )
    >>> result = await MetaOrchestrator.execute(config, request)
    >>> print(f"Succeeded: {result.succeeded_count}/{result.total_tenants}")
"""

import asyncio
import logging
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from azure_haymaker.models.config import OrchestratorConfig, TenantConfig
from azure_haymaker.utils.credentials import MultiTenantCredentialFactory

logger = logging.getLogger(__name__)


class FailureMode(str, Enum):
    """Controls behavior when a tenant execution fails.

    CONTINUE: Continue executing remaining tenants even if some fail.
    FAIL_FAST: Stop execution immediately on first failure.
    """

    CONTINUE = "continue"
    FAIL_FAST = "fail_fast"


class TenantExecutionState(str, Enum):
    """State of execution for a single tenant."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TenantExecutionStatus(BaseModel):
    """Execution status for a single tenant within a meta-execution."""

    tenant_id: str = Field(..., description="Azure tenant ID")
    tenant_display_name: str | None = Field(default=None, description="Human-readable tenant name")
    state: TenantExecutionState = Field(
        default=TenantExecutionState.PENDING, description="Current execution state"
    )
    execution_id: str | None = Field(
        default=None, description="Per-tenant execution ID (from run_orchestration)"
    )
    started_at: datetime | None = Field(default=None, description="Execution start time")
    completed_at: datetime | None = Field(default=None, description="Execution end time")
    error_message: str | None = Field(default=None, description="Error message if execution failed")
    scenarios_completed: int = Field(default=0, description="Number of scenarios completed")
    scenarios_failed: int = Field(default=0, description="Number of scenarios that failed")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class MetaExecutionRequest(BaseModel):
    """Request to execute orchestration across multiple tenants.

    Example:
        >>> request = MetaExecutionRequest(
        ...     tenant_ids=["tenant-1", "tenant-2"],
        ...     scenarios=["compute-01-linux-vm"],
        ...     duration_hours=8,
        ...     max_parallelism=5,
        ...     failure_mode=FailureMode.CONTINUE,
        ... )
    """

    tenant_ids: list[str] = Field(
        ...,
        description="List of tenant IDs to execute on",
        min_length=1,
    )
    scenarios: list[str] | None = Field(
        default=None,
        description="Specific scenarios to run (None = use default selection)",
    )
    scenario_count: int | None = Field(
        default=None,
        description="Number of scenarios to select if scenarios not specified",
        ge=1,
        le=30,
    )
    duration_hours: int = Field(
        default=8,
        description="Execution duration in hours",
        ge=1,
        le=24,
    )
    max_parallelism: int = Field(
        default=10,
        description="Maximum number of tenants to execute in parallel",
        ge=1,
        le=50,
    )
    failure_mode: FailureMode = Field(
        default=FailureMode.CONTINUE,
        description="How to handle tenant execution failures",
    )
    skip_validation: bool = Field(
        default=False,
        description="Skip environment validation for each tenant",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Optional tags for tracking",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "tenant_ids": ["tenant-abc-123", "tenant-def-456"],
                "scenarios": ["compute-01-linux-vm-web-server"],
                "duration_hours": 8,
                "max_parallelism": 10,
                "failure_mode": "continue",
            }
        }


class MetaExecutionResult(BaseModel):
    """Result of a multi-tenant meta-execution.

    Example:
        >>> result = await MetaOrchestrator.execute(config, request)
        >>> if result.all_succeeded:
        ...     print("All tenants completed successfully")
        >>> else:
        ...     for status in result.tenant_statuses:
        ...         if status.state == TenantExecutionState.FAILED:
        ...             print(f"Failed: {status.tenant_id}: {status.error_message}")
    """

    meta_execution_id: str = Field(..., description="Unique ID for this meta-execution")
    started_at: datetime = Field(..., description="Meta-execution start time")
    completed_at: datetime | None = Field(
        default=None, description="Meta-execution completion time"
    )
    total_tenants: int = Field(..., description="Total number of tenants in request")
    succeeded_count: int = Field(default=0, description="Number of tenants that succeeded")
    failed_count: int = Field(default=0, description="Number of tenants that failed")
    skipped_count: int = Field(default=0, description="Number of tenants skipped")
    tenant_statuses: list[TenantExecutionStatus] = Field(
        default_factory=list,
        description="Status for each tenant",
    )
    failure_mode: FailureMode = Field(..., description="Failure mode used")
    aborted_early: bool = Field(
        default=False,
        description="True if execution stopped early due to FAIL_FAST mode",
    )

    @property
    def all_succeeded(self) -> bool:
        """Check if all tenants completed successfully."""
        return self.failed_count == 0 and self.skipped_count == 0

    @property
    def duration_seconds(self) -> float | None:
        """Get execution duration in seconds, or None if not completed."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class FanOutController:
    """Controls parallel execution across multiple tenants.

    Uses asyncio.Semaphore to limit concurrent executions to max_parallelism.
    Supports CONTINUE and FAIL_FAST failure modes.

    Example:
        >>> controller = FanOutController(max_parallelism=5)
        >>> statuses = await controller.execute(
        ...     tenants=[tenant1, tenant2, tenant3],
        ...     execute_fn=some_async_function,
        ...     failure_mode=FailureMode.CONTINUE,
        ... )
    """

    def __init__(self, max_parallelism: int = 10):
        """Initialize the FanOutController.

        Args:
            max_parallelism: Maximum concurrent tenant executions (default 10)
        """
        self._max_parallelism = max_parallelism
        self._semaphore = asyncio.Semaphore(max_parallelism)
        self._abort_event = asyncio.Event()
        self._first_failure: Exception | None = None

    async def execute(
        self,
        config: OrchestratorConfig,
        tenants: list[TenantConfig],
        request: MetaExecutionRequest,
        run_orchestration_fn,
    ) -> list[TenantExecutionStatus]:
        """Execute orchestration for multiple tenants in parallel.

        Args:
            config: Base orchestrator configuration
            tenants: List of tenant configurations to execute
            request: Meta-execution request with parameters
            run_orchestration_fn: The run_orchestration function to call

        Returns:
            List of TenantExecutionStatus for each tenant
        """
        logger.info(
            f"FanOutController: Starting execution for {len(tenants)} tenants "
            f"(max_parallelism={self._max_parallelism})"
        )

        # Create tasks for each tenant
        tasks = [
            self._execute_for_tenant(
                config=config,
                tenant=tenant,
                request=request,
                run_orchestration_fn=run_orchestration_fn,
            )
            for tenant in tenants
        ]

        # Execute all tasks (semaphore limits actual parallelism)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results into TenantExecutionStatus list
        statuses = []
        for i, result in enumerate(results):
            if isinstance(result, TenantExecutionStatus):
                statuses.append(result)
            elif isinstance(result, Exception):
                # Task itself raised an exception (shouldn't happen normally)
                statuses.append(
                    TenantExecutionStatus(
                        tenant_id=tenants[i].tenant_id,
                        tenant_display_name=tenants[i].display_name,
                        state=TenantExecutionState.FAILED,
                        error_message=f"Unexpected error: {str(result)}",
                    )
                )

        return statuses

    async def _execute_for_tenant(
        self,
        config: OrchestratorConfig,
        tenant: TenantConfig,
        request: MetaExecutionRequest,
        run_orchestration_fn,
    ) -> TenantExecutionStatus:
        """Execute orchestration for a single tenant.

        Args:
            config: Base orchestrator configuration
            tenant: Tenant configuration to execute
            request: Meta-execution request with parameters
            run_orchestration_fn: The run_orchestration function to call

        Returns:
            TenantExecutionStatus with execution result
        """
        status = TenantExecutionStatus(
            tenant_id=tenant.tenant_id,
            tenant_display_name=tenant.display_name,
            state=TenantExecutionState.PENDING,
        )

        # Check if we should abort (FAIL_FAST mode)
        if self._abort_event.is_set():
            status.state = TenantExecutionState.SKIPPED
            status.error_message = "Skipped due to FAIL_FAST abort"
            return status

        async with self._semaphore:
            # Double-check abort after acquiring semaphore
            if self._abort_event.is_set():
                status.state = TenantExecutionState.SKIPPED
                status.error_message = "Skipped due to FAIL_FAST abort"
                return status

            status.state = TenantExecutionState.RUNNING
            status.started_at = datetime.now(UTC)
            run_id = str(uuid4())
            status.execution_id = run_id

            logger.info(f"Starting execution for tenant {tenant.display}: run_id={run_id}")

            try:
                # Get credential for this tenant
                credential = MultiTenantCredentialFactory.get_credential_for_tenant(tenant)

                # Build tenant_config dict to pass to run_orchestration
                tenant_config = {
                    "tenant_id": tenant.tenant_id,
                    "subscription_id": tenant.subscription_id,
                    "credential": credential,
                    "resource_group": tenant.resource_group,
                }

                # Call the run_orchestration function
                await run_orchestration_fn(
                    run_id=run_id,
                    skip_validation=request.skip_validation,
                    scenario_names=request.scenarios,
                    scenario_count=request.scenario_count,
                    tenant_config=tenant_config,
                )

                status.state = TenantExecutionState.COMPLETED
                status.completed_at = datetime.now(UTC)
                logger.info(f"Completed execution for tenant {tenant.display}: run_id={run_id}")

            except Exception as e:
                status.state = TenantExecutionState.FAILED
                status.error_message = str(e)
                status.completed_at = datetime.now(UTC)
                logger.error(
                    f"Failed execution for tenant {tenant.display}: {e}",
                    exc_info=True,
                )

                # Signal abort if FAIL_FAST mode
                if request.failure_mode == FailureMode.FAIL_FAST and not self._abort_event.is_set():
                    self._first_failure = e
                    self._abort_event.set()
                    logger.warning("FAIL_FAST: Aborting remaining tenant executions")

            return status


class MetaOrchestrator:
    """Orchestrates execution across multiple tenants.

    This is the main entry point for Phase 3 multi-tenant orchestration.
    It validates tenant IDs, creates a FanOutController, and aggregates results.

    Example:
        >>> config = await load_config_with_tenants()
        >>> request = MetaExecutionRequest(
        ...     tenant_ids=["tenant-1", "tenant-2"],
        ...     scenarios=["compute-01-linux-vm"],
        ... )
        >>> result = await MetaOrchestrator.execute(config, request)
        >>> print(f"Success rate: {result.succeeded_count}/{result.total_tenants}")
    """

    @classmethod
    def validate_tenants(
        cls,
        config: OrchestratorConfig,
        tenant_ids: list[str],
    ) -> tuple[list[TenantConfig], list[str]]:
        """Validate tenant IDs against the registry.

        Args:
            config: Orchestrator configuration with tenant registry
            tenant_ids: List of tenant IDs to validate

        Returns:
            Tuple of (valid_tenants, invalid_tenant_ids)

        Example:
            >>> valid, invalid = MetaOrchestrator.validate_tenants(config, ["t1", "t2"])
            >>> if invalid:
            ...     print(f"Unknown tenants: {invalid}")
        """
        valid_tenants = []
        invalid_ids = []

        for tenant_id in tenant_ids:
            tenant = config.get_tenant_config(tenant_id)
            if tenant:
                valid_tenants.append(tenant)
            else:
                # Check if tenant exists but is disabled
                if tenant_id in config.tenants:
                    disabled_tenant = config.tenants[tenant_id]
                    logger.warning(f"Tenant {disabled_tenant.display} is disabled, skipping")
                invalid_ids.append(tenant_id)

        return valid_tenants, invalid_ids

    @classmethod
    async def execute(
        cls,
        config: OrchestratorConfig,
        request: MetaExecutionRequest,
        run_orchestration_fn=None,
    ) -> MetaExecutionResult:
        """Execute orchestration across multiple tenants.

        This is the main entry point for multi-tenant execution. It:
        1. Validates all tenant IDs against the registry
        2. Creates a FanOutController with configured parallelism
        3. Executes orchestration for each tenant
        4. Aggregates and returns results

        Args:
            config: Orchestrator configuration with tenant registry
            request: Meta-execution request specifying tenants and parameters
            run_orchestration_fn: Optional override for run_orchestration function
                                 (useful for testing). If None, imports from
                                 orchestrator_server.

        Returns:
            MetaExecutionResult with aggregated status and per-tenant details

        Raises:
            ValueError: If no valid tenants found in request

        Example:
            >>> result = await MetaOrchestrator.execute(config, request)
            >>> if result.all_succeeded:
            ...     print("All tenants completed successfully!")
            >>> else:
            ...     for status in result.tenant_statuses:
            ...         if status.state == TenantExecutionState.FAILED:
            ...             print(f"{status.tenant_id}: {status.error_message}")
        """
        meta_execution_id = str(uuid4())
        started_at = datetime.now(UTC)

        logger.info(
            f"Starting meta-execution {meta_execution_id} for {len(request.tenant_ids)} tenants"
        )

        # Validate tenants
        valid_tenants, invalid_ids = cls.validate_tenants(config, request.tenant_ids)

        if not valid_tenants:
            raise ValueError(f"No valid tenants found. Invalid/disabled tenant IDs: {invalid_ids}")

        if invalid_ids:
            logger.warning(
                f"Meta-execution {meta_execution_id}: Skipping invalid tenant IDs: {invalid_ids}"
            )

        # Import run_orchestration if not provided
        if run_orchestration_fn is None:
            # Late import to avoid circular dependency
            from orchestrator_server import run_orchestration

            run_orchestration_fn = run_orchestration

        # Create FanOutController and execute
        controller = FanOutController(max_parallelism=request.max_parallelism)
        tenant_statuses = await controller.execute(
            config=config,
            tenants=valid_tenants,
            request=request,
            run_orchestration_fn=run_orchestration_fn,
        )

        # Add statuses for invalid tenants
        for invalid_id in invalid_ids:
            tenant_statuses.append(
                TenantExecutionStatus(
                    tenant_id=invalid_id,
                    state=TenantExecutionState.SKIPPED,
                    error_message="Tenant not found or disabled in registry",
                )
            )

        # Aggregate results
        succeeded = sum(1 for s in tenant_statuses if s.state == TenantExecutionState.COMPLETED)
        failed = sum(1 for s in tenant_statuses if s.state == TenantExecutionState.FAILED)
        skipped = sum(1 for s in tenant_statuses if s.state == TenantExecutionState.SKIPPED)

        completed_at = datetime.now(UTC)

        result = MetaExecutionResult(
            meta_execution_id=meta_execution_id,
            started_at=started_at,
            completed_at=completed_at,
            total_tenants=len(request.tenant_ids),
            succeeded_count=succeeded,
            failed_count=failed,
            skipped_count=skipped,
            tenant_statuses=tenant_statuses,
            failure_mode=request.failure_mode,
            aborted_early=controller._abort_event.is_set(),
        )

        # Log summary
        duration = result.duration_seconds
        logger.info(
            f"Meta-execution {meta_execution_id} completed in {duration:.1f}s: "
            f"succeeded={succeeded}, failed={failed}, skipped={skipped}"
        )

        return result


__all__ = [
    "FailureMode",
    "TenantExecutionState",
    "TenantExecutionStatus",
    "MetaExecutionRequest",
    "MetaExecutionResult",
    "FanOutController",
    "MetaOrchestrator",
]
