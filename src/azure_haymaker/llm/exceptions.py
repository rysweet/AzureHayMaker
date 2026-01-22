"""Exceptions for LLM abstraction layer.

This module defines standard exceptions that wrap provider-specific errors.

Philosophy:
- Single responsibility: Exception definitions only
- Provider-agnostic error handling
- Self-contained and regeneratable

Public API (the "studs"):
    LLMError: Base exception for all LLM errors
    LLMAuthenticationError: Invalid credentials
    LLMRateLimitError: Rate limit exceeded (retryable)
    LLMInvalidRequestError: Invalid request parameters
    LLMProviderError: Provider-specific error
"""


class LLMError(Exception):
    """Base exception for all LLM errors."""

    pass


class LLMAuthenticationError(LLMError):
    """Invalid credentials for LLM provider."""

    pass


class LLMRateLimitError(LLMError):
    """Rate limit exceeded. This error is typically retryable."""

    pass


class LLMInvalidRequestError(LLMError):
    """Invalid request parameters."""

    pass


class LLMProviderError(LLMError):
    """Provider-specific error that doesn't fit other categories."""

    pass


__all__ = [
    "LLMError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMInvalidRequestError",
    "LLMProviderError",
]
