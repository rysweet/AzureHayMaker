"""Knowledge Worker Orchestrator for coordinating worker deployments.

The orchestrator manages the full lifecycle of knowledge worker deployments:
1. Setup - Create security groups, transport rules
2. Provision - Create Entra users and endpoints
3. Execute - Run worker activities
4. Cleanup - Remove all created resources

Manages full lifecycle of knowledge worker deployments with real Azure resources.

This module is a facade that delegates to specialized submodules:
- email_content_service: Email content generation
- worker_provisioning: Worker creation and registration
- activity_execution: Activity loop management
- deployment_phases: Phase coordination

Example:
    >>> orchestrator = KnowledgeWorkerOrchestrator(graph_client)
    >>> run_id = await orchestrator.start_deployment(deployment_config)
    >>> await orchestrator.wait_for_completion(run_id)
    >>> await orchestrator.cleanup(run_id)
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from azure_haymaker.knowledge_worker.agent import KnowledgeWorkerAgent
from azure_haymaker.knowledge_worker.cleanup import KnowledgeWorkerResourceInventory
from azure_haymaker.knowledge_worker.content import EmailContent, EmailGenerationConfig
from azure_haymaker.knowledge_worker.deployment_phases import (
    DeploymentPhaseContext,
    DeploymentPhaseManager,
)
from azure_haymaker.knowledge_worker.email_content_service import EmailContentService
from azure_haymaker.knowledge_worker.state_manager import DeploymentStateManager

if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient

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
        email_markers_enabled: Enable email markers for tracking
        marker_format: Format for markers (e.g., "MARKER", "TAG")
        marker_style: Where to place markers ("subject", "hidden", "both")
        email_generation: AI email generation configuration

    Note:
        Requires the following environment variables:
        - KW_TENANT_ID: Azure AD tenant ID
        - KW_APP_ID: Application (client) ID with Graph permissions
        - KW_CLIENT_SECRET: Client secret for application
        - ANTHROPIC_API_KEY: Anthropic API key (if email_generation.enabled=True)
    """

    name: str = "kw-deployment"
    total_workers: int = 10
    departments: dict[str, dict[str, Any]] = field(default_factory=dict)
    duration_hours: int = 8
    tenant_domain: str = ""
    m365_app_id: str = ""

    # Email marker configuration
    email_markers_enabled: bool = True
    marker_format: str = "MARKER"
    marker_style: str = "subject"  # "subject", "hidden", "both"

    # AI email generation configuration
    email_generation: EmailGenerationConfig = field(
        default_factory=lambda: EmailGenerationConfig(enabled=False)
    )

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
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
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

    def __init__(
        self,
        graph_client: "GraphServiceClient",
        config: DeploymentConfig | None = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            graph_client: Microsoft Graph API client (REQUIRED)
            config: Optional deployment configuration for initialization

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
        self._worker_tasks: dict[str, list] = {}  # Maintained for backward compatibility
        self._user_manager = None  # Maintained for backward compatibility
        self._worker_registry = None  # Maintained for backward compatibility

        # Store config for email generation
        self.config = config or DeploymentConfig()
        self.current_run_id: str | None = None

        # Initialize state manager for persistence
        self._state_manager = DeploymentStateManager()

        # Initialize email content service
        self._email_content_service = EmailContentService(
            email_generation_config=self.config.email_generation,
            email_markers_enabled=self.config.email_markers_enabled,
            marker_format=self.config.marker_format,
            marker_style=self.config.marker_style,
        )

        # Initialize deployment phase manager
        self._phase_manager = DeploymentPhaseManager(
            graph_client=self._graph_client,
            email_content_service=self._email_content_service,
        )

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

        # Persist deployment state to disk
        self._state_manager.save_deployment(
            run_id=run_id,
            name=config.name,
            phase=state.phase.value,
            status=state.status.value,
            worker_count=len(state.workers),
            started_at=state.started_at,
            config={
                "total_workers": config.total_workers,
                "duration_hours": config.duration_hours,
                "tenant_domain": config.tenant_domain,
                "departments": config.departments,
            },
        )

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
            self.current_run_id = run_id

            # Save initial running state
            self._save_deployment_state(state)

            # Update config if different from initialization
            if state.config != self.config:
                self.config = state.config
                # Reinitialize email content service if needed
                self._email_content_service = EmailContentService(
                    email_generation_config=self.config.email_generation,
                    email_markers_enabled=self.config.email_markers_enabled,
                    marker_format=self.config.marker_format,
                    marker_style=self.config.marker_style,
                )
                # Reinitialize phase manager with new email service
                self._phase_manager = DeploymentPhaseManager(
                    graph_client=self._graph_client,
                    email_content_service=self._email_content_service,
                )

            # Create phase context
            phase_context = DeploymentPhaseContext(
                run_id=run_id,
                tenant_domain=state.config.tenant_domain,
                m365_app_id=state.config.m365_app_id,
                departments=state.config.departments,
                duration_hours=state.config.duration_hours,
                workers=state.workers,
                inventory=state.inventory,
                state_manager=self._state_manager,
            )

            # Phase 1: Setup
            state.phase = DeploymentPhase.SETUP
            self._save_deployment_state(state)
            await self._phase_manager.run_setup_phase(phase_context)

            # Phase 2: Provision
            state.phase = DeploymentPhase.PROVISIONING
            self._save_deployment_state(state)
            await self._phase_manager.run_provision_phase(phase_context)

            # Update state with provisioned workers
            state.workers = phase_context.workers
            self._save_deployment_state(state)

            # Phase 3: Execute (starts async)
            state.phase = DeploymentPhase.EXECUTING
            self._save_deployment_state(state)
            await self._phase_manager.run_execute_phase(phase_context)

            return True

        except Exception as e:
            logger.error(f"Deployment failed: {run_id}: {e}")
            state.status = DeploymentStatus.FAILED
            state.phase = DeploymentPhase.FAILED
            state.error = str(e)

            # Save failed state
            self._save_deployment_state(state)

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

        # Save phase change
        self._save_deployment_state(state)

        # Cancel worker tasks via phase manager
        await self._phase_manager.stop_worker_tasks(run_id)

        state.phase = DeploymentPhase.COMPLETED
        state.status = DeploymentStatus.COMPLETED
        state.completed_at = datetime.now(UTC)

        # Save final state
        self._save_deployment_state(state)

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

        # Save phase change
        self._save_deployment_state(state)

        # In a full implementation, this would:
        # 1. Stop containers
        # 2. Delete Cloud PCs
        # 3. Remove transport rules
        # 4. Delete groups
        # 5. Delete users

        # For now, just clear local state
        state.workers.clear()

        state.phase = DeploymentPhase.COMPLETED

        # Save final state
        self._save_deployment_state(state)

        logger.info(f"Deployment cleanup complete: {run_id}")

        return True

    def _add_email_markers(
        self,
        email_content: EmailContent,
        worker_id: str,
        activity_count: int,
        run_id: str | None,
    ) -> EmailContent:
        """Backward compatibility method for email marker injection.

        Delegates to email_content_service.add_email_markers().

        Args:
            email_content: Email content to add markers to
            worker_id: Worker identifier
            activity_count: Current activity count
            run_id: Deployment run ID

        Returns:
            EmailContent with markers added
        """
        return self._email_content_service.add_email_markers(
            email_content, worker_id, activity_count, run_id
        )

    def _save_deployment_state(self, state: DeploymentState) -> None:
        """Save deployment state to disk.

        Args:
            state: Deployment state to save
        """
        self._state_manager.save_deployment(
            run_id=state.run_id,
            name=state.config.name,
            phase=state.phase.value,
            status=state.status.value,
            worker_count=len(state.workers),
            started_at=state.started_at,
            completed_at=state.completed_at,
            error=state.error,
            config={
                "total_workers": state.config.total_workers,
                "duration_hours": state.config.duration_hours,
                "tenant_domain": state.config.tenant_domain,
                "departments": state.config.departments,
            },
        )


__all__ = [
    "DeploymentConfig",
    "DeploymentPhase",
    "DeploymentState",
    "DeploymentStatus",
    "KnowledgeWorkerOrchestrator",
]
