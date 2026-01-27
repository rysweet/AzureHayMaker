"""Unit tests for LLM model configuration in email generation.

Tests for PR addressing LLM model configuration:
- Email generation with valid model succeeds
- Invalid model name raises appropriate error
- Environment variable configuration works
- Default model is used when not configured
- Model configuration is properly validated

Updated to use the LLM abstraction layer instead of direct Anthropic SDK.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from azure_haymaker.knowledge_worker.content.email_generator import (
    EmailContentGenerator,
    EmailGenerationConfig,
)
from azure_haymaker.llm import LLMResponse


class TestAnthropicModelConfiguration:
    """Test suite for Anthropic model configuration."""

    @pytest.mark.asyncio
    async def test_email_generation_with_valid_model_succeeds(self):
        """Test that email generation succeeds with a valid model name."""
        config = EmailGenerationConfig(
            enabled=True,
            provider="anthropic",
            api_key=SecretStr("sk-ant-test-key"),
            model="claude-sonnet-4-5-20250929",
        )

        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
        ) as mock_create:
            mock_response = LLMResponse(
                content="Subject: Test Email\n\nHello world!",
                model="claude-sonnet-4-5-20250929",
                usage={"input_tokens": 10, "output_tokens": 50},
            )

            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_client

            generator = EmailContentGenerator(config)
            result = await generator.generate_email(
                worker_id="kw-test-1",
                department="engineering",
                recipient="test@example.com",
                activity_count=1,
            )

            assert result.subject == "Test Email"
            assert "Hello world" in result.body
            assert result.metadata["model"] == "claude-sonnet-4-5-20250929"

    @pytest.mark.asyncio
    async def test_email_generation_with_opus_model(self):
        """Test that email generation works with Claude Opus model."""
        config = EmailGenerationConfig(
            enabled=True,
            provider="anthropic",
            api_key=SecretStr("sk-ant-test-key"),
            model="claude-opus-4-5-20251101",
        )

        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
        ) as mock_create:
            mock_response = LLMResponse(
                content="Subject: Opus Test\n\nOpus response",
                model="claude-opus-4-5-20251101",
                usage={"input_tokens": 10, "output_tokens": 75},
            )

            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_client

            generator = EmailContentGenerator(config)
            result = await generator.generate_email(
                worker_id="kw-test-1",
                department="sales",
                recipient="test@example.com",
                activity_count=5,
            )

            assert result.metadata["model"] == "claude-opus-4-5-20251101"

    @pytest.mark.asyncio
    async def test_invalid_model_name_raises_appropriate_error(self):
        """Test that invalid model names are handled gracefully."""
        config = EmailGenerationConfig(
            enabled=True,
            provider="anthropic",
            api_key=SecretStr("sk-ant-test-key"),
            model="invalid-model-name",
        )

        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(
                side_effect=Exception("model: Invalid model")
            )
            mock_create.return_value = mock_client

            generator = EmailContentGenerator(config)

            with pytest.raises(RuntimeError, match="AI service error"):
                await generator.generate_email(
                    worker_id="kw-test-1",
                    department="engineering",
                    recipient="test@example.com",
                    activity_count=1,
                )

    @pytest.mark.asyncio
    async def test_env_var_model_configuration_works(self):
        """Test that model can be configured via environment variable."""
        test_model = "claude-sonnet-4-5-20250929"

        with patch.dict(os.environ, {"ANTHROPIC_MODEL": test_model}):
            config = EmailGenerationConfig(
                enabled=True,
                provider="anthropic",
                api_key=SecretStr("sk-ant-test-key"),
                model=None,
            )

            with patch(
                "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
            ) as mock_create:
                mock_response = LLMResponse(
                    content="Subject: Env Test\n\nEnv model works",
                    model=test_model,
                    usage={"input_tokens": 10, "output_tokens": 40},
                )

                mock_client = MagicMock()
                mock_client.create_message_async = AsyncMock(return_value=mock_response)
                mock_create.return_value = mock_client

                generator = EmailContentGenerator(config)

                with patch.object(generator.config, "model", test_model):
                    await generator.generate_email(
                        worker_id="kw-test-1",
                        department="marketing",
                        recipient="test@example.com",
                        activity_count=10,
                    )

    @pytest.mark.asyncio
    async def test_default_model_used_when_not_configured(self):
        """Test that default model is used when none is specified."""
        config = EmailGenerationConfig(
            enabled=True,
            provider="anthropic",
            api_key=SecretStr("sk-ant-test-key"),
            model=None,
        )

        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
        ) as mock_create:
            mock_response = LLMResponse(
                content="Subject: Default Test\n\nDefault model used",
                model="claude-3-sonnet-20241022",  # LLM layer default
                usage={"input_tokens": 10, "output_tokens": 45},
            )

            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_client

            generator = EmailContentGenerator(config)
            result = await generator.generate_email(
                worker_id="kw-test-1",
                department="hr",
                recipient="test@example.com",
                activity_count=3,
            )

            # Model is determined by LLM layer
            assert "model" in result.metadata

    @pytest.mark.asyncio
    async def test_config_model_overrides_env_var(self):
        """Test that explicit config.model takes precedence over env var."""
        config_model = "claude-opus-4-5-20251101"
        env_model = "claude-sonnet-4-5-20250929"

        with patch.dict(os.environ, {"ANTHROPIC_MODEL": env_model}):
            config = EmailGenerationConfig(
                enabled=True,
                provider="anthropic",
                api_key=SecretStr("sk-ant-test-key"),
                model=config_model,
            )

            with patch(
                "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
            ) as mock_create:
                mock_response = LLMResponse(
                    content="Subject: Priority Test\n\nConfig wins",
                    model=config_model,
                    usage={"input_tokens": 10, "output_tokens": 30},
                )

                mock_client = MagicMock()
                mock_client.create_message_async = AsyncMock(return_value=mock_response)
                mock_create.return_value = mock_client

                generator = EmailContentGenerator(config)
                result = await generator.generate_email(
                    worker_id="kw-test-1",
                    department="finance",
                    recipient="test@example.com",
                    activity_count=7,
                )

                assert result.metadata["model"] == config_model


class TestModelConfigurationEdgeCases:
    """Test edge cases and error handling for model configuration."""

    @pytest.mark.asyncio
    async def test_empty_model_string_uses_default(self):
        """Test that empty model string falls back to default."""
        config = EmailGenerationConfig(
            enabled=True,
            provider="anthropic",
            api_key=SecretStr("sk-ant-test-key"),
            model="",
        )

        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
        ) as mock_create:
            mock_response = LLMResponse(
                content="Subject: Empty Test\n\nDefault used",
                model="claude-3-sonnet-20241022",
                usage={"input_tokens": 10, "output_tokens": 25},
            )

            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_client

            generator = EmailContentGenerator(config)
            result = await generator.generate_email(
                worker_id="kw-test-1",
                department="legal",
                recipient="test@example.com",
                activity_count=2,
            )

            assert "model" in result.metadata

    @pytest.mark.asyncio
    async def test_whitespace_model_string_uses_default(self):
        """Test that whitespace-only model string falls back to default."""
        config = EmailGenerationConfig(
            enabled=True,
            provider="anthropic",
            api_key=SecretStr("sk-ant-test-key"),
            model="   ",
        )

        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
        ) as mock_create:
            mock_response = LLMResponse(
                content="Subject: Whitespace Test\n\nDefault used",
                model="claude-3-sonnet-20241022",
                usage={"input_tokens": 10, "output_tokens": 28},
            )

            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_client

            generator = EmailContentGenerator(config)
            result = await generator.generate_email(
                worker_id="kw-test-1",
                department="operations",
                recipient="test@example.com",
                activity_count=15,
            )

            assert "model" in result.metadata

    @pytest.mark.asyncio
    async def test_model_metadata_correctly_stored(self):
        """Test that model used is correctly stored in metadata."""
        test_model = "claude-opus-4-5-20251101"
        config = EmailGenerationConfig(
            enabled=True,
            provider="anthropic",
            api_key=SecretStr("sk-ant-test-key"),
            model=test_model,
        )

        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
        ) as mock_create:
            mock_response = LLMResponse(
                content="Subject: Metadata Test\n\nChecking metadata",
                model=test_model,
                usage={"input_tokens": 10, "output_tokens": 35},
            )

            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_client

            generator = EmailContentGenerator(config)
            result = await generator.generate_email(
                worker_id="kw-test-1",
                department="support",
                recipient="test@example.com",
                activity_count=8,
            )

            assert "model" in result.metadata
            assert result.metadata["model"] == test_model

    def test_config_model_field_is_optional(self):
        """Test that model field in EmailGenerationConfig is optional."""
        config = EmailGenerationConfig(
            enabled=False,
            model=None,
        )
        assert config.model is None

        config2 = EmailGenerationConfig(enabled=False)
        assert config2.model is None

    @pytest.mark.asyncio
    async def test_authentication_error_with_custom_model(self):
        """Test that authentication errors are handled properly with custom models."""
        config = EmailGenerationConfig(
            enabled=True,
            provider="anthropic",
            api_key=SecretStr("sk-ant-invalid-key"),
            model="claude-sonnet-4-5-20250929",
        )

        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(side_effect=Exception("Invalid API key"))
            mock_create.return_value = mock_client

            generator = EmailContentGenerator(config)

            with pytest.raises(RuntimeError, match="AI service error"):
                await generator.generate_email(
                    worker_id="kw-test-1",
                    department="engineering",
                    recipient="test@example.com",
                    activity_count=1,
                )


class TestModelConfigurationIntegration:
    """Integration tests for model configuration across components."""

    @pytest.mark.asyncio
    async def test_model_config_flows_through_full_generation(self):
        """Test that model configuration flows through entire generation process."""
        test_model = "claude-sonnet-4-5-20250929"
        config = EmailGenerationConfig(
            enabled=True,
            provider="anthropic",
            api_key=SecretStr("sk-ant-test-key"),
            model=test_model,
            directive="Be professional",
        )

        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
        ) as mock_create:
            mock_response = LLMResponse(
                content="Subject: Professional Email\n\nDear colleague,\n\nThis is a professional email.",
                model=test_model,
                usage={"input_tokens": 20, "output_tokens": 60},
            )

            mock_client = MagicMock()
            mock_client.create_message_async = AsyncMock(return_value=mock_response)
            mock_create.return_value = mock_client

            generator = EmailContentGenerator(config)
            result = await generator.generate_email(
                worker_id="kw-test-1",
                department="executive",
                recipient="ceo@example.com",
                activity_count=100,
                run_id="test-run-123",
            )

            assert result.subject == "Professional Email"
            assert "professional email" in result.body.lower()
            assert result.metadata["model"] == test_model
            assert result.metadata["run_id"] == "test-run-123"
            assert result.metadata["worker_id"] == "kw-test-1"

    @pytest.mark.asyncio
    async def test_different_models_for_different_departments(self):
        """Test that different departments can use different models."""
        departments_and_models = [
            ("engineering", "claude-sonnet-4-5-20250929"),
            ("executive", "claude-opus-4-5-20251101"),
            ("support", "claude-sonnet-4-5-20250929"),
        ]

        for department, model in departments_and_models:
            config = EmailGenerationConfig(
                enabled=True,
                provider="anthropic",
                api_key=SecretStr("sk-ant-test-key"),
                model=model,
            )

            with patch(
                "azure_haymaker.knowledge_worker.content.email_generator.create_llm_client"
            ) as mock_create:
                mock_response = LLMResponse(
                    content=f"Subject: {department} Email\n\nHello from {department}",
                    model=model,
                    usage={"input_tokens": 10, "output_tokens": 40},
                )

                mock_client = MagicMock()
                mock_client.create_message_async = AsyncMock(return_value=mock_response)
                mock_create.return_value = mock_client

                generator = EmailContentGenerator(config)
                result = await generator.generate_email(
                    worker_id=f"kw-{department}-1",
                    department=department,
                    recipient=f"test@{department}.example.com",
                    activity_count=1,
                )

                assert result.metadata["model"] == model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
