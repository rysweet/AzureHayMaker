"""LLM provider implementations.

This package contains implementations for each supported LLM provider.

Philosophy:
- Single responsibility per provider
- Common interface via BaseLLMProvider
- Self-contained and regeneratable

Public API (the "studs"):
    BaseLLMProvider: Abstract base class for providers
    AnthropicProvider: Anthropic Claude provider
    AzureOpenAIProvider: Azure OpenAI provider
    AzureAIFoundryProvider: Azure AI Foundry provider
"""

from azure_haymaker.llm.providers.anthropic import AnthropicProvider
from azure_haymaker.llm.providers.azure_ai_foundry import AzureAIFoundryProvider
from azure_haymaker.llm.providers.azure_openai import AzureOpenAIProvider
from azure_haymaker.llm.providers.base import BaseLLMProvider

__all__ = [
    "BaseLLMProvider",
    "AnthropicProvider",
    "AzureOpenAIProvider",
    "AzureAIFoundryProvider",
]
