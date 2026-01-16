"""Trace context for cross-container propagation.

Provides a dataclass for serializing trace context to environment variables,
enabling trace correlation across container boundaries.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class TraceContext:
    """Trace context for cross-container propagation.

    Contains the essential trace identifiers needed to correlate spans
    across service boundaries. Can be serialized to/from environment
    variables for container-to-container propagation.

    Attributes:
        trace_id: W3C trace ID (32 hex chars)
        span_id: W3C span ID (16 hex chars)
        run_id: HayMaker orchestration run ID
        tenant_id: Optional Azure tenant ID for cross-tenant scenarios
        scenario_name: Optional scenario name for filtering/grouping
    """

    trace_id: str
    span_id: str
    run_id: str
    tenant_id: str | None = None
    scenario_name: str | None = None

    # Environment variable names for serialization
    _ENV_TRACE_ID: str = field(default="HAYMAKER_TRACE_ID", init=False, repr=False)
    _ENV_SPAN_ID: str = field(default="HAYMAKER_SPAN_ID", init=False, repr=False)
    _ENV_RUN_ID: str = field(default="HAYMAKER_RUN_ID", init=False, repr=False)
    _ENV_TENANT_ID: str = field(default="HAYMAKER_TENANT_ID", init=False, repr=False)
    _ENV_SCENARIO_NAME: str = field(default="HAYMAKER_SCENARIO_NAME", init=False, repr=False)

    def to_env_vars(self) -> dict[str, str]:
        """Convert trace context to environment variables.

        Returns:
            Dictionary of environment variable name -> value pairs.
            Only includes non-None values.

        Example:
            >>> ctx = TraceContext(trace_id="abc123", span_id="def456", run_id="run-1")
            >>> env_vars = ctx.to_env_vars()
            >>> env_vars["HAYMAKER_TRACE_ID"]
            'abc123'
        """
        env_vars = {
            self._ENV_TRACE_ID: self.trace_id,
            self._ENV_SPAN_ID: self.span_id,
            self._ENV_RUN_ID: self.run_id,
        }

        if self.tenant_id is not None:
            env_vars[self._ENV_TENANT_ID] = self.tenant_id

        if self.scenario_name is not None:
            env_vars[self._ENV_SCENARIO_NAME] = self.scenario_name

        return env_vars

    @classmethod
    def from_env(cls) -> TraceContext | None:
        """Create trace context from environment variables.

        Reads trace context from the standard HAYMAKER_* environment variables.
        Returns None if required fields (trace_id, span_id, run_id) are missing.

        Returns:
            TraceContext if all required env vars are present, None otherwise.

        Example:
            >>> import os
            >>> os.environ["HAYMAKER_TRACE_ID"] = "abc123"
            >>> os.environ["HAYMAKER_SPAN_ID"] = "def456"
            >>> os.environ["HAYMAKER_RUN_ID"] = "run-1"
            >>> ctx = TraceContext.from_env()
            >>> ctx.trace_id
            'abc123'
        """
        trace_id = os.environ.get("HAYMAKER_TRACE_ID")
        span_id = os.environ.get("HAYMAKER_SPAN_ID")
        run_id = os.environ.get("HAYMAKER_RUN_ID")

        # Required fields
        if not all([trace_id, span_id, run_id]):
            return None

        return cls(
            trace_id=trace_id,  # type: ignore[arg-type] - validated above
            span_id=span_id,  # type: ignore[arg-type] - validated above
            run_id=run_id,  # type: ignore[arg-type] - validated above
            tenant_id=os.environ.get("HAYMAKER_TENANT_ID"),
            scenario_name=os.environ.get("HAYMAKER_SCENARIO_NAME"),
        )

    @classmethod
    def create_new(cls, run_id: str | None = None, **kwargs) -> TraceContext:
        """Create a new trace context with generated IDs.

        Generates new W3C-compliant trace_id and span_id values.

        Args:
            run_id: Optional run ID. If not provided, generates a new UUID.
            **kwargs: Additional fields (tenant_id, scenario_name)

        Returns:
            New TraceContext with generated IDs.

        Example:
            >>> ctx = TraceContext.create_new(run_id="my-run")
            >>> len(ctx.trace_id)
            32
            >>> len(ctx.span_id)
            16
        """
        # Generate W3C-compliant IDs
        # trace_id: 32 hex chars (128 bits)
        # span_id: 16 hex chars (64 bits)
        trace_id = uuid4().hex + uuid4().hex[:16]  # 32 chars total
        span_id = uuid4().hex[:16]  # 16 chars

        return cls(
            trace_id=trace_id[:32],  # Ensure exactly 32 chars
            span_id=span_id,
            run_id=run_id or str(uuid4()),
            **kwargs,
        )
