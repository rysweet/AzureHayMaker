"""AI-powered email content generator for Knowledge Workers.

Uses Anthropic Claude API to generate realistic email content with
custom directives (e.g., include limericks in signature).
"""

import html
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from anthropic import Anthropic, AnthropicError, RateLimitError
from anthropic.types import TextBlock
from pydantic import BaseModel

from azure_haymaker.knowledge_worker.content.prompts import (
    build_system_prompt,
    build_user_prompt,
)

logger = logging.getLogger(__name__)


# Security: Input validation patterns
WORKER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
DEPARTMENT_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_input(value: str, pattern: re.Pattern, field_name: str) -> None:
    """Validate input against a pattern.

    Args:
        value: Input value to validate
        pattern: Regex pattern for validation
        field_name: Name of field for error messages

    Raises:
        ValueError: If input doesn't match pattern
    """
    if not pattern.match(value):
        raise ValueError(f"Invalid {field_name}: must match pattern {pattern.pattern}")


def sanitize_error_message(error: Exception) -> str:
    """Sanitize error messages to prevent information disclosure.

    Removes sensitive information like API keys, tokens, and internal paths
    from error messages.

    Args:
        error: Original exception

    Returns:
        Sanitized error message string
    """
    error_str = str(error)

    # Remove potential API keys (sk-ant-*, sk-*, etc.)
    error_str = re.sub(r"sk-[a-zA-Z0-9-]+", "[REDACTED]", error_str)

    # Remove potential tokens
    error_str = re.sub(
        r"token[:\s]+[a-zA-Z0-9_-]+", "token: [REDACTED]", error_str, flags=re.IGNORECASE
    )

    # Remove file paths that might leak internal structure
    error_str = re.sub(r"/[a-zA-Z0-9_/.-]+\.py", "[PATH]", error_str)

    return error_str


@dataclass
class EmailContent:
    """Email content with subject, body, and metadata.

    Attributes:
        subject: Email subject line
        body: Email body (HTML format)
        metadata: Additional metadata (generation source, timestamp, etc.)
    """

    subject: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)


class EmailGenerationConfig(BaseModel):
    """Configuration for AI email generation.

    Attributes:
        enabled: Whether AI generation is enabled
        api_key: Anthropic API key (optional, uses ANTHROPIC_API_KEY env var if not provided)
        model: Claude model to use
        directive: Custom directive for email generation (e.g., "Include a limerick")
        max_tokens: Maximum tokens for generation
        temperature: Temperature for generation (0.0-1.0)
        timeout_seconds: API timeout in seconds
    """

    enabled: bool = False
    api_key: str | None = None
    model: str | None = None  # Use Anthropic SDK default if not specified
    directive: str | None = None
    max_tokens: int = 1024
    temperature: float = 0.7
    timeout_seconds: int = 30

    model_config = {"frozen": False}


class EmailContentGenerator:
    """AI-powered email content generator using Anthropic Claude.

    Generates realistic email content with custom directives per department.
    Handles API errors gracefully and provides detailed logging.

    Example:
        >>> config = EmailGenerationConfig(
        ...     enabled=True,
        ...     api_key="sk-ant-...",
        ...     directive="Include a humorous limerick in your signature"
        ... )
        >>> generator = EmailContentGenerator(config)
        >>> content = await generator.generate_email(
        ...     worker_id="kw-eng-1",
        ...     department="engineering",
        ...     recipient="kw-eng-2@test.com",
        ...     activity_count=42,
        ... )
    """

    def __init__(self, config: EmailGenerationConfig) -> None:
        """Initialize the email content generator.

        Args:
            config: Email generation configuration

        Raises:
            ValueError: If config.enabled is True but API key is not available
        """
        self.config = config

        if config.enabled:
            # Initialize Anthropic client
            # If api_key is None, Anthropic SDK will use ANTHROPIC_API_KEY env var
            try:
                self.client = Anthropic(
                    api_key=config.api_key,
                    timeout=config.timeout_seconds,
                )
                logger.info("Anthropic client initialized successfully")
            except Exception as e:
                # Security: Sanitize error message to prevent API key leakage
                safe_error = sanitize_error_message(e)
                logger.error(f"Failed to initialize Anthropic client: {safe_error}")
                raise ValueError(f"Failed to initialize Anthropic client: {safe_error}") from e
        else:
            self.client = None
            logger.debug("AI email generation disabled")

    async def generate_email(
        self,
        worker_id: str,
        department: str,
        recipient: str,
        activity_count: int,
        run_id: str | None = None,
    ) -> EmailContent:
        """Generate email content using Claude AI.

        Args:
            worker_id: Worker identifier (e.g., "kw-eng-1")
            department: Department name (e.g., "engineering")
            recipient: Recipient email address
            activity_count: Current activity count for context
            run_id: Optional deployment run ID

        Returns:
            EmailContent with AI-generated subject and body

        Raises:
            RuntimeError: If AI generation is not enabled
            ValueError: If inputs fail validation
            AnthropicError: If API call fails
        """
        if not self.config.enabled or self.client is None:
            raise RuntimeError("AI email generation is not enabled")

        # Security: Validate all inputs to prevent injection attacks
        validate_input(worker_id, WORKER_ID_PATTERN, "worker_id")
        validate_input(department, DEPARTMENT_PATTERN, "department")
        validate_input(recipient, EMAIL_PATTERN, "recipient")

        if activity_count < 0 or activity_count > 1_000_000:
            raise ValueError("activity_count must be between 0 and 1,000,000")

        # Build prompts
        system_prompt = build_system_prompt(
            department=department,
            directive=self.config.directive,
        )

        user_prompt = build_user_prompt(
            worker_id=worker_id,
            recipient=recipient,
            activity_count=activity_count,
        )

        try:
            # Call Anthropic API
            logger.debug(
                f"Generating email content for {worker_id} -> {recipient} "
                f"(activity #{activity_count})"
            )

            # Use specified model or default to Claude Sonnet 4.5
            # Handle empty/whitespace strings by falling back to default
            model = (
                self.config.model.strip()
                if self.config.model and self.config.model.strip()
                else "claude-sonnet-4-5-20250929"
            )

            response = self.client.messages.create(
                model=model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ],
            )

            # Extract content from response
            # Only TextBlock has .text attribute, check block type first
            content_text = ""
            if response.content:
                first_block = response.content[0]
                if isinstance(first_block, TextBlock):
                    content_text = first_block.text

            # Parse subject and body from response
            subject, body = self._parse_email_response(content_text)

            # Create metadata
            metadata = {
                "source": "anthropic_claude",
                "model": model,  # Use the actual model that was used
                "worker_id": worker_id,
                "department": department,
                "activity_count": activity_count,
                "generated_at": datetime.now(UTC).isoformat(),
                "tokens_used": response.usage.output_tokens if response.usage else 0,
            }

            if run_id:
                metadata["run_id"] = run_id

            logger.info(
                f"Generated email content for {worker_id}: "
                f"{subject[:50]}... ({metadata['tokens_used']} tokens)"
            )

            return EmailContent(
                subject=subject,
                body=body,
                metadata=metadata,
            )

        except RateLimitError as e:
            # Security: Don't leak API details in rate limit errors
            logger.error("Anthropic API rate limit exceeded")
            raise RuntimeError("AI service temporarily unavailable due to rate limits") from e
        except AnthropicError as e:
            # Security: Sanitize API errors
            safe_error = sanitize_error_message(e)
            logger.error(f"Anthropic API error: {safe_error}")
            raise RuntimeError(f"AI service error: {safe_error}") from e
        except Exception as e:
            # Security: Sanitize unexpected errors
            safe_error = sanitize_error_message(e)
            logger.error(f"Unexpected error generating email content: {safe_error}")
            raise RuntimeError(f"Failed to generate email content: {safe_error}") from e

    def _parse_email_response(self, content: str) -> tuple[str, str]:
        """Parse subject and body from Claude's response.

        Expected format:
            Subject: [subject line]
            Body: [body content]

        Or:
            Subject: [subject line]

            [body content]

        Args:
            content: Raw response text from Claude

        Returns:
            Tuple of (subject, body)
        """
        lines = content.strip().split("\n", 1)

        # Extract subject
        subject = "Knowledge Worker Activity"
        if lines and lines[0].lower().startswith("subject:"):
            subject = lines[0].split(":", 1)[1].strip()

        # Extract body
        body = "<p>Automated activity generated by Knowledge Worker.</p>"
        if len(lines) > 1:
            body_text = lines[1].strip()

            # Remove "Body:" prefix if present
            if body_text.lower().startswith("body:"):
                body_text = body_text.split(":", 1)[1].strip()

            # Convert to HTML if not already
            if not body_text.startswith("<"):
                # Security: Escape all content to prevent XSS
                # Simple markdown-like conversion with proper escaping
                paragraphs = body_text.split("\n\n")
                body = "".join(f"<p>{html.escape(p.strip())}</p>" for p in paragraphs if p.strip())
            else:
                # Security: Even if it looks like HTML, escape it to prevent XSS
                # The AI should not be generating raw HTML
                body = html.escape(body_text)

        return subject, body


__all__ = [
    "EmailContent",
    "EmailGenerationConfig",
    "EmailContentGenerator",
]
