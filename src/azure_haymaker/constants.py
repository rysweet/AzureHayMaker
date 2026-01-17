"""Project-wide constants for Azure HayMaker.

This module centralizes magic numbers and configuration defaults used across
the project. All constants are typed and documented for clarity.

Addresses Issue #21: Extract magic numbers to constants modules.
"""

# ============================================================================
# Timeout Constants (seconds)
# ============================================================================

DEFAULT_API_TIMEOUT_SECONDS: int = 30
"""Default timeout for API calls."""

DEFAULT_OPERATION_TIMEOUT_SECONDS: int = 120
"""Default timeout for longer operations."""

MAILBOX_PROVISIONING_TIMEOUT_SECONDS: int = 900
"""Timeout for waiting for mailbox provisioning (15 minutes)."""

EMAIL_GENERATION_TIMEOUT_SECONDS: int = 30
"""Timeout for AI email content generation."""

# ============================================================================
# Retry Constants
# ============================================================================

DEFAULT_RETRY_COUNT: int = 3
"""Default number of retries for failed operations."""

MAX_RETRY_COUNT: int = 5
"""Maximum number of retries allowed."""

DEFAULT_RETRY_DELAY_SECONDS: float = 0.1
"""Default delay between retries."""

RATE_LIMIT_DELAY_SECONDS: float = 0.1
"""Delay between API calls to respect rate limits (10 requests/second)."""

# ============================================================================
# Worker Constants
# ============================================================================

DEFAULT_WORKERS_PER_DEPLOYMENT: int = 10
"""Default number of workers per deployment."""

MAX_WORKERS_PER_DEPLOYMENT: int = 100
"""Maximum workers allowed per deployment."""

PASSWORD_LENGTH: int = 24
"""Length of generated secure passwords."""

# ============================================================================
# Activity Constants
# ============================================================================

DEFAULT_DURATION_HOURS: int = 8
"""Default deployment duration in hours."""

DEFAULT_EMAIL_PER_HOUR: int = 4
"""Default emails generated per hour per worker."""

DEFAULT_TEAMS_MESSAGES_PER_HOUR: int = 15
"""Default Teams messages per hour per worker."""

DEFAULT_DOCUMENTS_PER_DAY: int = 5
"""Default documents created per day per worker."""

DEFAULT_MEETINGS_PER_DAY: int = 4
"""Default meetings created per day per worker."""

DEFAULT_ACTIVITY_FREQUENCY_MINUTES: int = 30
"""Default frequency of worker activity checks in minutes."""

# ============================================================================
# Container Constants
# ============================================================================

CONTAINER_MEMORY_GB: int = 64
"""Default container memory allocation in GB."""

CONTAINER_TIMEOUT_HOURS: int = 10
"""Default container timeout in hours."""

DEFAULT_BATCH_SIZE: int = 100
"""Default batch size for message processing."""

# ============================================================================
# TTL Constants
# ============================================================================

EVENT_TTL_SECONDS: int = 604800
"""Event time-to-live (7 days in seconds)."""

SECRET_ROTATION_DAYS: int = 30
"""Service principal secret rotation period in days."""

MAX_SECRET_AGE_DAYS: int = 90
"""Maximum age of secrets before forced rotation."""

# ============================================================================
# Token and Content Limits
# ============================================================================

MAX_TOKENS_EMAIL_GENERATION: int = 1024
"""Maximum tokens for email content generation."""

MAX_ACTIVITY_COUNT: int = 1_000_000
"""Maximum activity count for validation."""

# ============================================================================
# Tracing Constants
# ============================================================================

TRACE_ID_LENGTH: int = 32
"""Length of W3C trace ID in hex characters."""

SPAN_ID_LENGTH: int = 16
"""Length of W3C span ID in hex characters."""

# ============================================================================
# CI Pipeline Constants
# ============================================================================

CI_MAX_WAIT_SECONDS: int = 600
"""Maximum wait time for CI pipeline completion."""

CI_POLL_INTERVAL_SECONDS: int = 10
"""Polling interval for CI status checks."""

# ============================================================================
# Validation Patterns
# ============================================================================

WORKER_ID_MAX_LENGTH: int = 64
"""Maximum length for worker ID."""

DEPARTMENT_MAX_LENGTH: int = 50
"""Maximum length for department name."""

# ============================================================================
# Priority Constants
# ============================================================================

MIN_PRIORITY: int = 0
"""Minimum activity priority value."""

MAX_PRIORITY: int = 10
"""Maximum activity priority value."""

DEFAULT_PRIORITY: int = 5
"""Default activity priority value."""


__all__ = [
    # Timeouts
    "DEFAULT_API_TIMEOUT_SECONDS",
    "DEFAULT_OPERATION_TIMEOUT_SECONDS",
    "MAILBOX_PROVISIONING_TIMEOUT_SECONDS",
    "EMAIL_GENERATION_TIMEOUT_SECONDS",
    # Retries
    "DEFAULT_RETRY_COUNT",
    "MAX_RETRY_COUNT",
    "DEFAULT_RETRY_DELAY_SECONDS",
    "RATE_LIMIT_DELAY_SECONDS",
    # Workers
    "DEFAULT_WORKERS_PER_DEPLOYMENT",
    "MAX_WORKERS_PER_DEPLOYMENT",
    "PASSWORD_LENGTH",
    # Activities
    "DEFAULT_DURATION_HOURS",
    "DEFAULT_EMAIL_PER_HOUR",
    "DEFAULT_TEAMS_MESSAGES_PER_HOUR",
    "DEFAULT_DOCUMENTS_PER_DAY",
    "DEFAULT_MEETINGS_PER_DAY",
    "DEFAULT_ACTIVITY_FREQUENCY_MINUTES",
    # Containers
    "CONTAINER_MEMORY_GB",
    "CONTAINER_TIMEOUT_HOURS",
    "DEFAULT_BATCH_SIZE",
    # TTL
    "EVENT_TTL_SECONDS",
    "SECRET_ROTATION_DAYS",
    "MAX_SECRET_AGE_DAYS",
    # Tokens
    "MAX_TOKENS_EMAIL_GENERATION",
    "MAX_ACTIVITY_COUNT",
    # Tracing
    "TRACE_ID_LENGTH",
    "SPAN_ID_LENGTH",
    # CI
    "CI_MAX_WAIT_SECONDS",
    "CI_POLL_INTERVAL_SECONDS",
    # Validation
    "WORKER_ID_MAX_LENGTH",
    "DEPARTMENT_MAX_LENGTH",
    # Priority
    "MIN_PRIORITY",
    "MAX_PRIORITY",
    "DEFAULT_PRIORITY",
]
