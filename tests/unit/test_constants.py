"""Tests for constants modules.

Verifies that magic numbers are properly extracted to constants modules.
"""


class TestProjectConstants:
    """Test project-wide constants."""

    def test_constants_module_exists(self) -> None:
        """Test that constants module exists and is importable."""
        from azure_haymaker import constants

        assert constants is not None

    def test_timeout_constants(self) -> None:
        """Test timeout constants are defined."""
        from azure_haymaker.constants import (
            DEFAULT_API_TIMEOUT_SECONDS,
            DEFAULT_OPERATION_TIMEOUT_SECONDS,
            MAILBOX_PROVISIONING_TIMEOUT_SECONDS,
        )

        assert DEFAULT_API_TIMEOUT_SECONDS > 0
        assert DEFAULT_OPERATION_TIMEOUT_SECONDS > 0
        assert MAILBOX_PROVISIONING_TIMEOUT_SECONDS > 0

    def test_retry_constants(self) -> None:
        """Test retry constants are defined."""
        from azure_haymaker.constants import (
            DEFAULT_RETRY_COUNT,
            DEFAULT_RETRY_DELAY_SECONDS,
            MAX_RETRY_COUNT,
        )

        assert DEFAULT_RETRY_COUNT > 0
        assert DEFAULT_RETRY_DELAY_SECONDS > 0
        assert MAX_RETRY_COUNT >= DEFAULT_RETRY_COUNT

    def test_worker_constants(self) -> None:
        """Test worker-related constants are defined."""
        from azure_haymaker.constants import (
            DEFAULT_WORKERS_PER_DEPLOYMENT,
            MAX_WORKERS_PER_DEPLOYMENT,
            PASSWORD_LENGTH,
            RATE_LIMIT_DELAY_SECONDS,
        )

        assert DEFAULT_WORKERS_PER_DEPLOYMENT > 0
        assert MAX_WORKERS_PER_DEPLOYMENT >= DEFAULT_WORKERS_PER_DEPLOYMENT
        assert PASSWORD_LENGTH >= 16  # Minimum secure password length
        assert RATE_LIMIT_DELAY_SECONDS > 0

    def test_activity_constants(self) -> None:
        """Test activity-related constants are defined."""
        from azure_haymaker.constants import (
            DEFAULT_DURATION_HOURS,
            DEFAULT_EMAIL_PER_HOUR,
            DEFAULT_MEETINGS_PER_DAY,
            DEFAULT_TEAMS_MESSAGES_PER_HOUR,
        )

        assert DEFAULT_DURATION_HOURS > 0
        assert DEFAULT_EMAIL_PER_HOUR > 0
        assert DEFAULT_MEETINGS_PER_DAY >= 0
        assert DEFAULT_TEAMS_MESSAGES_PER_HOUR >= 0

    def test_container_constants(self) -> None:
        """Test container-related constants are defined."""
        from azure_haymaker.constants import (
            CONTAINER_MEMORY_GB,
            CONTAINER_TIMEOUT_HOURS,
            DEFAULT_BATCH_SIZE,
        )

        assert CONTAINER_MEMORY_GB > 0
        assert CONTAINER_TIMEOUT_HOURS > 0
        assert DEFAULT_BATCH_SIZE > 0

    def test_ttl_constants(self) -> None:
        """Test TTL constants are defined."""
        from azure_haymaker.constants import (
            EVENT_TTL_SECONDS,
            SECRET_ROTATION_DAYS,
        )

        assert EVENT_TTL_SECONDS > 0
        assert SECRET_ROTATION_DAYS > 0


class TestCliConstants:
    """Test CLI-specific constants."""

    def test_cli_constants_module_exists(self) -> None:
        """Test that CLI constants module exists."""
        from azure_haymaker.cli import constants

        assert constants is not None

    def test_output_constants(self) -> None:
        """Test output-related constants."""
        from azure_haymaker.cli.constants import (
            DEFAULT_LIST_LIMIT,
            DEFAULT_LOG_LINES,
            DEFAULT_OUTPUT_FORMAT,
        )

        assert DEFAULT_LIST_LIMIT > 0
        assert DEFAULT_LOG_LINES > 0
        assert DEFAULT_OUTPUT_FORMAT in ("table", "json", "yaml")

    def test_exit_code_constants(self) -> None:
        """Test exit code constants."""
        from azure_haymaker.cli.constants import (
            EXIT_CANCELLED,
            EXIT_CONFIG_ERROR,
            EXIT_ERROR,
            EXIT_NOT_FOUND,
            EXIT_SUCCESS,
        )

        assert EXIT_SUCCESS == 0
        assert EXIT_ERROR == 1
        assert EXIT_CONFIG_ERROR == 2
        assert EXIT_NOT_FOUND == 3
        assert EXIT_CANCELLED == 4

    def test_duration_parsing_constants(self) -> None:
        """Test duration parsing constants."""
        from azure_haymaker.cli.constants import DURATION_UNITS

        assert "h" in DURATION_UNITS  # hours
        assert "d" in DURATION_UNITS  # days
        assert DURATION_UNITS["h"] == 3600
        assert DURATION_UNITS["d"] == 86400
