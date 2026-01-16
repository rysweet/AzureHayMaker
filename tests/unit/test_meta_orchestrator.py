"""Unit tests for MetaOrchestrator (Phase 3 cross-tenant orchestration).

Tests cover:
- MetaOrchestrator.execute() fan-out to multiple tenants
- FanOutController parallelism limits via semaphore
- FailureMode.CONTINUE behavior (continue on tenant failure)
- FailureMode.FAIL_FAST behavior (abort on first failure)
- Abort propagation to skip remaining tenants

Testing Strategy:
- 60% unit tests (fast, mocked dependencies)
- Focus on FanOutController and MetaOrchestrator logic
- Mock run_orchestration_fn and tenant configs
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from azure_haymaker.orchestrator.meta_orchestrator import (
    FailureMode,
    FanOutController,
    MetaExecutionRequest,
    MetaExecutionResult,
    MetaOrchestrator,
    TenantExecutionState,
    TenantExecutionStatus,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_tenant_config():
    """Create a mock TenantConfig."""

    def _create(tenant_id: str, display_name: str | None = None, enabled: bool = True):
        mock = MagicMock()
        mock.tenant_id = tenant_id
        mock.display_name = display_name or f"Tenant {tenant_id}"
        mock.display = display_name or f"Tenant {tenant_id}"
        mock.subscription_id = f"sub-{tenant_id}"
        mock.resource_group = f"rg-{tenant_id}"
        mock.enabled = enabled
        return mock

    return _create


@pytest.fixture
def mock_orchestrator_config(mock_tenant_config):
    """Create a mock OrchestratorConfig with tenant registry."""
    config = MagicMock()
    config.tenants = {
        "tenant-1": mock_tenant_config("tenant-1", "Prod Tenant"),
        "tenant-2": mock_tenant_config("tenant-2", "Dev Tenant"),
        "tenant-3": mock_tenant_config("tenant-3", "Test Tenant"),
        "disabled-tenant": mock_tenant_config("disabled-tenant", "Disabled", enabled=False),
    }

    def get_tenant(tid):
        tenant = config.tenants.get(tid)
        if tenant and tenant.enabled:
            return tenant
        return None

    config.get_tenant_config = MagicMock(side_effect=get_tenant)
    return config


@pytest.fixture
def basic_request():
    """Create a basic MetaExecutionRequest."""
    return MetaExecutionRequest(
        tenant_ids=["tenant-1", "tenant-2"],
        scenarios=["compute-01-linux-vm"],
        duration_hours=1,
        max_parallelism=5,
        failure_mode=FailureMode.CONTINUE,
    )


@pytest.fixture
def mock_run_orchestration():
    """Create a mock run_orchestration function."""
    async def _run_orchestration(**kwargs):
        # Simulate successful execution
        await asyncio.sleep(0.01)  # Small delay to simulate work
        return {"status": "success"}

    return AsyncMock(side_effect=_run_orchestration)


# =============================================================================
# MetaExecutionRequest Tests
# =============================================================================


class TestMetaExecutionRequest:
    """Tests for MetaExecutionRequest model."""

    def test_create_basic_request(self):
        """Test creating a basic request with required fields."""
        request = MetaExecutionRequest(
            tenant_ids=["tenant-1", "tenant-2"],
        )
        assert len(request.tenant_ids) == 2
        assert request.failure_mode == FailureMode.CONTINUE  # Default
        assert request.max_parallelism == 10  # Default
        assert request.duration_hours == 8  # Default

    def test_request_with_all_options(self):
        """Test creating a request with all options specified."""
        request = MetaExecutionRequest(
            tenant_ids=["tenant-1"],
            scenarios=["compute-01"],
            scenario_count=5,
            duration_hours=4,
            max_parallelism=3,
            failure_mode=FailureMode.FAIL_FAST,
            skip_validation=True,
            tags={"env": "test"},
        )
        assert request.failure_mode == FailureMode.FAIL_FAST
        assert request.max_parallelism == 3
        assert request.skip_validation is True
        assert request.tags == {"env": "test"}

    def test_request_validates_tenant_ids(self):
        """Test that request requires at least one tenant."""
        with pytest.raises(ValueError):
            MetaExecutionRequest(tenant_ids=[])

    def test_request_validates_duration(self):
        """Test duration validation (1-24 hours)."""
        # Valid range
        request = MetaExecutionRequest(tenant_ids=["t1"], duration_hours=24)
        assert request.duration_hours == 24

        # Invalid range
        with pytest.raises(ValueError):
            MetaExecutionRequest(tenant_ids=["t1"], duration_hours=0)
        with pytest.raises(ValueError):
            MetaExecutionRequest(tenant_ids=["t1"], duration_hours=25)


class TestMetaExecutionResult:
    """Tests for MetaExecutionResult model."""

    def test_all_succeeded_property(self):
        """Test all_succeeded returns True when no failures."""
        result = MetaExecutionResult(
            meta_execution_id="test-123",
            started_at=datetime.now(UTC),
            total_tenants=2,
            succeeded_count=2,
            failed_count=0,
            skipped_count=0,
            failure_mode=FailureMode.CONTINUE,
        )
        assert result.all_succeeded is True

    def test_all_succeeded_false_on_failure(self):
        """Test all_succeeded returns False when there are failures."""
        result = MetaExecutionResult(
            meta_execution_id="test-123",
            started_at=datetime.now(UTC),
            total_tenants=2,
            succeeded_count=1,
            failed_count=1,
            skipped_count=0,
            failure_mode=FailureMode.CONTINUE,
        )
        assert result.all_succeeded is False

    def test_all_succeeded_false_on_skipped(self):
        """Test all_succeeded returns False when there are skipped tenants."""
        result = MetaExecutionResult(
            meta_execution_id="test-123",
            started_at=datetime.now(UTC),
            total_tenants=2,
            succeeded_count=1,
            failed_count=0,
            skipped_count=1,
            failure_mode=FailureMode.CONTINUE,
        )
        assert result.all_succeeded is False

    def test_duration_seconds_property(self):
        """Test duration calculation when completed."""
        started = datetime.now(UTC)
        completed = datetime.now(UTC)
        result = MetaExecutionResult(
            meta_execution_id="test-123",
            started_at=started,
            completed_at=completed,
            total_tenants=1,
            failure_mode=FailureMode.CONTINUE,
        )
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0

    def test_duration_seconds_none_when_incomplete(self):
        """Test duration is None when not completed."""
        result = MetaExecutionResult(
            meta_execution_id="test-123",
            started_at=datetime.now(UTC),
            completed_at=None,
            total_tenants=1,
            failure_mode=FailureMode.CONTINUE,
        )
        assert result.duration_seconds is None


# =============================================================================
# FanOutController Tests
# =============================================================================


class TestFanOutController:
    """Tests for FanOutController parallelism and execution."""

    @pytest.mark.asyncio
    async def test_parallelism_limit(self, mock_tenant_config, mock_orchestrator_config):
        """Test that semaphore limits concurrent executions."""
        max_parallelism = 2
        controller = FanOutController(max_parallelism=max_parallelism)

        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def tracking_run(**kwargs):
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)  # Simulate work
            async with lock:
                concurrent_count -= 1

        mock_run = AsyncMock(side_effect=tracking_run)

        tenants = [
            mock_tenant_config("tenant-1"),
            mock_tenant_config("tenant-2"),
            mock_tenant_config("tenant-3"),
            mock_tenant_config("tenant-4"),
        ]

        request = MetaExecutionRequest(
            tenant_ids=["tenant-1", "tenant-2", "tenant-3", "tenant-4"],
            max_parallelism=max_parallelism,
        )

        with patch(
            "azure_haymaker.orchestrator.meta_orchestrator.MultiTenantCredentialFactory"
        ) as mock_cred:
            mock_cred.get_credential_for_tenant.return_value = MagicMock()
            await controller.execute(
                config=mock_orchestrator_config,
                tenants=tenants,
                request=request,
                run_orchestration_fn=mock_run,
            )

        # Verify parallelism was respected
        assert max_concurrent <= max_parallelism

    @pytest.mark.asyncio
    async def test_all_tenants_executed(self, mock_tenant_config, mock_orchestrator_config):
        """Test that all tenants are executed."""
        controller = FanOutController(max_parallelism=5)
        executed_tenants = []

        async def track_execution(**kwargs):
            tenant_config = kwargs.get("tenant_config", {})
            executed_tenants.append(tenant_config.get("tenant_id"))

        mock_run = AsyncMock(side_effect=track_execution)

        tenants = [
            mock_tenant_config("tenant-1"),
            mock_tenant_config("tenant-2"),
            mock_tenant_config("tenant-3"),
        ]

        request = MetaExecutionRequest(tenant_ids=["tenant-1", "tenant-2", "tenant-3"])

        with patch(
            "azure_haymaker.orchestrator.meta_orchestrator.MultiTenantCredentialFactory"
        ) as mock_cred:
            mock_cred.get_credential_for_tenant.return_value = MagicMock()
            statuses = await controller.execute(
                config=mock_orchestrator_config,
                tenants=tenants,
                request=request,
                run_orchestration_fn=mock_run,
            )

        assert len(statuses) == 3
        assert len(executed_tenants) == 3

    @pytest.mark.asyncio
    async def test_continue_mode_handles_failure(
        self, mock_tenant_config, mock_orchestrator_config
    ):
        """Test CONTINUE mode continues after tenant failure."""
        controller = FanOutController(max_parallelism=5)
        execution_order = []

        async def failing_run(**kwargs):
            tenant_config = kwargs.get("tenant_config", {})
            tid = tenant_config.get("tenant_id")
            execution_order.append(tid)
            if tid == "tenant-2":
                raise RuntimeError("Simulated failure")

        mock_run = AsyncMock(side_effect=failing_run)

        tenants = [
            mock_tenant_config("tenant-1"),
            mock_tenant_config("tenant-2"),  # Will fail
            mock_tenant_config("tenant-3"),
        ]

        request = MetaExecutionRequest(
            tenant_ids=["tenant-1", "tenant-2", "tenant-3"],
            failure_mode=FailureMode.CONTINUE,
        )

        with patch(
            "azure_haymaker.orchestrator.meta_orchestrator.MultiTenantCredentialFactory"
        ) as mock_cred:
            mock_cred.get_credential_for_tenant.return_value = MagicMock()
            statuses = await controller.execute(
                config=mock_orchestrator_config,
                tenants=tenants,
                request=request,
                run_orchestration_fn=mock_run,
            )

        # All tenants should be executed
        assert len(execution_order) == 3

        # Check status states
        status_by_tenant = {s.tenant_id: s for s in statuses}
        assert status_by_tenant["tenant-1"].state == TenantExecutionState.COMPLETED
        assert status_by_tenant["tenant-2"].state == TenantExecutionState.FAILED
        assert status_by_tenant["tenant-3"].state == TenantExecutionState.COMPLETED

    @pytest.mark.asyncio
    async def test_fail_fast_mode_aborts(self, mock_tenant_config, mock_orchestrator_config):
        """Test FAIL_FAST mode aborts on first failure."""
        controller = FanOutController(max_parallelism=1)  # Sequential for predictable order
        execution_order = []

        async def failing_run(**kwargs):
            tenant_config = kwargs.get("tenant_config", {})
            tid = tenant_config.get("tenant_id")
            execution_order.append(tid)
            await asyncio.sleep(0.01)
            if tid == "tenant-1":
                raise RuntimeError("Simulated failure")

        mock_run = AsyncMock(side_effect=failing_run)

        tenants = [
            mock_tenant_config("tenant-1"),  # Will fail first
            mock_tenant_config("tenant-2"),
            mock_tenant_config("tenant-3"),
        ]

        request = MetaExecutionRequest(
            tenant_ids=["tenant-1", "tenant-2", "tenant-3"],
            failure_mode=FailureMode.FAIL_FAST,
            max_parallelism=1,
        )

        with patch(
            "azure_haymaker.orchestrator.meta_orchestrator.MultiTenantCredentialFactory"
        ) as mock_cred:
            mock_cred.get_credential_for_tenant.return_value = MagicMock()
            statuses = await controller.execute(
                config=mock_orchestrator_config,
                tenants=tenants,
                request=request,
                run_orchestration_fn=mock_run,
            )

        # Check that abort was triggered
        assert controller._abort_event.is_set()

        # Check status states - some should be skipped
        status_by_tenant = {s.tenant_id: s for s in statuses}
        assert status_by_tenant["tenant-1"].state == TenantExecutionState.FAILED
        # tenant-2 and tenant-3 should be either skipped or completed depending on timing


# =============================================================================
# MetaOrchestrator Tests
# =============================================================================


class TestMetaOrchestrator:
    """Tests for MetaOrchestrator main class."""

    def test_validate_tenants_all_valid(self, mock_orchestrator_config):
        """Test validate_tenants returns all tenants when all are valid."""
        valid, invalid = MetaOrchestrator.validate_tenants(
            mock_orchestrator_config,
            ["tenant-1", "tenant-2"],
        )
        assert len(valid) == 2
        assert len(invalid) == 0

    def test_validate_tenants_with_invalid(self, mock_orchestrator_config):
        """Test validate_tenants separates invalid tenant IDs."""
        valid, invalid = MetaOrchestrator.validate_tenants(
            mock_orchestrator_config,
            ["tenant-1", "nonexistent-tenant"],
        )
        assert len(valid) == 1
        assert valid[0].tenant_id == "tenant-1"
        assert len(invalid) == 1
        assert "nonexistent-tenant" in invalid

    def test_validate_tenants_with_disabled(self, mock_orchestrator_config):
        """Test validate_tenants excludes disabled tenants."""
        valid, invalid = MetaOrchestrator.validate_tenants(
            mock_orchestrator_config,
            ["tenant-1", "disabled-tenant"],
        )
        assert len(valid) == 1
        assert len(invalid) == 1
        assert "disabled-tenant" in invalid

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_orchestrator_config, mock_run_orchestration):
        """Test successful execution across multiple tenants."""
        request = MetaExecutionRequest(
            tenant_ids=["tenant-1", "tenant-2"],
            scenarios=["compute-01"],
        )

        with patch(
            "azure_haymaker.orchestrator.meta_orchestrator.MultiTenantCredentialFactory"
        ) as mock_cred:
            mock_cred.get_credential_for_tenant.return_value = MagicMock()
            result = await MetaOrchestrator.execute(
                mock_orchestrator_config,
                request,
                run_orchestration_fn=mock_run_orchestration,
            )

        assert isinstance(result, MetaExecutionResult)
        assert result.total_tenants == 2
        assert result.succeeded_count == 2
        assert result.failed_count == 0
        assert result.all_succeeded is True

    @pytest.mark.asyncio
    async def test_execute_no_valid_tenants_raises(self, mock_orchestrator_config):
        """Test that execute raises when no valid tenants found."""
        request = MetaExecutionRequest(
            tenant_ids=["nonexistent-1", "nonexistent-2"],
        )

        with pytest.raises(ValueError, match="No valid tenants found"):
            await MetaOrchestrator.execute(
                mock_orchestrator_config,
                request,
            )

    @pytest.mark.asyncio
    async def test_execute_adds_invalid_to_skipped(
        self, mock_orchestrator_config, mock_run_orchestration
    ):
        """Test that invalid tenant IDs are added to result as skipped."""
        request = MetaExecutionRequest(
            tenant_ids=["tenant-1", "nonexistent-tenant"],
        )

        with patch(
            "azure_haymaker.orchestrator.meta_orchestrator.MultiTenantCredentialFactory"
        ) as mock_cred:
            mock_cred.get_credential_for_tenant.return_value = MagicMock()
            result = await MetaOrchestrator.execute(
                mock_orchestrator_config,
                request,
                run_orchestration_fn=mock_run_orchestration,
            )

        assert result.total_tenants == 2
        assert result.succeeded_count == 1
        assert result.skipped_count == 1

        # Find the skipped status
        skipped = [s for s in result.tenant_statuses if s.state == TenantExecutionState.SKIPPED]
        assert len(skipped) == 1
        assert skipped[0].tenant_id == "nonexistent-tenant"

    @pytest.mark.asyncio
    async def test_execute_tracks_aborted_early(self, mock_orchestrator_config):
        """Test that aborted_early flag is set on FAIL_FAST abort."""
        call_count = 0

        async def failing_run(**kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            raise RuntimeError("Simulated failure")

        request = MetaExecutionRequest(
            tenant_ids=["tenant-1", "tenant-2", "tenant-3"],
            failure_mode=FailureMode.FAIL_FAST,
            max_parallelism=1,  # Sequential to ensure first fails first
        )

        with patch(
            "azure_haymaker.orchestrator.meta_orchestrator.MultiTenantCredentialFactory"
        ) as mock_cred:
            mock_cred.get_credential_for_tenant.return_value = MagicMock()
            result = await MetaOrchestrator.execute(
                mock_orchestrator_config,
                request,
                run_orchestration_fn=AsyncMock(side_effect=failing_run),
            )

        # Should have aborted early
        assert result.aborted_early is True
        assert result.failed_count >= 1


# =============================================================================
# TenantExecutionStatus Tests
# =============================================================================


class TestTenantExecutionStatus:
    """Tests for TenantExecutionStatus model."""

    def test_create_pending_status(self):
        """Test creating a pending status."""
        status = TenantExecutionStatus(
            tenant_id="tenant-123",
            tenant_display_name="Test Tenant",
        )
        assert status.state == TenantExecutionState.PENDING
        assert status.execution_id is None
        assert status.error_message is None

    def test_status_with_execution_details(self):
        """Test status with full execution details."""
        now = datetime.now(UTC)
        status = TenantExecutionStatus(
            tenant_id="tenant-123",
            tenant_display_name="Test Tenant",
            state=TenantExecutionState.COMPLETED,
            execution_id="exec-456",
            started_at=now,
            completed_at=now,
            scenarios_completed=5,
            scenarios_failed=0,
        )
        assert status.state == TenantExecutionState.COMPLETED
        assert status.execution_id == "exec-456"
        assert status.scenarios_completed == 5

    def test_status_with_error(self):
        """Test status with error message."""
        status = TenantExecutionStatus(
            tenant_id="tenant-123",
            state=TenantExecutionState.FAILED,
            error_message="Authentication failed",
        )
        assert status.state == TenantExecutionState.FAILED
        assert "Authentication failed" in status.error_message
