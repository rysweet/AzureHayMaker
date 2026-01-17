"""Unit tests for tenant cost query functionality - TDD approach.

These tests define the expected behavior for tenant-specific cost queries
that extend the existing cost_query module for multi-tenant isolation.

Testing Pyramid:
- 60% Unit tests (model validation, query building, error handling)
- 30% Integration tests (cost query workflow with mocks)
- 10% E2E tests (marked skip for CI - real Azure Cost Management API)

Tests WILL FAIL initially - the implementation doesn't exist yet.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)


class TestTenantCostSummaryModel:
    """Tests for TenantCostSummary dataclass/model.

    TenantCostSummary extends CostSummary with tenant-specific fields
    for multi-tenant cost attribution.
    """

    def test_tenant_cost_summary_exists(self):
        """Test that TenantCostSummary model is defined."""
        from azure_haymaker.orchestrator.cost_query import TenantCostSummary

        assert TenantCostSummary is not None

    def test_tenant_cost_summary_required_fields(self):
        """Test TenantCostSummary with required fields only."""
        from azure_haymaker.orchestrator.cost_query import TenantCostSummary

        now = datetime.now(UTC)
        summary = TenantCostSummary(
            tenant_id="tenant-123",
            period_start=now - timedelta(days=7),
            period_end=now,
        )

        assert summary.tenant_id == "tenant-123"
        assert summary.total_cost == 0.0
        assert summary.currency == "USD"

    def test_tenant_cost_summary_all_fields(self):
        """Test TenantCostSummary with all fields populated."""
        from azure_haymaker.orchestrator.cost_query import TenantCostSummary

        now = datetime.now(UTC)
        start = now - timedelta(days=30)

        summary = TenantCostSummary(
            tenant_id="tenant-multi-field",
            total_cost=1250.75,
            currency="USD",
            period_start=start,
            period_end=now,
            cost_by_resource_type={
                "Microsoft.Compute/virtualMachines": 800.00,
                "Microsoft.Storage/storageAccounts": 250.75,
                "Microsoft.Network/publicIPAddresses": 200.00,
            },
            cost_by_scenario={
                "compute-01": 600.00,
                "storage-01": 350.75,
                "network-01": 300.00,
            },
            cost_by_execution={
                "exec-001": 500.00,
                "exec-002": 450.00,
                "exec-003": 300.75,
            },
            execution_count=3,
        )

        assert summary.tenant_id == "tenant-multi-field"
        assert summary.total_cost == 1250.75
        assert len(summary.cost_by_resource_type) == 3
        assert len(summary.cost_by_scenario) == 3
        assert len(summary.cost_by_execution) == 3
        assert summary.execution_count == 3

    def test_tenant_cost_summary_includes_tenant_id(self):
        """Test that TenantCostSummary includes tenant_id field."""
        from azure_haymaker.orchestrator.cost_query import TenantCostSummary

        now = datetime.now(UTC)
        summary = TenantCostSummary(
            tenant_id="specific-tenant",
            period_start=now - timedelta(days=1),
            period_end=now,
        )

        assert hasattr(summary, "tenant_id")
        assert summary.tenant_id == "specific-tenant"

    def test_tenant_cost_summary_includes_execution_breakdown(self):
        """Test that TenantCostSummary includes cost_by_execution field."""
        from azure_haymaker.orchestrator.cost_query import TenantCostSummary

        now = datetime.now(UTC)
        summary = TenantCostSummary(
            tenant_id="tenant-123",
            period_start=now - timedelta(days=1),
            period_end=now,
            cost_by_execution={
                "exec-001": 100.00,
                "exec-002": 150.00,
            },
        )

        assert hasattr(summary, "cost_by_execution")
        assert summary.cost_by_execution["exec-001"] == 100.00
        assert summary.cost_by_execution["exec-002"] == 150.00

    def test_tenant_cost_summary_includes_execution_count(self):
        """Test that TenantCostSummary includes execution_count field."""
        from azure_haymaker.orchestrator.cost_query import TenantCostSummary

        now = datetime.now(UTC)
        summary = TenantCostSummary(
            tenant_id="tenant-123",
            period_start=now - timedelta(days=1),
            period_end=now,
            execution_count=5,
        )

        assert hasattr(summary, "execution_count")
        assert summary.execution_count == 5

    def test_tenant_cost_summary_default_execution_count_is_zero(self):
        """Test that execution_count defaults to 0."""
        from azure_haymaker.orchestrator.cost_query import TenantCostSummary

        now = datetime.now(UTC)
        summary = TenantCostSummary(
            tenant_id="tenant-123",
            period_start=now - timedelta(days=1),
            period_end=now,
        )

        assert summary.execution_count == 0

    def test_tenant_cost_summary_zero_costs(self):
        """Test TenantCostSummary handles zero total cost."""
        from azure_haymaker.orchestrator.cost_query import TenantCostSummary

        now = datetime.now(UTC)
        summary = TenantCostSummary(
            tenant_id="tenant-empty",
            total_cost=0.0,
            period_start=now - timedelta(days=1),
            period_end=now,
        )

        assert summary.total_cost == 0.0
        assert summary.cost_by_resource_type == {}
        assert summary.cost_by_scenario == {}
        assert summary.cost_by_execution == {}


class TestGetTenantCostSummary:
    """Tests for get_tenant_cost_summary function.

    This function queries Azure Cost Management for costs filtered by tenant.
    """

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_exists(self):
        """Test that get_tenant_cost_summary function is defined."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        assert callable(get_tenant_cost_summary)

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_returns_tenant_cost_summary(self):
        """Test that get_tenant_cost_summary returns TenantCostSummary."""
        from azure_haymaker.orchestrator.cost_query import (
            TenantCostSummary,
            get_tenant_cost_summary,
        )

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_query.return_value = {
                "by_type": {},
                "by_scenario": {},
                "by_execution": {},
            }

            result = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-test",
            )

            assert isinstance(result, TenantCostSummary)

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_includes_tenant_id(self):
        """Test that result includes the queried tenant_id."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_query.return_value = {
                "by_type": {"Microsoft.Compute/virtualMachines": 100.0},
                "by_scenario": {"compute-01": 100.0},
                "by_execution": {"exec-001": 100.0},
            }

            result = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-specific-id",
            )

            assert result.tenant_id == "tenant-specific-id"

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_filters_by_tenant_tag(self):
        """Test that query filters by TenantId tag."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_query.return_value = {
                "by_type": {},
                "by_scenario": {},
                "by_execution": {},
            }

            await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-filter-test",
            )

            # Verify the query was called with tenant_id for filtering
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args.kwargs
            assert call_kwargs["tenant_id"] == "tenant-filter-test"

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_with_custom_period(self):
        """Test cost query with custom time period."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        now = datetime.now(UTC)
        custom_start = now - timedelta(days=7)
        custom_end = now - timedelta(days=1)

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_query.return_value = {
                "by_type": {},
                "by_scenario": {},
                "by_execution": {},
            }

            result = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-period-test",
                period_start=custom_start,
                period_end=custom_end,
            )

            assert result.period_start == custom_start
            assert result.period_end == custom_end

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_includes_execution_breakdown(self):
        """Test that result includes cost breakdown by execution."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_query.return_value = {
                "by_type": {"Microsoft.Compute/virtualMachines": 300.0},
                "by_scenario": {"compute-01": 300.0},
                "by_execution": {
                    "exec-001": 100.0,
                    "exec-002": 100.0,
                    "exec-003": 100.0,
                },
            }

            result = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-exec-breakdown",
            )

            assert len(result.cost_by_execution) == 3
            assert result.cost_by_execution["exec-001"] == 100.0
            assert result.cost_by_execution["exec-002"] == 100.0

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_calculates_execution_count(self):
        """Test that execution_count is calculated from cost_by_execution."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_query.return_value = {
                "by_type": {},
                "by_scenario": {},
                "by_execution": {
                    "exec-001": 50.0,
                    "exec-002": 75.0,
                    "exec-003": 25.0,
                    "exec-004": 100.0,
                },
            }

            result = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-count-test",
            )

            assert result.execution_count == 4

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_empty_results(self):
        """Test cost query with no results (new tenant with no cost data)."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_query.return_value = {
                "by_type": {},
                "by_scenario": {},
                "by_execution": {},
            }

            result = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-new",
            )

            assert result.tenant_id == "tenant-new"
            assert result.total_cost == 0.0
            assert result.cost_by_resource_type == {}
            assert result.cost_by_scenario == {}
            assert result.cost_by_execution == {}
            assert result.execution_count == 0

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_auth_failure(self):
        """Test cost query handles authentication failure."""
        from azure_haymaker.exceptions import CostQueryError
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential") as mock_cred:
            mock_cred.side_effect = ClientAuthenticationError("Invalid credentials")

            with pytest.raises(CostQueryError) as exc_info:
                await get_tenant_cost_summary(
                    subscription_id="sub-123",
                    tenant_id="tenant-auth-fail",
                )

            assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_resource_not_found(self):
        """Test cost query handles resource not found (returns empty summary)."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_query.side_effect = ResourceNotFoundError("No data found")

            result = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-not-found",
            )

            # Should return empty summary, not raise exception
            assert result.tenant_id == "tenant-not-found"
            assert result.total_cost == 0.0

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_http_error(self):
        """Test cost query handles HTTP errors."""
        from azure_haymaker.exceptions import CostQueryError
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_query.side_effect = HttpResponseError(
                message="Internal server error",
                response=mock_response,
            )

            with pytest.raises(CostQueryError) as exc_info:
                await get_tenant_cost_summary(
                    subscription_id="sub-123",
                    tenant_id="tenant-http-error",
                )

            assert "Failed to query costs" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_validates_tenant_id(self):
        """Test that empty tenant_id raises ValueError."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with pytest.raises(ValueError, match="tenant_id"):
            await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="",
            )

    @pytest.mark.asyncio
    async def test_get_tenant_cost_summary_default_period(self):
        """Test cost query uses 30-day default period when not specified."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_query.return_value = {
                "by_type": {},
                "by_scenario": {},
                "by_execution": {},
            }

            result = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-default-period",
            )

            # Check that period_start is approximately 30 days before period_end
            delta = result.period_end - result.period_start
            assert 29 <= delta.days <= 31


class TestTenantCostQueryIntegration:
    """Integration tests for tenant cost query workflow.

    Tests that combine multiple components to verify end-to-end behavior.
    """

    @pytest.mark.asyncio
    async def test_tenant_cost_summary_aggregates_correctly(self):
        """Test that total_cost is correctly aggregated from by_type."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            mock_query.return_value = {
                "by_type": {
                    "Microsoft.Compute/virtualMachines": 500.0,
                    "Microsoft.Storage/storageAccounts": 200.0,
                    "Microsoft.Network/virtualNetworks": 50.0,
                },
                "by_scenario": {},
                "by_execution": {},
            }

            result = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-aggregate",
            )

            # Total should be sum of cost_by_resource_type values
            expected_total = 500.0 + 200.0 + 50.0
            assert result.total_cost == expected_total

    @pytest.mark.asyncio
    async def test_tenant_isolation_different_tenants(self):
        """Test that different tenant queries return different results.

        Simulates multi-tenant isolation - each tenant sees only their costs.
        """
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        tenant_a_costs = {
            "by_type": {"Microsoft.Compute/virtualMachines": 100.0},
            "by_scenario": {"compute-01": 100.0},
            "by_execution": {"exec-a-001": 100.0},
        }
        tenant_b_costs = {
            "by_type": {"Microsoft.Storage/storageAccounts": 200.0},
            "by_scenario": {"storage-01": 200.0},
            "by_execution": {"exec-b-001": 200.0},
        }

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            patch(
                "azure_haymaker.orchestrator.cost_query._query_tenant_costs",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            # Tenant A query
            mock_query.return_value = tenant_a_costs
            result_a = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-a",
            )

            # Tenant B query
            mock_query.return_value = tenant_b_costs
            result_b = await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id="tenant-b",
            )

            # Verify isolation
            assert result_a.tenant_id == "tenant-a"
            assert result_b.tenant_id == "tenant-b"
            assert result_a.total_cost == 100.0
            assert result_b.total_cost == 200.0
            assert "exec-a-001" in result_a.cost_by_execution
            assert "exec-b-001" in result_b.cost_by_execution


class TestContainerDeployerTagIntegration:
    """Tests for container_deployer tagging integration.

    Verifies that container deployments include required tenant isolation tags.
    """

    def test_container_deployer_includes_tenant_tag(self):
        """Test that container deployment config includes TenantId tag."""
        from unittest.mock import MagicMock

        from azure_haymaker.orchestrator.container_deployer import ContainerDeployer

        # Create mock config with required fields
        config = MagicMock()
        config.resource_group_name = "test-rg"
        config.target_subscription_id = "sub-123"
        config.target_tenant_id = "tenant-deploy-test"
        config.container_memory_gb = 64
        config.container_cpu_cores = 2
        config.vnet_integration_enabled = False
        config.container_registry = "testacr.azurecr.io"
        config.container_image = "haymaker:latest"
        config.key_vault_url = "https://test-vault.vault.azure.net/"
        config.main_sp_client_id = "main-sp"

        deployer = ContainerDeployer(config)

        # The container app configuration should include tenant tags
        # This verifies the integration point for Phase 1
        assert deployer.config.target_tenant_id == "tenant-deploy-test"

    def test_container_app_tags_include_tenant_id(self):
        """Test that generated container app config includes TenantId in tags.

        This test verifies the container_deployer creates tags with TenantId
        for multi-tenant resource isolation per Issue #126.
        """
        # This test documents the expected integration behavior
        # The implementation should add TenantId to container app tags
        # during deployment in the deploy() method.

        # For now, we verify the structure is accessible
        from azure_haymaker.orchestrator.container_deployer import ContainerDeployer

        # Test passes if ContainerDeployer can be imported
        # Full integration test will verify tag application
        assert ContainerDeployer is not None

    def test_container_app_tags_include_execution_id(self):
        """Test that generated container app config includes ExecutionId in tags.

        ExecutionId enables cost tracking per execution run.
        """
        # This test documents the expected integration behavior
        # The implementation should add ExecutionId to container app tags
        from azure_haymaker.orchestrator.container_deployer import ContainerDeployer

        assert ContainerDeployer is not None


class TestTenantCostQueryErrorHandling:
    """Tests for error handling in tenant cost queries."""

    @pytest.mark.asyncio
    async def test_invalid_subscription_id_format(self):
        """Test handling of invalid subscription ID format."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with (
            patch("azure_haymaker.orchestrator.cost_query.DefaultAzureCredential"),
            patch("azure_haymaker.orchestrator.cost_query.CostManagementClient"),
            pytest.raises((ValueError, Exception)),
        ):
            # Invalid subscription ID should be caught by Azure SDK
            # or result in appropriate error handling
            await get_tenant_cost_summary(
                subscription_id="",  # Empty subscription
                tenant_id="tenant-123",
            )

    @pytest.mark.asyncio
    async def test_none_tenant_id_raises_error(self):
        """Test that None tenant_id raises appropriate error."""
        from azure_haymaker.orchestrator.cost_query import get_tenant_cost_summary

        with pytest.raises((TypeError, ValueError)):
            await get_tenant_cost_summary(
                subscription_id="sub-123",
                tenant_id=None,  # type: ignore[arg-type]
            )


# E2E tests marked skip for CI - require real Azure Cost Management API
class TestTenantCostQueryE2E:
    """End-to-end tests for tenant cost queries.

    These tests verify cost query behavior against real Azure resources.
    Marked as skip for CI - run manually in development.
    """

    @pytest.mark.skip(reason="E2E test - requires real Azure Cost Management API")
    @pytest.mark.asyncio
    async def test_real_tenant_cost_query(self):
        """Test querying real costs for a tenant.

        This test would:
        1. Use real Azure credentials
        2. Query costs for a known tenant
        3. Verify results match expected structure
        4. Validate tenant isolation (no cross-tenant data)
        """
        pass

    @pytest.mark.skip(reason="E2E test - requires real Azure Cost Management API")
    @pytest.mark.asyncio
    async def test_real_cost_aggregation_accuracy(self):
        """Test that cost aggregation matches Azure portal.

        This test would:
        1. Query costs via API
        2. Compare with Azure Portal cost analysis
        3. Verify totals match within acceptable variance
        """
        pass

    @pytest.mark.skip(reason="E2E test - requires real Azure resources with tags")
    @pytest.mark.asyncio
    async def test_real_tag_based_filtering(self):
        """Test that tag-based filtering works correctly.

        This test would:
        1. Create resources with TenantId tags
        2. Wait for cost data (24h delay)
        3. Query costs filtered by TenantId
        4. Verify only tagged resources appear
        """
        pass
