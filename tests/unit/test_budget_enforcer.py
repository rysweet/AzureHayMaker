"""Tests for budget enforcement service.

Tests BudgetEnforcer functionality including:
- Budget configuration validation
- Cost estimation
- Deployment permission checks
- Azure Cost Management integration (mocked)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from azure_haymaker.orchestrator.services.budget_enforcer import (
    VM_HOURLY_RATES,
    BudgetConfig,
    BudgetEnforcer,
    CostEstimate,
    DeploymentDecision,
    SpendSummary,
    ThrottleAction,
)


class TestBudgetConfig:
    """Tests for BudgetConfig model."""

    def test_default_config(self):
        """Test default configuration has no limits."""
        config = BudgetConfig()
        assert config.daily_limit is None
        assert config.weekly_limit is None
        assert config.monthly_limit is None
        assert config.auto_throttle is True
        assert config.alert_threshold == 0.8
        assert config.warn_threshold == 0.5

    def test_custom_limits(self):
        """Test custom budget limits."""
        config = BudgetConfig(
            daily_limit=100.0,
            weekly_limit=500.0,
            monthly_limit=1500.0,
        )
        assert config.daily_limit == 100.0
        assert config.weekly_limit == 500.0
        assert config.monthly_limit == 1500.0

    def test_threshold_validation(self):
        """Test threshold must be between 0 and 1."""
        config = BudgetConfig(alert_threshold=0.9, warn_threshold=0.6)
        assert config.alert_threshold == 0.9
        assert config.warn_threshold == 0.6

        with pytest.raises(ValueError):
            BudgetConfig(alert_threshold=1.5)

        with pytest.raises(ValueError):
            BudgetConfig(warn_threshold=-0.1)

    def test_disabled_throttle(self):
        """Test throttle can be disabled."""
        config = BudgetConfig(auto_throttle=False)
        assert config.auto_throttle is False


class TestSpendSummary:
    """Tests for SpendSummary model."""

    def test_default_spend(self):
        """Test default spend is zero."""
        spend = SpendSummary()
        assert spend.daily == 0.0
        assert spend.weekly == 0.0
        assert spend.monthly == 0.0
        assert spend.timestamp is not None

    def test_custom_spend(self):
        """Test custom spend values."""
        now = datetime.now(UTC)
        spend = SpendSummary(
            daily=50.0,
            weekly=200.0,
            monthly=800.0,
            timestamp=now,
        )
        assert spend.daily == 50.0
        assert spend.weekly == 200.0
        assert spend.monthly == 800.0
        assert spend.timestamp == now


class TestCostEstimate:
    """Tests for CostEstimate model."""

    def test_default_estimate(self):
        """Test default estimate."""
        estimate = CostEstimate()
        assert estimate.compute == 0.0
        assert estimate.storage == 0.0
        assert estimate.network == 0.0
        assert estimate.total == 0.0
        assert estimate.duration_hours == 1.0
        assert estimate.confidence == 0.8

    def test_custom_estimate(self):
        """Test custom cost estimate."""
        estimate = CostEstimate(
            compute=50.0,
            storage=5.0,
            network=5.0,
            total=60.0,
            duration_hours=8.0,
            confidence=0.9,
        )
        assert estimate.compute == 50.0
        assert estimate.storage == 5.0
        assert estimate.network == 5.0
        assert estimate.total == 60.0
        assert estimate.duration_hours == 8.0
        assert estimate.confidence == 0.9


class TestBudgetEnforcerCostEstimation:
    """Tests for cost estimation functionality."""

    def test_estimate_known_vm_size(self):
        """Test cost estimation for known VM size."""
        enforcer = BudgetEnforcer(subscription_id="test-sub")

        estimate = enforcer.estimate_deployment_cost(
            vm_count=1,
            vm_size="Standard_D4s_v3",
            duration_hours=4.0,
        )

        # D4s_v3 is ~$0.192/hour
        expected_compute = 1 * 0.192 * 4.0
        assert estimate.compute == pytest.approx(expected_compute, rel=0.01)
        assert estimate.confidence == 0.9  # Known VM size

    def test_estimate_unknown_vm_size(self):
        """Test cost estimation for unknown VM size uses default."""
        enforcer = BudgetEnforcer(subscription_id="test-sub")

        estimate = enforcer.estimate_deployment_cost(
            vm_count=1,
            vm_size="Unknown_VM_Size",
            duration_hours=1.0,
        )

        # Should use default rate
        expected_compute = 1 * VM_HOURLY_RATES["default"] * 1.0
        assert estimate.compute == pytest.approx(expected_compute, rel=0.01)
        assert estimate.confidence == 0.6  # Unknown VM size

    def test_estimate_multiple_vms(self):
        """Test cost estimation for multiple VMs."""
        enforcer = BudgetEnforcer(subscription_id="test-sub")

        estimate = enforcer.estimate_deployment_cost(
            vm_count=5,
            vm_size="Standard_D4s_v3",
            duration_hours=4.0,
        )

        expected_compute = 5 * 0.192 * 4.0
        assert estimate.compute == pytest.approx(expected_compute, rel=0.01)

    def test_estimate_includes_storage_and_network(self):
        """Test estimate includes storage and network costs."""
        enforcer = BudgetEnforcer(subscription_id="test-sub")

        estimate = enforcer.estimate_deployment_cost(
            vm_count=1,
            vm_size="Standard_D4s_v3",
            duration_hours=4.0,
            storage_gb=100.0,
        )

        assert estimate.compute > 0
        assert estimate.storage > 0
        assert estimate.network > 0
        assert estimate.total == pytest.approx(
            estimate.compute + estimate.storage + estimate.network, rel=0.01
        )


class TestBudgetEnforcerDeploymentDecision:
    """Tests for deployment permission checking."""

    @pytest.fixture
    def enforcer_with_limits(self):
        """Create enforcer with budget limits."""
        config = BudgetConfig(
            daily_limit=100.0,
            weekly_limit=500.0,
            monthly_limit=1500.0,
            alert_threshold=0.8,
            auto_throttle=True,
        )
        return BudgetEnforcer(subscription_id="test-sub", config=config)

    @pytest.mark.asyncio
    async def test_allow_under_budget(self, enforcer_with_limits):
        """Test deployment allowed when under budget."""
        # Mock current spend to be low
        with patch.object(
            enforcer_with_limits,
            "get_current_spend",
            new_callable=AsyncMock,
            return_value=SpendSummary(daily=10.0, weekly=50.0, monthly=200.0),
        ):
            decision = await enforcer_with_limits.can_deploy(estimated_cost=20.0)

            assert decision.allowed is True
            assert decision.action == ThrottleAction.ALLOW
            assert "within budget" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_block_over_budget(self, enforcer_with_limits):
        """Test deployment blocked when would exceed budget."""
        # Mock current spend to be near limit
        with patch.object(
            enforcer_with_limits,
            "get_current_spend",
            new_callable=AsyncMock,
            return_value=SpendSummary(daily=90.0, weekly=450.0, monthly=1400.0),
        ):
            decision = await enforcer_with_limits.can_deploy(estimated_cost=20.0)

            assert decision.allowed is False
            assert decision.action == ThrottleAction.BLOCK
            assert "exceeded" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_warn_near_budget(self, enforcer_with_limits):
        """Test warning when approaching budget."""
        # Mock current spend at 70% (above warn threshold)
        with patch.object(
            enforcer_with_limits,
            "get_current_spend",
            new_callable=AsyncMock,
            return_value=SpendSummary(daily=70.0, weekly=350.0, monthly=1050.0),
        ):
            decision = await enforcer_with_limits.can_deploy(estimated_cost=10.0)

            assert decision.allowed is True
            assert decision.action == ThrottleAction.WARN
            assert "approaching" in decision.reason.lower() or "%" in decision.reason

    @pytest.mark.asyncio
    async def test_throttle_disabled(self):
        """Test deployment allowed with warning when throttle disabled."""
        config = BudgetConfig(
            daily_limit=100.0,
            auto_throttle=False,  # Disabled
        )
        enforcer = BudgetEnforcer(subscription_id="test-sub", config=config)

        with patch.object(
            enforcer,
            "get_current_spend",
            new_callable=AsyncMock,
            return_value=SpendSummary(daily=90.0),
        ):
            decision = await enforcer.can_deploy(estimated_cost=20.0)

            assert decision.allowed is True
            assert decision.action == ThrottleAction.WARN
            assert "throttle disabled" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_no_limit_always_allows(self):
        """Test deployment always allowed when no limits set."""
        enforcer = BudgetEnforcer(subscription_id="test-sub")

        with patch.object(
            enforcer,
            "get_current_spend",
            new_callable=AsyncMock,
            return_value=SpendSummary(daily=10000.0, weekly=50000.0, monthly=200000.0),
        ):
            decision = await enforcer.can_deploy(estimated_cost=1000.0)

            assert decision.allowed is True
            assert decision.action == ThrottleAction.ALLOW


class TestBudgetEnforcerCostQuery:
    """Tests for Azure Cost Management integration."""

    @pytest.mark.asyncio
    async def test_get_current_spend_success(self):
        """Test successful cost query."""
        enforcer = BudgetEnforcer(subscription_id="test-sub")

        # Mock _query_cost_for_period directly since asyncio.to_thread
        # doesn't work well with deep mock chains
        with patch.object(
            enforcer,
            "_query_cost_for_period",
            new_callable=AsyncMock,
            return_value=100.0,
        ):
            spend = await enforcer.get_current_spend(use_cache=False)

            assert spend.daily == 100.0
            assert spend.weekly == 100.0
            assert spend.monthly == 100.0

    @pytest.mark.asyncio
    async def test_get_current_spend_uses_cache(self):
        """Test spend query uses cache when fresh."""
        enforcer = BudgetEnforcer(subscription_id="test-sub")

        # Set cache
        cached_spend = SpendSummary(daily=50.0, weekly=200.0, monthly=800.0)
        enforcer._spend_cache = cached_spend
        enforcer._cache_timestamp = datetime.now(UTC)

        # Should return cache without calling API
        spend = await enforcer.get_current_spend(use_cache=True)

        assert spend.daily == 50.0
        assert spend.weekly == 200.0
        assert spend.monthly == 800.0

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation."""
        enforcer = BudgetEnforcer(subscription_id="test-sub")

        # Set cache
        enforcer._spend_cache = SpendSummary(daily=50.0)
        enforcer._cache_timestamp = datetime.now(UTC)

        # Invalidate
        enforcer.invalidate_cache()

        assert enforcer._spend_cache is None
        assert enforcer._cache_timestamp is None


class TestBudgetStatus:
    """Tests for comprehensive budget status."""

    @pytest.mark.asyncio
    async def test_status_ok(self):
        """Test status is OK when well under budget."""
        config = BudgetConfig(
            daily_limit=100.0,
            monthly_limit=1500.0,
        )
        enforcer = BudgetEnforcer(subscription_id="test-sub", config=config)

        with patch.object(
            enforcer,
            "get_current_spend",
            new_callable=AsyncMock,
            return_value=SpendSummary(daily=10.0, monthly=200.0),
        ):
            status = await enforcer.get_status()

            assert status.status == "ok"
            assert "within limits" in status.message.lower()
            assert status.remaining["daily"] == pytest.approx(90.0)
            assert status.remaining["monthly"] == pytest.approx(1300.0)

    @pytest.mark.asyncio
    async def test_status_warning(self):
        """Test status is warning when approaching limit."""
        config = BudgetConfig(
            daily_limit=100.0,
            warn_threshold=0.5,
        )
        enforcer = BudgetEnforcer(subscription_id="test-sub", config=config)

        with patch.object(
            enforcer,
            "get_current_spend",
            new_callable=AsyncMock,
            return_value=SpendSummary(daily=60.0),  # 60% of daily
        ):
            status = await enforcer.get_status()

            assert status.status == "warning"
            assert "60%" in status.message

    @pytest.mark.asyncio
    async def test_status_exceeded(self):
        """Test status is exceeded when over budget."""
        config = BudgetConfig(daily_limit=100.0)
        enforcer = BudgetEnforcer(subscription_id="test-sub", config=config)

        with patch.object(
            enforcer,
            "get_current_spend",
            new_callable=AsyncMock,
            return_value=SpendSummary(daily=150.0),  # Over limit
        ):
            status = await enforcer.get_status()

            assert status.status == "exceeded"
            assert "exceeded" in status.message.lower()


class TestDeploymentDecision:
    """Tests for DeploymentDecision dataclass."""

    def test_allowed_decision(self):
        """Test allowed deployment decision."""
        decision = DeploymentDecision(
            allowed=True,
            action=ThrottleAction.ALLOW,
            reason="Within budget",
            estimated_cost=50.0,
            remaining_budget={"daily": 50.0, "monthly": 1000.0},
        )
        assert decision.allowed is True
        assert decision.action == ThrottleAction.ALLOW
        assert decision.estimated_cost == 50.0

    def test_blocked_decision(self):
        """Test blocked deployment decision."""
        decision = DeploymentDecision(
            allowed=False,
            action=ThrottleAction.BLOCK,
            reason="Budget exceeded",
        )
        assert decision.allowed is False
        assert decision.action == ThrottleAction.BLOCK


class TestVMHourlyRates:
    """Tests for VM pricing data."""

    def test_known_vm_sizes_have_rates(self):
        """Test common VM sizes have pricing data."""
        expected_sizes = [
            "Standard_D2s_v3",
            "Standard_D4s_v3",
            "Standard_D8s_v3",
            "Standard_E4s_v3",
            "Standard_E8s_v3",
        ]
        for size in expected_sizes:
            assert size in VM_HOURLY_RATES
            assert VM_HOURLY_RATES[size] > 0

    def test_default_rate_exists(self):
        """Test default rate exists for unknown sizes."""
        assert "default" in VM_HOURLY_RATES
        assert VM_HOURLY_RATES["default"] > 0
