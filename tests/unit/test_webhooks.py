"""Unit tests for webhook notification system."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from azure_haymaker.orchestrator.webhooks import (
    WebhookValidationError,
    get_webhook_url,
    notify_execution_completed,
    notify_execution_failed,
    notify_execution_started,
    send_webhook,
    validate_webhook_url,
)


class TestValidateWebhookUrl:
    """Tests for URL validation function."""

    def test_valid_https_url(self) -> None:
        """Test that valid HTTPS URLs pass validation."""
        url = "https://example.com/webhook"
        result = validate_webhook_url(url)
        assert result == url

    def test_valid_http_url(self) -> None:
        """Test that valid HTTP URLs pass validation."""
        url = "http://example.com/webhook"
        result = validate_webhook_url(url)
        assert result == url

    def test_valid_url_with_port(self) -> None:
        """Test that URLs with ports pass validation."""
        url = "https://example.com:8443/webhook"
        result = validate_webhook_url(url)
        assert result == url

    def test_valid_url_with_path_and_query(self) -> None:
        """Test that URLs with paths and query strings pass validation."""
        url = "https://example.com/api/v1/webhook?token=abc123"
        result = validate_webhook_url(url)
        assert result == url

    def test_invalid_scheme_ftp(self) -> None:
        """Test that FTP scheme is rejected."""
        with pytest.raises(WebhookValidationError) as exc_info:
            validate_webhook_url("ftp://example.com/file")
        assert "Invalid URL scheme" in str(exc_info.value)
        assert "ftp" in str(exc_info.value)

    def test_invalid_scheme_file(self) -> None:
        """Test that file scheme is rejected."""
        with pytest.raises(WebhookValidationError) as exc_info:
            validate_webhook_url("file:///etc/passwd")
        assert "Invalid URL scheme" in str(exc_info.value)

    def test_invalid_scheme_javascript(self) -> None:
        """Test that javascript scheme is rejected."""
        with pytest.raises(WebhookValidationError) as exc_info:
            validate_webhook_url("javascript:alert(1)")
        assert "Invalid URL scheme" in str(exc_info.value)

    def test_missing_hostname(self) -> None:
        """Test that URLs without hostname are rejected."""
        with pytest.raises(WebhookValidationError) as exc_info:
            validate_webhook_url("http:///path")
        assert "hostname" in str(exc_info.value).lower()

    def test_private_ip_10_range(self) -> None:
        """Test that 10.x.x.x private IPs are blocked."""
        with pytest.raises(WebhookValidationError) as exc_info:
            validate_webhook_url("http://10.0.0.1/webhook")
        assert "Private IP" in str(exc_info.value)

    def test_private_ip_172_range(self) -> None:
        """Test that 172.16-31.x.x private IPs are blocked."""
        with pytest.raises(WebhookValidationError) as exc_info:
            validate_webhook_url("http://172.16.0.1/webhook")
        assert "Private IP" in str(exc_info.value)

    def test_private_ip_192_168_range(self) -> None:
        """Test that 192.168.x.x private IPs are blocked."""
        with pytest.raises(WebhookValidationError) as exc_info:
            validate_webhook_url("http://192.168.1.1/webhook")
        assert "Private IP" in str(exc_info.value)

    def test_localhost_ip(self) -> None:
        """Test that 127.x.x.x localhost IPs are blocked."""
        with pytest.raises(WebhookValidationError) as exc_info:
            validate_webhook_url("http://127.0.0.1/webhook")
        assert "Private IP" in str(exc_info.value)

    def test_link_local_ip(self) -> None:
        """Test that 169.254.x.x link-local IPs are blocked."""
        with pytest.raises(WebhookValidationError) as exc_info:
            validate_webhook_url("http://169.254.169.254/metadata")
        assert "Private IP" in str(exc_info.value)

    def test_ipv6_localhost(self) -> None:
        """Test that IPv6 localhost is blocked."""
        with pytest.raises(WebhookValidationError) as exc_info:
            validate_webhook_url("http://[::1]/webhook")
        assert "Private IP" in str(exc_info.value)

    def test_private_ip_allowed_when_disabled(self) -> None:
        """Test that private IPs are allowed when block_private_ips=False."""
        url = "http://192.168.1.1/webhook"
        result = validate_webhook_url(url, block_private_ips=False)
        assert result == url

    def test_hostname_allowed(self) -> None:
        """Test that regular hostnames are allowed (no DNS resolution)."""
        url = "https://internal.example.com/webhook"
        result = validate_webhook_url(url)
        assert result == url

    def test_public_ip_allowed(self) -> None:
        """Test that public IPs are allowed."""
        url = "https://8.8.8.8/webhook"
        result = validate_webhook_url(url)
        assert result == url


class TestGetWebhookUrl:
    """Tests for get_webhook_url function."""

    def test_returns_env_var_when_set(self) -> None:
        """Test that function returns environment variable value."""
        with patch.dict("os.environ", {"HAYMAKER_WEBHOOK_URL": "https://example.com/hook"}):
            result = get_webhook_url()
            assert result == "https://example.com/hook"

    def test_returns_none_when_not_set(self) -> None:
        """Test that function returns None when env var is not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = get_webhook_url()
            assert result is None


class TestSendWebhook:
    """Tests for send_webhook function."""

    @pytest.mark.asyncio
    async def test_successful_webhook_delivery(self) -> None:
        """Test successful webhook delivery with mocked httpx."""
        mock_response = AsyncMock()
        mock_response.is_success = True
        mock_response.status_code = 200

        with patch("azure_haymaker.orchestrator.webhooks.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_webhook(
                url="https://example.com/webhook",
                event_type="execution.started",
                data={"run_id": "test-123"},
            )

            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://example.com/webhook"
            assert call_args[1]["json"]["event"] == "execution.started"
            assert call_args[1]["json"]["run_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_noop_when_url_not_configured(self) -> None:
        """Test that send_webhook returns True when URL is None."""
        result = await send_webhook(
            url=None,
            event_type="execution.started",
            data={"run_id": "test-123"},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_noop_when_url_is_empty_string(self) -> None:
        """Test that send_webhook returns True when URL is empty string."""
        result = await send_webhook(
            url="",
            event_type="execution.started",
            data={"run_id": "test-123"},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_timeout_handling(self) -> None:
        """Test that timeout exceptions are handled gracefully."""
        with patch("azure_haymaker.orchestrator.webhooks.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_webhook(
                url="https://example.com/webhook",
                event_type="execution.started",
                data={"run_id": "test-123"},
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_http_error_response(self) -> None:
        """Test that HTTP error responses (4xx, 5xx) return False."""
        mock_response = AsyncMock()
        mock_response.is_success = False
        mock_response.status_code = 500

        with patch("azure_haymaker.orchestrator.webhooks.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_webhook(
                url="https://example.com/webhook",
                event_type="execution.started",
                data={"run_id": "test-123"},
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_connection_error_handling(self) -> None:
        """Test that connection errors are handled gracefully."""
        with patch("azure_haymaker.orchestrator.webhooks.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_webhook(
                url="https://example.com/webhook",
                event_type="execution.started",
                data={"run_id": "test-123"},
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_url_validation_blocks_private_ip(self) -> None:
        """Test that URL validation blocks private IPs."""
        result = await send_webhook(
            url="http://192.168.1.1/webhook",
            event_type="execution.started",
            data={"run_id": "test-123"},
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_url_validation_blocks_invalid_scheme(self) -> None:
        """Test that URL validation blocks invalid schemes."""
        result = await send_webhook(
            url="ftp://example.com/webhook",
            event_type="execution.started",
            data={"run_id": "test-123"},
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_url_validation_can_be_disabled(self) -> None:
        """Test that URL validation can be bypassed when needed."""
        mock_response = AsyncMock()
        mock_response.is_success = True

        with patch("azure_haymaker.orchestrator.webhooks.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_webhook(
                url="http://192.168.1.1/webhook",
                event_type="execution.started",
                data={"run_id": "test-123"},
                validate_url=False,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_payload_includes_timestamp(self) -> None:
        """Test that webhook payload includes timestamp."""
        mock_response = AsyncMock()
        mock_response.is_success = True

        with patch("azure_haymaker.orchestrator.webhooks.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await send_webhook(
                url="https://example.com/webhook",
                event_type="execution.started",
                data={"run_id": "test-123"},
            )

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert "timestamp" in payload
            assert "T" in payload["timestamp"]  # ISO format check


class TestNotifyExecutionStarted:
    """Tests for notify_execution_started function."""

    @pytest.mark.asyncio
    async def test_sends_correct_event_type(self) -> None:
        """Test that execution.started event type is sent."""
        mock_response = AsyncMock()
        mock_response.is_success = True

        with (
            patch.dict("os.environ", {"HAYMAKER_WEBHOOK_URL": "https://example.com/hook"}),
            patch("azure_haymaker.orchestrator.webhooks.httpx.AsyncClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await notify_execution_started(
                run_id="run-123",
                scenarios=["scenario1", "scenario2"],
            )

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["event"] == "execution.started"
            assert payload["run_id"] == "run-123"
            assert payload["scenarios"] == ["scenario1", "scenario2"]

    @pytest.mark.asyncio
    async def test_noop_when_no_webhook_configured(self) -> None:
        """Test that nothing happens when webhook URL is not configured."""
        with patch.dict("os.environ", {}, clear=True):
            result = await notify_execution_started(
                run_id="run-123",
                scenarios=["scenario1"],
            )
            assert result is True


class TestNotifyExecutionCompleted:
    """Tests for notify_execution_completed function."""

    @pytest.mark.asyncio
    async def test_sends_correct_event_type(self) -> None:
        """Test that execution.completed event type is sent."""
        mock_response = AsyncMock()
        mock_response.is_success = True

        with (
            patch.dict("os.environ", {"HAYMAKER_WEBHOOK_URL": "https://example.com/hook"}),
            patch("azure_haymaker.orchestrator.webhooks.httpx.AsyncClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await notify_execution_completed(
                run_id="run-123",
                duration_hours=2.5,
                scenarios_count=10,
            )

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["event"] == "execution.completed"
            assert payload["run_id"] == "run-123"
            assert payload["duration_hours"] == 2.5
            assert payload["scenarios_count"] == 10


class TestNotifyExecutionFailed:
    """Tests for notify_execution_failed function."""

    @pytest.mark.asyncio
    async def test_sends_correct_event_type(self) -> None:
        """Test that execution.failed event type is sent."""
        mock_response = AsyncMock()
        mock_response.is_success = True

        with (
            patch.dict("os.environ", {"HAYMAKER_WEBHOOK_URL": "https://example.com/hook"}),
            patch("azure_haymaker.orchestrator.webhooks.httpx.AsyncClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await notify_execution_failed(
                run_id="run-123",
                error="Something went wrong",
            )

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["event"] == "execution.failed"
            assert payload["run_id"] == "run-123"
            assert payload["error"] == "Something went wrong"
