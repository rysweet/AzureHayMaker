"""Communication validation for internal-only M365 operations.

Implements the application-level safety controls to ensure all
communications (email, Teams, calendar invites) stay within the
tenant boundary.
"""

import logging
from collections.abc import Sequence

logger = logging.getLogger(__name__)


class ExternalRecipientError(Exception):
    """Raised when an operation attempts to contact external recipients.

    This is a critical safety exception that indicates an attempt to
    send communications outside the tenant boundary.

    Attributes:
        recipients: List of external recipient addresses that were blocked
        message: Descriptive error message
    """

    def __init__(self, recipients: Sequence[str], message: str | None = None):
        """Initialize ExternalRecipientError.

        Args:
            recipients: List of external recipient addresses
            message: Optional custom error message
        """
        self.recipients = list(recipients)
        if message is None:
            message = f"External recipients blocked: {', '.join(self.recipients)}"
        super().__init__(message)


class CommunicationValidator:
    """Validates all communications are internal-only.

    This is a critical safety component that ensures no M365 operations
    can send communications to recipients outside the tenant. It operates
    as part of the defense-in-depth strategy alongside Exchange transport
    rules.

    The validator checks recipients against:
    1. An explicit allowlist of known internal UPNs
    2. The tenant domain for any addresses not in the allowlist

    Attributes:
        tenant_domain: The tenant's primary domain (lowercase)
        allowed_upns: Set of allowed internal UPNs (lowercase)
    """

    def __init__(
        self,
        tenant_domain: str,
        allowed_upns: set[str] | None = None,
    ):
        """Initialize CommunicationValidator.

        Args:
            tenant_domain: Primary domain of the M365 tenant
            allowed_upns: Optional set of explicitly allowed UPNs/emails
        """
        self.tenant_domain = tenant_domain.lower().strip()
        self.allowed_upns: set[str] = (
            {upn.lower().strip() for upn in allowed_upns}
            if allowed_upns
            else set()
        )

    def add_allowed_upn(self, upn: str) -> None:
        """Add a UPN to the allowed list.

        Args:
            upn: User principal name or email to allow
        """
        self.allowed_upns.add(upn.lower().strip())

    def add_allowed_upns(self, upns: Sequence[str]) -> None:
        """Add multiple UPNs to the allowed list.

        Args:
            upns: List of user principal names or emails to allow
        """
        for upn in upns:
            self.add_allowed_upn(upn)

    def remove_allowed_upn(self, upn: str) -> None:
        """Remove a UPN from the allowed list.

        Args:
            upn: User principal name or email to remove
        """
        self.allowed_upns.discard(upn.lower().strip())

    def is_internal(self, recipient: str) -> bool:
        """Check if recipient is internal to the tenant.

        A recipient is considered internal if:
        1. It is in the explicit allowed UPNs list, OR
        2. Its domain matches the tenant domain

        Args:
            recipient: Email address or UPN to check

        Returns:
            True if recipient is internal, False otherwise
        """
        recipient = recipient.lower().strip()

        # Check explicit allowlist first
        if recipient in self.allowed_upns:
            return True

        # Check domain
        if "@" in recipient:
            domain = recipient.split("@", 1)[1]
            return domain == self.tenant_domain

        # No @ sign means this isn't a valid email/UPN
        logger.warning(f"Invalid recipient format (no @): {recipient}")
        return False

    def filter_recipients(self, recipients: Sequence[str]) -> list[str]:
        """Filter list to only internal recipients.

        Returns only the recipients that pass the internal check.
        Logs warnings for any filtered (external) recipients.

        Args:
            recipients: List of email addresses or UPNs to filter

        Returns:
            List of internal recipients only
        """
        internal: list[str] = []
        external: list[str] = []

        for recipient in recipients:
            if self.is_internal(recipient):
                internal.append(recipient)
            else:
                external.append(recipient)

        if external:
            logger.warning(
                f"Filtered {len(external)} external recipients: {', '.join(external)}"
            )

        return internal

    def validate_or_raise(self, recipients: Sequence[str]) -> None:
        """Validate recipients or raise exception.

        Checks all recipients and raises ExternalRecipientError if
        any external recipients are found.

        Args:
            recipients: List of email addresses or UPNs to validate

        Raises:
            ExternalRecipientError: If any recipients are external
        """
        external = [r for r in recipients if not self.is_internal(r)]
        if external:
            logger.error(f"External recipients blocked: {', '.join(external)}")
            raise ExternalRecipientError(external)

    def validate_single(self, recipient: str) -> bool:
        """Validate a single recipient.

        Convenience method for checking a single recipient.

        Args:
            recipient: Email address or UPN to validate

        Returns:
            True if internal, False if external
        """
        return self.is_internal(recipient)

    def get_statistics(self) -> dict[str, int]:
        """Get statistics about the validator state.

        Returns:
            Dictionary with allowlist size and domain info
        """
        return {
            "allowed_upns_count": len(self.allowed_upns),
            "tenant_domain_length": len(self.tenant_domain),
        }
