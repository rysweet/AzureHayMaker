"""Worker provisioning service for knowledge worker deployments.

This module handles the creation of Entra users, worker registration,
and distribution of allowed recipients.

Philosophy:
- Single responsibility: Worker provisioning
- Coordinates user creation, registry, and recipient distribution
- Clean separation from orchestration logic
"""

import logging
from typing import TYPE_CHECKING

from azure_haymaker.knowledge_worker.agent import (
    KnowledgeWorkerAgent,
    KnowledgeWorkerConfig,
)
from azure_haymaker.knowledge_worker.cleanup import KnowledgeWorkerResourceInventory
from azure_haymaker.knowledge_worker.models.worker import (
    WorkerConfig,
    WorkerPersona,
)
from azure_haymaker.knowledge_worker.state_manager import DeploymentStateManager
from azure_haymaker.knowledge_worker.worker_registry import WorkerRegistry

if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient

    from azure_haymaker.knowledge_worker.identity.user_manager import EntraUserManager

logger = logging.getLogger(__name__)


class WorkerProvisioningService:
    """Handles worker provisioning for deployments.

    Creates Entra users, registers workers in registry, and distributes
    allowed recipients to all workers.

    Example:
        >>> service = WorkerProvisioningService(
        ...     graph_client=graph_client,
        ...     run_id="kw-abc123",
        ...     tenant_domain="test.onmicrosoft.com"
        ... )
        >>> workers = await service.provision_workers(
        ...     departments={"engineering": {"count": 5}},
        ...     m365_app_id="app-id-123",
        ...     inventory=inventory,
        ...     state_manager=state_manager
        ... )
    """

    def __init__(
        self,
        graph_client: "GraphServiceClient",
        run_id: str,
        tenant_domain: str,
    ) -> None:
        """Initialize the worker provisioning service.

        Args:
            graph_client: Microsoft Graph API client
            run_id: Deployment run ID
            tenant_domain: M365 tenant domain
        """
        self._graph_client = graph_client
        self._run_id = run_id
        self._tenant_domain = tenant_domain
        self._user_manager: EntraUserManager | None = None
        self._worker_registry: WorkerRegistry | None = None

    async def provision_workers(
        self,
        departments: dict[str, dict],
        m365_app_id: str,
        inventory: KnowledgeWorkerResourceInventory | None,
        state_manager: DeploymentStateManager,
    ) -> list[KnowledgeWorkerAgent]:
        """Provision workers for all departments.

        Creates Entra users, registers workers, and distributes allowed recipients.

        Args:
            departments: Department configurations
            m365_app_id: M365 application ID
            inventory: Resource inventory for cleanup tracking
            state_manager: State manager for persistence

        Returns:
            List of created KnowledgeWorkerAgent instances
        """
        # Import here to avoid circular imports
        from azure_haymaker.knowledge_worker.identity.user_manager import (
            EntraUserManager,
        )

        # Initialize user manager and registry
        self._user_manager = EntraUserManager(
            graph_client=self._graph_client,
            run_id=self._run_id,
            tenant_domain=self._tenant_domain,
        )
        self._worker_registry = WorkerRegistry(run_id=self._run_id)

        logger.info(f"[{self._run_id}] Provisioning Entra users")

        workers: list[KnowledgeWorkerAgent] = []

        # Provision workers for each department
        for dept, dept_config in departments.items():
            count = dept_config.get("count", 5)
            activity = dept_config.get("activity", {})

            for i in range(count):
                worker = await self._provision_single_worker(
                    department=dept,
                    index=i,
                    activity=activity,
                    m365_app_id=m365_app_id,
                    inventory=inventory,
                    state_manager=state_manager,
                )
                workers.append(worker)

        # Distribute allowed recipients to all workers
        all_upns = self._worker_registry.get_all_upns()
        for worker in workers:
            worker.add_allowed_recipients(all_upns)

        logger.info(
            f"[{self._run_id}] Distributed {len(all_upns)} allowed recipients to "
            f"{len(workers)} workers"
        )

        return workers

    async def _provision_single_worker(
        self,
        department: str,
        index: int,
        activity: dict,
        m365_app_id: str,
        inventory: KnowledgeWorkerResourceInventory | None,
        state_manager: DeploymentStateManager,
    ) -> KnowledgeWorkerAgent:
        """Provision a single knowledge worker.

        Args:
            department: Department name
            index: Worker index within department
            activity: Activity configuration
            m365_app_id: M365 application ID
            inventory: Resource inventory for cleanup tracking
            state_manager: State manager for persistence

        Returns:
            Created KnowledgeWorkerAgent instance
        """
        display_name = f"KW {department.title()} {index + 1}"

        # Map department to persona
        try:
            persona = WorkerPersona(department.lower())
        except ValueError:
            persona = WorkerPersona.ENGINEERING

        # Provision real Entra user
        assert self._user_manager is not None, "User manager not initialized"
        identity = await self._user_manager.provision_worker(
            department=department,
            index=index,
            display_name=display_name,
            persona=persona,
        )

        # Register in inventory for cleanup
        if inventory:
            inventory.register("entra_users", identity.entra_object_id)

        # Register in worker registry
        assert self._worker_registry is not None, "Worker registry not initialized"
        self._worker_registry.register(identity)

        # Save worker to state manager
        state_manager.save_worker(self._run_id, identity)

        # Create worker config using provisioned identity
        worker_config = KnowledgeWorkerConfig(
            worker_id=identity.worker_id,
            display_name=identity.display_name,
            department=department,
            persona=persona.value,
            tenant_domain=self._tenant_domain,
            m365_app_id=m365_app_id,
        )

        # Create activity config
        activity_config = WorkerConfig(
            email_per_hour=activity.get("email_per_hour", 5),
            teams_messages_per_hour=activity.get("teams_messages_per_hour", 10),
            documents_per_day=activity.get("documents_per_day", 3),
            meetings_per_day=activity.get("meetings_per_day", 4),
        )

        # Create agent with pre-provisioned identity
        agent = KnowledgeWorkerAgent(
            worker_config=worker_config,
            worker_identity=identity,
            activity_config=activity_config,
        )

        logger.info(f"Provisioned Entra user: {identity.user_principal_name}")

        return agent


__all__ = ["WorkerProvisioningService"]
