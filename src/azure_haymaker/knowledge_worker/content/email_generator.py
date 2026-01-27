"""AI-powered email content generator for Knowledge Workers.

Uses the LLM abstraction layer to generate realistic email content with
custom directives (e.g., include limericks in signature). Supports multiple
LLM providers: Anthropic Claude, Azure OpenAI, and Azure AI Foundry.
"""

import html
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, SecretStr

from azure_haymaker.knowledge_worker.content.prompts import (
    build_system_prompt,
    build_user_prompt,
)
from azure_haymaker.llm import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMRateLimitError,
    create_llm_client,
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

    Supports multiple LLM providers through the LLM abstraction layer.

    Attributes:
        enabled: Whether AI generation is enabled
        provider: LLM provider to use (anthropic, azure_openai, azure_ai_foundry)
        api_key: API key (optional, uses env var or managed identity if not provided)
        endpoint: Azure endpoint URL (required for Azure providers)
        deployment: Azure OpenAI deployment name (required for azure_openai)
        model: Model name to use
        directive: Custom directive for email generation (e.g., "Include a limerick")
        max_tokens: Maximum tokens for generation
        temperature: Temperature for generation (0.0-1.0)
        timeout_seconds: API timeout in seconds
    """

    enabled: bool = False
    provider: Literal["anthropic", "azure_openai", "azure_ai_foundry"] = "anthropic"
    api_key: SecretStr | None = None
    endpoint: str | None = None
    deployment: str | None = None
    model: str | None = None
    directive: str | None = None
    max_tokens: int = 1024
    temperature: float = 0.7
    timeout_seconds: int = 30

    model_config = {"frozen": False}

    def to_llm_config(self) -> LLMConfig:
        """Convert to LLMConfig for the LLM abstraction layer.

        Returns:
            LLMConfig configured for the selected provider
        """
        return LLMConfig(
            provider=self.provider,
            api_key=self.api_key,
            endpoint=self.endpoint,
            deployment=self.deployment,
            model=self.model,
            timeout_seconds=self.timeout_seconds,
        )


class EmailContentGenerator:
    """AI-powered email content generator using the LLM abstraction layer.

    Generates realistic email content with custom directives per department.
    Supports multiple LLM providers: Anthropic Claude, Azure OpenAI, Azure AI Foundry.
    Handles API errors gracefully and provides detailed logging.

    Example:
        >>> # Anthropic Claude (default, backward compatible)
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
        >>>
        >>> # Azure OpenAI with managed identity
        >>> config = EmailGenerationConfig(
        ...     enabled=True,
        ...     provider="azure_openai",
        ...     endpoint="https://myresource.openai.azure.com",
        ...     deployment="gpt-4",
        ...     directive="Include a humorous limerick in your signature"
        ... )
        >>> generator = EmailContentGenerator(config)
    """

    def __init__(self, config: EmailGenerationConfig) -> None:
        """Initialize the email content generator.

        Args:
            config: Email generation configuration

        Raises:
            ValueError: If config.enabled is True but required config is missing
        """
        self.config = config
        self._client: BaseLLMProvider | None = None

        if config.enabled:
            try:
                llm_config = config.to_llm_config()
                self._client = create_llm_client(llm_config)
                logger.info(f"LLM client initialized successfully (provider: {config.provider})")
            except Exception as e:
                safe_error = sanitize_error_message(e)
                logger.error(f"Failed to initialize LLM client: {safe_error}")
                raise ValueError(f"Failed to initialize LLM client: {safe_error}") from e
        else:
            logger.debug("AI email generation disabled")

    async def generate_email(
        self,
        worker_id: str,
        department: str,
        recipient: str,
        activity_count: int,
        run_id: str | None = None,
    ) -> EmailContent:
        """Generate email content using the configured LLM provider.

        Args:
            worker_id: Worker identifier (e.g., "kw-eng-1")
            department: Department name (e.g., "engineering")
            recipient: Recipient email address
            activity_count: Current activity count for context
            run_id: Optional deployment run ID

        Returns:
            EmailContent with AI-generated subject and body

        Raises:
            RuntimeError: If AI generation is not enabled or LLM call fails
            ValueError: If inputs fail validation
        """
        if not self.config.enabled or self._client is None:
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
            logger.debug(
                f"Generating email content for {worker_id} -> {recipient} "
                f"(activity #{activity_count}, provider: {self.config.provider})"
            )

            # Use the LLM abstraction layer
            messages = [LLMMessage(role="user", content=user_prompt)]
            response = await self._client.create_message_async(
                messages=messages,
                system=system_prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            # Parse subject and body from response
            subject, body = self._parse_email_response(response.content)

            # Create metadata (preserve backward-compatible source name for Anthropic)
            source_name = (
                "anthropic_claude"
                if self.config.provider == "anthropic"
                else f"llm_{self.config.provider}"
            )
            metadata = {
                "source": source_name,
                "model": response.model,
                "worker_id": worker_id,
                "department": department,
                "activity_count": activity_count,
                "generated_at": datetime.now(UTC).isoformat(),
                "tokens_used": response.usage.get("output_tokens", 0),
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

        except LLMRateLimitError as e:
            logger.error("LLM rate limit exceeded")
            raise RuntimeError("AI service temporarily unavailable due to rate limits") from e
        except Exception as e:
            safe_error = sanitize_error_message(e)
            logger.error(f"LLM error: {safe_error}")
            raise RuntimeError(f"AI service error: {safe_error}") from e

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
