"""Azure SDK Mock Factory for testing.

This module provides centralized mock factories for Azure SDK clients used throughout
Azure HayMaker tests. It eliminates boilerplate and ensures consistent mocking patterns.

Usage:
    from tests.fixtures.azure_mocks import create_mock_graph_client, MockAzureCredential

    # In tests:
    mock_graph = create_mock_graph_client()
    mock_credential = MockAzureCredential()
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock


@dataclass
class MockAzureCredential:
    """Mock Azure credential for testing.

    Simulates DefaultAzureCredential or ClientSecretCredential behavior.
    """

    tenant_id: str = "test-tenant-id"
    client_id: str = "test-client-id"
    token: str = "mock-access-token"
    expires_on: float = field(default_factory=lambda: datetime.now(UTC).timestamp() + 3600)

    def get_token(self, *scopes: str, **kwargs: Any) -> MagicMock:
        """Return a mock access token."""
        token = MagicMock()
        token.token = self.token
        token.expires_on = self.expires_on
        return token

    async def get_token_async(self, *scopes: str, **kwargs: Any) -> MagicMock:
        """Return a mock access token asynchronously."""
        return self.get_token(*scopes, **kwargs)


class MockKeyVaultClient:
    """Mock Azure Key Vault SecretClient for testing.

    Provides in-memory secret storage with async interface matching azure.keyvault.secrets.
    """

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}
        self._deleted_secrets: set[str] = set()

    def set_secret(self, name: str, value: str, **kwargs: Any) -> MagicMock:
        """Store a secret."""
        self._secrets[name] = value
        secret = MagicMock()
        secret.name = name
        secret.value = value
        secret.properties = MagicMock()
        secret.properties.vault_url = "https://mock-vault.vault.azure.net"
        return secret

    def get_secret(self, name: str, **kwargs: Any) -> MagicMock:
        """Retrieve a secret."""
        if name in self._deleted_secrets:
            raise self._resource_not_found_error(f"Secret {name} not found")
        if name not in self._secrets:
            raise self._resource_not_found_error(f"Secret {name} not found")
        secret = MagicMock()
        secret.name = name
        secret.value = self._secrets[name]
        return secret

    def begin_delete_secret(self, name: str, **kwargs: Any) -> MagicMock:
        """Begin deleting a secret (simulates async deletion)."""
        if name in self._secrets:
            del self._secrets[name]
        self._deleted_secrets.add(name)
        poller = MagicMock()
        poller.result.return_value = MagicMock()
        return poller

    def list_properties_of_secrets(self, **kwargs: Any) -> list[MagicMock]:
        """List all secret properties."""
        result = []
        for name in self._secrets:
            prop = MagicMock()
            prop.name = name
            result.append(prop)
        return result

    @staticmethod
    def _resource_not_found_error(message: str) -> Exception:
        """Create ResourceNotFoundError-like exception."""
        from azure.core.exceptions import ResourceNotFoundError

        return ResourceNotFoundError(message)


class MockTableClient:
    """Mock Azure Table Storage client for testing.

    Provides in-memory entity storage with async interface matching azure.data.tables.
    """

    def __init__(self) -> None:
        self._entities: dict[tuple[str, str], dict[str, Any]] = {}
        self._etag_counter = 0

    def _generate_etag(self) -> str:
        """Generate a unique ETag."""
        self._etag_counter += 1
        return f'W/"etag-{self._etag_counter}"'

    async def get_entity(self, partition_key: str, row_key: str, **kwargs: Any) -> dict[str, Any]:
        """Retrieve an entity."""
        key = (partition_key, row_key)
        if key not in self._entities:
            raise self._resource_not_found_error(f"Entity not found: {partition_key}/{row_key}")
        return self._entities[key].copy()

    async def create_entity(self, entity: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Create a new entity."""
        pk = entity.get("PartitionKey")
        rk = entity.get("RowKey")
        if not pk or not rk:
            raise ValueError("PartitionKey and RowKey are required")
        key = (pk, rk)
        if key in self._entities:
            raise self._resource_exists_error(f"Entity already exists: {pk}/{rk}")
        entity["etag"] = self._generate_etag()
        self._entities[key] = entity.copy()
        return entity

    async def update_entity(
        self, entity: dict[str, Any], mode: str = "merge", **kwargs: Any
    ) -> dict[str, Any]:
        """Update an existing entity."""
        pk = entity.get("PartitionKey")
        rk = entity.get("RowKey")
        key = (pk, rk)

        # Check ETag for optimistic concurrency
        if "etag" in kwargs and key in self._entities:
            current_etag = self._entities[key].get("etag")
            if current_etag != kwargs["etag"]:
                raise self._resource_modified_error("Entity was modified")

        if key not in self._entities:
            raise self._resource_not_found_error(f"Entity not found: {pk}/{rk}")

        entity["etag"] = self._generate_etag()
        if mode == "merge":
            self._entities[key].update(entity)
        else:
            self._entities[key] = entity.copy()
        return entity

    async def upsert_entity(
        self, entity: dict[str, Any], mode: str = "merge", **kwargs: Any
    ) -> dict[str, Any]:
        """Upsert an entity (create or update)."""
        pk = entity.get("PartitionKey")
        rk = entity.get("RowKey")
        key = (pk, rk)
        entity["etag"] = self._generate_etag()
        if mode == "merge" and key in self._entities:
            self._entities[key].update(entity)
        else:
            self._entities[key] = entity.copy()
        return entity

    async def delete_entity(self, partition_key: str, row_key: str, **kwargs: Any) -> None:
        """Delete an entity."""
        key = (partition_key, row_key)
        if key in self._entities:
            del self._entities[key]

    def query_entities(
        self, query_filter: str | None = None, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Query entities (simple implementation)."""
        # Simple implementation - returns all entities
        # Real filtering would require OData parser
        return [e.copy() for e in self._entities.values()]

    @staticmethod
    def _resource_not_found_error(message: str) -> Exception:
        """Create ResourceNotFoundError-like exception."""
        from azure.core.exceptions import ResourceNotFoundError

        return ResourceNotFoundError(message)

    @staticmethod
    def _resource_exists_error(message: str) -> Exception:
        """Create ResourceExistsError-like exception."""
        from azure.core.exceptions import ResourceExistsError

        return ResourceExistsError(message)

    @staticmethod
    def _resource_modified_error(message: str) -> Exception:
        """Create ResourceModifiedError-like exception."""
        from azure.core.exceptions import ResourceModifiedError

        return ResourceModifiedError(message)


class MockContainerClient:
    """Mock Azure Blob Storage ContainerClient for testing.

    Provides in-memory blob storage with interface matching azure.storage.blob.
    """

    def __init__(self, container_name: str = "test-container") -> None:
        self.container_name = container_name
        self._blobs: dict[str, bytes] = {}
        self._metadata: dict[str, dict[str, str]] = {}

    def get_blob_client(self, blob_name: str) -> "MockBlobClient":
        """Get a blob client for the specified blob."""
        return MockBlobClient(self, blob_name)

    def list_blobs(self, name_starts_with: str | None = None, **kwargs: Any) -> list[MagicMock]:
        """List blobs in the container."""
        blobs = []
        for name in self._blobs:
            if name_starts_with is None or name.startswith(name_starts_with):
                blob = MagicMock()
                blob.name = name
                blob.size = len(self._blobs[name])
                blob.metadata = self._metadata.get(name, {})
                blobs.append(blob)
        return blobs

    def upload_blob(
        self,
        name: str,
        data: bytes | str,
        overwrite: bool = False,
        metadata: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> MagicMock:
        """Upload a blob."""
        if name in self._blobs and not overwrite:
            raise self._resource_exists_error(f"Blob {name} already exists")
        if isinstance(data, str):
            data = data.encode("utf-8")
        self._blobs[name] = data
        if metadata:
            self._metadata[name] = metadata
        result = MagicMock()
        result.etag = f"etag-{name}"
        return result

    def delete_blob(self, name: str, **kwargs: Any) -> None:
        """Delete a blob."""
        if name in self._blobs:
            del self._blobs[name]
        if name in self._metadata:
            del self._metadata[name]

    def exists(self) -> bool:
        """Check if container exists."""
        return True

    @staticmethod
    def _resource_exists_error(message: str) -> Exception:
        """Create ResourceExistsError-like exception."""
        from azure.core.exceptions import ResourceExistsError

        return ResourceExistsError(message)


class MockBlobClient:
    """Mock blob client for individual blob operations."""

    def __init__(self, container: MockContainerClient, blob_name: str) -> None:
        self._container = container
        self.blob_name = blob_name

    def download_blob(self) -> MagicMock:
        """Download blob content."""
        if self.blob_name not in self._container._blobs:
            from azure.core.exceptions import ResourceNotFoundError

            raise ResourceNotFoundError(f"Blob {self.blob_name} not found")

        downloader = MagicMock()
        downloader.readall.return_value = self._container._blobs[self.blob_name]
        downloader.content_as_text.return_value = self._container._blobs[self.blob_name].decode(
            "utf-8"
        )
        return downloader

    def upload_blob(
        self,
        data: bytes | str,
        overwrite: bool = False,
        metadata: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> MagicMock:
        """Upload blob content."""
        return self._container.upload_blob(
            self.blob_name, data, overwrite=overwrite, metadata=metadata, **kwargs
        )

    def delete_blob(self, **kwargs: Any) -> None:
        """Delete the blob."""
        self._container.delete_blob(self.blob_name, **kwargs)

    def exists(self) -> bool:
        """Check if blob exists."""
        return self.blob_name in self._container._blobs

    def get_blob_properties(self) -> MagicMock:
        """Get blob properties."""
        if self.blob_name not in self._container._blobs:
            from azure.core.exceptions import ResourceNotFoundError

            raise ResourceNotFoundError(f"Blob {self.blob_name} not found")

        props = MagicMock()
        props.name = self.blob_name
        props.size = len(self._container._blobs[self.blob_name])
        props.metadata = self._container._metadata.get(self.blob_name, {})
        return props


class MockGraphClient:
    """Mock Microsoft Graph client for testing.

    Provides mock application and service principal operations.
    """

    def __init__(self) -> None:
        self._applications: dict[str, MagicMock] = {}
        self._service_principals: dict[str, MagicMock] = {}
        self._app_counter = 0
        self._sp_counter = 0

    @property
    def applications(self) -> "MockApplicationsCollection":
        """Get applications collection."""
        return MockApplicationsCollection(self)

    @property
    def service_principals(self) -> "MockServicePrincipalsCollection":
        """Get service principals collection."""
        return MockServicePrincipalsCollection(self)


class MockApplicationsCollection:
    """Mock applications collection for Graph client."""

    def __init__(self, graph_client: MockGraphClient) -> None:
        self._graph = graph_client

    def post(self, body: Any) -> MagicMock:
        """Create a new application."""
        self._graph._app_counter += 1
        app = MagicMock()
        app.id = f"app-obj-{self._graph._app_counter}"
        app.app_id = f"app-id-{self._graph._app_counter}"
        app.display_name = getattr(body, "display_name", "test-app")
        self._graph._applications[app.id] = app
        return app

    def by_application_id(self, app_id: str | None = None) -> "MockApplicationBuilder":
        """Get application by ID."""
        return MockApplicationBuilder(self._graph, app_id)

    def get(self, **kwargs: Any) -> MagicMock:
        """List applications."""
        result = MagicMock()
        result.value = list(self._graph._applications.values())
        return result


class MockApplicationBuilder:
    """Mock application builder for Graph operations."""

    def __init__(self, graph_client: MockGraphClient, app_id: str | None) -> None:
        self._graph = graph_client
        self._app_id = app_id

    def delete(self) -> None:
        """Delete the application."""
        if self._app_id and self._app_id in self._graph._applications:
            del self._graph._applications[self._app_id]

    @property
    def add_password(self) -> "MockAddPasswordBuilder":
        """Get add password builder."""
        return MockAddPasswordBuilder()


class MockAddPasswordBuilder:
    """Mock add password builder."""

    def post(self, body: Any = None) -> MagicMock:
        """Add a password credential."""
        credential = MagicMock()
        credential.secret_text = f"mock-secret-{datetime.now(UTC).timestamp()}"
        credential.key_id = "key-id-123"
        credential.end_date_time = datetime.now(UTC).isoformat()
        return credential


class MockServicePrincipalsCollection:
    """Mock service principals collection for Graph client."""

    def __init__(self, graph_client: MockGraphClient) -> None:
        self._graph = graph_client

    def post(self, body: Any) -> MagicMock:
        """Create a new service principal."""
        self._graph._sp_counter += 1
        sp = MagicMock()
        sp.id = f"sp-obj-{self._graph._sp_counter}"
        sp.app_id = getattr(body, "app_id", f"app-id-{self._graph._sp_counter}")
        sp.display_name = getattr(body, "display_name", "test-sp")
        self._graph._service_principals[sp.id] = sp
        return sp

    def by_service_principal_id(self, sp_id: str | None = None) -> "MockServicePrincipalBuilder":
        """Get service principal by ID."""
        return MockServicePrincipalBuilder(self._graph, sp_id)

    def get(self, **kwargs: Any) -> MagicMock:
        """List service principals."""
        result = MagicMock()
        result.value = list(self._graph._service_principals.values())
        return result


class MockServicePrincipalBuilder:
    """Mock service principal builder for Graph operations."""

    def __init__(self, graph_client: MockGraphClient, sp_id: str | None) -> None:
        self._graph = graph_client
        self._sp_id = sp_id

    def delete(self) -> None:
        """Delete the service principal."""
        if self._sp_id and self._sp_id in self._graph._service_principals:
            del self._graph._service_principals[self._sp_id]


class MockServiceBusClient:
    """Mock Azure Service Bus client for testing.

    Provides mock topic and queue operations.
    """

    def __init__(self, namespace: str = "test-namespace") -> None:
        self.namespace = namespace
        self._topics: dict[str, list[dict[str, Any]]] = {}
        self._queues: dict[str, list[dict[str, Any]]] = {}

    def get_topic_sender(self, topic_name: str) -> "MockServiceBusSender":
        """Get a sender for the specified topic."""
        if topic_name not in self._topics:
            self._topics[topic_name] = []
        return MockServiceBusSender(self._topics[topic_name])

    def get_queue_sender(self, queue_name: str) -> "MockServiceBusSender":
        """Get a sender for the specified queue."""
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        return MockServiceBusSender(self._queues[queue_name])

    def get_topic_receiver(
        self, topic_name: str, subscription_name: str
    ) -> "MockServiceBusReceiver":
        """Get a receiver for the specified topic subscription."""
        if topic_name not in self._topics:
            self._topics[topic_name] = []
        return MockServiceBusReceiver(self._topics[topic_name])

    def get_queue_receiver(self, queue_name: str) -> "MockServiceBusReceiver":
        """Get a receiver for the specified queue."""
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        return MockServiceBusReceiver(self._queues[queue_name])


class MockServiceBusSender:
    """Mock Service Bus sender."""

    def __init__(self, message_store: list[dict[str, Any]]) -> None:
        self._messages = message_store

    async def send_messages(self, message: Any) -> None:
        """Send a message."""
        msg_dict = {
            "body": str(message),
            "sent_at": datetime.now(UTC).isoformat(),
        }
        self._messages.append(msg_dict)

    async def __aenter__(self) -> "MockServiceBusSender":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class MockServiceBusReceiver:
    """Mock Service Bus receiver."""

    def __init__(self, message_store: list[dict[str, Any]]) -> None:
        self._messages = message_store

    async def receive_messages(
        self, max_message_count: int = 1, max_wait_time: float = 5.0
    ) -> list[MagicMock]:
        """Receive messages."""
        result = []
        for _ in range(min(max_message_count, len(self._messages))):
            if self._messages:
                msg_data = self._messages.pop(0)
                msg = MagicMock()
                msg.body = msg_data["body"]
                result.append(msg)
        return result

    async def complete_message(self, message: Any) -> None:
        """Complete a message."""
        pass

    async def __aenter__(self) -> "MockServiceBusReceiver":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


# Factory functions for creating mock instances


def create_mock_azure_credential(
    tenant_id: str = "test-tenant-id",
    client_id: str = "test-client-id",
    token: str = "mock-access-token",
) -> MockAzureCredential:
    """Create a mock Azure credential.

    Args:
        tenant_id: Mock tenant ID
        client_id: Mock client ID
        token: Mock access token

    Returns:
        MockAzureCredential instance
    """
    return MockAzureCredential(tenant_id=tenant_id, client_id=client_id, token=token)


def create_mock_keyvault_client(
    initial_secrets: dict[str, str] | None = None,
) -> MockKeyVaultClient:
    """Create a mock Key Vault client.

    Args:
        initial_secrets: Optional dict of secret name -> value to pre-populate

    Returns:
        MockKeyVaultClient instance
    """
    client = MockKeyVaultClient()
    if initial_secrets:
        for name, value in initial_secrets.items():
            client.set_secret(name, value)
    return client


def create_mock_table_client(
    initial_entities: list[dict[str, Any]] | None = None,
) -> MockTableClient:
    """Create a mock Table Storage client.

    Args:
        initial_entities: Optional list of entities to pre-populate

    Returns:
        MockTableClient instance
    """
    import asyncio

    client = MockTableClient()
    if initial_entities:
        for entity in initial_entities:
            asyncio.get_event_loop().run_until_complete(client.create_entity(entity))
    return client


def create_mock_container_client(
    container_name: str = "test-container",
    initial_blobs: dict[str, bytes | str] | None = None,
) -> MockContainerClient:
    """Create a mock Blob Container client.

    Args:
        container_name: Name of the mock container
        initial_blobs: Optional dict of blob name -> content to pre-populate

    Returns:
        MockContainerClient instance
    """
    client = MockContainerClient(container_name=container_name)
    if initial_blobs:
        for name, data in initial_blobs.items():
            client.upload_blob(name, data, overwrite=True)
    return client


def create_mock_graph_client() -> MockGraphClient:
    """Create a mock Microsoft Graph client.

    Returns:
        MockGraphClient instance
    """
    return MockGraphClient()


def create_mock_service_bus_client(
    namespace: str = "test-namespace",
) -> MockServiceBusClient:
    """Create a mock Service Bus client.

    Args:
        namespace: Mock Service Bus namespace

    Returns:
        MockServiceBusClient instance
    """
    return MockServiceBusClient(namespace=namespace)


# Async versions of mock clients for direct pytest-asyncio usage


def create_async_mock_keyvault_client(
    initial_secrets: dict[str, str] | None = None,
) -> AsyncMock:
    """Create an AsyncMock Key Vault client for use with patch.

    This returns an AsyncMock that can be used directly with unittest.mock.patch
    for async code paths.

    Args:
        initial_secrets: Optional dict of secret name -> value

    Returns:
        AsyncMock configured as SecretClient
    """
    mock = AsyncMock()
    secrets: dict[str, str] = initial_secrets or {}

    async def mock_set_secret(name: str, value: str, **kwargs: Any) -> MagicMock:
        secrets[name] = value
        result = MagicMock()
        result.name = name
        result.value = value
        return result

    async def mock_get_secret(name: str, **kwargs: Any) -> MagicMock:
        if name not in secrets:
            from azure.core.exceptions import ResourceNotFoundError

            raise ResourceNotFoundError(f"Secret {name} not found")
        result = MagicMock()
        result.name = name
        result.value = secrets[name]
        return result

    async def mock_begin_delete_secret(name: str, **kwargs: Any) -> MagicMock:
        if name in secrets:
            del secrets[name]
        poller = MagicMock()
        poller.result.return_value = MagicMock()
        return poller

    mock.set_secret = mock_set_secret
    mock.get_secret = mock_get_secret
    mock.begin_delete_secret = mock_begin_delete_secret

    return mock
