"""Tests for LLM factory function.

Tests the create_llm_client factory for multi-provider LLM support.

Testing pyramid:
- 60% Unit tests (factory function)
- 30% Integration tests (provider instantiation)
- 10% E2E tests (complete flow)
"""

from unittest.mock import MagicMock, patch

import pytest


class TestCreateLLMClient:
    """Unit tests for create_llm_client factory."""

    def test_creates_anthropic_provider(self):
        """Test factory creates AnthropicProvider for anthropic config."""
        from azure_haymaker.llm import LLMConfig, create_llm_client
        from azure_haymaker.llm.providers import AnthropicProvider

        config = LLMConfig(
            provider="anthropic",
            api_key="sk-test",
        )

        with patch("azure_haymaker.llm.providers.anthropic.Anthropic"):
            client = create_llm_client(config)
            assert isinstance(client, AnthropicProvider)

    def test_creates_azure_openai_provider(self):
        """Test factory creates AzureOpenAIProvider for azure_openai config."""
        from azure_haymaker.llm import LLMConfig, create_llm_client
        from azure_haymaker.llm.providers import AzureOpenAIProvider

        config = LLMConfig(
            provider="azure_openai",
            endpoint="https://test.openai.azure.com",
            deployment="gpt-4",
        )

        with (
            patch("azure_haymaker.llm.providers.azure_openai.AzureOpenAI"),
            patch("azure_haymaker.llm.providers.azure_openai.DefaultAzureCredential"),
        ):
            client = create_llm_client(config)
            assert isinstance(client, AzureOpenAIProvider)

    def test_creates_azure_ai_foundry_provider(self):
        """Test factory creates AzureAIFoundryProvider for azure_ai_foundry config."""
        from azure_haymaker.llm import LLMConfig, create_llm_client
        from azure_haymaker.llm.providers import AzureAIFoundryProvider

        config = LLMConfig(
            provider="azure_ai_foundry",
            endpoint="https://test.inference.ml.azure.com",
            model="Llama-3",
        )

        with (
            patch("azure_haymaker.llm.providers.azure_ai_foundry.ChatCompletionsClient"),
            patch("azure_haymaker.llm.providers.azure_ai_foundry.DefaultAzureCredential"),
        ):
            client = create_llm_client(config)
            assert isinstance(client, AzureAIFoundryProvider)

    def test_raises_for_unknown_provider(self):
        """Test factory raises for unknown provider."""
        from azure_haymaker.llm import LLMConfig, create_llm_client

        # Create config with valid provider first, then override
        config = LLMConfig(provider="anthropic", api_key="test")
        # Manually set invalid provider to test factory error handling
        object.__setattr__(config, "provider", "unknown")

        with pytest.raises(ValueError, match="Unknown provider"):
            create_llm_client(config)


class TestFactoryWithCredentials:
    """Integration tests for factory with different credentials."""

    def test_azure_openai_with_api_key(self):
        """Test Azure OpenAI uses API key when provided."""
        from azure_haymaker.llm import LLMConfig, create_llm_client

        config = LLMConfig(
            provider="azure_openai",
            endpoint="https://test.openai.azure.com",
            deployment="gpt-4",
            api_key="test-api-key",
        )

        with patch("azure_haymaker.llm.providers.azure_openai.AzureOpenAI") as mock_client:
            create_llm_client(config)
            # Should use api_key, not token provider
            call_kwargs = mock_client.call_args.kwargs
            assert "api_key" in call_kwargs
            assert "azure_ad_token_provider" not in call_kwargs

    def test_azure_openai_with_managed_identity(self):
        """Test Azure OpenAI uses managed identity when no API key."""
        from azure_haymaker.llm import LLMConfig, create_llm_client

        config = LLMConfig(
            provider="azure_openai",
            endpoint="https://test.openai.azure.com",
            deployment="gpt-4",
        )

        with (
            patch("azure_haymaker.llm.providers.azure_openai.AzureOpenAI") as mock_client,
            patch("azure_haymaker.llm.providers.azure_openai.DefaultAzureCredential"),
            patch(
                "azure_haymaker.llm.providers.azure_openai.get_bearer_token_provider"
            ) as mock_token,
        ):
            mock_token.return_value = MagicMock()
            create_llm_client(config)
            # Should use token provider, not api_key
            call_kwargs = mock_client.call_args.kwargs
            assert "azure_ad_token_provider" in call_kwargs
            assert call_kwargs.get("api_key") is None

    def test_azure_ai_foundry_with_managed_identity(self):
        """Test Azure AI Foundry uses managed identity."""
        from azure_haymaker.llm import LLMConfig, create_llm_client

        config = LLMConfig(
            provider="azure_ai_foundry",
            endpoint="https://test.inference.ml.azure.com",
            model="Llama-3",
        )

        with (
            patch(
                "azure_haymaker.llm.providers.azure_ai_foundry.ChatCompletionsClient"
            ) as mock_client,
            patch(
                "azure_haymaker.llm.providers.azure_ai_foundry.DefaultAzureCredential"
            ) as mock_cred,
        ):
            create_llm_client(config)
            # Should be called with credential
            assert mock_cred.called
            call_kwargs = mock_client.call_args.kwargs
            assert "credential" in call_kwargs
