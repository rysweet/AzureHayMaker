"""CLI-specific constants for Azure HayMaker.

Constants used by the command-line interface including output formatting,
exit codes, and duration parsing.
"""

# ============================================================================
# Output Constants
# ============================================================================

DEFAULT_LIST_LIMIT: int = 10
"""Default number of items to list."""

DEFAULT_LOG_LINES: int = 100
"""Default number of log lines to show."""

DEFAULT_OUTPUT_FORMAT: str = "table"
"""Default output format (table, json, yaml)."""

# ============================================================================
# Exit Codes
# ============================================================================

EXIT_SUCCESS: int = 0
"""Successful execution."""

EXIT_ERROR: int = 1
"""General error."""

EXIT_CONFIG_ERROR: int = 2
"""Configuration error."""

EXIT_NOT_FOUND: int = 3
"""Resource not found."""

EXIT_CANCELLED: int = 4
"""Operation cancelled by user."""

# ============================================================================
# Duration Parsing
# ============================================================================

DURATION_UNITS: dict[str, int] = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 604800,
}
"""Mapping of duration unit suffixes to seconds."""

# ============================================================================
# Display Constants
# ============================================================================

TABLE_COLUMN_PADDING: int = 2
"""Padding between table columns."""

MAX_COLUMN_WIDTH: int = 50
"""Maximum width for table columns."""

TRUNCATE_SUFFIX: str = "..."
"""Suffix for truncated values."""


__all__ = [
    # Output
    "DEFAULT_LIST_LIMIT",
    "DEFAULT_LOG_LINES",
    "DEFAULT_OUTPUT_FORMAT",
    # Exit codes
    "EXIT_SUCCESS",
    "EXIT_ERROR",
    "EXIT_CONFIG_ERROR",
    "EXIT_NOT_FOUND",
    "EXIT_CANCELLED",
    # Duration
    "DURATION_UNITS",
    # Display
    "TABLE_COLUMN_PADDING",
    "MAX_COLUMN_WIDTH",
    "TRUNCATE_SUFFIX",
]
