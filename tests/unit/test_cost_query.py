"""Unit tests for cost query module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)

from azure_haymaker.exceptions import CostQueryError
from azure_haymaker.orchestrator.cost_query import (
    CostSummary,
    get_cost_summary,
)


class TestCostSummaryModel:
    """Tests for CostSummary Pydantic model."""

    def test_cost_summary_required_fields(self):
        """Test CostSummary with required fields only."""
        now = datetime.now(UTC)
        summary = CostSummary(
            run_id="run-123",
            period_start=now - timedelta(days=7),
            period_end=now,
        )

        assert summary.run_id == "run-123"
        assert summary.total_cost == 0.0
        assert summary.currency == "USD"
        assert summary.cost_by_resource_type == {}
        assert summary.cost_by_scenario == {}

    def test_cost_summary_all_fields(self):
        """Test CostSummary with all fields populated."""
        now = datetime.now(UTC)
        start = now - timedelta(days=30)

        summary = CostSummary(
            run_id="run-456",
            total_cost=125.50,
            currency="USD",
            period_start=start,
            period_end=now,
            cost_by_resource_type={
                "Microsoft.Compute/virtualMachines": 100.00,
                "Microsoft.Storage/storageAccounts": 25.50,
            },
            cost_by_scenario={
                "compute-01": 75.00,
                "storage-01": 50.50,
            },
        )

        assert summary.run_id == "run-456"
        assert summary.total_cost == 125.50
        assert summary.currency == "USD"
        assert len(summary.cost_by_resource_type) == 2
        assert len(summary.cost_by_scenario) == 2
        assert summary.cost_by_resource_type["Microsoft.Compute/virtualMachines"] == 100.00

    def test_cost_summary_zero_costs(self):
        """Test CostSummary handles zero total cost."""
        now = datetime.now(UTC)
        summary = CostSummary(
            run_id="run-empty",
            total_cost=0.0,
            period_start=now - timedelta(days=1),
            period_end=now,
        )

        assert summary.total_cost == 0.0
        assert summary.cost_by_resource_type == {}


class TestGetCostSummary:
    """Tests for get_cost_summary function."""

    @pytest.mark.asyncio
    async def test_get_cost_summary_success(self):
        """Test successful cost query with mocked helper function."""
        cost_by_type = {
            "Microsoft.Compute/virtualMachines": 50.0,
            "Microsoft.Storage/storageAccounts": 25.0,
        }
        cost_by_scenario = {
            "compute-01": 75.0,
        }

        with (
            patch("azure_haymaker.orchestrator.cost_query.queries.DefaultAzureCredential") as mock_cred,
            patch("azure_haymaker.orchestrator.cost_query.queries.CostManagementClient") as mock_client,
            patch(
                "azure_haymaker.orchestrator.cost_query.queries._query_costs_grouped_by",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            # Mock credential and client constructors
            mock_cred.return_value = MagicMock()
            mock_client.return_value = MagicMock()

            # First call returns cost_by_type, second returns cost_by_scenario
            mock_query.side_effect = [cost_by_type, cost_by_scenario]

            result = await get_cost_summary(
                subscription_id="sub-123",
                run_id="run-test",
            )

            assert result.run_id == "run-test"
            assert result.total_cost == 75.0  # Sum of cost_by_type values
            assert result.currency == "USD"
            assert result.cost_by_resource_type == cost_by_type
            assert result.cost_by_scenario == cost_by_scenario

    @pytest.mark.asyncio
    async def test_get_cost_summary_empty_results(self):
        """Test cost query with no results (new run with no cost data yet)."""
        with (
            patch("azure_haymaker.orchestrator.cost_query.queries.DefaultAzureCredential") as mock_cred,
            patch("azure_haymaker.orchestrator.cost_query.queries.CostManagementClient") as mock_client,
            patch(
                "azure_haymaker.orchestrator.cost_query.queries._query_costs_grouped_by",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            # Mock credential and client constructors
            mock_cred.return_value = MagicMock()
            mock_client.return_value = MagicMock()
            
            mock_query.return_value = {}  # Empty results

            result = await get_cost_summary(
                subscription_id="sub-123",
                run_id="run-new",
            )

            assert result.run_id == "run-new"
            assert result.total_cost == 0.0
            assert result.cost_by_resource_type == {}
            assert result.cost_by_scenario == {}

    @pytest.mark.asyncio
    async def test_get_cost_summary_with_custom_period(self):
        """Test cost query with custom time period."""
        now = datetime.now(UTC)
        custom_start = now - timedelta(days=7)
        custom_end = now - timedelta(days=1)

        with (
            patch("azure_haymaker.orchestrator.cost_query.queries.DefaultAzureCredential") as mock_cred,
            patch("azure_haymaker.orchestrator.cost_query.queries.CostManagementClient") as mock_client,
            patch(
                "azure_haymaker.orchestrator.cost_query.queries._query_costs_grouped_by",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            # Mock credential and client constructors
            mock_cred.return_value = MagicMock()
            mock_client.return_value = MagicMock()
            
            mock_query.return_value = {"Microsoft.Compute/virtualMachines": 10.0}

            result = await get_cost_summary(
                subscription_id="sub-123",
                run_id="run-custom",
                period_start=custom_start,
                period_end=custom_end,
            )

            assert result.period_start == custom_start
            assert result.period_end == custom_end
            # Verify the helper was called with correct period
            calls = mock_query.call_args_list
            assert len(calls) == 2  # Two calls: by type and by scenario
            assert calls[0].kwargs["period_start"] == custom_start
            assert calls[0].kwargs["period_end"] == custom_end

    @pytest.mark.asyncio
    async def test_get_cost_summary_auth_failure(self):
        """Test cost query handles authentication failure."""
        with patch("azure_haymaker.orchestrator.cost_query.queries.DefaultAzureCredential") as mock_cred:
            mock_cred.side_effect = ClientAuthenticationError("Invalid credentials")

            with pytest.raises(CostQueryError) as exc_info:
                await get_cost_summary(
                    subscription_id="sub-123",
                    run_id="run-auth-fail",
                )

            assert "Authentication failed" in str(exc_info.value)
            assert exc_info.value.run_id == "run-auth-fail"

    @pytest.mark.asyncio
    async def test_get_cost_summary_resource_not_found(self):
        """Test cost query handles resource not found (returns empty summary)."""
        with (
            patch("azure_haymaker.orchestrator.cost_query.queries.DefaultAzureCredential") as mock_cred,
            patch("azure_haymaker.orchestrator.cost_query.queries.CostManagementClient") as mock_client,
            patch(
                "azure_haymaker.orchestrator.cost_query.queries._query_costs_grouped_by",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            # Mock credential and client constructors
            mock_cred.return_value = MagicMock()
            mock_client.return_value = MagicMock()
            
            mock_query.side_effect = ResourceNotFoundError("No data found")

            result = await get_cost_summary(
                subscription_id="sub-123",
                run_id="run-not-found",
            )

            # Should return empty summary, not raise exception
            assert result.run_id == "run-not-found"
            assert result.total_cost == 0.0
            assert result.cost_by_resource_type == {}

    @pytest.mark.asyncio
    async def test_get_cost_summary_http_error(self):
        """Test cost query handles HTTP errors."""
        with (
            patch("azure_haymaker.orchestrator.cost_query.queries.DefaultAzureCredential") as mock_cred,
            patch("azure_haymaker.orchestrator.cost_query.queries.CostManagementClient") as mock_client,
            patch(
                "azure_haymaker.orchestrator.cost_query.queries._query_costs_grouped_by",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            # Mock credential and client constructors
            mock_cred.return_value = MagicMock()
            mock_client.return_value = MagicMock()

            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_query.side_effect = HttpResponseError(
                message="Internal server error",
                response=mock_response,
            )

            with pytest.raises(CostQueryError) as exc_info:
                await get_cost_summary(
                    subscription_id="sub-123",
                    run_id="run-http-error",
                )

            assert "Failed to query costs" in str(exc_info.value)
            assert exc_info.value.run_id == "run-http-error"

    @pytest.mark.asyncio
    async def test_get_cost_summary_unexpected_error(self):
        """Test cost query handles unexpected errors."""
        with patch("azure_haymaker.orchestrator.cost_query.queries.DefaultAzureCredential") as mock_cred:
            mock_cred.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(CostQueryError) as exc_info:
                await get_cost_summary(
                    subscription_id="sub-123",
                    run_id="run-unexpected",
                )

            assert "Unexpected error" in str(exc_info.value)
            assert exc_info.value.run_id == "run-unexpected"

    @pytest.mark.asyncio
    async def test_get_cost_summary_default_period(self):
        """Test cost query uses 30-day default period when not specified."""
        with (
            patch("azure_haymaker.orchestrator.cost_query.queries.DefaultAzureCredential") as mock_cred,
            patch("azure_haymaker.orchestrator.cost_query.queries.CostManagementClient") as mock_client,
            patch(
                "azure_haymaker.orchestrator.cost_query.queries._query_costs_grouped_by",
                new_callable=AsyncMock,
            ) as mock_query,
        ):
            # Mock credential and client constructors
            mock_cred.return_value = MagicMock()
            mock_client.return_value = MagicMock()
            
            mock_query.return_value = {}

            result = await get_cost_summary(
                subscription_id="sub-123",
                run_id="run-default-period",
            )

            # Check that period_start is approximately 30 days before period_end
            delta = result.period_end - result.period_start
            assert 29 <= delta.days <= 31  # Allow for slight timing variations


class TestCostQueryErrorHandling:
    """Tests for CostQueryError exception."""

    def test_cost_query_error_with_run_id(self):
        """Test CostQueryError includes run_id in details."""
        error = CostQueryError(
            message="Test error",
            run_id="run-error-test",
        )

        assert error.message == "Test error"
        assert error.run_id == "run-error-test"
        assert "run_id" in error.details
        assert error.details["run_id"] == "run-error-test"

    def test_cost_query_error_without_run_id(self):
        """Test CostQueryError works without run_id."""
        error = CostQueryError(message="Generic error")

        assert error.message == "Generic error"
        assert error.run_id is None
