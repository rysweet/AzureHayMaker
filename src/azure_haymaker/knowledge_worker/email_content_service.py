"""Email content generation service for knowledge workers.

This module handles email content generation with three-level fallback:
1. AI-generated content (if enabled)
2. Simple template generation
3. Hardcoded fallback content

Philosophy:
- Single responsibility: Email content generation
- Graceful degradation through fallback chain
- No external dependencies beyond content generators
"""

import html
import logging

from azure_haymaker.knowledge_worker.content import (
    EmailContent,
    EmailContentGenerator,
    EmailGenerationConfig,
    FallbackEmailGenerator,
)

logger = logging.getLogger(__name__)


class EmailContentService:
    """Handles email content generation with fallback strategies.

    Provides three-level fallback:
    1. AI generation (if enabled)
    2. Simple template generation
    3. Hardcoded content

    Example:
        >>> config = EmailGenerationConfig(enabled=True)
        >>> service = EmailContentService(config, email_markers_enabled=True)
        >>> content = await service.generate_email_content(
        ...     worker_id="kw-001",
        ...     activity_count=1,
        ...     recipient="user@test.com",
        ...     department="engineering",
        ...     run_id="kw-abc123"
        ... )
    """

    def __init__(
        self,
        email_generation_config: EmailGenerationConfig,
        email_markers_enabled: bool = True,
        marker_format: str = "MARKER",
        marker_style: str = "subject",
    ) -> None:
        """Initialize the email content service.

        Args:
            email_generation_config: AI email generation configuration
            email_markers_enabled: Enable email markers for tracking
            marker_format: Format for markers (e.g., "MARKER", "TAG")
            marker_style: Where to place markers ("subject", "hidden", "both")
        """
        self.email_markers_enabled = email_markers_enabled
        self.marker_format = marker_format
        self.marker_style = marker_style

        # Initialize email generators
        self.email_generator: EmailContentGenerator | None = None
        self.fallback_generator = FallbackEmailGenerator()

        if email_generation_config.enabled:
            try:
                self.email_generator = EmailContentGenerator(email_generation_config)
                logger.info("AI email generation enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize AI email generator: {e}. Using fallback.")

    async def generate_email_content(
        self,
        worker_id: str,
        activity_count: int,
        recipient: str,
        department: str,
        run_id: str | None = None,
    ) -> EmailContent:
        """Generate email content with three-level fallback strategy.

        Strategy:
        1. Try AI generation (if enabled)
        2. Fall back to simple generator on AI failure
        3. Fall back to hardcoded content on any error

        Args:
            worker_id: Worker identifier
            activity_count: Current activity count
            recipient: Recipient email address
            department: Department name
            run_id: Optional deployment run ID

        Returns:
            EmailContent with subject and body
        """
        # Level 1: Try AI generation if enabled
        if self.email_generator:
            try:
                content = await self.email_generator.generate_email(
                    worker_id=worker_id,
                    department=department,
                    recipient=recipient,
                    activity_count=activity_count,
                    run_id=run_id,
                )
            except Exception as e:
                logger.warning(f"AI email generation failed for {worker_id}: {e}. Using fallback.")
                content = self._use_fallback(worker_id, activity_count, department, run_id)
        else:
            # Level 2 & 3: Use fallback generator
            content = self._use_fallback(worker_id, activity_count, department, run_id)

        # Add markers if enabled
        if self.email_markers_enabled:
            content = self.add_email_markers(
                content,
                worker_id=worker_id,
                activity_count=activity_count,
                run_id=run_id,
            )

        return content

    def _use_fallback(
        self,
        worker_id: str,
        activity_count: int,
        department: str,
        run_id: str | None,
    ) -> EmailContent:
        """Use fallback generator for email content.

        Args:
            worker_id: Worker identifier
            activity_count: Current activity count
            department: Department name
            run_id: Optional deployment run ID

        Returns:
            EmailContent from fallback generator
        """
        return self.fallback_generator.generate_email(
            worker_id=worker_id,
            activity_count=activity_count,
            department=department,
            run_id=run_id,
        )

    def add_email_markers(
        self,
        email_content: EmailContent,
        worker_id: str,
        activity_count: int,
        run_id: str | None,
    ) -> EmailContent:
        """Add tracking markers to email content.

        Adds markers based on configuration (subject, hidden, or both).

        Args:
            email_content: Original email content
            worker_id: Worker identifier
            activity_count: Current activity count
            run_id: Deployment run ID

        Returns:
            EmailContent with markers added
        """
        # Security: Escape all marker components to prevent HTML injection
        safe_format = html.escape(self.marker_format)
        safe_run_id = html.escape(run_id or "unknown")
        safe_worker_id = html.escape(worker_id)
        safe_count = html.escape(str(activity_count + 1))

        marker_text = f"[{safe_format}:{safe_run_id}:{safe_worker_id}:{safe_count}]"

        subject = email_content.subject
        body = email_content.body

        # Add to subject if configured
        if self.marker_style in ("subject", "both"):
            subject = f"{marker_text} {subject}"

        # Add hidden marker to body if configured
        if self.marker_style in ("hidden", "both"):
            # Security: HTML comment injection prevention
            # Escape the marker to prevent breaking out of comments with -->
            # Double escaping here is intentional - once for the marker text itself,
            # and the marker_text is already escaped above
            body = f"<!-- {marker_text} -->\n{body}"

        # Update metadata
        metadata = email_content.metadata.copy()
        metadata["marker"] = marker_text
        metadata["marker_style"] = self.marker_style

        return EmailContent(
            subject=subject,
            body=body,
            metadata=metadata,
        )


__all__ = ["EmailContentService"]
