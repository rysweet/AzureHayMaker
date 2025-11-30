"""Knowledge Worker Orchestrator for coordinating worker deployments.

The orchestrator manages the full lifecycle of knowledge worker deployments:
1. Setup - Create security groups, transport rules
2. Provision - Create Entra users and endpoints
3. Execute - Run worker activities
4. Cleanup - Remove all created resources

NOTE: This is a LOCAL SIMULATION orchestrator. It demonstrates the deployment
lifecycle but does not create actual Azure resources. For production use:
- Integrate with EntraUserManager for real user provisioning
- Connect to actual M365 endpoints via Graph API
- Implement proper Azure resource cleanup

The e2e-test CLI command validates real Graph API connectivity separately.

Example:
    >>> orchestrator = KnowledgeWorkerOrchestrator(graph_client)
    >>> run_id = await orchestrator.start_deployment(deployment_config)
    >>> await orchestrator.wait_for_completion(run_id)
    >>> await orchestrator.cleanup(run_id)
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from azure_haymaker.knowledge_worker.agent import (
    KnowledgeWorkerAgent,
    KnowledgeWorkerConfig,
)
from azure_haymaker.knowledge_worker.cleanup import KnowledgeWorkerResourceInventory
from azure_haymaker.knowledge_worker.models.worker import (
    WorkerConfig,
    WorkerPersona,
)
from azure_haymaker.knowledge_worker.worker_registry import WorkerRegistry

if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient

    from azure_haymaker.knowledge_worker.identity.user_manager import EntraUserManager

logger = logging.getLogger(__name__)


class DeploymentPhase(str, Enum):
    """Phases of a knowledge worker deployment."""

    INITIALIZING = "initializing"
    SETUP = "setup"
    PROVISIONING = "provisioning"
    EXECUTING = "executing"
    STOPPING = "stopping"
    CLEANUP = "cleanup"
    COMPLETED = "completed"
    FAILED = "failed"


class DeploymentStatus(str, Enum):
    """Status of a deployment."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DeploymentConfig:
    """Configuration for a knowledge worker deployment.

    Attributes:
        name: Deployment name
        total_workers: Total number of workers to deploy
        departments: Department configurations
        duration_hours: How long to run activities
        tenant_domain: M365 tenant domain
        m365_app_id: M365 application client ID (optional)

    Note:
        Requires the following environment variables:
        - KW_TENANT_ID: Azure AD tenant ID
        - KW_APP_ID: Application (client) ID with Graph permissions
        - KW_CLIENT_SECRET: Client secret for application
    """

    name: str = "kw-deployment"
    total_workers: int = 10
    departments: dict[str, dict[str, Any]] = field(default_factory=dict)
    duration_hours: int = 8
    tenant_domain: str = ""
    m365_app_id: str = ""

    def __post_init__(self) -> None:
        """Set default departments if not provided."""
        if not self.departments:
            # Default: 10 engineering workers
            self.departments = {
                "engineering": {
                    "count": self.total_workers,
                    "endpoint_type": "cli_container",
                    "activity": {
                        "email_per_hour": 4,
                        "teams_messages_per_hour": 15,
                        "documents_per_day": 5,
                        "meetings_per_day": 4,
                    },
                }
            }


@dataclass
class DeploymentState:
    """State of a knowledge worker deployment.

    Attributes:
        run_id: Unique deployment identifier
        config: Deployment configuration
        phase: Current deployment phase
        status: Overall deployment status
        workers: List of deployed workers
        inventory: Resource inventory for cleanup
        started_at: When deployment started
        completed_at: When deployment completed
        error: Error message if failed
    """

    run_id: str
    config: DeploymentConfig
    phase: DeploymentPhase = DeploymentPhase.INITIALIZING
    status: DeploymentStatus = DeploymentStatus.PENDING
    workers: list[KnowledgeWorkerAgent] = field(default_factory=list)
    inventory: KnowledgeWorkerResourceInventory | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "name": self.config.name,
            "phase": self.phase.value,
            "status": self.status.value,
            "worker_count": len(self.workers),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


class KnowledgeWorkerOrchestrator:
    """Orchestrates knowledge worker deployments.

    Manages the full lifecycle of knowledge worker deployments including
    worker provisioning, activity execution, and cleanup.

    The orchestrator:
    - Creates real Entra users via EntraUserManager
    - Registers all workers in WorkerRegistry for cross-worker communication
    - Distributes allowed recipients to all worker agents

    Example:
        >>> config = DeploymentConfig(
        ...     name="test-deployment",
        ...     total_workers=5,
        ...     tenant_domain="test.onmicrosoft.com",
        ... )
        >>> orchestrator = KnowledgeWorkerOrchestrator(graph_client)
        >>> run_id = await orchestrator.create_deployment(config)
        >>> await orchestrator.start_deployment(run_id)
    """

    def __init__(self, graph_client: "GraphServiceClient") -> None:
        """Initialize the orchestrator.

        Args:
            graph_client: Microsoft Graph API client (REQUIRED)

        Raises:
            ValueError: If graph_client is None
        """
        if graph_client is None:
            raise ValueError(
                "graph_client is required. Knowledge Worker orchestrator "
                "operates only with real M365 operations. "
                "Ensure credentials are configured: KW_TENANT_ID, KW_APP_ID, KW_CLIENT_SECRET"
            )
        self._graph_client = graph_client
        self._deployments: dict[str, DeploymentState] = {}
        self._worker_tasks: dict[str, list[asyncio.Task]] = {}
        self._user_manager: EntraUserManager | None = None
        self._worker_registry: WorkerRegistry | None = None

    def create_deployment(self, config: DeploymentConfig) -> str:
        """Create a new deployment.

        Args:
            config: Deployment configuration

        Returns:
            Run ID for the deployment
        """
        run_id = f"kw-{uuid4().hex[:8]}"

        state = DeploymentState(
            run_id=run_id,
            config=config,
            inventory=KnowledgeWorkerResourceInventory(run_id),
        )

        self._deployments[run_id] = state
        logger.info(f"Created deployment {run_id}: {config.name}")

        return run_id

    def get_deployment(self, run_id: str) -> DeploymentState | None:
        """Get deployment state by run ID.

        Args:
            run_id: Deployment run ID

        Returns:
            DeploymentState or None if not found
        """
        return self._deployments.get(run_id)

    def list_deployments(self) -> list[dict[str, Any]]:
        """List all deployments.

        Returns:
            List of deployment state dictionaries
        """
        return [state.to_dict() for state in self._deployments.values()]

    async def start_deployment(self, run_id: str) -> bool:
        """Start a deployment.

        Runs through all deployment phases:
        1. Setup - Create security infrastructure
        2. Provision - Create workers
        3. Execute - Start worker activities

        Args:
            run_id: Deployment run ID

        Returns:
            True if started successfully
        """
        state = self._deployments.get(run_id)
        if not state:
            logger.error(f"Deployment not found: {run_id}")
            return False

        if state.status == DeploymentStatus.RUNNING:
            logger.warning(f"Deployment already running: {run_id}")
            return False

        try:
            state.status = DeploymentStatus.RUNNING
            state.started_at = datetime.now(UTC)

            # Phase 1: Setup
            await self._phase_setup(state)

            # Phase 2: Provision
            await self._phase_provision(state)

            # Phase 3: Execute (starts async)
            await self._phase_execute(state)

            return True

        except Exception as e:
            logger.error(f"Deployment failed: {run_id}: {e}")
            state.status = DeploymentStatus.FAILED
            state.phase = DeploymentPhase.FAILED
            state.error = str(e)
            return False

    async def stop_deployment(self, run_id: str) -> bool:
        """Stop a running deployment.

        Args:
            run_id: Deployment run ID

        Returns:
            True if stopped successfully
        """
        state = self._deployments.get(run_id)
        if not state:
            logger.error(f"Deployment not found: {run_id}")
            return False

        state.phase = DeploymentPhase.STOPPING
        logger.info(f"Stopping deployment: {run_id}")

        # Cancel worker tasks
        tasks = self._worker_tasks.get(run_id, [])
        for task in tasks:
            task.cancel()

        # Wait for tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        state.phase = DeploymentPhase.COMPLETED
        state.status = DeploymentStatus.COMPLETED
        state.completed_at = datetime.now(UTC)

        logger.info(f"Deployment stopped: {run_id}")
        return True

    async def cleanup_deployment(self, run_id: str) -> bool:
        """Clean up deployment resources.

        Args:
            run_id: Deployment run ID

        Returns:
            True if cleanup successful
        """
        state = self._deployments.get(run_id)
        if not state:
            logger.error(f"Deployment not found: {run_id}")
            return False

        state.phase = DeploymentPhase.CLEANUP
        logger.info(f"Cleaning up deployment: {run_id}")

        # In a full implementation, this would:
        # 1. Stop containers
        # 2. Delete Cloud PCs
        # 3. Remove transport rules
        # 4. Delete groups
        # 5. Delete users

        # For now, just clear local state
        state.workers.clear()

        state.phase = DeploymentPhase.COMPLETED
        logger.info(f"Deployment cleanup complete: {run_id}")

        return True

    async def _phase_setup(self, state: DeploymentState) -> None:
        """Setup phase: Create security infrastructure.

        Args:
            state: Deployment state
        """
        state.phase = DeploymentPhase.SETUP
        logger.info(f"[{state.run_id}] Starting setup phase")

        # In a full implementation, this would:
        # 1. Create security group for all workers
        # 2. Create transport rules to block external email
        # 3. Configure app permissions

        # For now, just log
        logger.info(f"[{state.run_id}] Setup phase complete")

    async def _phase_provision(self, state: DeploymentState) -> None:
        """Provision phase: Create Entra users and initialize workers.

        Creates real Entra users via Graph API, registers them in WorkerRegistry,
        assigns licenses, and distributes allowed recipients to all workers.

        Args:
            state: Deployment state

        Raises:
            ValueError: If tenant_domain not configured
        """
        state.phase = DeploymentPhase.PROVISIONING
        logger.info(f"[{state.run_id}] Starting provisioning phase")

        # Validate tenant configuration
        if not state.config.tenant_domain:
            raise ValueError(
                "tenant_domain is required. Set this in DeploymentConfig to match your M365 tenant."
            )

        await self._provision_users(state)

        logger.info(f"[{state.run_id}] Provisioning complete: {len(state.workers)} workers created")

    async def _provision_users(self, state: DeploymentState) -> None:
        """Provision real Entra users for M365 operations.

        Creates actual Entra users via Graph API, registers them in the
        WorkerRegistry, and distributes allowed recipients to all workers.

        Args:
            state: Deployment state
        """

        # Import here to avoid circular imports and optional dependency issues
        from azure_haymaker.knowledge_worker.identity.user_manager import (
            EntraUserManager,
        )

        # Initialize user manager
        self._user_manager = EntraUserManager(
            graph_client=self._graph_client,
            run_id=state.run_id,
            tenant_domain=state.config.tenant_domain,
        )

        # Initialize worker registry
        self._worker_registry = WorkerRegistry(run_id=state.run_id)

        logger.info(f"[{state.run_id}] Provisioning Entra users")

        for dept, dept_config in state.config.departments.items():
            count = dept_config.get("count", 5)
            activity = dept_config.get("activity", {})

            for i in range(count):
                display_name = f"KW {dept.title()} {i + 1}"

                # Map department to persona
                try:
                    persona = WorkerPersona(dept.lower())
                except ValueError:
                    persona = WorkerPersona.ENGINEERING

                # Provision real Entra user
                identity = await self._user_manager.provision_worker(
                    department=dept,
                    index=i,
                    display_name=display_name,
                    persona=persona,
                )

                # Register in inventory for cleanup
                if state.inventory:
                    state.inventory.register("entra_users", identity.entra_object_id)

                # Register in worker registry
                self._worker_registry.register(identity)

                # Create worker config using provisioned identity
                worker_config = KnowledgeWorkerConfig(
                    worker_id=identity.worker_id,
                    display_name=identity.display_name,
                    department=dept,
                    persona=persona.value,
                    tenant_domain=state.config.tenant_domain,
                    m365_app_id=state.config.m365_app_id,
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

                state.workers.append(agent)

                logger.info(f"Provisioned Entra user: {identity.user_principal_name}")

        # Distribute allowed recipients to all workers
        all_upns = self._worker_registry.get_all_upns()
        for worker in state.workers:
            worker.add_allowed_recipients(all_upns)

        logger.info(
            f"[{state.run_id}] Distributed {len(all_upns)} allowed recipients to "
            f"{len(state.workers)} workers"
        )

    async def _phase_execute(self, state: DeploymentState) -> None:
        """Execute phase: Start worker M365 activity generation.

        Launches async tasks for each worker to generate M365 activities
        (emails, calendar events) at configured intervals.

        Args:
            state: Deployment state
        """
        state.phase = DeploymentPhase.EXECUTING
        logger.info(f"[{state.run_id}] Starting execution phase")

        # Create worker tasks
        tasks = []
        for worker in state.workers:
            task = asyncio.create_task(self._run_worker(worker, state.config.duration_hours))
            tasks.append(task)

        self._worker_tasks[state.run_id] = tasks

        logger.info(
            f"[{state.run_id}] Started {len(tasks)} worker tasks "
            f"(duration: {state.config.duration_hours}h)"
        )

    async def _run_worker(
        self,
        worker: KnowledgeWorkerAgent,
        duration_hours: int,
    ) -> None:
        """Run worker with M365 operations.

        Args:
            worker: Worker agent
            duration_hours: How long to run
        """
        worker_id = worker.worker_config.worker_id

        try:
            logger.info(f"Worker {worker_id} starting M365 operations")

            # Initialize the worker (creates M365 client)
            worker.on_start()

            # Run activity loop
            await self._run_activity_loop(worker, duration_hours)

            # Cleanup
            worker.on_cleanup(0)

            logger.info(f"Worker {worker_id} completed M365 operations")

        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id} cancelled")
            worker.on_cleanup(1)
            raise
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {e}")
            worker.on_cleanup(1)

    async def _run_activity_loop(
        self,
        worker: KnowledgeWorkerAgent,
        duration_hours: int,
    ) -> None:
        """Run the activity generation loop for a worker.

        Generates and executes activities at configured intervals.

        Args:
            worker: Worker agent with initialized M365 client
            duration_hours: How long to run (in hours)
        """
        worker_id = worker.worker_config.worker_id
        config = worker.activity_config

        end_time = datetime.now(UTC) + timedelta(hours=duration_hours)
        activity_count = 0

        # Calculate base interval (in seconds) from emails_per_hour
        base_interval = 3600.0 / max(config.email_per_hour, 1)

        while datetime.now(UTC) < end_time:
            try:
                # Add variance to interval (50-150% of base)
                interval = base_interval * random.uniform(0.5, 1.5)

                # Pick random activity type
                activity_type = random.choice(["email", "calendar"])

                if activity_type == "email":
                    # Generate and send email to a random allowed recipient
                    recipients = worker.get_allowed_recipients()
                    if recipients:
                        to = [random.choice(recipients)]
                        subject = f"Activity {activity_count + 1} from {worker_id}"
                        body = f"<p>Automated activity generated at {datetime.now(UTC).isoformat()}</p>"

                        await worker.send_email(to=to, subject=subject, body=body)
                        logger.info(f"Worker {worker_id} sent email to {to[0]}")
                    else:
                        logger.debug(f"Worker {worker_id}: no recipients available")

                elif activity_type == "calendar":
                    # Create a calendar event
                    start = datetime.now(UTC) + timedelta(hours=1)
                    end = start + timedelta(minutes=30)

                    await worker.create_calendar_event(
                        subject=f"Meeting {activity_count + 1}",
                        start_time=start.isoformat(),
                        end_time=end.isoformat(),
                        body="Automated meeting created by KW agent",
                    )
                    logger.info(f"Worker {worker_id} created calendar event")

                activity_count += 1

                # Wait before next activity
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Worker {worker_id} activity error: {e}")
                await asyncio.sleep(5)  # Brief pause on error

        logger.info(f"Worker {worker_id} completed {activity_count} activities")


__all__ = [
    "DeploymentConfig",
    "DeploymentPhase",
    "DeploymentState",
    "DeploymentStatus",
    "KnowledgeWorkerOrchestrator",
]
