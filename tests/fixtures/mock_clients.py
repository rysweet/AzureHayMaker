"""Mock Azure clients for testing cross-tenant orchestration."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from azure.core.exceptions import ResourceNotFoundError


class MockKeyVaultClient:
    """Mock Azure Key Vault SecretClient."""

    def __init__(self):
        self.secrets = {}
        self.get_secret_calls = []

    def get_secret(self, name: str) -> MagicMock:
        """Mock get_secret method that raises ResourceNotFoundError for missing secrets."""
        self.get_secret_calls.append(name)
        if name not in self.secrets:
            raise ResourceNotFoundError(f"Secret {name} not found")

        mock_secret = MagicMock()
        mock_secret.value = self.secrets[name]
        mock_secret.name = name
        return mock_secret

    def set_secret(self, name: str, value: str) -> None:
        """Mock set_secret method."""
        self.secrets[name] = value

    def list_secrets(self) -> list:
        """Mock list_secrets method."""
        return [{"name": name} for name in self.secrets.keys()]


class MockBlobClient:
    """Mock Azure Blob Storage BlobClient."""

    def __init__(self):
        self.blobs = {}
        self.uploaded_blobs = []
        self.downloaded_blobs = []

    async def upload_blob(self, name: str, data: bytes, overwrite: bool = True) -> None:
        """Mock upload_blob method."""
        self.blobs[name] = data
        self.uploaded_blobs.append(name)

    async def download_blob(self, name: str) -> MagicMock:
        """Mock download_blob method."""
        self.downloaded_blobs.append(name)
        if name not in self.blobs:
            raise Exception(f"Blob {name} not found")

        mock_download = MagicMock()
        mock_download.readall = MagicMock(return_value=self.blobs[name])
        return mock_download

    async def list_blobs(self, name_starts_with: str = None) -> list:
        """Mock list_blobs method."""
        if name_starts_with:
            return [name for name in self.blobs.keys() if name.startswith(name_starts_with)]
        return list(self.blobs.keys())


class MockTableClient:
    """Mock Azure Table Storage TableClient."""

    def __init__(self):
        self.entities = []
        self.queries = []

    async def create_entity(self, entity: dict) -> None:
        """Mock create_entity method."""
        self.entities.append(entity)

    async def query_entities(self, query_filter: str) -> list:
        """Mock query_entities method."""
        self.queries.append(query_filter)
        # Simple filter parsing for testing
        if "PartitionKey eq" in query_filter:
            partition_key = query_filter.split("'")[1]
            return [e for e in self.entities if e.get("PartitionKey") == partition_key]

        # Handle partition key range queries for tenant filtering (ge/lt)
        if "PartitionKey ge" in query_filter and "PartitionKey lt" in query_filter:
            # Extract range bounds from filter like "PartitionKey ge 'tenant#' and PartitionKey lt 'tenant$'"
            parts = query_filter.split("'")
            # parts will be: [..., 'tenant#', ..., 'tenant$', ...]
            ge_value = None
            lt_value = None
            for i, part in enumerate(parts):
                if i > 0 and "ge" in parts[i - 1]:
                    ge_value = part
                if i > 0 and "lt" in parts[i - 1]:
                    lt_value = part

            if ge_value and lt_value:
                # Filter entities with partition keys in range [ge_value, lt_value)
                return [
                    e
                    for e in self.entities
                    if ge_value <= e.get("PartitionKey", "") < lt_value
                ]

        return self.entities

    async def get_entity(self, partition_key: str, row_key: str) -> dict:
        """Mock get_entity method."""
        for entity in self.entities:
            if entity.get("PartitionKey") == partition_key and entity.get("RowKey") == row_key:
                return entity
        raise Exception(f"Entity not found: {partition_key}/{row_key}")


class MockCosmosClient:
    """Mock Azure Cosmos DB ContainerClient."""

    def __init__(self):
        self.documents = []
        self.queries = []

    async def create_item(self, body: dict) -> dict:
        """Mock create_item method."""
        doc = body.copy()
        doc["id"] = doc.get("id", str(uuid4()))
        self.documents.append(doc)
        return doc

    async def query_items(
        self, query: str, parameters=None, enable_cross_partition_query: bool = False
    ) -> list:
        """Mock query_items method with parameter support."""
        self.queries.append(query)

        # Handle parameterized queries
        if "WHERE" in query and "tenant_id" in query:
            # Check if using parameterized query (@tenantId)
            if "@tenantId" in query and parameters:
                # Find tenant_id parameter value
                tenant_id = None
                for param in parameters:
                    if param.get("name") == "@tenantId":
                        tenant_id = param.get("value")
                        break

                if tenant_id:
                    return [d for d in self.documents if d.get("tenant_id") == tenant_id]
            # Old-style string interpolation (for backward compatibility)
            elif "'" in query:
                tenant_id = query.split("'")[1]
                return [d for d in self.documents if d.get("tenant_id") == tenant_id]

        return self.documents

    async def read_item(self, item: str, partition_key: str) -> dict:
        """Mock read_item method."""
        for doc in self.documents:
            if doc.get("id") == item and doc.get("tenant_id") == partition_key:
                return doc
        raise Exception(f"Document not found: {item}")


class MockDurableFunctionsContext:
    """Mock Durable Functions orchestration context."""

    def __init__(self):
        self.instance_id = str(uuid4())
        self.is_replaying = False
        self.activities = []
        self.sub_orchestrators = []

    async def call_activity(self, name: str, input_data: Any) -> Any:
        """Mock call_activity method."""
        self.activities.append({"name": name, "input": input_data})
        return {"status": "completed", "result": f"Activity {name} completed"}

    async def call_sub_orchestrator(self, name: str, input_data: Any, instance_id: str = None) -> Any:
        """Mock call_sub_orchestrator method."""
        orchestrator_id = instance_id or str(uuid4())
        self.sub_orchestrators.append({
            "name": name,
            "input": input_data,
            "instance_id": orchestrator_id,
        })
        return {"status": "completed", "instance_id": orchestrator_id}

    def create_timer(self, fire_at: Any) -> AsyncMock:
        """Mock create_timer method."""
        return AsyncMock()


def create_mock_credential():
    """Create a mock DefaultAzureCredential."""
    mock = MagicMock()
    mock.get_token = MagicMock(return_value=MagicMock(token="fake-token"))
    return mock


def create_sample_tenant_credentials():
    """Create sample tenant credentials for testing."""
    return {
        "client_id": str(uuid4()),
        "client_secret": f"secret-{uuid4()}",  # Generate unique secret each time
        "tenant_id": str(uuid4()),
        "subscription_id": str(uuid4()),
    }
