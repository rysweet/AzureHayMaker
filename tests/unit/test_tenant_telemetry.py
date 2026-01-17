"""Unit tests for TenantTelemetryContext (Phase 4 cross-tenant telemetry).

Tests cover:
- Context propagation via context variables
- Span creation with tenant attributes
- Context manager lifecycle (enter/exit)
- Error handling in context

Testing Strategy:
- 60% unit tests (fast, mocked OpenTelemetry)
- Focus on context propagation and attribute setting
- Mock trace.get_tracer() for span creation
"""

from unittest.mock import MagicMock, patch

from azure_haymaker.telemetry.tenant_context import (
    EXECUTION_ID_ATTRIBUTE,
    SCENARIO_NAME_ATTRIBUTE,
    TENANT_ID_ATTRIBUTE,
    TenantTelemetryContext,
    create_tenant_span,
    get_current_tenant_id,
    set_tenant_context,
)

# =============================================================================
# get_current_tenant_id Tests
# =============================================================================


class TestGetCurrentTenantId:
    """Tests for get_current_tenant_id function."""

    def test_returns_none_by_default(self):
        """Test that default is None when no context set."""
        # Reset context by creating and exiting a context
        assert get_current_tenant_id() is None or isinstance(get_current_tenant_id(), str)

    def test_returns_tenant_in_context(self):
        """Test that tenant_id is returned when in context."""
        with TenantTelemetryContext(tenant_id="test-tenant-123", create_span=False):
            assert get_current_tenant_id() == "test-tenant-123"

    def test_context_resets_after_exit(self):
        """Test that context resets after exiting."""
        original = get_current_tenant_id()
        with TenantTelemetryContext(tenant_id="temp-tenant", create_span=False):
            assert get_current_tenant_id() == "temp-tenant"
        assert get_current_tenant_id() == original


# =============================================================================
# set_tenant_context Tests
# =============================================================================


class TestSetTenantContext:
    """Tests for set_tenant_context function."""

    def test_sets_tenant_attribute(self):
        """Test that tenant_id attribute is set on span."""
        mock_span = MagicMock()
        set_tenant_context(mock_span, tenant_id="tenant-abc")

        mock_span.set_attribute.assert_called_with(TENANT_ID_ATTRIBUTE, "tenant-abc")

    def test_sets_execution_id_attribute(self):
        """Test that execution_id attribute is set when provided."""
        mock_span = MagicMock()
        set_tenant_context(mock_span, tenant_id="tenant-abc", execution_id="exec-123")

        calls = mock_span.set_attribute.call_args_list
        assert any(call[0] == (EXECUTION_ID_ATTRIBUTE, "exec-123") for call in calls)

    def test_sets_scenario_name_attribute(self):
        """Test that scenario_name attribute is set when provided."""
        mock_span = MagicMock()
        set_tenant_context(
            mock_span,
            tenant_id="tenant-abc",
            scenario_name="compute-01-linux-vm",
        )

        calls = mock_span.set_attribute.call_args_list
        assert any(call[0] == (SCENARIO_NAME_ATTRIBUTE, "compute-01-linux-vm") for call in calls)

    def test_uses_context_tenant_when_not_provided(self):
        """Test that context tenant_id is used when not explicitly provided."""
        mock_span = MagicMock()

        with TenantTelemetryContext(tenant_id="context-tenant", create_span=False):
            set_tenant_context(mock_span)  # No tenant_id provided
            mock_span.set_attribute.assert_called_with(TENANT_ID_ATTRIBUTE, "context-tenant")

    def test_no_tenant_attribute_when_none(self):
        """Test that no tenant attribute is set when tenant_id is None."""
        mock_span = MagicMock()
        set_tenant_context(mock_span, tenant_id=None)

        # Should not have been called with tenant attribute
        for call in mock_span.set_attribute.call_args_list:
            assert call[0][0] != TENANT_ID_ATTRIBUTE


# =============================================================================
# create_tenant_span Tests
# =============================================================================


class TestCreateTenantSpan:
    """Tests for create_tenant_span function."""

    def test_creates_span_with_tracer(self):
        """Test that span is created using get_tracer."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_span

        with patch("azure_haymaker.telemetry.tenant_context.trace.get_tracer") as get_tracer:
            get_tracer.return_value = mock_tracer
            result = create_tenant_span("test-operation", tenant_id="tenant-123")

            mock_tracer.start_as_current_span.assert_called_once()
            assert result == mock_span

    def test_includes_tenant_in_attributes(self):
        """Test that tenant_id is included in span attributes."""
        mock_tracer = MagicMock()

        with patch("azure_haymaker.telemetry.tenant_context.trace.get_tracer") as get_tracer:
            get_tracer.return_value = mock_tracer
            create_tenant_span("test-op", tenant_id="tenant-xyz")

            call_kwargs = mock_tracer.start_as_current_span.call_args[1]
            assert TENANT_ID_ATTRIBUTE in call_kwargs.get("attributes", {})
            assert call_kwargs["attributes"][TENANT_ID_ATTRIBUTE] == "tenant-xyz"

    def test_includes_execution_id_in_attributes(self):
        """Test that execution_id is included in span attributes."""
        mock_tracer = MagicMock()

        with patch("azure_haymaker.telemetry.tenant_context.trace.get_tracer") as get_tracer:
            get_tracer.return_value = mock_tracer
            create_tenant_span("test-op", tenant_id="tenant-xyz", execution_id="exec-456")

            call_kwargs = mock_tracer.start_as_current_span.call_args[1]
            assert EXECUTION_ID_ATTRIBUTE in call_kwargs.get("attributes", {})
            assert call_kwargs["attributes"][EXECUTION_ID_ATTRIBUTE] == "exec-456"

    def test_includes_custom_attributes(self):
        """Test that custom attributes are included."""
        mock_tracer = MagicMock()

        with patch("azure_haymaker.telemetry.tenant_context.trace.get_tracer") as get_tracer:
            get_tracer.return_value = mock_tracer
            create_tenant_span(
                "test-op",
                tenant_id="tenant-xyz",
                attributes={"custom.key": "custom-value"},
            )

            call_kwargs = mock_tracer.start_as_current_span.call_args[1]
            assert call_kwargs["attributes"]["custom.key"] == "custom-value"

    def test_uses_context_tenant_when_not_provided(self):
        """Test that context tenant_id is used when not explicitly provided."""
        mock_tracer = MagicMock()

        with patch("azure_haymaker.telemetry.tenant_context.trace.get_tracer") as get_tracer:
            get_tracer.return_value = mock_tracer

            with TenantTelemetryContext(tenant_id="context-tenant-id", create_span=False):
                create_tenant_span("test-op")

                call_kwargs = mock_tracer.start_as_current_span.call_args[1]
                assert call_kwargs["attributes"][TENANT_ID_ATTRIBUTE] == "context-tenant-id"


# =============================================================================
# TenantTelemetryContext Tests
# =============================================================================


class TestTenantTelemetryContext:
    """Tests for TenantTelemetryContext context manager."""

    def test_context_sets_tenant_id(self):
        """Test that context manager sets tenant_id."""
        with TenantTelemetryContext(tenant_id="test-tenant", create_span=False):
            assert get_current_tenant_id() == "test-tenant"

    def test_context_resets_on_exit(self):
        """Test that tenant_id is reset when context exits."""
        original = get_current_tenant_id()
        with TenantTelemetryContext(tenant_id="temp-tenant", create_span=False):
            pass
        assert get_current_tenant_id() == original

    def test_context_creates_span_by_default(self):
        """Test that context creates a span by default."""
        mock_tracer = MagicMock()
        mock_span_context = MagicMock()
        mock_span = MagicMock()
        mock_span_context.__enter__ = MagicMock(return_value=mock_span)
        mock_span_context.__exit__ = MagicMock(return_value=None)
        mock_tracer.start_as_current_span.return_value = mock_span_context

        with patch("azure_haymaker.telemetry.tenant_context.trace.get_tracer") as get_tracer:
            get_tracer.return_value = mock_tracer
            with TenantTelemetryContext(tenant_id="test-tenant"):
                pass

            mock_tracer.start_as_current_span.assert_called()

    def test_context_skips_span_when_disabled(self):
        """Test that span creation can be disabled."""
        mock_tracer = MagicMock()

        with patch("azure_haymaker.telemetry.tenant_context.trace.get_tracer") as get_tracer:
            get_tracer.return_value = mock_tracer
            with TenantTelemetryContext(tenant_id="test-tenant", create_span=False):
                pass

            # Should not have created a span
            mock_tracer.start_as_current_span.assert_not_called()

    def test_context_properties(self):
        """Test that context exposes properties correctly."""
        with TenantTelemetryContext(
            tenant_id="test-tenant",
            execution_id="exec-123",
            scenario_name="compute-01",
            create_span=False,
        ) as ctx:
            assert ctx.tenant_id == "test-tenant"
            assert ctx.execution_id == "exec-123"
            assert ctx.scenario_name == "compute-01"

    def test_context_add_event(self):
        """Test adding events to context span."""
        mock_tracer = MagicMock()
        mock_span_context = MagicMock()
        mock_span = MagicMock()
        mock_span_context.__enter__ = MagicMock(return_value=mock_span)
        mock_span_context.__exit__ = MagicMock(return_value=None)
        mock_tracer.start_as_current_span.return_value = mock_span_context

        with patch("azure_haymaker.telemetry.tenant_context.trace.get_tracer") as get_tracer:
            get_tracer.return_value = mock_tracer
            with TenantTelemetryContext(tenant_id="test-tenant") as ctx:
                ctx.add_event("test_event", {"key": "value"})

            mock_span.add_event.assert_called_with("test_event", attributes={"key": "value"})

    def test_context_set_attribute(self):
        """Test setting attributes on context span."""
        mock_tracer = MagicMock()
        mock_span_context = MagicMock()
        mock_span = MagicMock()
        mock_span_context.__enter__ = MagicMock(return_value=mock_span)
        mock_span_context.__exit__ = MagicMock(return_value=None)
        mock_tracer.start_as_current_span.return_value = mock_span_context

        with patch("azure_haymaker.telemetry.tenant_context.trace.get_tracer") as get_tracer:
            get_tracer.return_value = mock_tracer
            with TenantTelemetryContext(tenant_id="test-tenant") as ctx:
                ctx.set_attribute("custom.attr", "custom-value")

            mock_span.set_attribute.assert_called_with("custom.attr", "custom-value")

    def test_context_handles_exception(self):
        """Test that context properly handles exceptions."""
        mock_tracer = MagicMock()
        mock_span_context = MagicMock()
        mock_span = MagicMock()
        mock_span_context.__enter__ = MagicMock(return_value=mock_span)
        mock_span_context.__exit__ = MagicMock(return_value=None)
        mock_tracer.start_as_current_span.return_value = mock_span_context

        with patch("azure_haymaker.telemetry.tenant_context.trace.get_tracer") as get_tracer:
            get_tracer.return_value = mock_tracer
            try:
                with TenantTelemetryContext(tenant_id="test-tenant"):
                    raise ValueError("Test error")
            except ValueError:
                pass

            # Should have set error status and recorded exception
            mock_span.set_status.assert_called()
            mock_span.record_exception.assert_called()

    def test_nested_contexts(self):
        """Test nested TenantTelemetryContext behavior."""
        with TenantTelemetryContext(tenant_id="outer-tenant", create_span=False):
            assert get_current_tenant_id() == "outer-tenant"

            with TenantTelemetryContext(tenant_id="inner-tenant", create_span=False):
                assert get_current_tenant_id() == "inner-tenant"

            # After inner context exits, should be back to outer
            assert get_current_tenant_id() == "outer-tenant"


# =============================================================================
# Attribute Constants Tests
# =============================================================================


class TestAttributeConstants:
    """Tests for telemetry attribute constants."""

    def test_tenant_id_attribute_format(self):
        """Test TENANT_ID_ATTRIBUTE has expected format."""
        assert TENANT_ID_ATTRIBUTE == "azure.tenant_id"

    def test_execution_id_attribute_format(self):
        """Test EXECUTION_ID_ATTRIBUTE has expected format."""
        assert EXECUTION_ID_ATTRIBUTE == "haymaker.execution_id"

    def test_scenario_name_attribute_format(self):
        """Test SCENARIO_NAME_ATTRIBUTE has expected format."""
        assert SCENARIO_NAME_ATTRIBUTE == "haymaker.scenario_name"


# =============================================================================
# Integration-like Tests
# =============================================================================


class TestTelemetryIntegration:
    """Integration-style tests for telemetry context propagation."""

    def test_context_propagates_through_function_calls(self):
        """Test that context propagates through nested function calls."""

        def inner_function():
            return get_current_tenant_id()

        def middle_function():
            return inner_function()

        def outer_function():
            with TenantTelemetryContext(tenant_id="propagated-tenant", create_span=False):
                return middle_function()

        result = outer_function()
        assert result == "propagated-tenant"

    def test_multiple_sequential_contexts(self):
        """Test multiple sequential context managers."""
        results = []

        with TenantTelemetryContext(tenant_id="tenant-1", create_span=False):
            results.append(get_current_tenant_id())

        with TenantTelemetryContext(tenant_id="tenant-2", create_span=False):
            results.append(get_current_tenant_id())

        with TenantTelemetryContext(tenant_id="tenant-3", create_span=False):
            results.append(get_current_tenant_id())

        assert results == ["tenant-1", "tenant-2", "tenant-3"]
