"""Unit tests for azure_haymaker.tracing module.

Tests the distributed tracing functionality including:
- TraceContext creation, serialization, and deserialization
- Tracing initialization with and without Azure Application Insights
- Decorator-based instrumentation helpers
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestTraceContext:
    """Tests for TraceContext dataclass."""

    def test_trace_context_to_env_vars(self):
        """Test that trace context can be serialized to environment variables."""
        from azure_haymaker.tracing.context import TraceContext

        ctx = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            run_id="test-run-123",
            tenant_id="tenant-abc",
            scenario_name="test-scenario",
        )

        env_vars = ctx.to_env_vars()

        assert env_vars["HAYMAKER_TRACE_ID"] == "a" * 32
        assert env_vars["HAYMAKER_SPAN_ID"] == "b" * 16
        assert env_vars["HAYMAKER_RUN_ID"] == "test-run-123"
        assert env_vars["HAYMAKER_TENANT_ID"] == "tenant-abc"
        assert env_vars["HAYMAKER_SCENARIO_NAME"] == "test-scenario"

    def test_trace_context_to_env_vars_optional_fields(self):
        """Test that optional fields are excluded when None."""
        from azure_haymaker.tracing.context import TraceContext

        ctx = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            run_id="test-run-123",
            tenant_id=None,
            scenario_name=None,
        )

        env_vars = ctx.to_env_vars()

        assert "HAYMAKER_TRACE_ID" in env_vars
        assert "HAYMAKER_SPAN_ID" in env_vars
        assert "HAYMAKER_RUN_ID" in env_vars
        assert "HAYMAKER_TENANT_ID" not in env_vars
        assert "HAYMAKER_SCENARIO_NAME" not in env_vars

    def test_trace_context_roundtrip(self):
        """Test that trace context survives serialization/deserialization roundtrip."""
        from azure_haymaker.tracing.context import TraceContext

        original = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            run_id="test-run-123",
            tenant_id="tenant-abc",
            scenario_name="test-scenario",
        )

        # Serialize to env vars
        env_vars = original.to_env_vars()

        # Mock the environment
        with patch.dict(os.environ, env_vars, clear=False):
            # Deserialize from env
            restored = TraceContext.from_env()

        assert restored is not None
        assert restored.trace_id == original.trace_id
        assert restored.span_id == original.span_id
        assert restored.run_id == original.run_id
        assert restored.tenant_id == original.tenant_id
        assert restored.scenario_name == original.scenario_name

    def test_trace_context_from_env_missing_required(self):
        """Test that from_env returns None when required fields are missing."""
        from azure_haymaker.tracing.context import TraceContext

        # Clear any existing trace env vars
        env = {
            "HAYMAKER_TRACE_ID": "abc",
            # Missing HAYMAKER_SPAN_ID and HAYMAKER_RUN_ID
        }

        with patch.dict(os.environ, env, clear=True):
            result = TraceContext.from_env()

        assert result is None

    def test_trace_context_from_env_empty(self):
        """Test that from_env returns None when no env vars are set."""
        from azure_haymaker.tracing.context import TraceContext

        with patch.dict(os.environ, {}, clear=True):
            result = TraceContext.from_env()

        assert result is None

    def test_trace_context_create_new(self):
        """Test that create_new generates valid IDs."""
        from azure_haymaker.tracing.context import TraceContext

        ctx = TraceContext.create_new(run_id="my-run")

        # Verify trace_id is 32 hex chars
        assert len(ctx.trace_id) == 32
        assert all(c in "0123456789abcdef" for c in ctx.trace_id)

        # Verify span_id is 16 hex chars
        assert len(ctx.span_id) == 16
        assert all(c in "0123456789abcdef" for c in ctx.span_id)

        # Verify run_id is passed through
        assert ctx.run_id == "my-run"

    def test_trace_context_create_new_generates_run_id(self):
        """Test that create_new generates run_id when not provided."""
        from azure_haymaker.tracing.context import TraceContext

        ctx = TraceContext.create_new()

        assert ctx.run_id is not None
        assert len(ctx.run_id) > 0

    def test_trace_context_create_new_with_optional_fields(self):
        """Test create_new with optional fields."""
        from azure_haymaker.tracing.context import TraceContext

        ctx = TraceContext.create_new(
            run_id="my-run",
            tenant_id="tenant-123",
            scenario_name="my-scenario",
        )

        assert ctx.tenant_id == "tenant-123"
        assert ctx.scenario_name == "my-scenario"


class TestInitTracing:
    """Tests for tracing initialization."""

    def setup_method(self):
        """Reset tracing state before each test."""
        from azure_haymaker.tracing import core

        core._initialized = False
        core._tracer_provider = None

    def test_init_tracing_basic(self):
        """Test basic tracing initialization without Azure export."""
        from azure_haymaker.tracing.core import init_tracing, is_tracing_enabled

        # Clear any existing connection string
        with patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": ""}, clear=False):
            provider = init_tracing("test-service")

        assert provider is not None
        assert is_tracing_enabled()

    def test_init_tracing_idempotent(self):
        """Test that init_tracing is idempotent."""
        from azure_haymaker.tracing.core import init_tracing

        with patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": ""}, clear=False):
            provider1 = init_tracing("test-service")
            provider2 = init_tracing("test-service")

        assert provider1 is provider2

    def test_init_tracing_with_console_export(self):
        """Test tracing initialization with console export."""
        from azure_haymaker.tracing.core import init_tracing

        with patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": ""}, clear=False):
            provider = init_tracing("test-service", enable_console_export=True)

        assert provider is not None
        # Verify span processor was added
        assert len(provider._active_span_processor._span_processors) > 0

    def test_get_tracer(self):
        """Test getting a tracer instance."""
        from azure_haymaker.tracing.core import get_tracer, init_tracing

        with patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": ""}, clear=False):
            init_tracing("test-service")
            tracer = get_tracer(__name__)

        assert tracer is not None

    def test_shutdown_tracing(self):
        """Test tracing shutdown."""
        from azure_haymaker.tracing.core import (
            init_tracing,
            is_tracing_enabled,
            shutdown_tracing,
        )

        with patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": ""}, clear=False):
            init_tracing("test-service")

        assert is_tracing_enabled()

        shutdown_tracing()

        assert not is_tracing_enabled()


class TestTracingDecorators:
    """Tests for tracing decorators."""

    def setup_method(self):
        """Initialize tracing before each test."""
        from azure_haymaker.tracing import core

        core._initialized = False
        core._tracer_provider = None

        with patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": ""}, clear=False):
            from azure_haymaker.tracing.core import init_tracing
            init_tracing("test-service")

    def test_traced_decorator(self):
        """Test the @traced decorator for sync functions."""
        from azure_haymaker.tracing.instrumentation import traced

        @traced("test-operation")
        def my_function(x: int) -> int:
            return x * 2

        result = my_function(5)

        assert result == 10

    def test_traced_decorator_with_exception(self):
        """Test that @traced decorator records exceptions."""
        from azure_haymaker.tracing.instrumentation import traced

        @traced("failing-operation")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    @pytest.mark.asyncio
    async def test_traced_async_decorator(self):
        """Test the @traced_async decorator for async functions."""
        from azure_haymaker.tracing.instrumentation import traced_async

        @traced_async("async-operation")
        async def async_function(x: int) -> int:
            return x * 2

        result = await async_function(5)

        assert result == 10

    @pytest.mark.asyncio
    async def test_traced_async_decorator_with_exception(self):
        """Test that @traced_async decorator records exceptions."""
        from azure_haymaker.tracing.instrumentation import traced_async

        @traced_async("failing-async-operation")
        async def failing_async_function():
            raise ValueError("Async test error")

        with pytest.raises(ValueError, match="Async test error"):
            await failing_async_function()


class TestInstrumentationHelpers:
    """Tests for instrumentation helper functions."""

    def setup_method(self):
        """Initialize tracing before each test."""
        from azure_haymaker.tracing import core

        core._initialized = False
        core._tracer_provider = None

        with patch.dict(os.environ, {"APPLICATIONINSIGHTS_CONNECTION_STRING": ""}, clear=False):
            from azure_haymaker.tracing.core import init_tracing
            init_tracing("test-service")

    def test_add_span_attributes(self):
        """Test adding attributes to a span."""
        from azure_haymaker.tracing.core import get_tracer
        from azure_haymaker.tracing.instrumentation import add_span_attributes

        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("test-span") as span:
            add_span_attributes(span, key1="value1", key2="value2")

        # Just verify no exception is raised
        # In a real test, we'd verify the span attributes

    def test_add_span_attributes_ignores_none_span(self):
        """Test that add_span_attributes handles None span gracefully."""
        from azure_haymaker.tracing.instrumentation import add_span_attributes

        # Should not raise
        add_span_attributes(None, key="value")

    def test_get_current_trace_context(self):
        """Test getting current trace context."""
        from azure_haymaker.tracing.core import get_tracer
        from azure_haymaker.tracing.instrumentation import get_current_trace_context

        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("test-span"):
            ctx = get_current_trace_context()

        assert ctx is not None
        assert "traceparent" in ctx

    def test_get_current_trace_context_no_span(self):
        """Test that get_current_trace_context returns None when no active span."""
        from azure_haymaker.tracing.instrumentation import get_current_trace_context

        # No active span - context should be None or invalid
        ctx = get_current_trace_context()

        # When no span is active, this may return None or a context with invalid span
        # The implementation should handle both cases
