"""Core knowledge worker agent implementation.

Coordinates agent lifecycle, recipient management, and M365 operations.

Philosophy: Agent lifecycle coordination, delegates M365 to m365_integration,
pure business logic with async-first operations.

Public API: KnowledgeWorkerAgent

See README.md for complete documentation and usage examples.
"""

import logging
from pathlib import Path
from typing import Any

from azure_haymaker.agent_base import AgentBase, AgentConfig
from azure_haymaker.knowledge_worker.models.worker import (
    WorkerConfig,
    WorkerIdentity,
)
from azure_haymaker.knowledge_worker.operations.validators import (
    CommunicationValidator,
)

from .config import KnowledgeWorkerConfig, build_worker_identity
from .m365_integration import (
    create_calendar_event,
    initialize_m365_client,
    send_email,
)

logger = logging.getLogger(__name__)

__all__ = ["KnowledgeWorkerAgent"]


class KnowledgeWorkerAgent(AgentBase):
    """Knowledge worker agent with M365 activity capabilities.

    Lifecycle: on_start() → on_execute() → on_cleanup()
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
            self.worker_identity = build_worker_identity(worker_config)

        # Use provided activity config or defaults
        self.activity_config = activity_config or WorkerConfig()

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
        """Initialize M365 client, validator, and allowed recipients."""
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
        """Execute activities (delegates to parent). Override for custom patterns."""
        return super().on_execute()

    def on_cleanup(self, exit_code: int) -> None:
        """Disconnect M365 client and cleanup."""
        logger.info(f"Cleaning up knowledge worker: {self.worker_config.worker_id}")

        self._disconnect_m365_client()

        super().on_cleanup(exit_code)

    def _initialize_validator(self) -> None:
        """Initialize communication validator with tenant domain."""
        tenant_domain = self.worker_config.tenant_domain
        if not tenant_domain:
            raise ValueError(
                "tenant_domain is required for validator initialization. "
                "Set tenant_domain in KnowledgeWorkerConfig."
            )

        self._validator = CommunicationValidator(
            tenant_domain=tenant_domain,
            allowed_upns=self._allowed_recipients,
        )

    def _initialize_m365_client(self) -> None:
        """Initialize M365 client (credentials from environment variables)."""
        self._m365_client = initialize_m365_client(
            worker_id=self.worker_config.worker_id
        )

        # Ensure client was initialized successfully
        if self._m365_client is None:
            raise RuntimeError(
                f"Failed to initialize M365 client for {self.worker_config.worker_id}. "
                "Ensure M365 credentials are set in environment variables "
                "(KW_APP_ID, KW_CLIENT_SECRET, KW_TENANT_ID) and msgraph-sdk is installed."
            )

    def _load_allowed_recipients(self) -> None:
        """Load allowed recipients (orchestrator typically populates before start)."""
        # If orchestrator already populated, we're done
        if self._allowed_recipients:
            logger.info(
                f"Allowed recipients already populated: {len(self._allowed_recipients)} recipients"
            )
            if self._validator:
                self._validator.allowed_upns = self._allowed_recipients
            return

        logger.warning(
            f"No allowed recipients provided by orchestrator for {self.worker_config.worker_id}. "
            "Emails will be blocked unless recipients are added."
        )

        # Create empty set if orchestrator hasn't set it
        self._allowed_recipients = set()

        if self._validator:
            self._validator.allowed_upns = self._allowed_recipients

    def _disconnect_m365_client(self) -> None:
        """Disconnect M365 client and cleanup connections."""
        if self._m365_client is not None:
            # The Graph SDK handles connection pooling automatically
            # Just clear the reference
            self._m365_client = None
            logger.debug(f"M365 client disconnected for {self.worker_config.worker_id}")

    def add_allowed_recipient(self, recipient: str) -> None:
        """Add recipient to allowed list."""
        self._allowed_recipients.add(recipient.lower().strip())
        if self._validator:
            self._validator.add_allowed_upn(recipient)

    def add_allowed_recipients(self, recipients: list[str]) -> None:
        """Add multiple recipients to allowed list."""
        for recipient in recipients:
            self.add_allowed_recipient(recipient)

    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient is internal and allowed."""
        if self._validator is None:
            # If validator not initialized, deny all
            return False
        return self._validator.is_internal(recipient)

    def get_worker_stats(self) -> dict[str, Any]:
        """Get worker statistics and state."""
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
        """Get list of allowed recipients."""
        return list(self._allowed_recipients)

    async def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
    ) -> str | None:
        """Send email to internal recipients. Returns message ID or None."""
        return await send_email(
            worker_identity=self.worker_identity,
            m365_client=self._m365_client,
            validator=self.validator,
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
        """Create calendar event. Returns event ID or None."""
        return await create_calendar_event(
            worker_identity=self.worker_identity,
            m365_client=self._m365_client,
            validator=self.validator,
            subject=subject,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            body=body,
            is_online_meeting=is_online_meeting,
        )
