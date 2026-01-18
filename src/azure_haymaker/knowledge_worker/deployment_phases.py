"""Deployment phase management for knowledge worker orchestrator.

This module handles the three main deployment phases:
1. Setup - Create security groups and grant permissions
2. Provision - Create workers via provisioning service
3. Execute - Start worker activities via execution service

Philosophy:
- Single responsibility: Deployment phase coordination
- Thin coordination layer (delegates to specialized services)
- Clean separation of concerns
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from azure_haymaker.knowledge_worker.activity_execution import ActivityExecutionService
from azure_haymaker.knowledge_worker.agent import KnowledgeWorkerAgent
from azure_haymaker.knowledge_worker.cleanup import KnowledgeWorkerResourceInventory
from azure_haymaker.knowledge_worker.email_content_service import EmailContentService
from azure_haymaker.knowledge_worker.identity import (
    EntraGroupManager,
    PermissionGranter,
)
from azure_haymaker.knowledge_worker.state_manager import DeploymentStateManager
from azure_haymaker.knowledge_worker.worker_provisioning import (
    WorkerProvisioningService,
)

if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient

logger = logging.getLogger(__name__)


@dataclass
class DeploymentPhaseContext:
    """Context for deployment phase execution.

    Attributes:
        run_id: Deployment run ID
        tenant_domain: M365 tenant domain
        m365_app_id: M365 application ID
        departments: Department configurations
        duration_hours: How long to run activities
        workers: List of deployed workers
        inventory: Resource inventory for cleanup
        state_manager: State manager for persistence
    """

    run_id: str
    tenant_domain: str
    m365_app_id: str
    departments: dict[str, dict[str, Any]]
    duration_hours: int
    workers: list[KnowledgeWorkerAgent] = field(default_factory=list)
    inventory: KnowledgeWorkerResourceInventory | None = None
    state_manager: DeploymentStateManager | None = None


class DeploymentPhaseManager:
    """Manages deployment phases for knowledge worker orchestrator.

    Coordinates the three main phases: setup, provision, execute.

    Example:
        >>> manager = DeploymentPhaseManager(
        ...     graph_client=graph_client,
        ...     email_content_service=email_service
        ... )
        >>> context = DeploymentPhaseContext(...)
        >>> await manager.run_setup_phase(context)
        >>> await manager.run_provision_phase(context)
        >>> await manager.run_execute_phase(context)
    """

    def __init__(
        self,
        graph_client: "GraphServiceClient",
        email_content_service: EmailContentService,
    ) -> None:
        """Initialize the deployment phase manager.

        Args:
            graph_client: Microsoft Graph API client
            email_content_service: Service for generating email content
        """
        self._graph_client = graph_client
        self._email_content_service = email_content_service
        self._worker_tasks: dict[str, list[asyncio.Task]] = {}

    async def run_setup_phase(self, context: DeploymentPhaseContext) -> None:
        """Setup phase: Create security infrastructure.

        Args:
            context: Deployment phase context
        """
        logger.info(f"[{context.run_id}] Starting setup phase")

        # Create all-workers security group for deployment
        await self._create_security_group(context)

        # Grant Mail.ReadWrite and Mail.Send permissions
        await self._ensure_mail_permission_granted(context)

        logger.info(f"[{context.run_id}] Setup phase complete")

    async def run_provision_phase(self, context: DeploymentPhaseContext) -> None:
        """Provision phase: Create Entra users and initialize workers.

        Args:
            context: Deployment phase context

        Raises:
            ValueError: If tenant_domain not configured
        """
        logger.info(f"[{context.run_id}] Starting provisioning phase")

        # Validate tenant configuration
        if not context.tenant_domain:
            raise ValueError(
                "tenant_domain is required. Set this in DeploymentConfig to match your M365 tenant."
            )

        # Create provisioning service
        provisioning_service = WorkerProvisioningService(
            graph_client=self._graph_client,
            run_id=context.run_id,
            tenant_domain=context.tenant_domain,
        )

        # Provision workers
        assert context.state_manager is not None, "State manager must be set"
        context.workers = await provisioning_service.provision_workers(
            departments=context.departments,
            m365_app_id=context.m365_app_id,
            inventory=context.inventory,
            state_manager=context.state_manager,
        )

        logger.info(
            f"[{context.run_id}] Provisioning complete: {len(context.workers)} workers created"
        )

    async def run_execute_phase(self, context: DeploymentPhaseContext) -> None:
        """Execute phase: Start worker M365 activity generation.

        Launches async tasks for each worker to generate M365 activities
        (emails, calendar events) at configured intervals.

        Args:
            context: Deployment phase context
        """
        logger.info(f"[{context.run_id}] Starting execution phase")

        # Create activity execution service
        execution_service = ActivityExecutionService(self._email_content_service)

        # Create worker tasks
        tasks = []
        for worker in context.workers:
            task = asyncio.create_task(
                execution_service.run_worker(worker, context.duration_hours)
            )
            tasks.append(task)

        self._worker_tasks[context.run_id] = tasks

        logger.info(
            f"[{context.run_id}] Started {len(tasks)} worker tasks "
            f"(duration: {context.duration_hours}h)"
        )

    async def stop_worker_tasks(self, run_id: str) -> None:
        """Stop all worker tasks for a deployment.

        Args:
            run_id: Deployment run ID
        """
        tasks = self._worker_tasks.get(run_id, [])
        for task in tasks:
            task.cancel()

        # Wait for tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _ensure_mail_permission_granted(
        self, context: DeploymentPhaseContext
    ) -> None:
        """Ensure Mail.ReadWrite permission is granted to the KW app.

        Idempotent - safe to call multiple times. Logs warning on failure
        but does not block deployment.

        Args:
            context: Deployment phase context
        """
        try:
            # Get app ID from config or environment
            app_id = context.m365_app_id or os.getenv("KW_APP_ID", "")
            if not app_id:
                logger.warning(
                    f"[{context.run_id}] No app ID configured. "
                    "Skipping Mail.ReadWrite permission grant."
                )
                return

            logger.info(
                f"[{context.run_id}] Ensuring Mail.ReadWrite permission for app {app_id}"
            )

            granter = PermissionGranter(self._graph_client, app_id)
            success = await granter.ensure_mail_permission()

            if not success:
                logger.warning(
                    f"[{context.run_id}] Failed to grant Mail.ReadWrite permission. "
                    "Email operations may fail."
                )

        except Exception as e:
            logger.error(f"[{context.run_id}] Permission grant error: {e}")

    async def _create_security_group(self, context: DeploymentPhaseContext) -> None:
        """Create all-workers security group for deployment.

        Creates a security group containing all workers for easier
        management and potential transport rule application.

        Args:
            context: Deployment phase context
        """
        try:
            group_manager = EntraGroupManager(self._graph_client, context.run_id)

            group_id = await group_manager.create_all_workers_group(
                description=f"All workers for deployment"
            )

            logger.info(
                f"[{context.run_id}] Created all-workers security group: {group_id}"
            )

        except Exception as e:
            logger.warning(f"[{context.run_id}] Failed to create security group: {e}")
            logger.warning(
                "Continuing without security group - not critical for functionality"
            )


__all__ = ["DeploymentPhaseContext", "DeploymentPhaseManager"]
