"""Knowledge Worker Agent base class.

Provides the core agent class for knowledge worker activity simulation,
extending AgentBase with M365-specific capabilities.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from azure_haymaker.agent_base import AgentBase, AgentConfig
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerConfig,
    WorkerIdentity,
    WorkerPersona,
)
from azure_haymaker.knowledge_worker.operations.validators import (
    CommunicationValidator,
)

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeWorkerConfig(AgentConfig):
    """Configuration for a knowledge worker agent.

    Extends AgentConfig with knowledge worker-specific settings
    including identity, team membership, and M365 credentials.

    Attributes:
        name: Agent name (auto-generated from worker_id if empty)
        goal: Agent goal (auto-generated from display_name if empty)
        worker_id: Unique worker identifier
        display_name: Display name in Entra
        department: Department/team name
        persona: Worker persona type
        team_id: ID of the worker's team
        team_name: Name of the worker's team
        activity_types: List of activity types to perform
        activity_frequency_minutes: Base interval between activities
        endpoint_type: Type of endpoint (cloud_pc or cli_container)
        endpoint_id: ID of assigned endpoint
        m365_app_id: M365 application client ID
        m365_cert_thumbprint: Certificate thumbprint for auth
        tenant_domain: M365 tenant domain
    """

    # Override parent required fields with defaults (populated in __post_init__)
    name: str = ""
    goal: str = ""

    # Worker identity
    worker_id: str = ""
    display_name: str = ""
    department: str = ""
    persona: str = ""

    # Team membership
    team_id: str = ""
    team_name: str = ""

    # Activity configuration
    activity_types: list[str] = field(default_factory=list)
    activity_frequency_minutes: int = 30

    # Endpoint configuration
    endpoint_type: str = "cli_container"  # "cli_container" or "cloud_pc"
    endpoint_id: str = ""

    # M365 credentials
    m365_app_id: str = ""
    m365_cert_thumbprint: str = ""
    tenant_domain: str = ""

    def __post_init__(self) -> None:
        """Set default name and goal if not provided."""
        if not self.name:
            self.name = f"knowledge-worker-{self.worker_id}"
        if not self.goal:
            self.goal = f"Perform M365 activities as {self.display_name or self.worker_id}"


class KnowledgeWorkerAgent(AgentBase):
    """Base class for knowledge worker activity agents.

    Extends AgentBase to add M365 activity capabilities including:
    - Email send/receive/organize operations
    - Teams messaging and channel operations
    - Document creation and collaboration
    - Calendar event management

    Each worker executes activities from a distinct endpoint identity,
    ensuring all communications stay within the tenant boundary.

    Lifecycle:
        1. on_start() - Initialize M365 client and load allowed recipients
        2. on_execute() - Execute scheduled activities
        3. on_cleanup() - Disconnect M365 client and report metrics

    Example:
        >>> config = KnowledgeWorkerConfig(
        ...     worker_id="kw-abc12345-engi-001",
        ...     display_name="Alex Developer",
        ...     department="engineering",
        ...     persona="engineering",
        ...     tenant_domain="tenant.onmicrosoft.com",
        ... )
        >>> agent = KnowledgeWorkerAgent(config)
        >>> exit_code = agent.run()

    Attributes:
        worker_config: Knowledge worker configuration
        worker_identity: Worker identity model (created from config)
        activity_config: Activity pattern configuration
        validator: Communication validator for recipient checks
        m365_client: M365 Graph API client (initialized on start)
        allowed_recipients: Set of allowed internal recipients
    """

    def __init__(
        self,
        worker_config: KnowledgeWorkerConfig,
        worker_identity: WorkerIdentity | None = None,
        activity_config: WorkerConfig | None = None,
        prompt_path: Path | None = None,
    ):
        """Initialize KnowledgeWorkerAgent.

        Args:
            worker_config: Knowledge worker configuration
            worker_identity: Optional pre-built worker identity
            activity_config: Optional activity configuration
            prompt_path: Path to the prompt file
        """
        super().__init__(prompt_path)
        self.worker_config = worker_config
        self._m365_client: Any = None
        self._allowed_recipients: set[str] = set()
        self._validator: CommunicationValidator | None = None

        # Build worker identity from config if not provided
        if worker_identity:
            self.worker_identity = worker_identity
        else:
            self.worker_identity = self._build_worker_identity()

        # Use provided activity config or defaults
        self.activity_config = activity_config or WorkerConfig()

    def _build_worker_identity(self) -> WorkerIdentity:
        """Build WorkerIdentity from configuration.

        Returns:
            WorkerIdentity model populated from config
        """
        # Map persona string to enum
        try:
            persona = WorkerPersona(self.worker_config.persona.lower())
        except ValueError:
            logger.warning(
                f"Unknown persona '{self.worker_config.persona}', defaulting to ENGINEERING"
            )
            persona = WorkerPersona.ENGINEERING

        # Map endpoint type string to enum
        try:
            endpoint_type = EndpointType(self.worker_config.endpoint_type.lower())
        except ValueError:
            endpoint_type = EndpointType.CLI_CONTAINER

        return WorkerIdentity(
            worker_id=self.worker_config.worker_id,
            display_name=self.worker_config.display_name,
            user_principal_name="",  # Set during provisioning
            department=self.worker_config.department,
            persona=persona,
            endpoint_type=endpoint_type,
            endpoint_id=self.worker_config.endpoint_id,
            team_ids=[self.worker_config.team_id] if self.worker_config.team_id else [],
        )

    def get_config(self) -> AgentConfig:
        """Return the worker configuration.

        Returns:
            KnowledgeWorkerConfig instance
        """
        return self.worker_config

    @property
    def validator(self) -> CommunicationValidator:
        """Get the communication validator.

        Returns:
            CommunicationValidator instance

        Raises:
            RuntimeError: If validator not initialized (call on_start first)
        """
        if self._validator is None:
            raise RuntimeError("Validator not initialized. Call on_start() first.")
        return self._validator

    @property
    def m365_client(self) -> Any:
        """Get the M365 client.

        Returns:
            M365 client instance

        Raises:
            RuntimeError: If client not initialized (call on_start first)
        """
        if self._m365_client is None:
            raise RuntimeError("M365 client not initialized. Call on_start() first.")
        return self._m365_client

    def on_start(self) -> None:
        """Initialize M365 client and load allowed recipients.

        Called before execution begins. Sets up:
        - M365 Graph API client with certificate auth
        - Communication validator with tenant domain
        - Allowed recipients list from Entra
        """
        super().on_start()

        logger.info(
            f"Starting knowledge worker: {self.worker_config.worker_id} "
            f"({self.worker_config.display_name})"
        )

        # Initialize validator with tenant domain
        self._initialize_validator()

        # Initialize M365 client
        self._initialize_m365_client()

        # Load allowed recipients
        self._load_allowed_recipients()

        logger.info(
            f"Knowledge worker initialized with {len(self._allowed_recipients)} allowed recipients"
        )

    def on_execute(self) -> int:
        """Execute knowledge worker activities.

        Default implementation delegates to the parent class.
        Subclasses can override to implement specific activity patterns.

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        return super().on_execute()

    def on_cleanup(self, exit_code: int) -> None:
        """Disconnect M365 client and report metrics.

        Called after execution completes, regardless of success/failure.

        Args:
            exit_code: Exit code from on_execute()
        """
        logger.info(f"Cleaning up knowledge worker: {self.worker_config.worker_id}")

        self._disconnect_m365_client()

        super().on_cleanup(exit_code)

    def _initialize_validator(self) -> None:
        """Initialize the communication validator.

        Creates a CommunicationValidator with the tenant domain.
        """
        tenant_domain = self.worker_config.tenant_domain
        if not tenant_domain:
            logger.warning("No tenant domain configured. Validator will reject all recipients.")
            tenant_domain = "invalid.domain"

        self._validator = CommunicationValidator(
            tenant_domain=tenant_domain,
            allowed_upns=self._allowed_recipients,
        )

    def _initialize_m365_client(self) -> None:
        """Initialize M365 client connection with client secret auth.

        Connects to Microsoft Graph using client secret credentials
        from environment variables (KW_APP_ID, KW_CLIENT_SECRET, KW_TENANT_ID).
        """
        try:
            # Import here to avoid dependency issues if not installed
            from azure_haymaker.knowledge_worker.m365_client import M365ClientFactory

            self._m365_client = M365ClientFactory.create()

            logger.info(f"M365 client initialized for {self.worker_config.worker_id}")

        except ImportError:
            logger.warning(
                "Microsoft Graph SDK not installed. "
                "Install with: pip install msgraph-sdk azure-identity"
            )
        except ValueError as e:
            # Missing credentials - expected in simulation mode
            logger.debug(f"M365 client not initialized: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize M365 client: {e}")

    def _extract_tenant_id(self) -> str:
        """Extract tenant ID from tenant domain.

        In practice, you would look this up or have it configured.
        This is a placeholder that returns a reasonable default.

        Returns:
            Tenant ID string
        """
        # This would normally be configured or looked up
        return self.worker_config.extra.get("tenant_id", "")

    def _load_allowed_recipients(self) -> None:
        """Load allowed recipient list for communication safety.

        Queries Entra to build the list of internal recipients
        that this worker is allowed to communicate with.
        """
        # In a full implementation, this would query:
        # 1. All workers in the same run
        # 2. Team shared mailboxes
        # 3. Distribution groups

        # For now, start with an empty set that gets populated
        # as the orchestrator provisions workers
        self._allowed_recipients = set()

        if self._validator:
            self._validator.allowed_upns = self._allowed_recipients

    def _disconnect_m365_client(self) -> None:
        """Disconnect M365 CLI session.

        Cleans up any open connections to Microsoft Graph.
        """
        if self._m365_client is not None:
            # The Graph SDK handles connection pooling automatically
            # Just clear the reference
            self._m365_client = None
            logger.debug(f"M365 client disconnected for {self.worker_config.worker_id}")

    def add_allowed_recipient(self, recipient: str) -> None:
        """Add a recipient to the allowed list.

        Call this to add internal recipients discovered during
        orchestration.

        Args:
            recipient: Email address or UPN to allow
        """
        self._allowed_recipients.add(recipient.lower().strip())
        if self._validator:
            self._validator.add_allowed_upn(recipient)

    def add_allowed_recipients(self, recipients: list[str]) -> None:
        """Add multiple recipients to the allowed list.

        Args:
            recipients: List of email addresses or UPNs to allow
        """
        for recipient in recipients:
            self.add_allowed_recipient(recipient)

    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient is in allowed list (internal only).

        Args:
            recipient: Email address or UPN to validate

        Returns:
            True if recipient is internal and allowed
        """
        if self._validator is None:
            # If validator not initialized, deny all
            return False
        return self._validator.is_internal(recipient)

    def get_worker_stats(self) -> dict[str, Any]:
        """Get statistics about this worker.

        Returns:
            Dictionary with worker state and statistics
        """
        return {
            "worker_id": self.worker_config.worker_id,
            "display_name": self.worker_config.display_name,
            "department": self.worker_config.department,
            "persona": self.worker_config.persona,
            "endpoint_type": self.worker_config.endpoint_type,
            "allowed_recipients_count": len(self._allowed_recipients),
            "m365_client_initialized": self._m365_client is not None,
            "validator_initialized": self._validator is not None,
        }

    def get_allowed_recipients(self) -> list[str]:
        """Get list of allowed internal recipients.

        Returns:
            List of allowed email addresses/UPNs
        """
        return list(self._allowed_recipients)

    async def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
    ) -> str | None:
        """Send an email to internal recipients.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body (HTML supported)
            cc: Optional CC recipients

        Returns:
            Message ID if sent, None if blocked or failed

        Raises:
            RuntimeError: If M365 client not initialized
            ValueError: If no recipients provided
        """
        if self._m365_client is None:
            raise RuntimeError("M365 client not initialized. Call on_start() first.")

        if not to:
            raise ValueError("At least one recipient is required")

        from azure_haymaker.knowledge_worker.operations import EmailOperations

        ops = EmailOperations(
            worker_identity=self.worker_identity,
            m365_client=self._m365_client,
            validator=self.validator,
        )

        return await ops.send_email(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
        )

    async def create_calendar_event(
        self,
        subject: str,
        start_time: str,
        end_time: str,
        attendees: list[str] | None = None,
        body: str = "",
        is_online_meeting: bool = False,
    ) -> str | None:
        """Create a calendar event.

        Args:
            subject: Event subject
            start_time: Start time in ISO format
            end_time: End time in ISO format
            attendees: List of attendee email addresses
            body: Optional event body
            is_online_meeting: If True, create Teams meeting

        Returns:
            Event ID if created, None if failed

        Raises:
            RuntimeError: If M365 client not initialized
        """
        if self._m365_client is None:
            raise RuntimeError("M365 client not initialized. Call on_start() first.")

        from datetime import datetime

        from azure_haymaker.knowledge_worker.operations import CalendarOperations

        # Parse ISO strings to datetime if needed
        start_dt = (
            datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if isinstance(start_time, str)
            else start_time
        )
        end_dt = (
            datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            if isinstance(end_time, str)
            else end_time
        )

        ops = CalendarOperations(
            worker_identity=self.worker_identity,
            m365_client=self._m365_client,
            validator=self.validator,
        )

        return await ops.create_event(
            subject=subject,
            start_time=start_dt,
            end_time=end_dt,
            attendees=attendees or [],
            body=body,
            is_online=is_online_meeting,
        )
