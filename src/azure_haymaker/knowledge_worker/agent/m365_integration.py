"""Microsoft 365 integration module for knowledge worker agents.

Provides M365 Graph API client initialization, email, and calendar operations.
Isolates M365 SDK dependencies with graceful degradation when SDK not installed.

Philosophy:
- Single responsibility: M365 API operations
- Isolates M365 SDK dependencies (msgraph-sdk, azure-identity)
- Factory pattern for client creation
- Graceful degradation when SDK not installed
- Environment variable support for credentials

Public API (the "studs"):
    M365ClientFactory: Factory class for creating Graph clients
    initialize_m365_client: Helper function with error handling
    validate_content: Email content length validation
    send_email: Send email via M365 Graph API
    create_calendar_event: Create calendar event via M365 Graph API

Security:
    Credentials loaded from environment variables (KW_APP_ID, KW_CLIENT_SECRET,
    KW_TENANT_ID) and NEVER stored in config files or plaintext.

See README.md for complete documentation and usage examples.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "M365ClientFactory",
    "initialize_m365_client",
    "validate_content",
    "send_email",
    "create_calendar_event",
]


class M365ClientFactory:
    """Factory for creating Microsoft 365 Graph API clients.

    Provides static methods for creating configured Graph clients with
    client secret authentication.

    SECURITY: Credentials are loaded from environment variables (KW_APP_ID,
    KW_CLIENT_SECRET, KW_TENANT_ID) and NEVER stored in config files.
    """

    @staticmethod
    def create(
        app_id: str | None = None,
        client_secret: str | None = None,
        tenant_id: str | None = None,
    ) -> Any:
        """Create a Microsoft Graph client with client secret authentication.

        Args:
            app_id: M365 application client ID (falls back to KW_APP_ID env var)
            client_secret: Client secret (falls back to KW_CLIENT_SECRET env var)
            tenant_id: Azure tenant ID (falls back to KW_TENANT_ID env var)

        Returns:
            Configured GraphServiceClient instance

        Raises:
            ImportError: If msgraph-sdk or azure-identity not installed
            ValueError: If credentials not provided and not in environment
        """
        # Import here to avoid dependency if not installed
        from azure.identity import ClientSecretCredential
        from msgraph import GraphServiceClient

        # Fall back to environment variables
        app_id = app_id or os.getenv("KW_APP_ID")
        client_secret = client_secret or os.getenv("KW_CLIENT_SECRET")
        tenant_id = tenant_id or os.getenv("KW_TENANT_ID")

        # Validate credentials
        if not all([app_id, client_secret, tenant_id]):
            raise ValueError(
                "M365 credentials required. Set KW_APP_ID, KW_CLIENT_SECRET, "
                "and KW_TENANT_ID environment variables or provide parameters."
            )

        # Create credential
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=app_id,
            client_secret=client_secret,
        )

        # Create and return Graph client
        return GraphServiceClient(credentials=credential)


def initialize_m365_client(
    worker_id: str,
    app_id: str | None = None,
    client_secret: str | None = None,
    tenant_id: str | None = None,
) -> Any | None:
    """Initialize M365 client with comprehensive error handling.

    This helper function wraps M365ClientFactory.create() with error handling
    and logging appropriate for agent initialization.

    Args:
        worker_id: Worker ID for logging context
        app_id: Optional M365 application client ID
        client_secret: Optional client secret
        tenant_id: Optional Azure tenant ID

    Returns:
        Configured M365 client on success, None on any error

    Note:
        This function never raises exceptions - it logs errors and returns None
        to support graceful degradation when M365 SDK not available.
    """
    try:
        client = M365ClientFactory.create(
            app_id=app_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
        )

        logger.info(f"M365 client initialized for {worker_id}")
        return client

    except ImportError:
        logger.warning(
            "Microsoft Graph SDK not installed. "
            "Install with: pip install msgraph-sdk azure-identity"
        )
        return None

    except ValueError as e:
        # Missing credentials - log for debugging
        logger.debug(f"M365 client not initialized for {worker_id}: {e}")
        return None

    except Exception as e:
        logger.error(f"Failed to initialize M365 client for {worker_id}: {e}")
        return None


def validate_content(subject: str, body: str) -> None:
    """Validate email content length.

    Args:
        subject: Email subject line
        body: Email body content

    Raises:
        ValueError: If subject or body exceeds maximum length
    """
    max_subject_length = 200
    max_body_length = 50000

    if len(subject) > max_subject_length:
        raise ValueError(
            f"Email subject too long ({len(subject)} chars). "
            f"Maximum: {max_subject_length} characters."
        )

    if len(body) > max_body_length:
        raise ValueError(
            f"Email body too long ({len(body)} chars). "
            f"Maximum: {max_body_length} characters."
        )


async def send_email(
    worker_identity: Any,
    m365_client: Any,
    validator: Any,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
) -> str | None:
    """Send email to internal recipients. Returns message ID or None.

    Args:
        worker_identity: WorkerIdentity with sender details
        m365_client: M365 Graph client instance
        validator: CommunicationValidator instance
        to: List of recipient email addresses
        subject: Email subject line
        body: Email body content
        cc: Optional list of CC recipients

    Returns:
        Message ID on success, None on failure

    Raises:
        RuntimeError: If M365 client not initialized
        ValueError: If no recipients or content validation fails
    """
    if m365_client is None:
        raise RuntimeError("M365 client not initialized. Call on_start() first.")

    if not to:
        raise ValueError("At least one recipient is required")

    # Validate content length
    validate_content(subject, body)

    from azure_haymaker.knowledge_worker.operations import EmailOperations

    ops = EmailOperations(
        worker_identity=worker_identity,
        m365_client=m365_client,
        validator=validator,
    )

    return await ops.send_email(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
    )


async def create_calendar_event(
    worker_identity: Any,
    m365_client: Any,
    validator: Any,
    subject: str,
    start_time: str,
    end_time: str,
    attendees: list[str] | None = None,
    body: str = "",
    is_online_meeting: bool = False,
) -> str | None:
    """Create calendar event. Returns event ID or None.

    Args:
        worker_identity: WorkerIdentity with organizer details
        m365_client: M365 Graph client instance
        validator: CommunicationValidator instance
        subject: Event subject/title
        start_time: Event start time (ISO format string)
        end_time: Event end time (ISO format string)
        attendees: Optional list of attendee email addresses
        body: Optional event description
        is_online_meeting: Whether to create an online meeting

    Returns:
        Event ID on success, None on failure

    Raises:
        RuntimeError: If M365 client not initialized
    """
    if m365_client is None:
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
        worker_identity=worker_identity,
        m365_client=m365_client,
        validator=validator,
    )

    return await ops.create_event(
        subject=subject,
        start_time=start_dt,
        end_time=end_dt,
        attendees=attendees or [],
        body=body,
        is_online=is_online_meeting,
    )
