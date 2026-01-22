"""Azure AI Foundry provider implementation.

This module implements the BaseLLMProvider interface for Azure AI Foundry.

Philosophy:
- Single responsibility: Azure AI Foundry provider only
- DefaultAzureCredential for managed identity support
- Self-contained and regeneratable

Public API (the "studs"):
    AzureAIFoundryProvider: Azure AI Foundry provider implementation
"""

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from azure.identity import DefaultAzureCredential

from azure_haymaker.llm.config import LLMConfig
from azure_haymaker.llm.exceptions import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
)
from azure_haymaker.llm.providers.base import BaseLLMProvider
from azure_haymaker.llm.types import LLMMessage, LLMResponse


class AzureAIFoundryProvider(BaseLLMProvider):
    """Azure AI Foundry provider implementation.

    Supports open-source models (Llama, Mistral, Phi) via Azure ML inference.
    Uses DefaultAzureCredential for managed identity when no API key provided.
    """

    def __init__(self, config: LLMConfig) -> None:
        """Initialize Azure AI Foundry provider.

        Args:
            config: LLMConfig with provider="azure_ai_foundry", endpoint, and model set
        """
        self._config = config
        self._model = config.model
        self._endpoint = config.endpoint

        api_key = config.api_key.get_secret_value() if config.api_key else None

        if api_key:
            # Use API key authentication
            self._client = ChatCompletionsClient(
                endpoint=self._endpoint,
                credential=AzureKeyCredential(api_key),
            )
        else:
            # Use DefaultAzureCredential for managed identity
            credential = DefaultAzureCredential()
            self._client = ChatCompletionsClient(
                endpoint=self._endpoint,
                credential=credential,
            )

    def _format_messages(
        self, messages: list[LLMMessage], system: str | None = None
    ) -> list:
        """Format messages for Azure AI Foundry API.

        Args:
            messages: List of conversation messages
            system: Optional system prompt

        Returns:
            List of formatted messages for the API
        """
        formatted = []

        if system:
            formatted.append(SystemMessage(content=system))

        for msg in messages:
            if msg.role == "user":
                formatted.append(UserMessage(content=msg.content))
            elif msg.role == "system":
                formatted.append(SystemMessage(content=msg.content))
            # Note: Azure AI Foundry uses different message types

        return formatted

    def create_message(
        self,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Create a message synchronously using Azure AI Foundry API.

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
            LLMProviderError: Other Azure AI Foundry errors
        """
        try:
            formatted_messages = self._format_messages(messages, system)

            response = self._client.complete(
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                model=self._model,
            )

            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model or self._model,
                usage={
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                },
                stop_reason=choice.finish_reason,
            )

        except ClientAuthenticationError as e:
            raise LLMAuthenticationError(
                f"Azure AI Foundry authentication failed: {e}"
            ) from e
        except HttpResponseError as e:
            if e.status_code == 429:
                raise LLMRateLimitError(
                    f"Azure AI Foundry rate limit exceeded: {e}"
                ) from e
            raise LLMProviderError(f"Azure AI Foundry error: {e}") from e
        except Exception as e:
            raise LLMProviderError(f"Azure AI Foundry error: {e}") from e

    async def create_message_async(
        self,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Create a message asynchronously using Azure AI Foundry API.

        Note: Azure AI Inference SDK doesn't have native async support,
        so we run the sync method in a thread pool.

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
            LLMProviderError: Other Azure AI Foundry errors
        """
        import asyncio

        # Run sync method in thread pool for async compatibility
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.create_message(messages, system, max_tokens, temperature),
        )


__all__ = ["AzureAIFoundryProvider"]
