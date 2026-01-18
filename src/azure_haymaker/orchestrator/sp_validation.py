"""Input validation and security checks for Service Principal operations.

This module provides input sanitization and validation functions to prevent
injection attacks and ensure data integrity in Service Principal management.

Philosophy:
- Single responsibility: Input validation only
- Security-first approach
- Standard library only (no external dependencies beyond type hints)
"""


def sanitize_odata_value(value: str) -> str:
    """Sanitize input for OData/Graph API query filters to prevent injection attacks.

    OData query filters are vulnerable to injection if user input is directly
    interpolated. This function escapes single quotes according to OData standard.

    Args:
        value: Input string to sanitize

    Returns:
        Sanitized string safe for use in OData filters

    Example:
        >>> sanitize_odata_value("O'Brien")
        "O''Brien"
        >>> sanitize_odata_value("Normal name")
        "Normal name"
    """
    # Escape single quotes by doubling them (OData standard)
    return value.replace("'", "''")


__all__ = ["sanitize_odata_value"]
