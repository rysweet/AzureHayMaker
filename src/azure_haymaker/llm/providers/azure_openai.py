"""Azure OpenAI provider implementation.

This module implements the BaseLLMProvider interface for Azure OpenAI.

Philosophy:
- Single responsibility: Azure OpenAI provider only
- DefaultAzureCredential for managed identity support
- Self-contained and regeneratable

Public API (the "studs"):
    AzureOpenAIProvider: Azure OpenAI provider implementation
"""

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI, AuthenticationError, AzureOpenAI, RateLimitError

from azure_haymaker.llm.config import LLMConfig
from azure_haymaker.llm.exceptions import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
)
from azure_haymaker.llm.providers.base import BaseLLMProvider
from azure_haymaker.llm.types import LLMMessage, LLMResponse


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI provider implementation.

    Supports GPT-4 and GPT-4o models via Azure-hosted endpoints.
    Uses DefaultAzureCredential for managed identity when no API key provided.
    """

    def __init__(self, config: LLMConfig) -> None:
        """Initialize Azure OpenAI provider.

        Args:
            config: LLMConfig with provider="azure_openai", endpoint, and deployment set
        """
        self._config = config
        self._deployment = config.deployment
        self._endpoint = config.endpoint
        self._api_version = config.api_version

        api_key = config.api_key.get_secret_value() if config.api_key else None

        if api_key:
            # Use API key authentication
            self._client = AzureOpenAI(
                api_key=api_key,
                api_version=self._api_version,
                azure_endpoint=self._endpoint,
                timeout=config.timeout_seconds,
                max_retries=config.max_retries,
            )
            self._async_client = AsyncAzureOpenAI(
                api_key=api_key,
                api_version=self._api_version,
                azure_endpoint=self._endpoint,
                timeout=config.timeout_seconds,
                max_retries=config.max_retries,
            )
        else:
            # Use DefaultAzureCredential for managed identity
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )

            self._client = AzureOpenAI(
                azure_ad_token_provider=token_provider,
                api_version=self._api_version,
                azure_endpoint=self._endpoint,
                timeout=config.timeout_seconds,
                max_retries=config.max_retries,
            )
            self._async_client = AsyncAzureOpenAI(
                azure_ad_token_provider=token_provider,
                api_version=self._api_version,
                azure_endpoint=self._endpoint,
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
        """Create a message synchronously using Azure OpenAI API.

        Args:
            messages: List of conversation messages
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            LLMResponse with generated content

        Raises:
            LLMAuthenticationError: Invalid credentials
            LLMRateLimitError: Rate limit exceeded
            LLMProviderError: Other Azure OpenAI errors
        """
        try:
            formatted_messages = []

            # Add system message first if provided
            if system:
                formatted_messages.append({"role": "system", "content": system})

            # Add conversation messages
            formatted_messages.extend(
                [{"role": msg.role, "content": msg.content} for msg in messages]
            )

            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                usage={
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                },
                stop_reason=choice.finish_reason,
            )

        except AuthenticationError as e:
            raise LLMAuthenticationError(f"Azure OpenAI authentication failed: {e}") from e
        except RateLimitError as e:
            raise LLMRateLimitError(f"Azure OpenAI rate limit exceeded: {e}") from e
        except Exception as e:
            raise LLMProviderError(f"Azure OpenAI error: {e}") from e

    async def create_message_async(
        self,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Create a message asynchronously using Azure OpenAI API.

        Args:
            messages: List of conversation messages
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            LLMResponse with generated content

        Raises:
            LLMAuthenticationError: Invalid credentials
            LLMRateLimitError: Rate limit exceeded
            LLMProviderError: Other Azure OpenAI errors
        """
        try:
            formatted_messages = []

            # Add system message first if provided
            if system:
                formatted_messages.append({"role": "system", "content": system})

            # Add conversation messages
            formatted_messages.extend(
                [{"role": msg.role, "content": msg.content} for msg in messages]
            )

            response = await self._async_client.chat.completions.create(
                model=self._deployment,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                usage={
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                },
                stop_reason=choice.finish_reason,
            )

        except AuthenticationError as e:
            raise LLMAuthenticationError(f"Azure OpenAI authentication failed: {e}") from e
        except RateLimitError as e:
            raise LLMRateLimitError(f"Azure OpenAI rate limit exceeded: {e}") from e
        except Exception as e:
            raise LLMProviderError(f"Azure OpenAI error: {e}") from e


__all__ = ["AzureOpenAIProvider"]
