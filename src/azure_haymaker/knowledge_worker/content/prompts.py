"""Prompt templates and builders for AI email generation.

Provides system and user prompts for Claude to generate realistic
Knowledge Worker email content with custom directives.
"""

import re


# Security: Dangerous patterns in directives that could lead to prompt injection
DANGEROUS_DIRECTIVE_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|directives|rules)",
    r"disregard\s+(all\s+)?(previous|above|prior)",
    r"forget\s+(all\s+)?(previous|above|prior)",
    r"new\s+(instructions|directives|rules|system\s+prompt)",
    r"you\s+are\s+now",
    r"act\s+as",
    r"pretend\s+(to\s+be|you\s+are)",
    r"override",
    r"system\s*:",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"\{system\}",
]


def validate_directive(directive: str | None) -> str | None:
    """Validate and sanitize directive to prevent prompt injection.

    Args:
        directive: User-provided directive string

    Returns:
        Validated directive or None if invalid

    Raises:
        ValueError: If directive contains injection patterns
    """
    if directive is None or directive.strip() == "":
        return None

    directive_lower = directive.lower()

    # Check for dangerous patterns
    for pattern in DANGEROUS_DIRECTIVE_PATTERNS:
        if re.search(pattern, directive_lower, re.IGNORECASE):
            raise ValueError(
                f"Invalid directive: contains potentially malicious pattern. "
                f"Directives should only contain simple instructions for email style."
            )

    # Length check to prevent extremely long directives
    if len(directive) > 500:
        raise ValueError("Directive too long: maximum 500 characters")

    # Character whitelist - allow letters, numbers, spaces, and basic punctuation
    if not re.match(r"^[a-zA-Z0-9\s.,!?;:()\-'\"]+$", directive):
        raise ValueError(
            "Invalid characters in directive: only letters, numbers, spaces, "
            "and basic punctuation allowed"
        )

    return directive.strip()


# Default system prompt template
DEFAULT_SYSTEM_PROMPT = """You are a {department} worker in a corporate environment generating a realistic work email.

Write a brief, professional email that a {department} worker would naturally send to a colleague during their workday. The email should be contextually appropriate and feel authentic.

Format your response EXACTLY as:
Subject: [your subject line]
Body: [your email body]

Guidelines:
- Keep the subject line concise and relevant (5-10 words)
- Keep the body brief and natural (2-4 sentences)
- Use appropriate tone for a {department} professional
- Do not include greetings like "Hi" or "Dear" - start directly with content
- Do not include signature blocks with names/titles
- Focus on realistic work activities (status updates, questions, sharing info, etc.)

{directive_section}"""

# Directive section template
DIRECTIVE_SECTION = """
IMPORTANT CUSTOM DIRECTIVE:
{directive}

You MUST follow this directive in your email generation."""


def build_system_prompt(department: str, directive: str | None = None) -> str:
    """Build system prompt for Claude based on department and directive.

    Args:
        department: Department name (e.g., "engineering", "marketing")
        directive: Optional custom directive (e.g., "Include a limerick in signature")

    Returns:
        Complete system prompt string

    Raises:
        ValueError: If directive contains malicious patterns

    Example:
        >>> prompt = build_system_prompt(
        ...     department="engineering",
        ...     directive="Include a humorous limerick about AI in your signature"
        ... )
    """
    # Security: Validate directive to prevent prompt injection
    validated_directive = validate_directive(directive)

    # Build directive section if provided and valid
    directive_section = ""
    if validated_directive:
        directive_section = DIRECTIVE_SECTION.format(directive=validated_directive)

    # Build complete system prompt
    return DEFAULT_SYSTEM_PROMPT.format(
        department=department,
        directive_section=directive_section,
    )


# User prompt template
USER_PROMPT_TEMPLATE = """Generate an email for this context:

Worker ID: {worker_id}
Sending to: {recipient}
Activity number: {activity_count}

Generate a realistic work email appropriate for this worker's daily activities."""


def build_user_prompt(
    worker_id: str,
    recipient: str,
    activity_count: int,
) -> str:
    """Build user prompt with activity context.

    Args:
        worker_id: Worker identifier (e.g., "kw-eng-1")
        recipient: Recipient email address
        activity_count: Current activity count

    Returns:
        Complete user prompt string

    Example:
        >>> prompt = build_user_prompt(
        ...     worker_id="kw-eng-1",
        ...     recipient="kw-eng-2@test.com",
        ...     activity_count=42,
        ... )
    """
    return USER_PROMPT_TEMPLATE.format(
        worker_id=worker_id,
        recipient=recipient,
        activity_count=activity_count,
    )


__all__ = [
    "build_system_prompt",
    "build_user_prompt",
]
