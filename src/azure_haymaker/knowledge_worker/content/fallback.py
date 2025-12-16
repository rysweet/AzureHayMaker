"""Fallback email content generator for Knowledge Workers.

Provides simple, hardcoded email content when AI generation is unavailable
or fails. Matches the format of the original orchestrator.py implementation.
"""

import logging
from datetime import UTC, datetime

from azure_haymaker.knowledge_worker.content.email_generator import EmailContent

logger = logging.getLogger(__name__)


class FallbackEmailGenerator:
    """Simple fallback email generator with hardcoded content.

    Generates basic email content without AI, matching the format
    from the original orchestrator.py lines 584-585.

    Example:
        >>> generator = FallbackEmailGenerator()
        >>> content = generator.generate_email(
        ...     worker_id="kw-eng-1",
        ...     activity_count=42,
        ... )
    """

    def generate_email(
        self,
        worker_id: str,
        activity_count: int,
        department: str | None = None,
        run_id: str | None = None,
    ) -> EmailContent:
        """Generate simple fallback email content.

        Args:
            worker_id: Worker identifier (e.g., "kw-eng-1")
            activity_count: Current activity count
            department: Optional department name (for metadata)
            run_id: Optional deployment run ID (for metadata)

        Returns:
            EmailContent with simple subject and body

        Example:
            >>> content = generator.generate_email("kw-eng-1", 42)
            >>> print(content.subject)
            Activity 43 from kw-eng-1
        """
        subject = f"Activity {activity_count + 1} from {worker_id}"
        body = f"<p>Automated activity generated at {datetime.now(UTC).isoformat()}</p>"

        metadata = {
            "source": "fallback",
            "worker_id": worker_id,
            "activity_count": activity_count,
            "generated_at": datetime.now(UTC).isoformat(),
        }

        if department:
            metadata["department"] = department

        if run_id:
            metadata["run_id"] = run_id

        logger.debug(f"Generated fallback email for {worker_id} (activity #{activity_count + 1})")

        return EmailContent(
            subject=subject,
            body=body,
            metadata=metadata,
        )


__all__ = ["FallbackEmailGenerator"]
