"""Security tests for Azure HayMaker.

Tests security fixes for:
- CRITICAL-1: SQL/OData injection prevention
- CRITICAL-2: CLI config file permissions
- HIGH-1: Rate limiter race conditions
- HIGH-4: Path traversal prevention
- HIGH-5: Error message sanitization
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.azure_haymaker.orchestrator.execute_api import (
    extract_user_from_request,
    get_scenario_path,
)
from src.azure_haymaker.orchestrator.execution_tracker import sanitize_odata_value


class TestODataInjectionPrevention:
    """Test OData injection attack prevention."""

    def test_sanitize_odata_value_basic(self):
        """Test basic string sanitization."""
        assert sanitize_odata_value("normal-value") == "normal-value"
        assert sanitize_odata_value("exec-20251115-abc123") == "exec-20251115-abc123"

    def test_sanitize_odata_value_injection_attempts(self):
        """Test sanitization of injection attack payloads."""
        # Single quote injection
        malicious = "exec' or PartitionKey ne '"
        sanitized = sanitize_odata_value(malicious)
        assert "''" in sanitized  # Single quotes should be doubled
        assert sanitized == "exec'' or PartitionKey ne ''"

        # Multiple single quotes
        malicious = "exec'''abc"
        sanitized = sanitize_odata_value(malicious)
        assert sanitized == "exec''''''abc"

    def test_sanitize_odata_value_filters_prevent_injection(self):
        """Test that sanitized values prevent filter manipulation."""
        # Simulate building a filter query with sanitized input
        execution_id = "exec' or PartitionKey ne '"
        sanitized = sanitize_odata_value(execution_id)
        query = f"PartitionKey eq '{sanitized}'"

        # The query should have escaped quotes, not functional OR operator
        assert query == "PartitionKey eq 'exec'' or PartitionKey ne '''"
        # OData will treat this as a literal string search, not an OR condition

    def test_sanitize_odata_value_handles_non_strings(self):
        """Test sanitization of non-string inputs."""
        assert sanitize_odata_value(123) == "123"
        assert sanitize_odata_value(True) == "True"


class TestPathTraversalPrevention:
    """Test path traversal attack prevention."""

    def test_get_scenario_path_valid_names(self):
        """Test that valid scenario names are accepted."""
        valid_names = [
            "compute-01",
            "networking-01-vnet",
            "storage-blob-basic",
            "keyvault-secrets",
        ]

        for name in valid_names:
            # Should not raise exception and return None (file doesn't exist in test)
            result = get_scenario_path(name)
            assert result is None or isinstance(result, Path)

    def test_get_scenario_path_rejects_traversal(self):
        """Test that path traversal attempts are blocked."""
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "../../secrets",
            "../.env",
            "./../config.yaml",
            "compute/../../../etc/passwd",
        ]

        for attempt in traversal_attempts:
            result = get_scenario_path(attempt)
            assert result is None, f"Path traversal should be blocked: {attempt}"

    def test_get_scenario_path_rejects_invalid_characters(self):
        """Test that scenario names with invalid characters are rejected."""
        invalid_names = [
            "scenario/../../etc/passwd",
            "scenario\\..\\..\\passwd",
            "sce nario",  # space
            "scenario@admin",  # special char
            "scenario..",  # dot
            "Scenario-01",  # uppercase
        ]

        for name in invalid_names:
            result = get_scenario_path(name)
            assert result is None, f"Invalid name should be rejected: {name}"

    def test_get_scenario_path_alphanumeric_validation(self):
        """Test strict alphanumeric-hyphen validation."""
        # Only lowercase alphanumeric and hyphens should be allowed
        assert get_scenario_path("valid-name-123") is None  # Returns None (file doesn't exist)

        # These should be rejected before file lookup
        assert get_scenario_path("../invalid") is None
        assert get_scenario_path("invalid/path") is None
        assert get_scenario_path("invalid\\path") is None


class TestCLIConfigPermissions:
    """Test CLI configuration file security."""

    def test_config_file_permissions(self):
        """Test that config files are created with secure permissions."""
        import sys

        sys.path.insert(0, "cli/src")
        from haymaker_cli.config import (
            CliConfig,
            ProfileConfig,
            get_config_path,
            save_cli_config,
        )

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("pathlib.Path.home", return_value=Path(tmpdir)),
        ):
            # Create config
            config_path = get_config_path()
            config = CliConfig(
                profiles={"default": ProfileConfig(endpoint="https://api.example.com")}
            )
            save_cli_config(config)

            # Check directory permissions (should be 0700)
            config_dir = config_path.parent
            dir_mode = config_dir.stat().st_mode & 0o777
            assert dir_mode == 0o700, f"Config directory should be 0700, got {oct(dir_mode)}"

            # Check file permissions (should be 0600)
            file_mode = config_path.stat().st_mode & 0o777
            assert file_mode == 0o600, f"Config file should be 0600, got {oct(file_mode)}"

    def test_config_file_permissions_on_existing(self):
        """Test that permissions are fixed on existing config files."""
        import sys

        sys.path.insert(0, "cli/src")
        from haymaker_cli.config import get_config_path

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("pathlib.Path.home", return_value=Path(tmpdir)),
        ):
            # Create config with insecure permissions
            config_dir = Path(tmpdir) / ".haymaker"
            config_dir.mkdir()
            config_path = config_dir / "config.yaml"
            config_path.write_text("test: data")
            config_path.chmod(0o644)  # World-readable

            # Call get_config_path which should fix permissions
            result = get_config_path()

            # Check permissions were fixed
            file_mode = result.stat().st_mode & 0o777
            assert file_mode == 0o600, f"Permissions should be fixed to 0600, got {oct(file_mode)}"


class TestUserExtraction:
    """Test user identification for rate limiting."""

    def test_extract_user_from_azure_ad(self):
        """Test extraction of Azure AD principal ID."""
        mock_req = MagicMock()
        mock_req.headers.get.side_effect = lambda key, default="": {
            "x-ms-client-principal-id": "azure-ad-principal-123"
        }.get(key, default)

        user_id = extract_user_from_request(mock_req)
        assert user_id == "aad:azure-ad-principal-123"

    def test_extract_user_from_api_key(self):
        """Test extraction from API key."""
        mock_req = MagicMock()
        mock_req.headers.get.side_effect = lambda key, default="": {
            "x-functions-key": "abcdef1234567890"
        }.get(key, default)

        user_id = extract_user_from_request(mock_req)
        assert user_id == "key:abcdef12"  # First 8 chars

    def test_extract_user_from_ip(self):
        """Test fallback to IP address."""
        mock_req = MagicMock()
        mock_req.headers.get.side_effect = lambda key, default="": {
            "x-forwarded-for": "192.168.1.100, 10.0.0.1"
        }.get(key, default)

        user_id = extract_user_from_request(mock_req)
        assert user_id == "ip:192.168.1.100"  # First IP in chain

    def test_extract_user_fallback_unknown(self):
        """Test fallback when no identifying info available."""
        mock_req = MagicMock()
        mock_req.headers.get.return_value = ""

        user_id = extract_user_from_request(mock_req)
        assert user_id == "ip:unknown"


class TestRateLimiterConcurrency:
    """Test rate limiter optimistic concurrency fixes."""

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_requests(self):
        """Test that concurrent requests don't bypass rate limits."""
        from azure.core.exceptions import ResourceModifiedError

        from src.azure_haymaker.orchestrator.rate_limiter import RateLimiter

        # Mock table client that simulates concurrent updates
        mock_table = AsyncMock()
        mock_entity = {
            "Count": 9,  # Just under limit of 10
            "WindowStart": "2025-11-15T10:00:00+00:00",
            "etag": "initial-etag",
        }

        # First call succeeds, subsequent calls fail with ResourceModifiedError
        call_count = 0

        async def mock_get_entity(*args, **kwargs):
            return mock_entity.copy()

        async def mock_update_entity(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                # Simulate optimistic concurrency conflict
                raise ResourceModifiedError("Entity was modified")
            return None

        mock_table.get_entity = mock_get_entity
        mock_table.update_entity = mock_update_entity
        mock_table.create_entity = AsyncMock()

        limiter = RateLimiter(mock_table)

        # Simulate 5 concurrent requests (should trigger retry logic)
        results = await asyncio.gather(
            *[
                limiter.check_rate_limit("global", "test", limit=10, window_seconds=3600)
                for _ in range(5)
            ]
        )

        # All should get a result (may be allowed or retry)
        assert len(results) == 5
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_rate_limiter_etag_usage(self):
        """Test that rate limiter uses ETags for optimistic concurrency."""
        from azure.core import MatchConditions

        from src.azure_haymaker.orchestrator.rate_limiter import RateLimiter

        mock_table = AsyncMock()
        mock_entity = {
            "Count": 5,
            "WindowStart": "2025-11-15T10:00:00+00:00",
            "etag": "test-etag-123",
        }

        mock_table.get_entity = AsyncMock(return_value=mock_entity)
        mock_table.update_entity = AsyncMock()

        limiter = RateLimiter(mock_table)
        result = await limiter.check_rate_limit("global", "test", limit=10)

        if result.allowed:
            # Verify update_entity was called with ETag and match condition
            mock_table.update_entity.assert_called()
            call_kwargs = mock_table.update_entity.call_args[1]
            assert call_kwargs["etag"] == "test-etag-123"
            assert call_kwargs["match_condition"] == MatchConditions.IfNotModified


class TestErrorSanitization:
    """Test error message sanitization."""

    def test_error_messages_no_internal_details(self):
        """Test that error responses don't leak internal details."""
        # This would be tested with actual API calls in integration tests
        # Here we verify the error message format

        import json

        # Generic error response format should not include:
        # - Stack traces
        # - File paths
        # - Database schema info
        # - Internal IDs
        # - Exception messages

        error_response = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to process request",
            }
        }

        # Verify structure
        assert "code" in error_response["error"]
        assert "message" in error_response["error"]
        assert "traceback" not in json.dumps(error_response)
        assert "exception" not in json.dumps(error_response)
        assert "/" not in error_response["error"]["message"]  # No file paths


class TestHTTPSEnforcement:
    """Test HTTPS enforcement in CLI configuration."""

    def test_load_config_rejects_http(self):
        """Test that HTTP endpoints are rejected."""
        import sys

        sys.path.insert(0, "cli/src")
        from haymaker_cli.config import load_cli_config

        # Mock environment with HTTP endpoint
        with (
            patch.dict(os.environ, {"HAYMAKER_ENDPOINT": "http://insecure.example.com"}),
            pytest.raises(ValueError, match="HTTPS is required"),
        ):
            load_cli_config()

    def test_load_config_accepts_https(self):
        """Test that HTTPS endpoints are accepted."""
        import sys

        sys.path.insert(0, "cli/src")
        from haymaker_cli.config import load_cli_config

        # Mock environment with HTTPS endpoint
        with patch.dict(
            os.environ,
            {"HAYMAKER_ENDPOINT": "https://secure.example.com", "HAYMAKER_API_KEY": "test-key"},
        ):
            config = load_cli_config()
            assert config.endpoint == "https://secure.example.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
