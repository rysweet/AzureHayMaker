# Tests fixtures package
"""Centralized test fixtures and mock factories for Azure HayMaker tests."""

from .azure_mocks import (
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

__all__ = [
    "MockAzureCredential",
    "MockContainerClient",
    "MockGraphClient",
    "MockKeyVaultClient",
    "MockServiceBusClient",
    "MockTableClient",
    "create_async_mock_keyvault_client",
    "create_mock_azure_credential",
    "create_mock_container_client",
    "create_mock_graph_client",
    "create_mock_keyvault_client",
    "create_mock_service_bus_client",
    "create_mock_table_client",
]
