"""Tests for email_generator module.

Comprehensive unit tests for AI-powered email generation using Anthropic Claude.
Tests cover:
- EmailContent dataclass
- EmailGenerationConfig validation
- EmailContentGenerator initialization and generation
- Input validation and security
- Error handling (rate limits, timeouts, API errors)
- Response parsing
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from anthropic import AnthropicError, RateLimitError
from anthropic.types import Message, TextBlock, Usage

from azure_haymaker.knowledge_worker.content.email_generator import (
    DEPARTMENT_PATTERN,
    EMAIL_PATTERN,
    WORKER_ID_PATTERN,
    EmailContent,
    EmailContentGenerator,
    EmailGenerationConfig,
    sanitize_error_message,
    validate_input,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# UNIT TESTS - EmailContent dataclass
# =============================================================================


class TestEmailContent:
    """Tests for EmailContent dataclass."""

    def test_email_content_creation(self) -> None:
        """Test basic EmailContent creation."""
        content = EmailContent(
            subject="Test Subject",
            body="<p>Test body</p>",
        )
        assert content.subject == "Test Subject"
        assert content.body == "<p>Test body</p>"
        assert content.metadata == {}

    def test_email_content_with_metadata(self) -> None:
        """Test EmailContent with metadata."""
        metadata = {
            "source": "anthropic_claude",
            "model": "claude-sonnet-4-5-20250929",
            "tokens_used": 100,
        }
        content = EmailContent(
            subject="Meeting Update",
            body="<p>The meeting is rescheduled.</p>",
            metadata=metadata,
        )
        assert content.metadata["source"] == "anthropic_claude"
        assert content.metadata["tokens_used"] == 100


# =============================================================================
# UNIT TESTS - EmailGenerationConfig
# =============================================================================


class TestEmailGenerationConfig:
    """Tests for EmailGenerationConfig Pydantic model."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = EmailGenerationConfig()
        assert config.enabled is False
        assert config.api_key is None
        assert config.model is None
        assert config.directive is None
        assert config.max_tokens == 1024
        assert config.temperature == 0.7
        assert config.timeout_seconds == 30

    def test_enabled_config(self) -> None:
        """Test enabled configuration with custom values."""
        config = EmailGenerationConfig(
            enabled=True,
            api_key="sk-ant-test-key",
            model="claude-sonnet-4-5-20250929",
            directive="Include a limerick",
            max_tokens=2048,
            temperature=0.9,
            timeout_seconds=60,
        )
        assert config.enabled is True
        assert config.api_key == "sk-ant-test-key"
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.directive == "Include a limerick"
        assert config.max_tokens == 2048
        assert config.temperature == 0.9
        assert config.timeout_seconds == 60


# =============================================================================
# UNIT TESTS - Input Validation
# =============================================================================


class TestInputValidation:
    """Tests for input validation functions."""

    def test_validate_worker_id_valid(self) -> None:
        """Test valid worker IDs."""
        valid_ids = ["kw-eng-1", "worker_123", "KW-ABC-001", "test-worker"]
        for worker_id in valid_ids:
            validate_input(worker_id, WORKER_ID_PATTERN, "worker_id")

    def test_validate_worker_id_invalid(self) -> None:
        """Test invalid worker IDs raise ValueError."""
        invalid_ids = [
            "kw eng 1",  # spaces
            "worker@123",  # special chars
            "a" * 65,  # too long
            "",  # empty
        ]
        for worker_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid worker_id"):
                validate_input(worker_id, WORKER_ID_PATTERN, "worker_id")

    def test_validate_department_valid(self) -> None:
        """Test valid department names."""
        valid_depts = ["engineering", "hr", "SALES", "tech-ops"]
        for dept in valid_depts:
            validate_input(dept, DEPARTMENT_PATTERN, "department")

    def test_validate_department_invalid(self) -> None:
        """Test invalid department names raise ValueError."""
        invalid_depts = [
            "tech ops",  # spaces
            "HR@Corp",  # special chars
            "d" * 51,  # too long
        ]
        for dept in invalid_depts:
            with pytest.raises(ValueError, match="Invalid department"):
                validate_input(dept, DEPARTMENT_PATTERN, "department")

    def test_validate_email_valid(self) -> None:
        """Test valid email addresses."""
        valid_emails = [
            "user@example.com",
            "test.user@corp.onmicrosoft.com",
            "kw-eng-1@tenant.com",
        ]
        for email in valid_emails:
            validate_input(email, EMAIL_PATTERN, "recipient")

    def test_validate_email_invalid(self) -> None:
        """Test invalid email addresses raise ValueError."""
        invalid_emails = [
            "not-an-email",
            "user@",
            "@domain.com",
            "user@.com",
        ]
        for email in invalid_emails:
            with pytest.raises(ValueError, match="Invalid recipient"):
                validate_input(email, EMAIL_PATTERN, "recipient")


# =============================================================================
# UNIT TESTS - Error Sanitization
# =============================================================================


class TestErrorSanitization:
    """Tests for error message sanitization."""

    def test_sanitize_api_keys(self) -> None:
        """Test API keys are redacted from error messages."""
        error = Exception("Error with key sk-ant-api123abc")
        sanitized = sanitize_error_message(error)
        assert "sk-ant-api123abc" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_tokens(self) -> None:
        """Test tokens are redacted."""
        error = Exception("Failed with token: abc123xyz")
        sanitized = sanitize_error_message(error)
        assert "abc123xyz" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_file_paths(self) -> None:
        """Test file paths are redacted."""
        error = Exception("Error in /home/user/project/secret.py")
        sanitized = sanitize_error_message(error)
        assert "/home/user/project/secret.py" not in sanitized
        assert "[PATH]" in sanitized


# =============================================================================
# UNIT TESTS - EmailContentGenerator Initialization
# =============================================================================


class TestEmailContentGeneratorInit:
    """Tests for EmailContentGenerator initialization."""

    def test_init_disabled(self) -> None:
        """Test initialization with disabled config."""
        config = EmailGenerationConfig(enabled=False)
        generator = EmailContentGenerator(config)
        assert generator.client is None

    @patch("azure_haymaker.knowledge_worker.content.email_generator.Anthropic")
    def test_init_enabled_with_api_key(self, mock_anthropic: MagicMock) -> None:
        """Test initialization with enabled config and API key."""
        config = EmailGenerationConfig(
            enabled=True,
            api_key="sk-ant-test-key",
            timeout_seconds=45,
        )
        generator = EmailContentGenerator(config)
        mock_anthropic.assert_called_once_with(
            api_key="sk-ant-test-key",
            timeout=45,
        )
        assert generator.client is not None

    @patch("azure_haymaker.knowledge_worker.content.email_generator.Anthropic")
    def test_init_enabled_without_api_key(self, mock_anthropic: MagicMock) -> None:
        """Test initialization uses env var when no API key provided."""
        config = EmailGenerationConfig(enabled=True)
        generator = EmailContentGenerator(config)
        mock_anthropic.assert_called_once_with(
            api_key=None,
            timeout=30,
        )
        assert generator.client is not None

    @patch("azure_haymaker.knowledge_worker.content.email_generator.Anthropic")
    def test_init_client_error(self, mock_anthropic: MagicMock) -> None:
        """Test initialization handles Anthropic client errors."""
        mock_anthropic.side_effect = Exception("Invalid API key sk-ant-secret123")
        config = EmailGenerationConfig(enabled=True, api_key="bad-key")

        with pytest.raises(ValueError, match="Failed to initialize Anthropic client") as exc_info:
            EmailContentGenerator(config)

        # Verify error is sanitized
        assert "sk-ant-secret123" not in str(exc_info.value)
        assert "[REDACTED]" in str(exc_info.value)


# =============================================================================
# UNIT TESTS - Email Generation
# =============================================================================


class TestEmailGeneration:
    """Tests for email generation functionality."""

    @pytest.fixture
    def mock_anthropic_response(self) -> Message:
        """Create a mock Anthropic API response."""
        text_block = MagicMock(spec=TextBlock)
        text_block.text = "Subject: Test Subject Line\nBody: This is the email body content."
        # Make isinstance check work
        text_block.__class__ = TextBlock

        usage = MagicMock(spec=Usage)
        usage.output_tokens = 50

        response = MagicMock(spec=Message)
        response.content = [text_block]
        response.usage = usage
        return response

    @pytest.fixture
    def generator_with_mock_client(self) -> tuple[EmailContentGenerator, MagicMock]:
        """Create generator with mocked Anthropic client."""
        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.Anthropic"
        ) as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            config = EmailGenerationConfig(
                enabled=True,
                api_key="sk-ant-test-key",
            )
            generator = EmailContentGenerator(config)
            return generator, mock_client

    @pytest.mark.asyncio
    async def test_generate_email_disabled(self) -> None:
        """Test generate_email raises when disabled."""
        config = EmailGenerationConfig(enabled=False)
        generator = EmailContentGenerator(config)

        with pytest.raises(RuntimeError, match="AI email generation is not enabled"):
            await generator.generate_email(
                worker_id="kw-eng-1",
                department="engineering",
                recipient="user@test.com",
                activity_count=1,
            )

    @pytest.mark.asyncio
    async def test_generate_email_success(
        self,
        generator_with_mock_client: tuple[EmailContentGenerator, MagicMock],
        mock_anthropic_response: Message,
    ) -> None:
        """Test successful email generation."""
        generator, mock_client = generator_with_mock_client
        mock_client.messages.create.return_value = mock_anthropic_response

        content = await generator.generate_email(
            worker_id="kw-eng-1",
            department="engineering",
            recipient="user@test.com",
            activity_count=42,
            run_id="run-123",
        )

        assert content.subject == "Test Subject Line"
        assert "email body content" in content.body
        assert content.metadata["source"] == "anthropic_claude"
        assert content.metadata["worker_id"] == "kw-eng-1"
        assert content.metadata["department"] == "engineering"
        assert content.metadata["activity_count"] == 42
        assert content.metadata["run_id"] == "run-123"
        assert content.metadata["tokens_used"] == 50

    @pytest.mark.asyncio
    async def test_generate_email_default_model(
        self,
        generator_with_mock_client: tuple[EmailContentGenerator, MagicMock],
        mock_anthropic_response: Message,
    ) -> None:
        """Test default model is used when not specified."""
        generator, mock_client = generator_with_mock_client
        mock_client.messages.create.return_value = mock_anthropic_response

        await generator.generate_email(
            worker_id="kw-eng-1",
            department="engineering",
            recipient="user@test.com",
            activity_count=1,
        )

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-sonnet-4-5-20250929"

    @pytest.mark.asyncio
    async def test_generate_email_invalid_worker_id(
        self,
        generator_with_mock_client: tuple[EmailContentGenerator, MagicMock],
    ) -> None:
        """Test validation fails for invalid worker_id."""
        generator, _ = generator_with_mock_client

        with pytest.raises(ValueError, match="Invalid worker_id"):
            await generator.generate_email(
                worker_id="invalid worker",  # spaces not allowed
                department="engineering",
                recipient="user@test.com",
                activity_count=1,
            )

    @pytest.mark.asyncio
    async def test_generate_email_invalid_activity_count(
        self,
        generator_with_mock_client: tuple[EmailContentGenerator, MagicMock],
    ) -> None:
        """Test validation fails for out-of-range activity_count."""
        generator, _ = generator_with_mock_client

        with pytest.raises(ValueError, match="activity_count must be between"):
            await generator.generate_email(
                worker_id="kw-eng-1",
                department="engineering",
                recipient="user@test.com",
                activity_count=-1,
            )

        with pytest.raises(ValueError, match="activity_count must be between"):
            await generator.generate_email(
                worker_id="kw-eng-1",
                department="engineering",
                recipient="user@test.com",
                activity_count=1_000_001,
            )


# =============================================================================
# UNIT TESTS - Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for API error handling."""

    @pytest.fixture
    def generator_with_mock_client(self) -> tuple[EmailContentGenerator, MagicMock]:
        """Create generator with mocked Anthropic client."""
        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.Anthropic"
        ) as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            config = EmailGenerationConfig(
                enabled=True,
                api_key="sk-ant-test-key",
            )
            generator = EmailContentGenerator(config)
            return generator, mock_client

    @pytest.mark.asyncio
    async def test_rate_limit_error(
        self,
        generator_with_mock_client: tuple[EmailContentGenerator, MagicMock],
    ) -> None:
        """Test rate limit errors are handled properly."""
        generator, mock_client = generator_with_mock_client

        # Create RateLimitError with required args
        rate_limit_error = RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body={"error": {"message": "Rate limit exceeded"}},
        )
        mock_client.messages.create.side_effect = rate_limit_error

        with pytest.raises(RuntimeError, match="rate limits"):
            await generator.generate_email(
                worker_id="kw-eng-1",
                department="engineering",
                recipient="user@test.com",
                activity_count=1,
            )

    @pytest.mark.asyncio
    async def test_anthropic_api_error(
        self,
        generator_with_mock_client: tuple[EmailContentGenerator, MagicMock],
    ) -> None:
        """Test Anthropic API errors are handled and sanitized."""
        generator, mock_client = generator_with_mock_client

        # Create AnthropicError with API key in message
        api_error = AnthropicError("Error with key sk-ant-secretkey123")
        mock_client.messages.create.side_effect = api_error

        with pytest.raises(RuntimeError) as exc_info:
            await generator.generate_email(
                worker_id="kw-eng-1",
                department="engineering",
                recipient="user@test.com",
                activity_count=1,
            )

        # Verify sensitive info is redacted
        assert "sk-ant-secretkey123" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unexpected_error(
        self,
        generator_with_mock_client: tuple[EmailContentGenerator, MagicMock],
    ) -> None:
        """Test unexpected errors are handled and sanitized."""
        generator, mock_client = generator_with_mock_client
        mock_client.messages.create.side_effect = Exception(
            "Unexpected error with token: secret123"
        )

        with pytest.raises(RuntimeError, match="Failed to generate email content"):
            await generator.generate_email(
                worker_id="kw-eng-1",
                department="engineering",
                recipient="user@test.com",
                activity_count=1,
            )


# =============================================================================
# UNIT TESTS - Response Parsing
# =============================================================================


class TestResponseParsing:
    """Tests for email response parsing."""

    @pytest.fixture
    def generator(self) -> EmailContentGenerator:
        """Create generator for testing parsing."""
        with patch("azure_haymaker.knowledge_worker.content.email_generator.Anthropic"):
            config = EmailGenerationConfig(enabled=True, api_key="test")
            return EmailContentGenerator(config)

    def test_parse_standard_format(self, generator: EmailContentGenerator) -> None:
        """Test parsing standard Subject:/Body: format."""
        content = "Subject: Project Update\nBody: The project is on track for delivery."
        subject, body = generator._parse_email_response(content)

        assert subject == "Project Update"
        assert "on track for delivery" in body

    def test_parse_without_body_prefix(self, generator: EmailContentGenerator) -> None:
        """Test parsing without Body: prefix."""
        content = "Subject: Meeting Notes\n\nAttached are the meeting notes from today."
        subject, body = generator._parse_email_response(content)

        assert subject == "Meeting Notes"
        assert "meeting notes" in body

    def test_parse_multiline_body(self, generator: EmailContentGenerator) -> None:
        """Test parsing multiline body content."""
        content = "Subject: Weekly Report\n\nFirst paragraph.\n\nSecond paragraph."
        subject, body = generator._parse_email_response(content)

        assert subject == "Weekly Report"
        assert "<p>" in body  # Should be HTML formatted

    def test_parse_empty_content(self, generator: EmailContentGenerator) -> None:
        """Test parsing empty content returns defaults."""
        content = ""
        subject, body = generator._parse_email_response(content)

        assert subject == "Knowledge Worker Activity"
        assert "Automated activity" in body

    def test_parse_html_escaping(self, generator: EmailContentGenerator) -> None:
        """Test HTML content is escaped for XSS prevention."""
        content = "Subject: Test\n<script>alert('xss')</script>"
        subject, body = generator._parse_email_response(content)

        # Script tag should be escaped
        assert "<script>" not in body
        assert "&lt;script&gt;" in body


# =============================================================================
# INTEGRATION TESTS - Full Flow
# =============================================================================


class TestEmailGenerationIntegration:
    """Integration tests for email generation flow."""

    @pytest.mark.asyncio
    async def test_full_generation_flow(self) -> None:
        """Test complete generation flow with mocked API."""
        with patch(
            "azure_haymaker.knowledge_worker.content.email_generator.Anthropic"
        ) as mock_anthropic:
            # Setup mock response using actual TextBlock instance
            text_block = TextBlock(
                type="text",
                text="Subject: Sprint Planning Update\nBody: The sprint planning meeting has been rescheduled to 3 PM.",
            )

            usage = MagicMock(spec=Usage)
            usage.output_tokens = 75

            response = MagicMock(spec=Message)
            response.content = [text_block]
            response.usage = usage

            mock_client = MagicMock()
            mock_client.messages.create.return_value = response
            mock_anthropic.return_value = mock_client

            # Create generator and generate email
            config = EmailGenerationConfig(
                enabled=True,
                api_key="sk-ant-test",
                directive="Keep it brief",
            )
            generator = EmailContentGenerator(config)

            content = await generator.generate_email(
                worker_id="kw-eng-1",
                department="engineering",
                recipient="user@tenant.com",
                activity_count=10,
            )

            assert content.subject == "Sprint Planning Update"
            assert "rescheduled" in content.body
            assert content.metadata["tokens_used"] == 75
