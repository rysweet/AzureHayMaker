"""Tests for LLM provider implementations.

Tests each LLM provider (Anthropic, Azure OpenAI, Azure AI Foundry).

Testing pyramid:
- 60% Unit tests (provider methods with mocked clients)
- 30% Integration tests (response parsing)
- 10% E2E tests (full message flow)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLLMMessage:
    """Tests for LLMMessage type."""

    def test_create_user_message(self):
        """Test creating a user message."""
        from azure_haymaker.llm import LLMMessage

        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_create_assistant_message(self):
        """Test creating an assistant message."""
        from azure_haymaker.llm import LLMMessage

        msg = LLMMessage(role="assistant", content="Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"


class TestLLMResponse:
    """Tests for LLMResponse type."""

    def test_response_attributes(self):
        """Test LLMResponse has expected attributes."""
        from azure_haymaker.llm import LLMResponse

        response = LLMResponse(
            content="Generated text",
            model="claude-3-sonnet",
            usage={"input_tokens": 10, "output_tokens": 20},
            stop_reason="end_turn",
        )

        assert response.content == "Generated text"
        assert response.model == "claude-3-sonnet"
        assert response.usage["input_tokens"] == 10
        assert response.stop_reason == "end_turn"


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def test_create_message_sync(self):
        """Test synchronous message creation."""
        from azure_haymaker.llm import LLMConfig, LLMMessage, create_llm_client

        config = LLMConfig(provider="anthropic", api_key="sk-test")

        # Mock the Anthropic client
        with patch("azure_haymaker.llm.providers.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            # Mock response
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Hello back!")]
            mock_response.model = "claude-3-sonnet-20241022"
            mock_response.usage.input_tokens = 5
            mock_response.usage.output_tokens = 10
            mock_response.stop_reason = "end_turn"
            mock_client.messages.create.return_value = mock_response

            provider = create_llm_client(config)
            messages = [LLMMessage(role="user", content="Hello")]

            response = provider.create_message(messages, max_tokens=100)

            assert response.content == "Hello back!"
            mock_client.messages.create.assert_called_once()

    @pytest.mark.anyio
    async def test_create_message_async(self):
        """Test asynchronous message creation."""
        from azure_haymaker.llm import LLMConfig, LLMMessage, create_llm_client

        config = LLMConfig(provider="anthropic", api_key="sk-test")

        with (
            patch("azure_haymaker.llm.providers.anthropic.Anthropic"),
            patch("azure_haymaker.llm.providers.anthropic.AsyncAnthropic") as mock_async,
        ):
            mock_async_client = AsyncMock()
            mock_async.return_value = mock_async_client

            # Mock async response
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Async hello!")]
            mock_response.model = "claude-3-sonnet-20241022"
            mock_response.usage.input_tokens = 5
            mock_response.usage.output_tokens = 10
            mock_response.stop_reason = "end_turn"
            mock_async_client.messages.create.return_value = mock_response

            provider = create_llm_client(config)
            messages = [LLMMessage(role="user", content="Hello")]

            response = await provider.create_message_async(messages, max_tokens=100)

            assert response.content == "Async hello!"


class TestAzureOpenAIProvider:
    """Tests for AzureOpenAIProvider."""

    def test_create_message_sync(self):
        """Test synchronous message creation with Azure OpenAI."""
        from azure_haymaker.llm import LLMConfig, LLMMessage, create_llm_client

        config = LLMConfig(
            provider="azure_openai",
            endpoint="https://test.openai.azure.com",
            deployment="gpt-4",
            api_key="test-key",
        )

        with patch("azure_haymaker.llm.providers.azure_openai.AzureOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock OpenAI response structure
            mock_choice = MagicMock()
            mock_choice.message.content = "Azure response"
            mock_choice.finish_reason = "stop"

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.model = "gpt-4"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_client.chat.completions.create.return_value = mock_response

            provider = create_llm_client(config)
            messages = [LLMMessage(role="user", content="Hello")]

            response = provider.create_message(messages, max_tokens=100)

            assert response.content == "Azure response"
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.anyio
    async def test_create_message_async(self):
        """Test asynchronous message creation with Azure OpenAI."""
        from azure_haymaker.llm import LLMConfig, LLMMessage, create_llm_client

        config = LLMConfig(
            provider="azure_openai",
            endpoint="https://test.openai.azure.com",
            deployment="gpt-4",
            api_key="test-key",
        )

        with patch("azure_haymaker.llm.providers.azure_openai.AzureOpenAI"), patch(
            "azure_haymaker.llm.providers.azure_openai.AsyncAzureOpenAI"
        ) as mock_async:
            mock_async_client = AsyncMock()
            mock_async.return_value = mock_async_client

            # Mock async OpenAI response
            mock_choice = MagicMock()
            mock_choice.message.content = "Async Azure response"
            mock_choice.finish_reason = "stop"

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.model = "gpt-4"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_async_client.chat.completions.create.return_value = mock_response

            provider = create_llm_client(config)
            messages = [LLMMessage(role="user", content="Hello")]

            response = await provider.create_message_async(messages, max_tokens=100)

            assert response.content == "Async Azure response"


class TestAzureAIFoundryProvider:
    """Tests for AzureAIFoundryProvider."""

    def test_create_message_sync(self):
        """Test synchronous message creation with Azure AI Foundry."""
        from azure_haymaker.llm import LLMConfig, LLMMessage, create_llm_client

        config = LLMConfig(
            provider="azure_ai_foundry",
            endpoint="https://test.inference.ml.azure.com",
            model="Meta-Llama-3-70B-Instruct",
        )

        with patch(
            "azure_haymaker.llm.providers.azure_ai_foundry.ChatCompletionsClient"
        ) as mock_foundry, patch(
            "azure_haymaker.llm.providers.azure_ai_foundry.DefaultAzureCredential"
        ):
            mock_client = MagicMock()
            mock_foundry.return_value = mock_client

            # Mock Foundry response structure
            mock_choice = MagicMock()
            mock_choice.message.content = "Foundry response"
            mock_choice.finish_reason = "stop"

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.model = "Meta-Llama-3-70B-Instruct"
            mock_response.usage.prompt_tokens = 15
            mock_response.usage.completion_tokens = 25
            mock_client.complete.return_value = mock_response

            provider = create_llm_client(config)
            messages = [LLMMessage(role="user", content="Hello")]

            response = provider.create_message(messages, max_tokens=100)

            assert response.content == "Foundry response"
            mock_client.complete.assert_called_once()


class TestProviderExceptionHandling:
    """Tests for provider exception handling."""

    def test_anthropic_rate_limit_error(self):
        """Test Anthropic rate limit error is wrapped."""
        from azure_haymaker.llm import LLMConfig, LLMMessage, create_llm_client
        from azure_haymaker.llm.exceptions import LLMRateLimitError

        config = LLMConfig(provider="anthropic", api_key="sk-test")

        with patch("azure_haymaker.llm.providers.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            # Simulate rate limit error
            from anthropic import RateLimitError

            mock_client.messages.create.side_effect = RateLimitError(
                "Rate limit exceeded",
                response=MagicMock(status_code=429),
                body={},
            )

            provider = create_llm_client(config)
            messages = [LLMMessage(role="user", content="Hello")]

            with pytest.raises(LLMRateLimitError):
                provider.create_message(messages)

    def test_azure_openai_authentication_error(self):
        """Test Azure OpenAI auth error is wrapped."""
        from azure_haymaker.llm import LLMConfig, LLMMessage, create_llm_client
        from azure_haymaker.llm.exceptions import LLMAuthenticationError

        config = LLMConfig(
            provider="azure_openai",
            endpoint="https://test.openai.azure.com",
            deployment="gpt-4",
            api_key="bad-key",
        )

        with patch("azure_haymaker.llm.providers.azure_openai.AzureOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Simulate auth error
            from openai import AuthenticationError

            mock_client.chat.completions.create.side_effect = AuthenticationError(
                "Invalid API key",
                response=MagicMock(status_code=401),
                body={},
            )

            provider = create_llm_client(config)
            messages = [LLMMessage(role="user", content="Hello")]

            with pytest.raises(LLMAuthenticationError):
                provider.create_message(messages)


class TestProviderSystemPrompt:
    """Tests for system prompt handling."""

    def test_anthropic_system_prompt(self):
        """Test Anthropic passes system prompt correctly."""
        from azure_haymaker.llm import LLMConfig, LLMMessage, create_llm_client

        config = LLMConfig(provider="anthropic", api_key="sk-test")

        with patch("azure_haymaker.llm.providers.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Response")]
            mock_response.model = "claude-3-sonnet"
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 20
            mock_response.stop_reason = "end_turn"
            mock_client.messages.create.return_value = mock_response

            provider = create_llm_client(config)
            messages = [LLMMessage(role="user", content="Hello")]

            provider.create_message(
                messages,
                system="You are a helpful assistant.",
                max_tokens=100,
            )

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs["system"] == "You are a helpful assistant."

    def test_azure_openai_system_prompt(self):
        """Test Azure OpenAI passes system prompt in messages."""
        from azure_haymaker.llm import LLMConfig, LLMMessage, create_llm_client

        config = LLMConfig(
            provider="azure_openai",
            endpoint="https://test.openai.azure.com",
            deployment="gpt-4",
            api_key="test-key",
        )

        with patch("azure_haymaker.llm.providers.azure_openai.AzureOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "Response"
            mock_choice.finish_reason = "stop"

            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.model = "gpt-4"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_client.chat.completions.create.return_value = mock_response

            provider = create_llm_client(config)
            messages = [LLMMessage(role="user", content="Hello")]

            provider.create_message(
                messages,
                system="You are a helpful assistant.",
                max_tokens=100,
            )

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            # System message should be first in messages list
            assert call_kwargs["messages"][0]["role"] == "system"
            assert call_kwargs["messages"][0]["content"] == "You are a helpful assistant."
