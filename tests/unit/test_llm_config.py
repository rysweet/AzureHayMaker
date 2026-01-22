"""Tests for LLM configuration model.

Tests the LLMConfig model for multi-provider LLM support.

Testing pyramid:
- 60% Unit tests (configuration validation)
- 30% Integration tests (config loading from env)
- 10% E2E tests (full config flow)
"""

import os
from unittest.mock import patch

import pytest


class TestLLMConfigValidation:
    """Unit tests for LLMConfig validation."""

    def test_anthropic_config_with_api_key(self):
        """Test creating Anthropic config with API key."""
        # Import here to fail gracefully if not implemented
        from azure_haymaker.llm import LLMConfig

        config = LLMConfig(
            provider="anthropic",
            model="claude-3-sonnet-20241022",
            api_key="sk-test-key-123",
        )

        assert config.provider == "anthropic"
        assert config.model == "claude-3-sonnet-20241022"
        assert config.api_key.get_secret_value() == "sk-test-key-123"

    def test_anthropic_config_requires_api_key(self):
        """Test Anthropic config requires API key."""
        from azure_haymaker.llm import LLMConfig

        with pytest.raises(ValueError, match="api_key.*required.*anthropic"):
            LLMConfig(provider="anthropic")

    def test_azure_openai_config_basic(self):
        """Test creating Azure OpenAI config."""
        from azure_haymaker.llm import LLMConfig

        config = LLMConfig(
            provider="azure_openai",
            endpoint="https://myresource.openai.azure.com",
            deployment="gpt-4",
        )

        assert config.provider == "azure_openai"
        assert config.endpoint == "https://myresource.openai.azure.com"
        assert config.deployment == "gpt-4"
        assert config.api_version == "2024-02-15-preview"  # default

    def test_azure_openai_config_requires_endpoint(self):
        """Test Azure OpenAI config requires endpoint."""
        from azure_haymaker.llm import LLMConfig

        with pytest.raises(ValueError, match="endpoint.*required.*azure_openai"):
            LLMConfig(provider="azure_openai", deployment="gpt-4")

    def test_azure_openai_config_requires_deployment(self):
        """Test Azure OpenAI config requires deployment."""
        from azure_haymaker.llm import LLMConfig

        with pytest.raises(ValueError, match="deployment.*required.*azure_openai"):
            LLMConfig(
                provider="azure_openai",
                endpoint="https://myresource.openai.azure.com",
            )

    def test_azure_ai_foundry_config_basic(self):
        """Test creating Azure AI Foundry config."""
        from azure_haymaker.llm import LLMConfig

        config = LLMConfig(
            provider="azure_ai_foundry",
            endpoint="https://myendpoint.inference.ml.azure.com",
            model="Meta-Llama-3-70B-Instruct",
        )

        assert config.provider == "azure_ai_foundry"
        assert config.endpoint == "https://myendpoint.inference.ml.azure.com"
        assert config.model == "Meta-Llama-3-70B-Instruct"

    def test_azure_ai_foundry_config_requires_endpoint(self):
        """Test Azure AI Foundry config requires endpoint."""
        from azure_haymaker.llm import LLMConfig

        with pytest.raises(ValueError, match="endpoint.*required.*azure_ai_foundry"):
            LLMConfig(
                provider="azure_ai_foundry",
                model="Meta-Llama-3-70B-Instruct",
            )

    def test_azure_ai_foundry_config_requires_model(self):
        """Test Azure AI Foundry config requires model."""
        from azure_haymaker.llm import LLMConfig

        with pytest.raises(ValueError, match="model.*required.*azure_ai_foundry"):
            LLMConfig(
                provider="azure_ai_foundry",
                endpoint="https://myendpoint.inference.ml.azure.com",
            )

    def test_invalid_provider_rejected(self):
        """Test invalid provider name is rejected."""
        from pydantic import ValidationError

        from azure_haymaker.llm import LLMConfig

        with pytest.raises(ValidationError, match="Input should be"):
            LLMConfig(provider="invalid_provider")

    def test_default_timeout_and_retries(self):
        """Test default timeout and retry values."""
        from azure_haymaker.llm import LLMConfig

        config = LLMConfig(
            provider="anthropic",
            api_key="sk-test",
        )

        assert config.timeout_seconds == 120
        assert config.max_retries == 3

    def test_custom_timeout_and_retries(self):
        """Test custom timeout and retry values."""
        from azure_haymaker.llm import LLMConfig

        config = LLMConfig(
            provider="anthropic",
            api_key="sk-test",
            timeout_seconds=60,
            max_retries=5,
        )

        assert config.timeout_seconds == 60
        assert config.max_retries == 5


class TestLLMConfigFromEnvironment:
    """Integration tests for LLMConfig loading from environment."""

    def test_anthropic_from_env(self):
        """Test loading Anthropic config from environment."""
        from azure_haymaker.llm import LLMConfig

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "sk-env-test",
            },
        ):
            config = LLMConfig.from_env()
            assert config.provider == "anthropic"
            assert config.api_key.get_secret_value() == "sk-env-test"

    def test_azure_openai_from_env(self):
        """Test loading Azure OpenAI config from environment."""
        from azure_haymaker.llm import LLMConfig

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "azure_openai",
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_DEPLOYMENT": "gpt-4-test",
                "AZURE_OPENAI_API_VERSION": "2024-01-01",
            },
        ):
            config = LLMConfig.from_env()
            assert config.provider == "azure_openai"
            assert config.endpoint == "https://test.openai.azure.com"
            assert config.deployment == "gpt-4-test"
            assert config.api_version == "2024-01-01"

    def test_azure_ai_foundry_from_env(self):
        """Test loading Azure AI Foundry config from environment."""
        from azure_haymaker.llm import LLMConfig

        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "azure_ai_foundry",
                "AZURE_AI_FOUNDRY_ENDPOINT": "https://test.inference.ml.azure.com",
                "AZURE_AI_FOUNDRY_MODEL": "Llama-3-test",
            },
        ):
            config = LLMConfig.from_env()
            assert config.provider == "azure_ai_foundry"
            assert config.endpoint == "https://test.inference.ml.azure.com"
            assert config.model == "Llama-3-test"

    def test_default_provider_is_anthropic(self):
        """Test default provider when not specified."""
        from azure_haymaker.llm import LLMConfig

        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "sk-default-test",
            },
            clear=True,
        ):
            config = LLMConfig.from_env()
            assert config.provider == "anthropic"
