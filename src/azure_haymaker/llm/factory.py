"""Factory function for creating LLM clients.

This module provides the main entry point for creating LLM provider instances.

Philosophy:
- Single responsibility: Factory function only
- Hide provider details from users
- Self-contained and regeneratable

Public API (the "studs"):
    create_llm_client: Factory function to create provider instances
"""

from azure_haymaker.llm.config import LLMConfig
from azure_haymaker.llm.providers.anthropic import AnthropicProvider
from azure_haymaker.llm.providers.azure_ai_foundry import AzureAIFoundryProvider
from azure_haymaker.llm.providers.azure_openai import AzureOpenAIProvider
from azure_haymaker.llm.providers.base import BaseLLMProvider


def create_llm_client(config: LLMConfig) -> BaseLLMProvider:
    """Create an LLM client based on configuration.

    Factory function that returns the appropriate provider implementation
    based on the provider field in the configuration.

    Args:
        config: LLMConfig specifying provider and settings

    Returns:
        BaseLLMProvider: Configured provider instance

    Raises:
        ValueError: If provider is unknown

    Example:
        >>> config = LLMConfig(provider="anthropic", api_key="sk-...")
        >>> client = create_llm_client(config)
        >>> response = client.create_message([LLMMessage(role="user", content="Hello")])
    """
    if config.provider == "anthropic":
        return AnthropicProvider(config)
    elif config.provider == "azure_openai":
        return AzureOpenAIProvider(config)
    elif config.provider == "azure_ai_foundry":
        return AzureAIFoundryProvider(config)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


__all__ = ["create_llm_client"]
