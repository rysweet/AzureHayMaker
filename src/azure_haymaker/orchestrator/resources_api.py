"""Resources API endpoint for HayMaker orchestrator."""

import logging
from datetime import datetime

import azure.functions as func
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, Field

app = func.FunctionApp()
logger = logging.getLogger(__name__)


class ResourceInfo(BaseModel):
    """Resource information."""

    id: str
    name: str
    type: str
    scenario: str
    execution_id: str
    created_at: datetime
    deleted_at: datetime | None = None
    status: str = "created"
    tags: dict[str, str] = Field(default_factory=dict)


async def query_resources_from_table(
    table_client,
    execution_id: str | None = None,
    scenario: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[ResourceInfo]:
    """Query resources from Table Storage.

    Args:
        table_client: Table client
        execution_id: Optional execution ID filter
        scenario: Optional scenario filter
        status: Optional status filter (created, deleted)
        limit: Maximum number of results

    Returns:
        List of resource information
    """
    resources = []

    try:
        # Build query filter
        filters = []

        if execution_id:
            filters.append(f"execution_id eq '{execution_id}'")

        if scenario:
            filters.append(f"scenario eq '{scenario}'")

        if status:
            filters.append(f"status eq '{status}'")

        query_filter = " and ".join(filters) if filters else None

        # Query table
        entities = table_client.query_entities(
            query_filter=query_filter,
            select=[
                "resource_id",
                "resource_name",
                "resource_type",
                "scenario",
                "execution_id",
                "created_at",
                "deleted_at",
                "status",
            ],
        )

        # Convert to ResourceInfo models
        for entity in entities:
            if len(resources) >= limit:
                break

            try:
                # Parse tags from entity
                tags = {}
                for key, value in entity.items():
                    if key.startswith("tag_"):
                        tag_name = key[4:]  # Remove 'tag_' prefix
                        tags[tag_name] = value

                resource = ResourceInfo(
                    id=entity.get("resource_id", entity.get("RowKey", "unknown")),
                    name=entity.get("resource_name", "unknown"),
                    type=entity.get("resource_type", "unknown"),
                    scenario=entity.get("scenario", "unknown"),
                    execution_id=entity.get("execution_id", "unknown"),
                    created_at=entity.get("created_at", datetime.now()),
                    deleted_at=entity.get("deleted_at"),
                    status=entity.get("status", "created"),
                    tags=tags,
                )
                resources.append(resource)
            except Exception as e:
                logger.warning(f"Error parsing resource entity: {e}")
                continue

    except Exception as e:
        logger.error(f"Error querying resources from table: {e}")
        raise

    return resources


@app.route(route="resources", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def list_resources(req: func.HttpRequest) -> func.HttpResponse:
    """List all resources.

    Query Parameters:
        execution_id: Optional execution ID filter
        scenario: Optional scenario filter
        status: Optional status filter (created, deleted)
        limit: Maximum number of results (default: 100)

    Response:
        200 OK: {
            "resources": [
                {
                    "id": str,
                    "name": str,
                    "type": str,
                    "scenario": str,
                    "execution_id": str,
                    "created_at": str (ISO 8601),
                    "deleted_at": str (ISO 8601) | null,
                    "status": str,
                    "tags": {
                        "key": "value"
                    }
                }
            ]
        }

        500 Internal Server Error: Server error

    Example:
        GET /api/v1/resources
        GET /api/v1/resources?scenario=compute-01
        GET /api/v1/resources?execution_id=exec-123
        GET /api/v1/resources?status=created
    """
    try:
        # Parse query parameters
        execution_id = req.params.get("execution_id")
        scenario = req.params.get("scenario")
        status = req.params.get("status")
        limit = int(req.params.get("limit", "100"))

        # Get Table Storage configuration
        import os

        table_account_name = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
        table_name = os.getenv("RESOURCES_TABLE_NAME", "resources")

        if not table_account_name:
            logger.error("TABLE_STORAGE_ACCOUNT_NAME not configured")
            return func.HttpResponse(
                body='{"error": "Resources storage not configured"}',
                status_code=500,
                mimetype="application/json",
            )

        # Create Table Storage client (using managed identity)
        credential = DefaultAzureCredential()
        table_service_client = TableServiceClient(
            endpoint=f"https://{table_account_name}.table.core.windows.net",
            credential=credential,
        )
        table_client = table_service_client.get_table_client(table_name)

        # Query resources
        resources = await query_resources_from_table(
            table_client,
            execution_id=execution_id,
            scenario=scenario,
            status=status,
            limit=limit,
        )

        # Build response
        response = {"resources": [resource.model_dump(mode="json") for resource in resources]}

        return func.HttpResponse(
            body=str(response),
            status_code=200,
            mimetype="application/json",
        )

    except ValueError as e:
        return func.HttpResponse(
            body=f'{{"error": "Invalid parameter: {str(e)}"}}',
            status_code=400,
            mimetype="application/json",
        )
    except Exception as e:
        logger.exception("Error listing resources")
        return func.HttpResponse(
            body=f'{{"error": "{str(e)}"}}',
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="resources/{resource_id}", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def get_resource(req: func.HttpRequest) -> func.HttpResponse:
    """Get details for a specific resource.

    Path Parameters:
        resource_id: Resource ID

    Response:
        200 OK: ResourceInfo object
        404 Not Found: Resource not found
        500 Internal Server Error: Server error

    Example:
        GET /api/v1/resources/resource-123
    """
    try:
        # Parse path parameter
        resource_id = req.route_params.get("resource_id")

        if not resource_id:
            return func.HttpResponse(
                body='{"error": "resource_id is required"}',
                status_code=400,
                mimetype="application/json",
            )

        # Get Table Storage configuration
        import os

        table_account_name = os.getenv("TABLE_STORAGE_ACCOUNT_NAME")
        table_name = os.getenv("RESOURCES_TABLE_NAME", "resources")

        if not table_account_name:
            logger.error("TABLE_STORAGE_ACCOUNT_NAME not configured")
            return func.HttpResponse(
                body='{"error": "Resources storage not configured"}',
                status_code=500,
                mimetype="application/json",
            )

        # Create Table Storage client (using managed identity)
        credential = DefaultAzureCredential()
        table_service_client = TableServiceClient(
            endpoint=f"https://{table_account_name}.table.core.windows.net",
            credential=credential,
        )
        table_client = table_service_client.get_table_client(table_name)

        # Query specific resource
        try:
            entity = table_client.get_entity(
                partition_key="resources",  # Assuming all resources use same partition
                row_key=resource_id,
            )

            # Parse tags
            tags = {}
            for key, value in entity.items():
                if key.startswith("tag_"):
                    tag_name = key[4:]
                    tags[tag_name] = value

            # Build resource info
            resource = ResourceInfo(
                id=entity.get("resource_id", resource_id),
                name=entity.get("resource_name", "unknown"),
                type=entity.get("resource_type", "unknown"),
                scenario=entity.get("scenario", "unknown"),
                execution_id=entity.get("execution_id", "unknown"),
                created_at=entity.get("created_at", datetime.now()),
                deleted_at=entity.get("deleted_at"),
                status=entity.get("status", "created"),
                tags=tags,
            )

            return func.HttpResponse(
                body=resource.model_dump_json(),
                status_code=200,
                mimetype="application/json",
            )

        except Exception:
            logger.warning(f"Resource not found: {resource_id}")
            return func.HttpResponse(
                body='{"error": "Resource not found"}',
                status_code=404,
                mimetype="application/json",
            )

    except Exception as e:
        logger.exception("Error retrieving resource")
        return func.HttpResponse(
            body=f'{{"error": "{str(e)}"}}',
            status_code=500,
            mimetype="application/json",
        )
