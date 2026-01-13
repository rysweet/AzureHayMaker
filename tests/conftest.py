"""Test configuration and fixtures for Azure HayMaker tests.

This conftest.py is loaded before any tests run and sets up the test environment.

Note: Azure Durable Functions decorators in orchestrator.py are only needed for
production runtime. Tests can run without them since we mock the activity functions.
"""

import contextlib

import pytest

# Ensure azure.durable_functions is available for orchestrator module import
# The module may not be found due to namespace package conflicts between system and venv
with contextlib.suppress(ImportError):
    import azure.durable_functions  # noqa: F401

# Import mock factories
from tests.fixtures.azure_mocks import (
    MockAzureCredential,
    MockContainerClient,
    MockGraphClient,
    MockKeyVaultClient,
    MockServiceBusClient,
    MockTableClient,
    create_async_mock_keyvault_client,
    create_mock_azure_credential,
    create_mock_container_client,
    create_mock_graph_client,
    create_mock_keyvault_client,
    create_mock_service_bus_client,
    create_mock_table_client,
)

# Azure SDK Mock Fixtures


@pytest.fixture
def mock_azure_credential() -> MockAzureCredential:
    """Fixture providing a mock Azure credential.

    Returns:
        MockAzureCredential instance that simulates DefaultAzureCredential
    """
    return create_mock_azure_credential()


@pytest.fixture
def mock_keyvault_client() -> MockKeyVaultClient:
    """Fixture providing a mock Key Vault client.

    Returns:
        MockKeyVaultClient with in-memory secret storage
    """
    return create_mock_keyvault_client()


@pytest.fixture
def mock_async_keyvault_client():
    """Fixture providing an async mock Key Vault client for patching.

    Returns:
        AsyncMock configured as SecretClient
    """
    return create_async_mock_keyvault_client()


@pytest.fixture
def mock_table_client() -> MockTableClient:
    """Fixture providing a mock Table Storage client.

    Returns:
        MockTableClient with in-memory entity storage
    """
    return create_mock_table_client()


@pytest.fixture
def mock_container_client() -> MockContainerClient:
    """Fixture providing a mock Blob Container client.

    Returns:
        MockContainerClient with in-memory blob storage
    """
    return create_mock_container_client()


@pytest.fixture
def mock_graph_client() -> MockGraphClient:
    """Fixture providing a mock Microsoft Graph client.

    Returns:
        MockGraphClient for application and service principal operations
    """
    return create_mock_graph_client()


@pytest.fixture
def mock_service_bus_client() -> MockServiceBusClient:
    """Fixture providing a mock Service Bus client.

    Returns:
        MockServiceBusClient for topic and queue operations
    """
    return create_mock_service_bus_client()


@pytest.fixture
def anyio_backend():
    """Force asyncio backend only for all anyio tests.

    This prevents pytest-anyio from trying to run tests with trio backend,
    which is not installed in this project.

    Returns:
        'asyncio' to force asyncio-only testing
    """
    return "asyncio"
