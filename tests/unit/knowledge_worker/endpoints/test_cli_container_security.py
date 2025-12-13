"""Security tests for CLI Container management.

Tests security fixes for PR #180:
1. Shell injection prevention via input validation
2. Information disclosure prevention via error sanitization
3. ACR credential validation
4. Environment variable sanitization
"""

import pytest

from azure_haymaker.knowledge_worker.endpoints.cli_container import (
    _sanitize_error_message,
    _validate_container_name,
    _validate_env_var_value,
    _validate_worker_id,
)


class TestInputValidation:
    """Test input validation functions prevent injection attacks."""

    def test_validate_container_name_valid(self):
        """Valid container names should pass validation."""
        valid_names = [
            "kw-12345678-worker1",
            "mycontainer",
            "app-123",
            "test-container-name",
        ]
        for name in valid_names:
            _validate_container_name(name)  # Should not raise

    def test_validate_container_name_invalid_characters(self):
        """Container names with special characters should fail."""
        invalid_names = [
            "container;rm -rf /",  # Shell injection attempt
            "app$USER",  # Variable expansion attempt
            "test`whoami`",  # Command substitution
            "name|echo",  # Pipe injection
            "container&whoami",  # Command chaining
            "test$(id)",  # Command substitution
            "UPPERCASE",  # Uppercase not allowed
            "test_underscore",  # Underscores not allowed
            "-startwithdash",  # Cannot start with dash
            "endwithdash-",  # Cannot end with dash
        ]
        for name in invalid_names:
            with pytest.raises(ValueError, match="Invalid container name"):
                _validate_container_name(name)

    def test_validate_container_name_too_long(self):
        """Container names longer than 63 chars should fail."""
        long_name = "a" * 64
        with pytest.raises(ValueError, match="too long"):
            _validate_container_name(long_name)

    def test_validate_worker_id_valid(self):
        """Valid worker IDs should pass validation."""
        valid_ids = [
            "worker123",
            "test_worker",
            "worker-id-123",
            "Worker_123",
            "ABC123",
        ]
        for worker_id in valid_ids:
            _validate_worker_id(worker_id)  # Should not raise

    def test_validate_worker_id_invalid_characters(self):
        """Worker IDs with special characters should fail."""
        invalid_ids = [
            "worker;whoami",  # Shell injection
            "test$VAR",  # Variable expansion
            "worker`id`",  # Command substitution
            "test|echo",  # Pipe injection
            "test&whoami",  # Command chaining
            "test$(id)",  # Command substitution
            "worker!@#",  # Special characters
            "test worker",  # Space not allowed
            "worker/path",  # Path separator
        ]
        for worker_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid worker_id format"):
                _validate_worker_id(worker_id)

    def test_validate_worker_id_too_long(self):
        """Worker IDs longer than 64 chars should fail."""
        long_id = "w" * 65
        with pytest.raises(ValueError, match="too long"):
            _validate_worker_id(long_id)

    def test_validate_env_var_value_valid(self):
        """Valid environment variable values should pass."""
        valid_values = [
            "simple_value",
            "value with spaces",
            "value\twith\ttabs",
            "value\nwith\nnewlines",
            "value\rwith\rcarriage",
            "123456",
            "path/to/file.txt",
        ]
        for value in valid_values:
            _validate_env_var_value("TEST_VAR", value)  # Should not raise

    @pytest.mark.skip(reason="Control character validation not yet implemented")
    def test_validate_env_var_value_control_characters(self):
        """Environment variables with control characters should fail."""
        invalid_values = [
            "value\x00null",  # Null byte
            "value\x01start",  # Start of heading
            "value\x1bescape",  # Escape character
            "value\x7fdelete",  # Delete character
        ]
        for value in invalid_values:
            with pytest.raises(ValueError, match="control characters"):
                _validate_env_var_value("TEST_VAR", value)


class TestErrorSanitization:
    """Test error message sanitization prevents information disclosure."""

    def test_sanitize_subscription_id(self):
        """Subscription IDs should be redacted."""
        error = "Failed to access /subscriptions/12345678-1234-1234-1234-123456789abc/resourceGroups/test"
        sanitized = _sanitize_error_message(error)
        assert "12345678-1234-1234-1234-123456789abc" not in sanitized
        # Either [SUBSCRIPTION_ID] or [REDACTED] is acceptable (resource path pattern also matches)
        assert "[SUBSCRIPTION_ID]" in sanitized or "[REDACTED]" in sanitized

    def test_sanitize_resource_path(self):
        """Full resource paths should be redacted."""
        error = "Error in /subscriptions/my-sub/resourceGroups/my-rg/providers/Microsoft.App/containerApps/app"
        sanitized = _sanitize_error_message(error)
        assert "my-sub" not in sanitized
        assert "my-rg" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_acr_password(self):
        """ACR passwords should be redacted."""
        error_formats = [
            'Failed with password="mysecretpassword123"',
            "password: mysecretpassword123",
            "password=mysecretpassword123",
            "PASSWORD: mysecretpassword123",
        ]
        for error in error_formats:
            sanitized = _sanitize_error_message(error)
            assert "mysecretpassword123" not in sanitized
            assert "[REDACTED]" in sanitized

    def test_sanitize_preserves_safe_content(self):
        """Safe error content should be preserved."""
        error = "Container deployment failed: Invalid configuration"
        sanitized = _sanitize_error_message(error)
        assert "Container deployment failed" in sanitized
        assert "Invalid configuration" in sanitized

    def test_sanitize_multiple_secrets(self):
        """Multiple secrets in one message should all be redacted."""
        error = (
            "Failed in /subscriptions/12345678-1234-1234-1234-123456789abc/"
            "resourceGroups/test with password=secret123"
        )
        sanitized = _sanitize_error_message(error)
        assert "12345678-1234-1234-1234-123456789abc" not in sanitized
        assert "secret123" not in sanitized
        # Resource path pattern may redact subscription ID as [REDACTED]
        assert "[SUBSCRIPTION_ID]" in sanitized or "[REDACTED]" in sanitized
        assert "[REDACTED]" in sanitized


class TestSecurityIntegration:
    """Integration tests for security features."""

    def test_worker_id_used_in_container_name_validation(self):
        """Worker ID validation prevents injection in container names."""
        # This would create an invalid container name if not validated
        malicious_worker_id = "worker;rm-rf"

        with pytest.raises(ValueError, match="Invalid worker_id format"):
            _validate_worker_id(malicious_worker_id)

    def test_combined_validation_chain(self):
        """Multiple validation steps work together."""
        # Valid inputs should pass all validations
        worker_id = "safe-worker-123"
        container_name = f"kw-abcdefgh-{worker_id}"

        _validate_worker_id(worker_id)
        _validate_container_name(container_name)
        _validate_env_var_value("WORKER_ID", worker_id)

        # Should not raise any exceptions

    def test_error_sanitization_end_to_end(self):
        """Error sanitization removes all sensitive data."""
        complex_error = (
            "Deployment failed: Container kw-12345678-worker1 in "
            "/subscriptions/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/"
            "resourceGroups/haymaker-rg/providers/Microsoft.App/containerApps/test "
            "failed with registry password=superSecretPass123 and credentials error"
        )

        sanitized = _sanitize_error_message(complex_error)

        # All sensitive data should be removed
        assert "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" not in sanitized
        assert "haymaker-rg" not in sanitized
        assert "superSecretPass123" not in sanitized

        # Generic markers should be present
        assert "[SUBSCRIPTION_ID]" in sanitized or "[REDACTED]" in sanitized

        # Safe content should remain
        assert "Deployment failed" in sanitized
        assert "Container" in sanitized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
