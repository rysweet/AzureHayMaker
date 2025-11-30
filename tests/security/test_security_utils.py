"""Tests for security_utils module.

This module tests the sanitization functions that prevent credential
leakage in logs and error messages.
"""

import pytest

from azure_haymaker.knowledge_worker.computer_use.security_utils import (
    mask_email,
    sanitize_connection_string,
    sanitize_dict,
    sanitize_error,
    sanitize_for_log,
    sanitize_url,
)


class TestSanitizeError:
    """Tests for sanitize_error function."""

    def test_sanitizes_password_in_error_message(self):
        """Test password is redacted from error messages."""
        error_msg = "Connection failed with password: SuperSecret123!"
        result = sanitize_error(error_msg)
        assert "SuperSecret123!" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_api_key(self):
        """Test API key is redacted."""
        error_msg = "API call failed: api_key=sk-1234567890abcdef"
        result = sanitize_error(error_msg)
        assert "sk-1234567890abcdef" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_bearer_token(self):
        """Test bearer token is redacted."""
        error_msg = "Authentication failed: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = sanitize_error(error_msg)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_url_credentials(self):
        """Test credentials in URLs are redacted."""
        error_msg = "Failed to connect to https://admin:password123@example.com/api"
        result = sanitize_error(error_msg)
        assert "admin:password123" not in result
        assert "[REDACTED]" in result
        assert "example.com" in result

    def test_sanitizes_azure_account_key(self):
        """Test Azure storage account key is redacted."""
        error_msg = "Storage error: AccountKey=abc123xyz789=="
        result = sanitize_error(error_msg)
        assert "abc123xyz789==" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_client_secret(self):
        """Test client secret is redacted."""
        error_msg = "Auth failed: client_secret=my-secret-value-123"
        result = sanitize_error(error_msg)
        assert "my-secret-value-123" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_private_key(self):
        """Test private key is redacted."""
        error_msg = """Certificate error: -----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890
-----END RSA PRIVATE KEY-----"""
        result = sanitize_error(error_msg)
        assert "MIIEpAIBAAKCAQEA1234567890" not in result
        assert "[REDACTED-PRIVATE-KEY]" in result

    def test_handles_exception_objects(self):
        """Test can sanitize Exception objects."""
        error = Exception("Password: secret123")
        result = sanitize_error(error)
        assert "secret123" not in result
        assert "[REDACTED]" in result

    def test_handles_non_string_input(self):
        """Test handles non-string input gracefully."""
        result = sanitize_error(123)
        assert result == "123"

    def test_preserves_safe_content(self):
        """Test safe content is preserved."""
        error_msg = "Connection timeout after 30 seconds"
        result = sanitize_error(error_msg)
        assert result == error_msg

    def test_multiple_credentials_in_same_message(self):
        """Test multiple credentials are all redacted."""
        error_msg = "Failed: password=secret1 and api_key=secret2"
        result = sanitize_error(error_msg)
        assert "secret1" not in result
        assert "secret2" not in result
        assert result.count("[REDACTED]") == 2


class TestSanitizeDict:
    """Tests for sanitize_dict function."""

    def test_sanitizes_password_key(self):
        """Test dictionary with password key is sanitized."""
        data = {"username": "admin", "password": "secret123"}
        result = sanitize_dict(data)
        assert result["username"] == "admin"
        assert result["password"] == "[REDACTED]"

    def test_sanitizes_nested_dict(self):
        """Test nested dictionaries are sanitized recursively."""
        data = {
            "config": {
                "api_key": "sk-123",
                "endpoint": "api.example.com"
            }
        }
        result = sanitize_dict(data)
        assert result["config"]["api_key"] == "[REDACTED]"
        assert result["config"]["endpoint"] == "api.example.com"

    def test_sanitizes_list_of_dicts(self):
        """Test list of dictionaries are sanitized."""
        data = {
            "credentials": [
                {"username": "user1", "password": "pass1"},
                {"username": "user2", "token": "token2"}
            ]
        }
        result = sanitize_dict(data)
        assert result["credentials"][0]["password"] == "[REDACTED]"
        assert result["credentials"][1]["token"] == "[REDACTED]"

    def test_custom_redaction_value(self):
        """Test custom redaction value is used."""
        data = {"password": "secret"}
        result = sanitize_dict(data, redact_value="***")
        assert result["password"] == "***"

    def test_sanitizes_various_secret_keys(self):
        """Test various secret-related keys are sanitized."""
        data = {
            "password": "pass",
            "secret": "secret",
            "token": "token",
            "api_key": "key",
            "apikey": "key2",
            "private_key": "pk",
            "credential": "cred",
        }
        result = sanitize_dict(data)
        for key in data.keys():
            assert result[key] == "[REDACTED]"

    def test_preserves_non_sensitive_data(self):
        """Test non-sensitive data is preserved."""
        data = {
            "username": "admin",
            "email": "user@example.com",
            "count": 42,
            "enabled": True
        }
        result = sanitize_dict(data)
        assert result == data


class TestSanitizeUrl:
    """Tests for sanitize_url function."""

    def test_sanitizes_url_with_credentials(self):
        """Test URL with username and password is sanitized."""
        url = "https://user:password@example.com/path"
        result = sanitize_url(url)
        assert "user:password" not in result
        assert "[REDACTED]" in result
        assert "example.com/path" in result

    def test_preserves_url_without_credentials(self):
        """Test URL without credentials is unchanged."""
        url = "https://example.com/path"
        result = sanitize_url(url)
        assert result == url

    def test_handles_non_string_input(self):
        """Test handles non-string input gracefully."""
        result = sanitize_url(123)
        assert result == "123"


class TestSanitizeConnectionString:
    """Tests for sanitize_connection_string function."""

    def test_sanitizes_azure_account_key(self):
        """Test Azure storage account key is sanitized."""
        conn_str = "DefaultEndpointsProtocol=https;AccountName=storage;AccountKey=abc123=="
        result = sanitize_connection_string(conn_str)
        assert "abc123==" not in result
        assert "AccountKey=[REDACTED]" in result
        assert "AccountName=storage" in result

    def test_sanitizes_shared_access_key(self):
        """Test shared access key is sanitized."""
        conn_str = "Endpoint=sb://namespace.servicebus.windows.net/;SharedAccessKey=xyz789=="
        result = sanitize_connection_string(conn_str)
        assert "xyz789==" not in result
        assert "SharedAccessKey=[REDACTED]" in result

    def test_sanitizes_aws_secret_key(self):
        """Test AWS secret access key is sanitized."""
        conn_str = "aws_access_key_id=AKIA123;aws_secret_access_key=secret456"
        result = sanitize_connection_string(conn_str)
        assert "secret456" not in result
        assert "aws_secret_access_key=[REDACTED]" in result

    def test_handles_non_string_input(self):
        """Test handles non-string input gracefully."""
        result = sanitize_connection_string(123)
        assert result == "123"


class TestMaskEmail:
    """Tests for mask_email function."""

    def test_masks_email_address(self):
        """Test email address is masked."""
        email = "user@example.com"
        result = mask_email(email)
        assert result == "u***r@example.com"

    def test_masks_long_username(self):
        """Test long username is masked correctly."""
        email = "verylongusername@example.com"
        result = mask_email(email)
        assert result == "v***e@example.com"

    def test_masks_short_username(self):
        """Test short username is masked."""
        email = "ab@example.com"
        result = mask_email(email)
        assert result == "***@example.com"

    def test_preserves_invalid_email(self):
        """Test invalid email is preserved."""
        email = "not-an-email"
        result = mask_email(email)
        assert result == email

    def test_handles_non_string_input(self):
        """Test handles non-string input gracefully."""
        result = mask_email(123)
        assert result == 123


class TestSanitizeForLog:
    """Tests for sanitize_for_log function (comprehensive)."""

    def test_comprehensive_sanitization(self):
        """Test multiple types of secrets are sanitized in one message."""
        text = (
            "Connection to https://admin:pass123@db.example.com failed. "
            "API key sk-abc123 invalid. "
            "AccountKey=secret456== not found."
        )
        result = sanitize_for_log(text)

        # All secrets should be redacted
        assert "pass123" not in result
        assert "sk-abc123" not in result
        assert "secret456==" not in result

        # Structure should be preserved
        assert "db.example.com" in result
        assert "[REDACTED]" in result

    def test_handles_winrm_exception_with_password(self):
        """Test WinRM exception containing password is sanitized."""
        text = "WinRM authentication failed: 401 Unauthorized for user admin with password VmP@ssw0rd!"
        result = sanitize_for_log(text)
        assert "VmP@ssw0rd!" not in result
        assert "[REDACTED]" in result

    def test_handles_playwright_exception_with_credentials(self):
        """Test Playwright exception with M365 credentials is sanitized."""
        text = "Login failed for user@tenant.com with password M365P@ss123!"
        result = sanitize_for_log(text)
        assert "M365P@ss123!" not in result
        assert "[REDACTED]" in result

    def test_handles_azure_sdk_exception_with_connection_string(self):
        """Test Azure SDK exception with connection string is sanitized."""
        text = "Storage error: DefaultEndpointsProtocol=https;AccountKey=abc123==;EndpointSuffix=core.windows.net"
        result = sanitize_for_log(text)
        assert "abc123==" not in result
        assert "AccountKey=[REDACTED]" in result


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_string(self):
        """Test empty string is handled."""
        assert sanitize_error("") == ""
        assert sanitize_url("") == ""
        assert sanitize_connection_string("") == ""

    def test_none_handling(self):
        """Test None is handled gracefully."""
        # Should convert to string
        assert sanitize_error(None) == "None"

    def test_very_long_password(self):
        """Test very long password is fully redacted."""
        long_password = "a" * 1000
        error_msg = f"Password: {long_password}"
        result = sanitize_error(error_msg)
        assert long_password not in result
        assert "[REDACTED]" in result

    def test_special_characters_in_password(self):
        """Test password with special characters is redacted."""
        error_msg = "Auth failed: password=P@ss!w0rd#$%"
        result = sanitize_error(error_msg)
        assert "P@ss!w0rd#$%" not in result
        assert "[REDACTED]" in result

    def test_case_insensitive_detection(self):
        """Test case-insensitive detection of sensitive patterns."""
        error_msg = "Failed: PASSWORD=secret123 and API_KEY=key456"
        result = sanitize_error(error_msg)
        assert "secret123" not in result
        assert "key456" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
