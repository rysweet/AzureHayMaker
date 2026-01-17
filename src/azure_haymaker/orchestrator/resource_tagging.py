"""Resource tagging utilities for multi-tenant Azure resource isolation.

Single responsibility: Generate and validate consistent Azure resource tags.

This module provides standardized tagging for Azure resources to enable:
- Multi-tenant resource isolation via TenantId tag
- Cost attribution per execution via ExecutionId tag
- Resource identification via AzureHayMaker-managed marker
- Scenario-based grouping via Scenario tag

Public API:
    generate_resource_tags: Build tag dict for Azure resources
    validate_tags: Check tags contain required keys
    sanitize_tag_value: Clean values for Azure compatibility
    REQUIRED_TAGS: List of mandatory tag keys
    MAX_TAG_VALUE_LENGTH: Azure limit (256)
"""

from datetime import UTC, datetime

# Constants for tag validation
REQUIRED_TAGS: list[str] = ["TenantId", "ExecutionId", "AzureHayMaker-managed"]
MAX_TAG_VALUE_LENGTH: int = 256


def generate_resource_tags(
    tenant_id: str,
    execution_id: str,
    scenario_name: str,
    additional_tags: dict[str, str] | None = None,
) -> dict[str, str]:
    """Generate standardized resource tags for Azure resources.

    Creates a tag dictionary that ensures multi-tenant resource isolation
    and enables cost tracking per tenant and execution.

    Args:
        tenant_id: Azure tenant ID for multi-tenant isolation
        execution_id: Unique execution run identifier
        scenario_name: Optional scenario name for grouping
        additional_tags: Optional custom tags (cannot override required tags)

    Returns:
        Dictionary of tag key-value pairs for Azure resources

    Raises:
        ValueError: If tenant_id, execution_id, or scenario_name is empty
        TypeError: If tenant_id or execution_id is None

    Example:
        >>> tags = generate_resource_tags(
        ...     tenant_id="tenant-123",
        ...     execution_id="exec-456",
        ...     scenario_name="compute-01"
        ... )
        >>> assert tags["TenantId"] == "tenant-123"
    """
    # Validate required parameters - None check first for proper TypeError
    if tenant_id is None:
        raise TypeError("tenant_id cannot be None")
    if execution_id is None:
        raise TypeError("execution_id cannot be None")

    # Validate non-empty strings
    if not tenant_id.strip():
        raise ValueError("tenant_id cannot be empty")
    if not execution_id.strip():
        raise ValueError("execution_id cannot be empty")
    if not scenario_name.strip():
        raise ValueError("scenario_name cannot be empty")

    # Build base tags with required fields
    tags: dict[str, str] = {
        "TenantId": tenant_id,
        "ExecutionId": execution_id,
        "AzureHayMaker-managed": "true",
        "CreatedAt": datetime.now(UTC).isoformat(),
        "Scenario": scenario_name,
    }

    # Add additional tags if provided, but do NOT override required tags
    if additional_tags:
        # Required keys that cannot be overridden (security: prevent tag spoofing)
        # Use case-insensitive comparison to prevent bypass via "tenantid" vs "TenantId"
        protected_keys = {"TenantId", "ExecutionId", "AzureHayMaker-managed"}
        protected_keys_lower = {k.lower() for k in protected_keys}

        for key, value in additional_tags.items():
            if key.lower() not in protected_keys_lower:
                tags[key] = value

    return tags


def validate_tags(tags: dict[str, str]) -> tuple[bool, list[str]]:
    """Validate tags contain all required keys with non-empty values.

    Checks that the tag dictionary meets Azure HayMaker requirements:
    - All required tags are present
    - No empty values for required tags
    - Values do not exceed Azure's 256 character limit

    Args:
        tags: Dictionary of tag key-value pairs to validate

    Returns:
        Tuple of (is_valid, list_of_errors) where:
        - is_valid: True if all validations pass
        - list_of_errors: List of validation error messages

    Example:
        >>> is_valid, errors = validate_tags({"TenantId": "t1", ...})
        >>> if not is_valid:
        ...     print("Validation errors:", errors)
    """
    errors: list[str] = []

    # Check for required tags
    for required_tag in REQUIRED_TAGS:
        if required_tag not in tags:
            errors.append(f"Missing required tag: {required_tag}")
        else:
            # Check for empty values
            value = tags[required_tag]
            # Handle non-string values gracefully
            if not isinstance(value, str):
                value = str(value) if value is not None else ""

            if not value.strip():
                errors.append(f"Tag '{required_tag}' has empty value")
            elif len(value) > MAX_TAG_VALUE_LENGTH:
                errors.append(
                    f"Tag '{required_tag}' value exceeds {MAX_TAG_VALUE_LENGTH} characters"
                )

    is_valid = len(errors) == 0
    return (is_valid, errors)


def sanitize_tag_value(value: str) -> str:
    """Sanitize tag value for Azure compatibility.

    Cleans tag values to ensure they meet Azure requirements:
    - Maximum 256 characters (truncated if longer)
    - No control characters (removed)
    - Leading/trailing whitespace stripped

    Args:
        value: Raw tag value to sanitize

    Returns:
        Sanitized tag value safe for Azure

    Example:
        >>> sanitize_tag_value("  test\\x00value  ")
        'testvalue'
    """
    # Strip leading/trailing whitespace
    sanitized = value.strip()

    # Remove control characters (ASCII 0-31)
    sanitized = "".join(char for char in sanitized if ord(char) >= 32)

    # Truncate to max length
    if len(sanitized) > MAX_TAG_VALUE_LENGTH:
        sanitized = sanitized[:MAX_TAG_VALUE_LENGTH]

    return sanitized


__all__ = [
    "generate_resource_tags",
    "validate_tags",
    "sanitize_tag_value",
    "REQUIRED_TAGS",
    "MAX_TAG_VALUE_LENGTH",
]
