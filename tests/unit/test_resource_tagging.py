"""Unit tests for resource_tagging module - TDD approach.

These tests define the expected behavior for the resource tagging module
that will implement multi-tenant resource isolation via Azure tags.

Testing Pyramid:
- 60% Unit tests (tag generation, validation, sanitization)
- 30% Integration tests (full tagging workflow)
- 10% E2E tests (marked skip for CI - real Azure calls)

Tests WILL FAIL initially - the implementation doesn't exist yet.
"""

from datetime import UTC, datetime

import pytest

# These imports will fail until the module is created
# This is expected TDD behavior - tests first, implementation second


class TestResourceTaggingConstants:
    """Tests for resource tagging constants.

    Verifies that the module exports the required constants for
    multi-tenant resource isolation.
    """

    def test_required_tags_constant_exists(self):
        """Test that REQUIRED_TAGS constant is defined.

        REQUIRED_TAGS should list the minimum required tags for
        multi-tenant resource isolation per Issue #126.
        """
        from azure_haymaker.orchestrator.resource_tagging import REQUIRED_TAGS

        assert isinstance(REQUIRED_TAGS, (list, tuple, frozenset))
        assert len(REQUIRED_TAGS) >= 3  # At minimum: TenantId, ExecutionId, AzureHayMaker-managed

    def test_required_tags_includes_tenant_id(self):
        """Test that TenantId is a required tag.

        TenantId enables filtering and cost attribution per tenant.
        """
        from azure_haymaker.orchestrator.resource_tagging import REQUIRED_TAGS

        assert "TenantId" in REQUIRED_TAGS

    def test_required_tags_includes_execution_id(self):
        """Test that ExecutionId is a required tag.

        ExecutionId enables tracking resources per execution run.
        """
        from azure_haymaker.orchestrator.resource_tagging import REQUIRED_TAGS

        assert "ExecutionId" in REQUIRED_TAGS

    def test_required_tags_includes_managed_marker(self):
        """Test that AzureHayMaker-managed tag is required.

        This marker enables querying all resources managed by HayMaker.
        """
        from azure_haymaker.orchestrator.resource_tagging import REQUIRED_TAGS

        assert "AzureHayMaker-managed" in REQUIRED_TAGS

    def test_max_tag_value_length_constant_exists(self):
        """Test that MAX_TAG_VALUE_LENGTH constant is defined.

        Azure has a 256 character limit for tag values.
        """
        from azure_haymaker.orchestrator.resource_tagging import MAX_TAG_VALUE_LENGTH

        assert isinstance(MAX_TAG_VALUE_LENGTH, int)
        assert MAX_TAG_VALUE_LENGTH == 256  # Azure limit


class TestGenerateResourceTags:
    """Tests for generate_resource_tags function.

    This function creates a standardized tag dictionary for Azure resources.
    """

    def test_generate_resource_tags_returns_dict(self):
        """Test that generate_resource_tags returns a dictionary."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        result = generate_resource_tags(
            tenant_id="tenant-123",
            execution_id="exec-456",
            scenario_name="compute-01",
        )

        assert isinstance(result, dict)

    def test_generate_resource_tags_includes_tenant_id(self):
        """Test that generated tags include TenantId."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        result = generate_resource_tags(
            tenant_id="tenant-abc",
            execution_id="exec-123",
            scenario_name="storage-01",
        )

        assert "TenantId" in result
        assert result["TenantId"] == "tenant-abc"

    def test_generate_resource_tags_includes_execution_id(self):
        """Test that generated tags include ExecutionId."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        result = generate_resource_tags(
            tenant_id="tenant-123",
            execution_id="exec-unique-id",
            scenario_name="network-01",
        )

        assert "ExecutionId" in result
        assert result["ExecutionId"] == "exec-unique-id"

    def test_generate_resource_tags_includes_scenario_name(self):
        """Test that generated tags include Scenario tag."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        result = generate_resource_tags(
            tenant_id="tenant-123",
            execution_id="exec-456",
            scenario_name="identity-test-01",
        )

        assert "Scenario" in result
        assert result["Scenario"] == "identity-test-01"

    def test_generate_resource_tags_includes_managed_marker(self):
        """Test that generated tags include AzureHayMaker-managed marker."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        result = generate_resource_tags(
            tenant_id="tenant-123",
            execution_id="exec-456",
            scenario_name="compute-01",
        )

        assert "AzureHayMaker-managed" in result
        assert result["AzureHayMaker-managed"] == "true"

    def test_generate_resource_tags_includes_timestamp(self):
        """Test that generated tags include CreatedAt timestamp."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        before = datetime.now(UTC).isoformat()
        result = generate_resource_tags(
            tenant_id="tenant-123",
            execution_id="exec-456",
            scenario_name="compute-01",
        )
        after = datetime.now(UTC).isoformat()

        assert "CreatedAt" in result
        # Verify timestamp is in ISO format and within expected range
        assert before <= result["CreatedAt"] <= after

    def test_generate_resource_tags_with_additional_tags(self):
        """Test that additional custom tags can be included."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        additional = {
            "Environment": "testing",
            "CostCenter": "engineering",
        }

        result = generate_resource_tags(
            tenant_id="tenant-123",
            execution_id="exec-456",
            scenario_name="compute-01",
            additional_tags=additional,
        )

        assert result["Environment"] == "testing"
        assert result["CostCenter"] == "engineering"
        # Required tags should still be present
        assert "TenantId" in result
        assert "ExecutionId" in result

    def test_generate_resource_tags_additional_tags_cannot_override_required(self):
        """Test that additional tags cannot override required tags.

        Security: Prevent tag spoofing by ensuring required tags
        cannot be overwritten by additional_tags.
        """
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        additional = {
            "TenantId": "malicious-tenant",  # Attempt to spoof
            "ExecutionId": "fake-exec",
        }

        result = generate_resource_tags(
            tenant_id="real-tenant",
            execution_id="real-exec",
            scenario_name="compute-01",
            additional_tags=additional,
        )

        # Required tags should be preserved
        assert result["TenantId"] == "real-tenant"
        assert result["ExecutionId"] == "real-exec"

    def test_generate_resource_tags_empty_tenant_id_raises(self):
        """Test that empty tenant_id raises ValueError."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        with pytest.raises(ValueError, match="tenant_id"):
            generate_resource_tags(
                tenant_id="",
                execution_id="exec-456",
                scenario_name="compute-01",
            )

    def test_generate_resource_tags_empty_execution_id_raises(self):
        """Test that empty execution_id raises ValueError."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        with pytest.raises(ValueError, match="execution_id"):
            generate_resource_tags(
                tenant_id="tenant-123",
                execution_id="",
                scenario_name="compute-01",
            )

    def test_generate_resource_tags_empty_scenario_name_raises(self):
        """Test that empty scenario_name raises ValueError."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        with pytest.raises(ValueError, match="scenario_name"):
            generate_resource_tags(
                tenant_id="tenant-123",
                execution_id="exec-456",
                scenario_name="",
            )

    def test_generate_resource_tags_none_values_raise(self):
        """Test that None values for required params raise TypeError/ValueError."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        with pytest.raises((TypeError, ValueError)):
            generate_resource_tags(
                tenant_id=None,  # type: ignore[arg-type]
                execution_id="exec-456",
                scenario_name="compute-01",
            )


class TestValidateTags:
    """Tests for validate_tags function.

    This function validates that a tag dictionary meets requirements.
    Returns (is_valid, list_of_errors).
    """

    def test_validate_tags_returns_tuple(self):
        """Test that validate_tags returns (bool, list) tuple."""
        from azure_haymaker.orchestrator.resource_tagging import validate_tags

        tags = {
            "TenantId": "tenant-123",
            "ExecutionId": "exec-456",
            "Scenario": "compute-01",
            "AzureHayMaker-managed": "true",
        }

        result = validate_tags(tags)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)

    def test_validate_tags_valid_minimal(self):
        """Test validation passes with minimal required tags."""
        from azure_haymaker.orchestrator.resource_tagging import validate_tags

        tags = {
            "TenantId": "tenant-123",
            "ExecutionId": "exec-456",
            "Scenario": "compute-01",
            "AzureHayMaker-managed": "true",
        }

        is_valid, errors = validate_tags(tags)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_tags_missing_tenant_id_fails(self):
        """Test validation fails when TenantId is missing."""
        from azure_haymaker.orchestrator.resource_tagging import validate_tags

        tags = {
            "ExecutionId": "exec-456",
            "Scenario": "compute-01",
            "AzureHayMaker-managed": "true",
        }

        is_valid, errors = validate_tags(tags)

        assert is_valid is False
        assert any("TenantId" in error for error in errors)

    def test_validate_tags_missing_execution_id_fails(self):
        """Test validation fails when ExecutionId is missing."""
        from azure_haymaker.orchestrator.resource_tagging import validate_tags

        tags = {
            "TenantId": "tenant-123",
            "Scenario": "compute-01",
            "AzureHayMaker-managed": "true",
        }

        is_valid, errors = validate_tags(tags)

        assert is_valid is False
        assert any("ExecutionId" in error for error in errors)

    def test_validate_tags_missing_managed_marker_fails(self):
        """Test validation fails when AzureHayMaker-managed is missing."""
        from azure_haymaker.orchestrator.resource_tagging import validate_tags

        tags = {
            "TenantId": "tenant-123",
            "ExecutionId": "exec-456",
            "Scenario": "compute-01",
        }

        is_valid, errors = validate_tags(tags)

        assert is_valid is False
        assert any("AzureHayMaker-managed" in error for error in errors)

    def test_validate_tags_empty_value_fails(self):
        """Test validation fails when a required tag has empty value."""
        from azure_haymaker.orchestrator.resource_tagging import validate_tags

        tags = {
            "TenantId": "",  # Empty value
            "ExecutionId": "exec-456",
            "Scenario": "compute-01",
            "AzureHayMaker-managed": "true",
        }

        is_valid, errors = validate_tags(tags)

        assert is_valid is False
        assert any("TenantId" in error and "empty" in error.lower() for error in errors)

    def test_validate_tags_value_too_long_fails(self):
        """Test validation fails when tag value exceeds 256 chars."""
        from azure_haymaker.orchestrator.resource_tagging import validate_tags

        tags = {
            "TenantId": "a" * 300,  # Too long
            "ExecutionId": "exec-456",
            "Scenario": "compute-01",
            "AzureHayMaker-managed": "true",
        }

        is_valid, errors = validate_tags(tags)

        assert is_valid is False
        assert any("TenantId" in error and "256" in error for error in errors)

    def test_validate_tags_multiple_errors(self):
        """Test validation returns all errors, not just the first."""
        from azure_haymaker.orchestrator.resource_tagging import validate_tags

        tags = {
            "Scenario": "compute-01",
            # Missing: TenantId, ExecutionId, AzureHayMaker-managed
        }

        is_valid, errors = validate_tags(tags)

        assert is_valid is False
        assert len(errors) >= 3  # At least 3 missing tags

    def test_validate_tags_empty_dict_fails(self):
        """Test validation fails with empty tag dictionary."""
        from azure_haymaker.orchestrator.resource_tagging import validate_tags

        is_valid, errors = validate_tags({})

        assert is_valid is False
        assert len(errors) >= 3  # Missing all required tags


class TestSanitizeTagValue:
    """Tests for sanitize_tag_value function.

    This function cleans tag values to ensure Azure compatibility.
    """

    def test_sanitize_tag_value_returns_string(self):
        """Test that sanitize_tag_value returns a string."""
        from azure_haymaker.orchestrator.resource_tagging import sanitize_tag_value

        result = sanitize_tag_value("test-value")

        assert isinstance(result, str)

    def test_sanitize_tag_value_unchanged_for_valid(self):
        """Test that valid values pass through unchanged."""
        from azure_haymaker.orchestrator.resource_tagging import sanitize_tag_value

        result = sanitize_tag_value("valid-tag-value-123")

        assert result == "valid-tag-value-123"

    def test_sanitize_tag_value_truncates_long_values(self):
        """Test that long values are truncated to 256 chars."""
        from azure_haymaker.orchestrator.resource_tagging import sanitize_tag_value

        long_value = "a" * 300

        result = sanitize_tag_value(long_value)

        assert len(result) == 256

    def test_sanitize_tag_value_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        from azure_haymaker.orchestrator.resource_tagging import sanitize_tag_value

        result = sanitize_tag_value("  value-with-spaces  ")

        assert result == "value-with-spaces"

    def test_sanitize_tag_value_handles_unicode(self):
        """Test that unicode characters are handled properly."""
        from azure_haymaker.orchestrator.resource_tagging import sanitize_tag_value

        # Azure tags support unicode
        result = sanitize_tag_value("value-with-unicode-")

        assert "value-with-unicode" in result

    def test_sanitize_tag_value_removes_control_chars(self):
        """Test that control characters are removed."""
        from azure_haymaker.orchestrator.resource_tagging import sanitize_tag_value

        result = sanitize_tag_value("value\x00with\x1fcontrol")

        assert "\x00" not in result
        assert "\x1f" not in result
        assert result == "valuewithcontrol"

    def test_sanitize_tag_value_preserves_hyphens_underscores(self):
        """Test that hyphens and underscores are preserved."""
        from azure_haymaker.orchestrator.resource_tagging import sanitize_tag_value

        result = sanitize_tag_value("my-tag_value-123")

        assert result == "my-tag_value-123"

    def test_sanitize_tag_value_empty_string(self):
        """Test handling of empty string input."""
        from azure_haymaker.orchestrator.resource_tagging import sanitize_tag_value

        result = sanitize_tag_value("")

        assert result == ""

    def test_sanitize_tag_value_only_whitespace(self):
        """Test handling of whitespace-only input."""
        from azure_haymaker.orchestrator.resource_tagging import sanitize_tag_value

        result = sanitize_tag_value("   ")

        assert result == ""


class TestTagIntegration:
    """Integration tests for the tagging workflow.

    Tests that combine multiple functions to verify end-to-end behavior.
    """

    def test_generated_tags_pass_validation(self):
        """Test that tags from generate_resource_tags pass validation."""
        from azure_haymaker.orchestrator.resource_tagging import (
            generate_resource_tags,
            validate_tags,
        )

        tags = generate_resource_tags(
            tenant_id="tenant-integration-test",
            execution_id="exec-integration-123",
            scenario_name="integration-scenario",
        )

        is_valid, errors = validate_tags(tags)

        assert is_valid is True
        assert len(errors) == 0

    def test_sanitized_values_pass_validation(self):
        """Test that sanitized values are valid for tags."""
        from azure_haymaker.orchestrator.resource_tagging import (
            sanitize_tag_value,
            validate_tags,
        )

        # Create tags with sanitized values
        long_tenant = "a" * 300
        tags = {
            "TenantId": sanitize_tag_value(long_tenant),
            "ExecutionId": sanitize_tag_value("exec-456"),
            "Scenario": sanitize_tag_value("compute-01"),
            "AzureHayMaker-managed": "true",
        }

        is_valid, errors = validate_tags(tags)

        assert is_valid is True
        assert len(errors) == 0

    def test_round_trip_preserves_values(self):
        """Test that generate -> validate preserves all values."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        tenant_id = "tenant-round-trip"
        execution_id = "exec-round-trip"
        scenario = "scenario-round-trip"

        tags = generate_resource_tags(
            tenant_id=tenant_id,
            execution_id=execution_id,
            scenario_name=scenario,
        )

        assert tags["TenantId"] == tenant_id
        assert tags["ExecutionId"] == execution_id
        assert tags["Scenario"] == scenario


class TestResourceTaggingEdgeCases:
    """Edge case tests for resource tagging.

    Tests boundary conditions and unusual inputs.
    """

    def test_generate_tags_with_special_chars_in_tenant_id(self):
        """Test handling of special characters in tenant ID.

        Azure tenant IDs are GUIDs, but we should handle edge cases.
        """
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        # GUID format tenant ID
        result = generate_resource_tags(
            tenant_id="12345678-1234-1234-1234-123456789abc",
            execution_id="exec-456",
            scenario_name="compute-01",
        )

        assert result["TenantId"] == "12345678-1234-1234-1234-123456789abc"

    def test_generate_tags_with_hyphenated_scenario_name(self):
        """Test handling of hyphenated scenario names."""
        from azure_haymaker.orchestrator.resource_tagging import generate_resource_tags

        result = generate_resource_tags(
            tenant_id="tenant-123",
            execution_id="exec-456",
            scenario_name="compute-linux-vm-01",
        )

        assert result["Scenario"] == "compute-linux-vm-01"

    def test_validate_tags_with_non_string_values(self):
        """Test validation handles non-string tag values gracefully."""
        from azure_haymaker.orchestrator.resource_tagging import validate_tags

        tags = {
            "TenantId": "tenant-123",
            "ExecutionId": 12345,  # type: ignore[dict-item] # Integer instead of string
            "Scenario": "compute-01",
            "AzureHayMaker-managed": "true",
        }

        # Should either convert to string or report error
        is_valid, errors = validate_tags(tags)

        # The function should handle this gracefully
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_sanitize_max_length_boundary(self):
        """Test sanitize at exactly 256 character boundary."""
        from azure_haymaker.orchestrator.resource_tagging import sanitize_tag_value

        # Exactly 256 chars - should pass unchanged
        exact_256 = "a" * 256
        result = sanitize_tag_value(exact_256)
        assert len(result) == 256

        # 257 chars - should be truncated
        over_256 = "a" * 257
        result = sanitize_tag_value(over_256)
        assert len(result) == 256


# E2E tests marked skip for CI - require real Azure resources
class TestResourceTaggingE2E:
    """End-to-end tests for resource tagging.

    These tests verify tagging behavior against real Azure resources.
    Marked as skip for CI - run manually in development.
    """

    @pytest.mark.skip(reason="E2E test - requires real Azure resources")
    def test_apply_tags_to_real_resource(self):
        """Test applying generated tags to a real Azure resource.

        This test would:
        1. Generate tags
        2. Create a test resource (e.g., resource group)
        3. Apply tags
        4. Verify tags are queryable via Azure Resource Graph
        5. Clean up test resource
        """
        pass

    @pytest.mark.skip(reason="E2E test - requires real Azure resources")
    def test_cost_query_by_tenant_tag(self):
        """Test querying costs filtered by TenantId tag.

        This test would:
        1. Create tagged resources
        2. Wait for cost data (24h delay)
        3. Query costs with TenantId filter
        4. Verify cost isolation
        """
        pass
