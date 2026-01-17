"""Output formatting utilities for the CLI.

Provides table and JSON formatting for command output.
Small, focused functions following the single-responsibility principle.

Addresses Issue #22: Refactor long CLI methods.
"""

import json
from typing import Any

from ..constants import MAX_COLUMN_WIDTH, TABLE_COLUMN_PADDING, TRUNCATE_SUFFIX


def format_table(data: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    """Format data as a table.

    Args:
        data: List of dictionaries to format
        columns: Column names to include (uses all keys if None)

    Returns:
        Formatted table string
    """
    if not data:
        return "No data to display."

    # Determine columns
    if columns is None:
        columns = list(data[0].keys())

    # Calculate column widths
    widths = _calculate_column_widths(data, columns)

    # Build table
    lines = []

    # Header
    header = _format_row(columns, widths)
    lines.append(header)

    # Separator
    separator = _format_separator(widths)
    lines.append(separator)

    # Data rows
    for row in data:
        values = [str(row.get(col, "")) for col in columns]
        lines.append(_format_row(values, widths))

    return "\n".join(lines)


def format_json(data: Any, indent: int = 2) -> str:
    """Format data as JSON.

    Args:
        data: Data to format
        indent: Indentation level

    Returns:
        JSON string
    """
    return json.dumps(data, indent=indent, default=str)


def _calculate_column_widths(data: list[dict[str, Any]], columns: list[str]) -> dict[str, int]:
    """Calculate optimal column widths.

    Args:
        data: Data rows
        columns: Column names

    Returns:
        Dictionary mapping column name to width
    """
    widths = {}
    for col in columns:
        # Start with header width
        max_width = len(col)

        # Check data values
        for row in data:
            value = str(row.get(col, ""))
            max_width = max(max_width, len(value))

        # Cap at maximum
        widths[col] = min(max_width, MAX_COLUMN_WIDTH)

    return widths


def _format_row(values: list[str], widths: dict[str, int]) -> str:
    """Format a single row.

    Args:
        values: Cell values
        widths: Column widths

    Returns:
        Formatted row string
    """
    cells = []
    for value, width in zip(values, widths.values(), strict=False):
        cells.append(_truncate(value, width).ljust(width))

    padding = " " * TABLE_COLUMN_PADDING
    return padding.join(cells)


def _format_separator(widths: dict[str, int]) -> str:
    """Format a separator line.

    Args:
        widths: Column widths

    Returns:
        Separator string
    """
    cells = ["-" * width for width in widths.values()]
    padding = " " * TABLE_COLUMN_PADDING
    return padding.join(cells)


def _truncate(value: str, max_length: int) -> str:
    """Truncate a value if too long.

    Args:
        value: Value to truncate
        max_length: Maximum length

    Returns:
        Truncated value
    """
    if len(value) <= max_length:
        return value

    return value[: max_length - len(TRUNCATE_SUFFIX)] + TRUNCATE_SUFFIX


def format_status_line(run_id: str, status: str, phase: str) -> str:
    """Format a single status line.

    Args:
        run_id: Deployment run ID
        status: Current status
        phase: Current phase

    Returns:
        Formatted status line
    """
    status_icon = _get_status_icon(status)
    return f"{status_icon} {run_id}: {status} ({phase})"


def _get_status_icon(status: str) -> str:
    """Get an icon for the status.

    Args:
        status: Status string

    Returns:
        Status icon character
    """
    icons = {
        "running": "*",
        "completed": "+",
        "failed": "!",
        "stopped": "-",
        "pending": "?",
    }
    return icons.get(status.lower(), "?")


__all__ = [
    "format_table",
    "format_json",
    "format_status_line",
]
