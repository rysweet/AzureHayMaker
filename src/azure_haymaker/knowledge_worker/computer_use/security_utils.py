"""Security utilities for Computer Use Knowledge Worker Agents.

This module provides security-focused utilities for sanitizing sensitive data
in logs, error messages, and telemetry to prevent credential leakage.

SECURITY: All error messages and logs must be sanitized before output to prevent
accidental exposure of passwords, tokens, API keys, and other sensitive data.

Key features:
- Credential sanitization in error messages
- Password/token redaction in logs
- Connection string sanitization
- URL credential removal
- Pattern-based secret detection
"""

import re
from typing import Any

# SECURITY: Patterns for detecting sensitive data
# Each pattern should match the entire sensitive portion including the keyword
SENSITIVE_PATTERNS = [
    # Password patterns - match "password: value" or "password=value" etc
    (re.compile(r"password[=:\s]+['\"]?([^'\";\s!]+!?)", re.IGNORECASE), "password"),
    (re.compile(r"passwd[=:\s]+['\"]?([^'\";\s!]+!?)", re.IGNORECASE), "passwd"),
    (re.compile(r"pwd[=:\s]+['\"]?([^'\";\s!]+!?)", re.IGNORECASE), "pwd"),
    # API keys and tokens (with various separators or just whitespace)
    (re.compile(r"(api[_-]?\s*key)[=:\s]+['\"]?([^'\";\s]+)", re.IGNORECASE), "api_key"),
    (re.compile(r"(access[_-]?\s*token)[=:\s]+['\"]?([^'\";\s]+)", re.IGNORECASE), "access_token"),
    (re.compile(r"bearer\s+([A-Za-z0-9._-]+)", re.IGNORECASE), "bearer_token"),
    (re.compile(r"(auth[_-]?\s*token)[=:\s]+['\"]?([^'\";\s]+)", re.IGNORECASE), "auth_token"),
    # Azure/AWS connection strings
    (re.compile(r"AccountKey=([^;\"'\s]+)", re.IGNORECASE), "account_key"),
    (re.compile(r"SharedAccessKey=([^;\"'\s]+)", re.IGNORECASE), "shared_access_key"),
    (re.compile(r"aws_secret_access_key[=:\s]+['\"]?([^'\";\s]+)", re.IGNORECASE), "aws_secret"),
    # URLs with credentials
    (re.compile(r"://([^:]+):([^@]+)@", re.IGNORECASE), "url_credentials"),
    # Private keys
    (re.compile(r"-----BEGIN[A-Z\s]+PRIVATE KEY-----[\s\S]*?-----END[A-Z\s]+PRIVATE KEY-----", re.IGNORECASE), "private_key"),
    # Client secrets
    (re.compile(r"client[_-]?secret[=:\s]+['\"]?([^'\";\s]+)", re.IGNORECASE), "client_secret"),
    # Certificates
    (re.compile(r"certificate[=:\s]+['\"]?([^'\";\s]+)", re.IGNORECASE), "certificate"),
]

# SECURITY: Keywords that indicate sensitive data
SENSITIVE_KEYWORDS = [
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "certificate",
    "cert",
    "credential",
    "auth",
]


def sanitize_error(error_message: str | Exception) -> str:
    """Sanitize error message to remove sensitive data.

    SECURITY: This function is critical for preventing credential leakage.
    It removes passwords, tokens, API keys, and other secrets from error
    messages before they are logged or displayed.

    Args:
        error_message: Error message string or Exception object to sanitize

    Returns:
        Sanitized error message with sensitive data replaced by [REDACTED]

    Example:
        >>> sanitize_error("Failed to connect with password: Secret123!")
        'Failed to connect with password: [REDACTED]'

        >>> sanitize_error("API call failed: Bearer sk-1234567890abcdef")
        'API call failed: Bearer [REDACTED]'

        >>> sanitize_error(Exception("Connection string: AccountKey=secret=="))
        'Connection string: AccountKey=[REDACTED]'
    """
    # Convert exception to string if needed
    if isinstance(error_message, Exception):
        error_message = str(error_message)

    if not isinstance(error_message, str):
        return str(error_message)

    sanitized = error_message

    # Apply all sensitive patterns
    for pattern, label in SENSITIVE_PATTERNS:
        if label == "url_credentials":
            # Special handling for URL credentials: user:pass@host -> [REDACTED]@host
            sanitized = pattern.sub(r"://[REDACTED]@", sanitized)
        elif label == "private_key":
            # Replace entire private key block
            sanitized = pattern.sub("[REDACTED-PRIVATE-KEY]", sanitized)
        elif label == "bearer_token":
            # Replace just the token value after "Bearer "
            sanitized = pattern.sub(r"Bearer [REDACTED]", sanitized)
        elif label in ["api_key", "access_token", "auth_token"]:
            # These patterns have 2 groups: (keyword)(value)
            # Replace the value group (group 2) with [REDACTED]
            def replacer(match):
                # Keep the keyword and separator, redact the value
                return match.group(0).replace(match.group(2), "[REDACTED]")
            sanitized = pattern.sub(replacer, sanitized)
        else:
            # Simple patterns with one capture group (the value to redact)
            # Replace the captured value with [REDACTED]
            def replacer(match):
                # Keep everything except the last captured group
                full_match = match.group(0)
                secret_value = match.group(match.lastindex if match.lastindex else 1)
                return full_match.replace(secret_value, "[REDACTED]")
            sanitized = pattern.sub(replacer, sanitized)

    return sanitized


def sanitize_dict(data: dict[str, Any], redact_value: str = "[REDACTED]") -> dict[str, Any]:
    """Sanitize dictionary by redacting sensitive keys.

    SECURITY: Recursively sanitizes dictionary data structures to remove
    sensitive values before logging or telemetry export.

    Args:
        data: Dictionary to sanitize
        redact_value: Value to use for redacted fields

    Returns:
        New dictionary with sensitive values redacted

    Example:
        >>> sanitize_dict({"username": "admin", "password": "secret"})
        {'username': 'admin', 'password': '[REDACTED]'}

        >>> sanitize_dict({"config": {"api_key": "sk-123", "endpoint": "api.com"}})
        {'config': {'api_key': '[REDACTED]', 'endpoint': 'api.com'}}
    """
    sanitized = {}

    for key, value in data.items():
        # Check if key indicates sensitive data (only for leaf values, not collections)
        key_lower = key.lower()
        is_sensitive = any(keyword in key_lower for keyword in SENSITIVE_KEYWORDS)

        if isinstance(value, dict):
            # Recursively sanitize nested dicts (don't redact the dict itself)
            sanitized[key] = sanitize_dict(value, redact_value)
        elif isinstance(value, list):
            # Sanitize lists (don't redact the list itself)
            sanitized[key] = [
                sanitize_dict(item, redact_value) if isinstance(item, dict) else item
                for item in value
            ]
        elif is_sensitive:
            # Redact sensitive leaf values (strings, numbers, etc)
            sanitized[key] = redact_value
        else:
            # Non-sensitive value, keep as is
            sanitized[key] = value

    return sanitized


def sanitize_url(url: str) -> str:
    """Sanitize URL by removing credentials.

    SECURITY: Removes embedded credentials from URLs before logging.

    Args:
        url: URL string that may contain credentials

    Returns:
        URL with credentials removed

    Example:
        >>> sanitize_url("https://admin:secret@example.com/path")
        'https://[REDACTED]@example.com/path'

        >>> sanitize_url("https://example.com/path")
        'https://example.com/path'
    """
    if not isinstance(url, str):
        return str(url)

    # Remove credentials from URL
    url_pattern = re.compile(r"://([^:]+):([^@]+)@")
    sanitized = url_pattern.sub(r"://[REDACTED]@", url)

    return sanitized


def sanitize_connection_string(connection_string: str) -> str:
    """Sanitize Azure/AWS connection string.

    SECURITY: Removes keys and secrets from connection strings.

    Args:
        connection_string: Connection string to sanitize

    Returns:
        Sanitized connection string with keys redacted

    Example:
        >>> sanitize_connection_string("AccountKey=abc123;AccountName=storage")
        'AccountKey=[REDACTED];AccountName=storage'

        >>> sanitize_connection_string("SharedAccessKey=xyz789;Endpoint=https://...")
        'SharedAccessKey=[REDACTED];Endpoint=https://...'
    """
    if not isinstance(connection_string, str):
        return str(connection_string)

    sanitized = connection_string

    # Sanitize Azure storage keys
    sanitized = re.sub(
        r"AccountKey=([^;\"'\s]+)",
        "AccountKey=[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )

    # Sanitize shared access keys
    sanitized = re.sub(
        r"SharedAccessKey=([^;\"'\s]+)",
        "SharedAccessKey=[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )

    # Sanitize AWS credentials
    sanitized = re.sub(
        r"aws_secret_access_key=([^;\"'\s]+)",
        "aws_secret_access_key=[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )

    return sanitized


def mask_email(email: str) -> str:
    """Mask email address for privacy.

    Args:
        email: Email address to mask

    Returns:
        Masked email (e.g., "u***r@domain.com")

    Example:
        >>> mask_email("user@example.com")
        'u***r@example.com'

        >>> mask_email("admin@tenant.onmicrosoft.com")
        'a***n@tenant.onmicrosoft.com'
    """
    if not isinstance(email, str) or "@" not in email:
        return email

    parts = email.split("@")
    if len(parts) != 2:
        return email

    username = parts[0]
    domain = parts[1]

    masked_username = "***" if len(username) <= 2 else username[0] + "***" + username[-1]

    return f"{masked_username}@{domain}"


def sanitize_for_log(text: str) -> str:
    """General-purpose sanitization for log messages.

    SECURITY: Combines multiple sanitization techniques for safe logging.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text safe for logging

    Example:
        >>> sanitize_for_log("Connected with password=secret to https://user:pass@example.com")
        'Connected with password=[REDACTED] to https://[REDACTED]@example.com'
    """
    if not isinstance(text, str):
        return str(text)

    # Apply error sanitization
    sanitized = sanitize_error(text)

    # Apply URL sanitization
    sanitized = sanitize_url(sanitized)

    # Apply connection string sanitization
    sanitized = sanitize_connection_string(sanitized)

    return sanitized
