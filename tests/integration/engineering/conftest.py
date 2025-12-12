"""Integration test fixtures for engineering simulation.

Provides shared fixtures for integration tests including mock GitHub clients
and test configurations.
"""

import pytest
from unittest.mock import AsyncMock, Mock


@pytest.fixture
def mock_github_client():
    """Fixture providing a mock GitHub API client for integration tests.

    Returns:
        Mock GitHubClient with common methods mocked
    """
    client = Mock()
    client.token = "mock_token"
    client.org = "test-org"
    client.rate_limit_strategy = "wait"

    # Mock async methods
    client.create_commit = AsyncMock(return_value={
        "sha": "mock_commit_sha",
        "commit": {
            "author": {"name": "Test Author", "email": "test@example.com"},
            "message": "Test commit"
        },
        "files": ["test_file.py"],
        "stats": {"additions": 10, "deletions": 5}
    })

    client.create_pull_request = AsyncMock(return_value={
        "number": 1,
        "title": "Test PR",
        "body": "Test description",
        "state": "open",
        "head": {"ref": "feature/test"},
        "base": {"ref": "main"},
        "created_at": "2025-12-08T10:00:00Z"
    })

    client.create_review = AsyncMock(return_value={
        "id": 1,
        "user": {"login": "reviewer"},
        "state": "APPROVED",
        "submitted_at": "2025-12-08T11:00:00Z"
    })

    client.trigger_workflow = AsyncMock(return_value={
        "id": 1,
        "status": "queued",
        "workflow_name": "ci.yml"
    })

    client.merge_pull_request = AsyncMock(return_value={
        "sha": "merge_commit_sha",
        "merged": True,
        "merged_at": "2025-12-08T12:00:00Z"
    })

    client.get_rate_limit = AsyncMock(return_value={
        "resources": {
            "core": {
                "remaining": 5000,
                "reset": 1733662800
            }
        }
    })

    return client
