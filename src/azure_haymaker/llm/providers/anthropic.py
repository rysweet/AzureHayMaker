"""Anthropic Claude provider implementation.

This module implements the BaseLLMProvider interface for Anthropic Claude.

Philosophy:
- Single responsibility: Anthropic provider only
- Wrap Anthropic-specific errors into standard exceptions
- Self-contained and regeneratable

Public API (the "studs"):
    AnthropicProvider: Anthropic Claude provider implementation
"""

from anthropic import Anthropic, AsyncAnthropic, AuthenticationError, RateLimitError

from azure_haymaker.llm.config import LLMConfig
from azure_haymaker.llm.exceptions import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
)
from azure_haymaker.llm.providers.base import BaseLLMProvider
from azure_haymaker.llm.types import LLMMessage, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation.

    Supports Claude models via the Anthropic API.
    """

    def __init__(self, config: LLMConfig) -> None:
        """Initialize Anthropic provider.

        Args:
            config: LLMConfig with provider="anthropic" and api_key set
        """
        self._config = config
        self._model = config.model or "claude-3-sonnet-20241022"
        api_key = config.api_key.get_secret_value() if config.api_key else None

        self._client = Anthropic(
            api_key=api_key,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        self._async_client = AsyncAnthropic(
            api_key=api_key,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
        )

    def create_message(
        self,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Create a message synchronously using Anthropic API.

        Args:
            messages: List of conversation messages
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            LLMResponse with generated content

        Raises:
            LLMAuthenticationError: Invalid API key
            LLMRateLimitError: Rate limit exceeded
            LLMProviderError: Other Anthropic errors
        """
        try:
            formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            kwargs = {
                "model": self._model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": formatted_messages,
            }
            if system:
                kwargs["system"] = system

            response = self._client.messages.create(**kwargs)

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                stop_reason=response.stop_reason,
            )

        except AuthenticationError as e:
            raise LLMAuthenticationError(f"Anthropic authentication failed: {e}") from e
        except RateLimitError as e:
            raise LLMRateLimitError(f"Anthropic rate limit exceeded: {e}") from e
        except Exception as e:
            raise LLMProviderError(f"Anthropic error: {e}") from e

    async def create_message_async(
        self,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Create a message asynchronously using Anthropic API.

        Args:
            messages: List of conversation messages
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            LLMResponse with generated content

        Raises:
            LLMAuthenticationError: Invalid API key
            LLMRateLimitError: Rate limit exceeded
            LLMProviderError: Other Anthropic errors
        """
        try:
            formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            kwargs = {
                "model": self._model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": formatted_messages,
            }
            if system:
                kwargs["system"] = system

            response = await self._async_client.messages.create(**kwargs)

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                stop_reason=response.stop_reason,
            )

        except AuthenticationError as e:
            raise LLMAuthenticationError(f"Anthropic authentication failed: {e}") from e
        except RateLimitError as e:
            raise LLMRateLimitError(f"Anthropic rate limit exceeded: {e}") from e
        except Exception as e:
            raise LLMProviderError(f"Anthropic error: {e}") from e


__all__ = ["AnthropicProvider"]
