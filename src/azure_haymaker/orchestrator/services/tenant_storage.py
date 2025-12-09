"""Tenant-aware storage clients for multi-tenant data isolation.

This module provides storage clients (Blob, Table, Cosmos) that automatically
apply tenant-specific prefixes and filters to ensure data isolation across tenants.

Phase 1 (MVP) - Foundation: Tenant-aware storage with path/partition isolation.
"""

from typing import Any
from uuid import UUID


class TenantAwareBlobClient:
    """Blob storage client with automatic tenant path prefixing.

    Wraps Azure Blob Storage operations to automatically prepend tenant-specific
    prefixes to blob paths, ensuring logical isolation of tenant data.

    In single-tenant mode (tenant_context=None), operates without prefixing
    for backward compatibility.

    Attributes:
        blob_client: Azure Blob ContainerClient or BlobClient
        tenant_context: Optional tenant context (dict) for multi-tenant isolation
    """

    def __init__(self, blob_client, tenant_context: dict[str, Any] | None):
        """Initialize tenant-aware blob client.

        Args:
            blob_client: Azure Blob storage client instance
            tenant_context: Tenant context dict with tenant_id, or None for single-tenant

        Raises:
            ValueError: If tenant_context is invalid or tenant_id is not a valid UUID
        """
        self.blob_client = blob_client

        # Validate tenant_context structure if provided
        if tenant_context is not None:
            if "tenant_id" not in tenant_context:
                raise ValueError("tenant_context must contain 'tenant_id' key")
            # Validate UUID format
            try:
                UUID(tenant_context["tenant_id"])
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"tenant_id must be valid UUID format: {tenant_context['tenant_id']}"
                ) from e

        self.tenant_context = tenant_context

    def _get_prefixed_path(self, blob_name: str) -> str:
        """Get blob path with tenant prefix.

        Args:
            blob_name: Base blob name/path

        Returns:
            Full path with tenant prefix (or original if single-tenant)
        """
        if self.tenant_context:
            tenant_id = self.tenant_context["tenant_id"]
            return f"{tenant_id}/{blob_name}"
        return blob_name

    async def upload_blob(self, blob_name: str, data: bytes) -> None:
        """Upload blob with tenant-prefixed path.

        Args:
            blob_name: Blob name (will be prefixed with tenant_id)
            data: Blob data bytes
        """
        prefixed_path = self._get_prefixed_path(blob_name)
        await self.blob_client.upload_blob(prefixed_path, data, overwrite=True)

    async def download_blob(self, blob_name: str) -> bytes:
        """Download blob using tenant-prefixed path.

        Args:
            blob_name: Blob name (will be prefixed with tenant_id)

        Returns:
            Blob data bytes
        """
        prefixed_path = self._get_prefixed_path(blob_name)

        # For mock client, it may not have get_blob_client method
        if hasattr(self.blob_client, 'download_blob'):
            # Direct download (mock or simpler client)
            download_stream = await self.blob_client.download_blob(prefixed_path)
            return download_stream
        else:
            # Real Azure client pattern
            blob_client = self.blob_client.get_blob_client(prefixed_path)
            download_stream = await blob_client.download_blob()
            return await download_stream.readall()

    async def list_blobs(self, name_starts_with: str | None = None) -> list[str]:
        """List blobs filtered by tenant prefix.

        Args:
            name_starts_with: Optional prefix filter (combined with tenant prefix)

        Returns:
            List of blob names with tenant prefix
        """
        # Build full prefix
        if self.tenant_context:
            tenant_id = self.tenant_context["tenant_id"]
            prefix = f"{tenant_id}/{name_starts_with}" if name_starts_with else f"{tenant_id}/"
        else:
            prefix = name_starts_with

        # List blobs with prefix
        blobs = []
        blob_list = await self.blob_client.list_blobs(name_starts_with=prefix)

        # Handle both async iterator and list responses
        if hasattr(blob_list, '__aiter__'):
            async for blob in blob_list:
                blobs.append(blob.name if hasattr(blob, 'name') else blob)
        else:
            # Mock client returns list
            blobs = blob_list

        return blobs


class TenantAwareTableClient:
    """Table storage client with tenant-prefixed partition keys.

    Wraps Azure Table Storage operations to automatically apply tenant-specific
    partition key prefixes, ensuring data isolation at the partition level.

    Partition key format: {tenant_id}#{base_key}

    In single-tenant mode (tenant_context=None), uses simple partition keys
    without prefixing for backward compatibility.

    Attributes:
        table_client: Azure Table TableClient
        tenant_context: Optional tenant context (dict) for multi-tenant isolation
    """

    def __init__(self, table_client, tenant_context: dict[str, Any] | None):
        """Initialize tenant-aware table client.

        Args:
            table_client: Azure Table storage client instance
            tenant_context: Tenant context dict with tenant_id, or None for single-tenant

        Raises:
            ValueError: If tenant_context is invalid or tenant_id is not a valid UUID
        """
        self.table_client = table_client

        # Validate tenant_context structure if provided
        if tenant_context is not None:
            if "tenant_id" not in tenant_context:
                raise ValueError("tenant_context must contain 'tenant_id' key")
            # Validate UUID format
            try:
                UUID(tenant_context["tenant_id"])
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"tenant_id must be valid UUID format: {tenant_context['tenant_id']}"
                ) from e

        self.tenant_context = tenant_context

    def _get_partition_key(self, base_key: str) -> str:
        """Generate partition key with tenant prefix.

        Args:
            base_key: Base partition key (e.g., run_id)

        Returns:
            Partition key with tenant prefix (or original if single-tenant)
        """
        if self.tenant_context:
            tenant_id = self.tenant_context["tenant_id"]
            return f"{tenant_id}#{base_key}"
        return base_key

    async def create_entity(self, entity: dict[str, Any]) -> None:
        """Create table entity with tenant-prefixed partition key.

        Args:
            entity: Entity dictionary (must have PartitionKey or run_id)
        """
        # Make a copy to avoid modifying original
        entity_copy = entity.copy()

        # Determine partition key
        if "run_id" in entity_copy:
            # Use run_id as base for partition key
            base_key = entity_copy["run_id"]
        elif "PartitionKey" in entity_copy:
            # Use existing PartitionKey as base
            base_key = entity_copy["PartitionKey"]
        else:
            # Fall back to generating a simple key
            base_key = "default"

        # Apply tenant prefix
        entity_copy["PartitionKey"] = self._get_partition_key(base_key)

        # Add tenant_id field for filtering (multi-tenant only)
        if self.tenant_context:
            entity_copy["tenant_id"] = self.tenant_context["tenant_id"]

        # Ensure RowKey exists
        if "RowKey" not in entity_copy:
            entity_copy["RowKey"] = entity_copy.get("id", base_key)

        await self.table_client.create_entity(entity_copy)

    async def query_entities(self, query_filter: str) -> list[dict[str, Any]]:
        """Query entities filtered by tenant_id.

        Args:
            query_filter: OData filter string

        Returns:
            List of matching entities
        """
        # Add tenant filter in multi-tenant mode
        if self.tenant_context:
            tenant_id = self.tenant_context["tenant_id"]
            tenant_filter = f"PartitionKey ge '{tenant_id}#' and PartitionKey lt '{tenant_id}$'"
            full_filter = f"({query_filter}) and {tenant_filter}" if query_filter else tenant_filter
        else:
            full_filter = query_filter

        # Execute query
        entities = []
        result = await self.table_client.query_entities(query_filter=full_filter)

        # Handle both async iterator and list responses
        if hasattr(result, '__aiter__'):
            async for entity in result:
                entities.append(entity)
        else:
            # Mock client returns list
            entities = result

        return entities


class TenantAwareCosmosClient:
    """Cosmos DB client with tenant_id field injection and filtering.

    Wraps Azure Cosmos DB operations to automatically inject tenant_id into
    documents and filter queries by tenant_id, ensuring data isolation.

    Partition key should be set to /tenant_id for optimal performance.

    In single-tenant mode (tenant_context=None), operates without tenant_id
    injection for backward compatibility.

    Attributes:
        cosmos_client: Azure Cosmos DB ContainerProxy
        tenant_context: Optional tenant context (dict) for multi-tenant isolation
        partition_key_path: Partition key path (default: /tenant_id)
    """

    def __init__(
        self,
        cosmos_client,
        tenant_context: dict[str, Any] | None,
        partition_key_path: str = "/tenant_id",
    ):
        """Initialize tenant-aware Cosmos client.

        Args:
            cosmos_client: Azure Cosmos DB container proxy
            tenant_context: Tenant context dict with tenant_id, or None for single-tenant
            partition_key_path: Partition key path (should match container config)

        Raises:
            ValueError: If tenant_context is invalid or tenant_id is not a valid UUID
        """
        self.cosmos_client = cosmos_client

        # Validate tenant_context structure if provided
        if tenant_context is not None:
            if "tenant_id" not in tenant_context:
                raise ValueError("tenant_context must contain 'tenant_id' key")
            # Validate UUID format
            try:
                UUID(tenant_context["tenant_id"])
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"tenant_id must be valid UUID format: {tenant_context['tenant_id']}"
                ) from e

        self.tenant_context = tenant_context
        self.partition_key_path = partition_key_path

    async def create_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Create document with tenant_id field.

        Args:
            item: Document to create

        Returns:
            Created document with tenant_id
        """
        # Make a copy to avoid modifying original
        item_copy = item.copy()

        # Inject tenant_id in multi-tenant mode
        if self.tenant_context:
            item_copy["tenant_id"] = self.tenant_context["tenant_id"]

        # Create item
        created = await self.cosmos_client.create_item(body=item_copy)
        return created

    async def query_items(
        self, query: str, parameters: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Query documents filtered by tenant_id using parameterized queries.

        Args:
            query: SQL query string
            parameters: Optional list of parameter dictionaries with 'name' and 'value' keys

        Returns:
            List of matching documents
        """
        # Add tenant filter in multi-tenant mode using parameterized queries
        if self.tenant_context:
            tenant_id = self.tenant_context["tenant_id"]

            # Add WHERE clause or AND condition for tenant_id
            query_upper = query.upper()
            if "WHERE" in query_upper:
                # Find WHERE position and append AND condition
                where_pos = query_upper.find("WHERE")
                # Insert tenant filter after existing WHERE condition(s)
                before_where = query[: where_pos + 5]  # Include "WHERE"
                after_where = query[where_pos + 5 :]  # Everything after WHERE

                # Use parameterized query to prevent SQL injection
                query_with_filter = f"{before_where} c.tenant_id = @tenantId AND ({after_where.strip()})"
            else:
                # Add WHERE clause with parameterized tenant_id
                query_with_filter = f"{query} WHERE c.tenant_id = @tenantId"

            # Add tenant_id as parameter
            if parameters is None:
                parameters = []
            parameters.append({"name": "@tenantId", "value": tenant_id})
        else:
            query_with_filter = query
            if parameters is None:
                parameters = []

        # Execute query with parameters
        items = []
        result = await self.cosmos_client.query_items(
            query=query_with_filter, parameters=parameters
        )

        # Handle both async iterator and list responses
        if hasattr(result, '__aiter__'):
            async for item in result:
                items.append(item)
        else:
            # Mock client returns list
            items = result

        return items
