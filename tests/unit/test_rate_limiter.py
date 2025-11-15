"""Unit tests for rate limiter module."""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from azure.core.exceptions import ResourceNotFoundError

from azure_haymaker.orchestrator.rate_limiter import RateLimiter, RateLimitResult


@pytest.fixture
def mock_table_client():
    """Create mock Table Storage client."""
    return AsyncMock()


@pytest.fixture
def rate_limiter(mock_table_client):
    """Create rate limiter instance."""
    return RateLimiter(mock_table_client)


@pytest.mark.asyncio
async def test_check_rate_limit_first_request(rate_limiter, mock_table_client):
    """Test first request within window (should be allowed)."""
    # Mock: no existing record
    mock_table_client.get_entity.side_effect = ResourceNotFoundError("Not found")
    mock_table_client.upsert_entity = AsyncMock()

    result = await rate_limiter.check_rate_limit(
        limit_type="global",
        identifier="default",
        limit=10,
        window_seconds=3600,
    )

    assert result.allowed is True
    assert result.retry_after == 0
    assert result.current_count == 1
    assert result.limit == 10

    # Verify entity was created
    mock_table_client.upsert_entity.assert_called_once()


@pytest.mark.asyncio
async def test_check_rate_limit_within_limit(rate_limiter, mock_table_client):
    """Test request within rate limit."""
    # Mock: existing record with count below limit
    now = datetime.now(UTC)
    mock_entity = {
        "Count": 5,
        "WindowStart": now.isoformat(),
        "LastRequest": now.isoformat(),
    }
    mock_table_client.get_entity.return_value = mock_entity
    mock_table_client.upsert_entity = AsyncMock()

    result = await rate_limiter.check_rate_limit(
        limit_type="global",
        identifier="default",
        limit=10,
        window_seconds=3600,
    )

    assert result.allowed is True
    assert result.retry_after == 0
    assert result.current_count == 6  # Incremented
    assert result.limit == 10


@pytest.mark.asyncio
async def test_check_rate_limit_exceeded(rate_limiter, mock_table_client):
    """Test request when rate limit exceeded."""
    # Mock: existing record at limit
    now = datetime.now(UTC)
    mock_entity = {
        "Count": 10,
        "WindowStart": now.isoformat(),
        "LastRequest": now.isoformat(),
    }
    mock_table_client.get_entity.return_value = mock_entity
    mock_table_client.upsert_entity = AsyncMock()

    result = await rate_limiter.check_rate_limit(
        limit_type="global",
        identifier="default",
        limit=10,
        window_seconds=3600,
    )

    assert result.allowed is False
    assert result.retry_after > 0
    assert result.current_count == 10
    assert result.limit == 10

    # Verify entity was NOT updated
    mock_table_client.upsert_entity.assert_not_called()


@pytest.mark.asyncio
async def test_check_rate_limit_window_expired(rate_limiter, mock_table_client):
    """Test request after window expires (should reset)."""
    # Mock: existing record with expired window
    old_time = datetime.now(UTC) - timedelta(hours=2)
    mock_entity = {
        "Count": 10,
        "WindowStart": old_time.isoformat(),
        "LastRequest": old_time.isoformat(),
    }
    mock_table_client.get_entity.return_value = mock_entity
    mock_table_client.upsert_entity = AsyncMock()

    result = await rate_limiter.check_rate_limit(
        limit_type="global",
        identifier="default",
        limit=10,
        window_seconds=3600,
    )

    assert result.allowed is True
    assert result.retry_after == 0
    assert result.current_count == 1  # Reset to 1
    assert result.limit == 10


@pytest.mark.asyncio
async def test_check_multiple_limits_all_pass(rate_limiter, mock_table_client):
    """Test multiple limits when all pass."""
    # Mock: all limits have room
    now = datetime.now(UTC)
    mock_entity = {
        "Count": 5,
        "WindowStart": now.isoformat(),
        "LastRequest": now.isoformat(),
    }
    mock_table_client.get_entity.return_value = mock_entity
    mock_table_client.upsert_entity = AsyncMock()

    checks = [
        ("global", "default"),
        ("scenario", "compute-01"),
        ("user", "user@example.com"),
    ]

    result = await rate_limiter.check_multiple_limits(checks)

    assert result.allowed is True


@pytest.mark.asyncio
async def test_check_multiple_limits_one_fails(rate_limiter, mock_table_client):
    """Test multiple limits when one fails."""
    # Mock: scenario limit exceeded
    now = datetime.now(UTC)

    def get_entity_side_effect(partition_key, row_key):
        if partition_key == "scenario":
            return {
                "Count": 10,
                "WindowStart": now.isoformat(),
                "LastRequest": now.isoformat(),
            }
        return {
            "Count": 5,
            "WindowStart": now.isoformat(),
            "LastRequest": now.isoformat(),
        }

    mock_table_client.get_entity.side_effect = get_entity_side_effect
    mock_table_client.upsert_entity = AsyncMock()

    checks = [
        ("global", "default"),
        ("scenario", "compute-01"),
        ("user", "user@example.com"),
    ]

    result = await rate_limiter.check_multiple_limits(checks)

    assert result.allowed is False


@pytest.mark.asyncio
async def test_reset_limit(rate_limiter, mock_table_client):
    """Test resetting a rate limit."""
    mock_table_client.delete_entity = AsyncMock()

    await rate_limiter.reset_limit(
        limit_type="user",
        identifier="user@example.com",
    )

    mock_table_client.delete_entity.assert_called_once_with(
        partition_key="user",
        row_key="user@example.com",
    )


@pytest.mark.asyncio
async def test_reset_limit_not_exists(rate_limiter, mock_table_client):
    """Test resetting a limit that doesn't exist."""
    mock_table_client.delete_entity.side_effect = ResourceNotFoundError("Not found")

    # Should not raise exception
    await rate_limiter.reset_limit(
        limit_type="user",
        identifier="user@example.com",
    )


@pytest.mark.asyncio
async def test_get_current_usage(rate_limiter, mock_table_client):
    """Test getting current usage."""
    now = datetime.now(UTC)
    mock_entity = {
        "Count": 7,
        "WindowStart": now.isoformat(),
        "Limit": 10,
    }
    mock_table_client.get_entity.return_value = mock_entity

    usage = await rate_limiter.get_current_usage(
        limit_type="global",
        identifier="default",
    )

    assert usage["current_count"] == 7
    assert usage["limit"] == 10
    assert usage["seconds_until_reset"] > 0


@pytest.mark.asyncio
async def test_get_current_usage_no_record(rate_limiter, mock_table_client):
    """Test getting usage when no record exists."""
    mock_table_client.get_entity.side_effect = ResourceNotFoundError("Not found")

    usage = await rate_limiter.get_current_usage(
        limit_type="global",
        identifier="default",
    )

    assert usage["current_count"] == 0
    assert usage["limit"] == 100  # Default global limit
    assert usage["seconds_until_reset"] == 0


@pytest.mark.asyncio
async def test_check_rate_limit_storage_failure(rate_limiter, mock_table_client):
    """Test rate limiter when storage update fails."""
    # Should allow request even if storage fails
    mock_table_client.get_entity.side_effect = ResourceNotFoundError("Not found")
    mock_table_client.upsert_entity.side_effect = Exception("Storage error")

    result = await rate_limiter.check_rate_limit(
        limit_type="global",
        identifier="default",
        limit=10,
        window_seconds=3600,
    )

    # Should still allow (fail open for availability)
    assert result.allowed is True
    assert result.current_count == 1


@pytest.mark.asyncio
async def test_different_limit_types(rate_limiter, mock_table_client):
    """Test different limit types have separate counters."""
    now = datetime.now(UTC)
    mock_table_client.get_entity.side_effect = ResourceNotFoundError("Not found")
    mock_table_client.upsert_entity = AsyncMock()

    # Check global limit
    result1 = await rate_limiter.check_rate_limit(
        limit_type="global",
        identifier="default",
        limit=10,
        window_seconds=3600,
    )

    # Check scenario limit
    result2 = await rate_limiter.check_rate_limit(
        limit_type="scenario",
        identifier="compute-01",
        limit=10,
        window_seconds=3600,
    )

    # Both should be allowed (separate counters)
    assert result1.allowed is True
    assert result2.allowed is True

    # Verify separate partition keys were used
    calls = mock_table_client.upsert_entity.call_args_list
    assert calls[0][1]["entity"]["PartitionKey"] == "global"
    assert calls[1][1]["entity"]["PartitionKey"] == "scenario"
