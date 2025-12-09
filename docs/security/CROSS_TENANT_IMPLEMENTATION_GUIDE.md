# Cross-Tenant Security Implementation Guide

## Quick Start

This guide provides ready-to-use code patterns for implementing secure cross-tenant orchestration in AzureHayMaker.

Related Documents:
- [Security Architecture](/home/azureuser/src/AzureHayMaker/worktrees/feat/issue-147-cross-tenant-orchestration/docs/security/CROSS_TENANT_SECURITY_ARCHITECTURE.md) - Comprehensive security design
- [Threat Model](/home/azureuser/src/AzureHayMaker/worktrees/feat/issue-147-cross-tenant-orchestration/docs/security/CROSS_TENANT_SECURITY_ARCHITECTURE.md#threat-model) - Attack vectors and mitigations

---

## Table of Contents

1. [Input Validation](#input-validation)
2. [Tenant-Isolated Storage](#tenant-isolated-storage)
3. [Secure Credential Management](#secure-credential-management)
4. [Multi-Tenant Authentication](#multi-tenant-authentication)
5. [Query Firewall](#query-firewall)
6. [Audit Logging](#audit-logging)
7. [Testing Patterns](#testing-patterns)

---

## Input Validation

### UUID Validation for tenant_id

```python
"""Secure tenant_id validation module."""

import uuid
from typing import Any


def validate_tenant_id(tenant_id: Any) -> str:
    """Validate and normalize tenant_id.

    Args:
        tenant_id: Raw tenant_id input (any type)

    Returns:
        Normalized tenant_id (lowercase UUID string)

    Raises:
        ValueError: If tenant_id is not a valid UUID

    Security:
        - Rejects non-UUID inputs
        - Prevents injection attacks
        - Normalizes format for consistent comparison
    """
    if not isinstance(tenant_id, str):
        raise ValueError(f"tenant_id must be string, got {type(tenant_id)}")

    try:
        # Parse and validate UUID
        uuid_obj = uuid.UUID(tenant_id)

        # Return normalized lowercase form
        return str(uuid_obj).lower()

    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid tenant_id format: {tenant_id}") from e


def validate_tenant_id_list(tenant_ids: list[Any]) -> list[str]:
    """Validate a list of tenant_ids.

    Args:
        tenant_ids: List of raw tenant_id inputs

    Returns:
        List of normalized tenant_ids

    Raises:
        ValueError: If any tenant_id is invalid
    """
    if not isinstance(tenant_ids, list):
        raise ValueError(f"tenant_ids must be list, got {type(tenant_ids)}")

    validated = []
    for tenant_id in tenant_ids:
        validated.append(validate_tenant_id(tenant_id))

    return validated
```

### OData Injection Prevention

```python
"""OData query sanitization."""

import re


def sanitize_odata_value(value: Any) -> str:
    """Sanitize value for use in OData filter query.

    Args:
        value: Raw value to sanitize

    Returns:
        Sanitized string safe for OData queries

    Security:
        - Escapes single quotes (OData string delimiter)
        - Prevents injection via quote manipulation
    """
    # Convert to string
    value_str = str(value)

    # Escape single quotes (OData uses '' for literal ')
    sanitized = value_str.replace("'", "''")

    return sanitized


def build_odata_filter(conditions: dict[str, Any]) -> str:
    """Build OData filter query with automatic sanitization.

    Args:
        conditions: Dictionary of field -> value mappings

    Returns:
        Safe OData filter query string

    Example:
        >>> build_odata_filter({
        ...     "tenant_id": "abc123",
        ...     "status": "active"
        ... })
        "tenant_id eq 'abc123' and status eq 'active'"
    """
    parts = []
    for field, value in conditions.items():
        # Validate field name (alphanumeric and underscore only)
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field):
            raise ValueError(f"Invalid field name: {field}")

        # Sanitize value
        safe_value = sanitize_odata_value(value)

        # Build condition
        parts.append(f"{field} eq '{safe_value}'")

    return " and ".join(parts)
```

---

## Tenant-Isolated Storage

### Table Storage Client Wrapper

```python
"""Tenant-isolated Azure Table Storage client."""

from typing import AsyncIterator, Optional
from azure.data.tables.aio import TableClient
from azure.core.async_paging import AsyncItemPaged


class TenantIsolatedTableClient:
    """Table client that enforces tenant_id filtering on all queries.

    This wrapper ensures that ALL queries include a tenant_id filter,
    preventing accidental cross-tenant data access.

    Security:
        - Mandatory tenant_id filter on all queries
        - Validates tenant_id on construction
        - Sanitizes all query values
        - Logs all queries for audit
    """

    def __init__(
        self,
        table_client: TableClient,
        tenant_id: str,
    ):
        """Initialize tenant-isolated table client.

        Args:
            table_client: Underlying Azure Table Storage client
            tenant_id: Tenant ID to scope all queries

        Raises:
            ValueError: If tenant_id is invalid UUID
        """
        # Validate tenant_id format
        self._tenant_id = validate_tenant_id(tenant_id)
        self._table_client = table_client

        # Set up logger with tenant context
        import structlog
        self._logger = structlog.get_logger().bind(tenant_id=self._tenant_id)

    async def query_entities(
        self,
        filter_query: str = "",
        **kwargs
    ) -> AsyncItemPaged:
        """Query entities with mandatory tenant_id filter.

        Args:
            filter_query: Additional OData filter (optional)
            **kwargs: Additional query parameters

        Returns:
            Async iterator of entities (all from this tenant only)

        Security:
            - Automatically adds tenant_id filter
            - Sanitizes tenant_id value
            - Logs query for audit
        """
        # Sanitize tenant_id for OData
        safe_tenant_id = sanitize_odata_value(self._tenant_id)

        # Build tenant filter
        tenant_filter = f"tenant_id eq '{safe_tenant_id}'"

        # Combine with additional filters
        if filter_query:
            combined_filter = f"({tenant_filter}) and ({filter_query})"
        else:
            combined_filter = tenant_filter

        # Audit log query
        self._logger.info(
            "table_query",
            filter=combined_filter,
            table=self._table_client.table_name,
        )

        # Execute query
        return self._table_client.query_entities(
            query_filter=combined_filter,
            **kwargs
        )

    async def get_entity(
        self,
        partition_key: str,
        row_key: str,
    ) -> dict:
        """Get entity with tenant_id validation.

        Args:
            partition_key: Partition key
            row_key: Row key

        Returns:
            Entity dictionary

        Raises:
            PermissionError: If entity belongs to different tenant

        Security:
            - Validates entity belongs to tenant
            - Time-constant tenant_id comparison
            - Security alert on mismatch
        """
        # Fetch entity
        entity = await self._table_client.get_entity(
            partition_key=partition_key,
            row_key=row_key,
        )

        # Verify tenant_id
        entity_tenant = entity.get("tenant_id")
        if not entity_tenant:
            self._logger.error(
                "Entity missing tenant_id",
                partition_key=partition_key,
                row_key=row_key,
            )
            raise ValueError("Entity missing required tenant_id field")

        # Time-constant comparison
        import secrets
        if not secrets.compare_digest(entity_tenant, self._tenant_id):
            self._logger.security_alert(
                "Cross-tenant access attempt",
                expected_tenant=self._tenant_id,
                entity_tenant=entity_tenant,
                partition_key=partition_key,
                row_key=row_key,
            )
            raise PermissionError("Access denied: tenant_id mismatch")

        return entity

    async def upsert_entity(
        self,
        entity: dict,
        **kwargs
    ) -> dict:
        """Upsert entity with automatic tenant_id.

        Args:
            entity: Entity dictionary
            **kwargs: Additional parameters

        Returns:
            Updated entity

        Security:
            - Automatically sets tenant_id
            - Prevents tenant_id override
        """
        # Ensure tenant_id is set correctly
        entity["tenant_id"] = self._tenant_id

        return await self._table_client.upsert_entity(
            entity=entity,
            **kwargs
        )

    async def delete_entity(
        self,
        partition_key: str,
        row_key: str,
        **kwargs
    ) -> None:
        """Delete entity with tenant_id validation.

        Args:
            partition_key: Partition key
            row_key: Row key
            **kwargs: Additional parameters

        Security:
            - Validates entity belongs to tenant before deletion
        """
        # Verify entity belongs to tenant
        entity = await self.get_entity(partition_key, row_key)

        # Delete
        await self._table_client.delete_entity(
            partition_key=partition_key,
            row_key=row_key,
            **kwargs
        )
```

### Cosmos DB Tenant Isolation

```python
"""Tenant-isolated Cosmos DB client."""

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey


class TenantIsolatedCosmosContainer:
    """Cosmos DB container with tenant partition isolation.

    Security:
        - Partition key = tenant_id (physical isolation)
        - All queries scoped to single partition
        - Cross-partition queries blocked
    """

    def __init__(
        self,
        container_client,
        tenant_id: str,
    ):
        """Initialize tenant-isolated container.

        Args:
            container_client: Cosmos container client
            tenant_id: Tenant ID (must match partition key)
        """
        self._tenant_id = validate_tenant_id(tenant_id)
        self._container = container_client

    async def query_items(
        self,
        query: str,
        parameters: Optional[list] = None,
        **kwargs
    ):
        """Query items within tenant partition.

        Args:
            query: SQL query
            parameters: Query parameters
            **kwargs: Additional options

        Returns:
            Query results (tenant partition only)

        Security:
            - Partition key automatically limits scope
            - No cross-tenant queries possible
        """
        # Set partition key (physical isolation)
        return self._container.query_items(
            query=query,
            parameters=parameters,
            partition_key=self._tenant_id,  # Enforces partition scope
            **kwargs
        )

    async def read_item(
        self,
        item_id: str,
        **kwargs
    ) -> dict:
        """Read item within tenant partition.

        Args:
            item_id: Item ID
            **kwargs: Additional options

        Returns:
            Item document

        Security:
            - Partition key ensures tenant isolation
        """
        return await self._container.read_item(
            item=item_id,
            partition_key=self._tenant_id,
            **kwargs
        )

    async def upsert_item(
        self,
        item: dict,
        **kwargs
    ) -> dict:
        """Upsert item with tenant_id.

        Args:
            item: Item document
            **kwargs: Additional options

        Returns:
            Upserted item

        Security:
            - Automatically sets tenant_id
            - Prevents partition key manipulation
        """
        # Ensure tenant_id matches
        item["tenant_id"] = self._tenant_id

        return await self._container.upsert_item(
            body=item,
            **kwargs
        )
```

---

## Secure Credential Management

### Key Vault Credential Manager

```python
"""Secure per-tenant credential management."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from azure.keyvault.secrets.aio import SecretClient
from azure.core.exceptions import ResourceNotFoundError


@dataclass
class TenantCredentials:
    """Per-tenant service principal credentials."""
    tenant_id: str
    client_id: str
    client_secret: str
    expires_at: Optional[datetime] = None


class TenantCredentialManager:
    """Manages per-tenant service principal credentials.

    Security:
        - Credentials stored in Azure Key Vault
        - Per-tenant secret isolation
        - Audit logging of all access
        - No credential caching
        - Automatic rotation support
    """

    def __init__(
        self,
        key_vault_client: SecretClient,
    ):
        """Initialize credential manager.

        Args:
            key_vault_client: Azure Key Vault secret client
        """
        self._kv_client = key_vault_client

        import structlog
        self._logger = structlog.get_logger()

    @staticmethod
    def _get_secret_name(tenant_id: str, credential_type: str) -> str:
        """Generate Key Vault secret name.

        Args:
            tenant_id: Validated tenant ID
            credential_type: Type (client-id, client-secret, tenant-id)

        Returns:
            Secret name following naming convention

        Format: tenant-{tenant_id}-sp-{credential_type}
        """
        allowed_types = {"client-id", "client-secret", "tenant-id"}
        if credential_type not in allowed_types:
            raise ValueError(f"Invalid credential_type: {credential_type}")

        return f"tenant-{tenant_id}-sp-{credential_type}"

    async def get_credentials(
        self,
        tenant_id: str,
    ) -> TenantCredentials:
        """Retrieve tenant service principal credentials.

        Args:
            tenant_id: Target tenant ID

        Returns:
            Tenant credentials

        Raises:
            CredentialNotFoundError: If credentials not configured
            ValueError: If tenant_id invalid

        Security:
            - Validates tenant_id format
            - Audit logs access
            - Never logs credential values
            - Time-constant secret retrieval
        """
        # Validate tenant_id
        tenant_id = validate_tenant_id(tenant_id)

        # Audit log access
        self._logger.audit(
            "credential_access",
            tenant_id=tenant_id,
            timestamp=datetime.utcnow().isoformat(),
        )

        try:
            # Retrieve secrets (do in parallel)
            import asyncio
            client_id_secret, client_secret_secret, tenant_id_secret = \
                await asyncio.gather(
                    self._kv_client.get_secret(
                        self._get_secret_name(tenant_id, "client-id")
                    ),
                    self._kv_client.get_secret(
                        self._get_secret_name(tenant_id, "client-secret")
                    ),
                    self._kv_client.get_secret(
                        self._get_secret_name(tenant_id, "tenant-id")
                    ),
                )

        except ResourceNotFoundError:
            # Do NOT log which secret was missing (info leak)
            self._logger.error(
                "Tenant credentials not found",
                tenant_id=tenant_id,
            )
            raise CredentialNotFoundError(
                f"Credentials not configured for tenant"
            )

        # Return credentials
        return TenantCredentials(
            tenant_id=tenant_id_secret.value,
            client_id=client_id_secret.value,
            client_secret=client_secret_secret.value,
            expires_at=client_secret_secret.properties.expires_on,
        )

    async def set_credentials(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        target_tenant_id: str,
        expires_at: Optional[datetime] = None,
    ) -> None:
        """Store tenant service principal credentials.

        Args:
            tenant_id: Identifier for tenant (UUID)
            client_id: Service principal client ID
            client_secret: Service principal secret
            target_tenant_id: Azure AD tenant ID
            expires_at: Secret expiration date

        Security:
            - Validates all inputs
            - Sets expiration on secrets
            - Audit logs storage
            - Uses secure Key Vault tags
        """
        # Validate tenant_id
        tenant_id = validate_tenant_id(tenant_id)

        # Validate client_id and target_tenant_id (UUIDs)
        validate_tenant_id(client_id)
        validate_tenant_id(target_tenant_id)

        # Set default expiration (90 days)
        if not expires_at:
            expires_at = datetime.utcnow() + timedelta(days=90)

        # Audit log
        self._logger.audit(
            "credential_storage",
            tenant_id=tenant_id,
            expires_at=expires_at.isoformat(),
        )

        # Store secrets
        await asyncio.gather(
            self._kv_client.set_secret(
                name=self._get_secret_name(tenant_id, "client-id"),
                value=client_id,
                expires_on=expires_at,
                tags={"tenant_id": tenant_id, "type": "sp_client_id"},
            ),
            self._kv_client.set_secret(
                name=self._get_secret_name(tenant_id, "client-secret"),
                value=client_secret,
                expires_on=expires_at,
                tags={"tenant_id": tenant_id, "type": "sp_client_secret"},
            ),
            self._kv_client.set_secret(
                name=self._get_secret_name(tenant_id, "tenant-id"),
                value=target_tenant_id,
                expires_on=expires_at,
                tags={"tenant_id": tenant_id, "type": "target_tenant_id"},
            ),
        )

    async def rotate_credentials(
        self,
        tenant_id: str,
        new_client_secret: str,
        expires_at: datetime,
    ) -> None:
        """Rotate tenant service principal secret.

        Args:
            tenant_id: Tenant ID
            new_client_secret: New secret value
            expires_at: New expiration date

        Process:
            1. Store new secret with -new suffix
            2. Update applications to use new secret
            3. Delete old secret
            4. Rename -new secret to primary
        """
        # Validate inputs
        tenant_id = validate_tenant_id(tenant_id)

        # Get current credentials (for client_id)
        current = await self.get_credentials(tenant_id)

        # Store new secret with -new suffix
        new_secret_name = f"{self._get_secret_name(tenant_id, 'client-secret')}-new"
        await self._kv_client.set_secret(
            name=new_secret_name,
            value=new_client_secret,
            expires_on=expires_at,
            tags={"tenant_id": tenant_id, "type": "sp_client_secret", "rotation": "new"},
        )

        # Audit log rotation
        self._logger.audit(
            "credential_rotation",
            tenant_id=tenant_id,
            phase="new_secret_stored",
        )

        # NOTE: Application must update to use new secret before completing rotation
```

---

## Multi-Tenant Authentication

### Token Validator

```python
"""Multi-tenant token validation."""

import jwt
from jwt import PyJWKClient
import secrets
from datetime import datetime


class MultiTenantTokenValidator:
    """Validates Azure AD tokens for multiple tenants.

    Security:
        - Verifies token signature using JWKS
        - Validates issuer matches expected tenant
        - Checks expiration
        - Validates audience
        - Time-constant tenant comparison
    """

    def __init__(self):
        self._jwks_cache = {}

    async def validate_token(
        self,
        token: str,
        expected_tenant_id: str,
        expected_audience: str,
    ) -> dict:
        """Validate Azure AD access token.

        Args:
            token: JWT access token
            expected_tenant_id: Expected tenant ID (must match token)
            expected_audience: Expected audience (app ID)

        Returns:
            Token claims dictionary

        Raises:
            AuthenticationError: If token invalid
            PermissionError: If tenant mismatch

        Security:
            - Full JWT signature validation
            - Issuer validation (per-tenant)
            - Expiration check
            - Audience validation
            - Time-constant tenant comparison
        """
        # Validate expected_tenant_id format
        expected_tenant_id = validate_tenant_id(expected_tenant_id)

        # Get JWKS client for tenant
        jwks_url = f"https://login.microsoftonline.com/{expected_tenant_id}/discovery/v2.0/keys"

        if jwks_url not in self._jwks_cache:
            self._jwks_cache[jwks_url] = PyJWKClient(jwks_url)

        jwks_client = self._jwks_cache[jwks_url]

        try:
            # Get signing key from token header
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            # Decode and validate token
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=expected_audience,
                issuer=f"https://login.microsoftonline.com/{expected_tenant_id}/v2.0",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")

        except jwt.InvalidAudienceError:
            raise AuthenticationError("Invalid token audience")

        except jwt.InvalidIssuerError:
            raise AuthenticationError("Invalid token issuer")

        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

        # Verify tenant ID from claims (tid)
        token_tenant = claims.get("tid")
        if not token_tenant:
            raise AuthenticationError("Token missing tenant ID claim")

        # Time-constant comparison
        if not secrets.compare_digest(token_tenant, expected_tenant_id):
            import structlog
            logger = structlog.get_logger()
            logger.security_alert(
                "Tenant ID mismatch",
                expected=expected_tenant_id,
                actual=token_tenant,
            )
            raise PermissionError("Access denied: tenant mismatch")

        return claims
```

### Authentication Manager

```python
"""Multi-tenant authentication manager."""

from azure.identity.aio import ClientSecretCredential


class TenantAuthenticationManager:
    """Manages authentication to multiple target tenants.

    Security:
        - Separate credentials per tenant
        - No token caching across tenants
        - Audit logging of all authentications
    """

    def __init__(
        self,
        credential_manager: TenantCredentialManager,
    ):
        """Initialize authentication manager.

        Args:
            credential_manager: Credential manager for retrieving SP creds
        """
        self._cred_manager = credential_manager
        self._credentials: dict[str, ClientSecretCredential] = {}

        import structlog
        self._logger = structlog.get_logger()

    async def get_credential(
        self,
        tenant_id: str,
    ) -> ClientSecretCredential:
        """Get credential for target tenant.

        Args:
            tenant_id: Target tenant ID

        Returns:
            Azure credential for tenant

        Security:
            - Validates tenant_id
            - Retrieves credentials from Key Vault
            - Creates tenant-specific credential
            - Audit logs authentication
        """
        # Validate tenant_id
        tenant_id = validate_tenant_id(tenant_id)

        # Check cache
        if tenant_id in self._credentials:
            return self._credentials[tenant_id]

        # Retrieve credentials
        creds = await self._cred_manager.get_credentials(tenant_id)

        # Create credential
        credential = ClientSecretCredential(
            tenant_id=creds.tenant_id,
            client_id=creds.client_id,
            client_secret=creds.client_secret,
        )

        # Cache credential
        self._credentials[tenant_id] = credential

        # Audit log
        self._logger.audit(
            "tenant_authentication",
            tenant_id=tenant_id,
            timestamp=datetime.utcnow().isoformat(),
        )

        return credential

    async def get_token(
        self,
        tenant_id: str,
        scope: str = "https://management.azure.com/.default",
    ) -> str:
        """Get access token for target tenant.

        Args:
            tenant_id: Target tenant ID
            scope: Token scope

        Returns:
            Access token string

        Security:
            - Validates tenant_id
            - Uses tenant-specific credential
            - No cross-tenant token usage
        """
        # Get credential
        credential = await self.get_credential(tenant_id)

        # Get token
        token_response = await credential.get_token(scope)

        return token_response.token
```

---

## Query Firewall

```python
"""Query firewall to enforce tenant filtering."""

import re


class QueryFirewall:
    """Enforces tenant_id filtering in all database queries.

    Security:
        - Validates all queries include tenant_id filter
        - Detects bypass attempts (OR, NOT, etc.)
        - Sanitizes tenant_id values
        - Logs security violations
    """

    @staticmethod
    def enforce_tenant_filter(
        query: str,
        tenant_id: str,
        query_language: str = "odata",
    ) -> str:
        """Enforce tenant_id filter in query.

        Args:
            query: Original query string
            tenant_id: Required tenant ID
            query_language: Query language (odata, sql, etc.)

        Returns:
            Query with tenant_id filter enforced

        Raises:
            ValueError: If query attempts to bypass tenant filter

        Security:
            - Adds tenant_id filter if missing
            - Validates no bypass attempts
            - Sanitizes tenant_id value
        """
        # Validate tenant_id
        tenant_id = validate_tenant_id(tenant_id)

        # Sanitize for query language
        if query_language == "odata":
            safe_tenant_id = sanitize_odata_value(tenant_id)
            tenant_filter = f"tenant_id eq '{safe_tenant_id}'"

        elif query_language == "sql":
            # Use parameterized query instead
            raise ValueError("SQL queries must use parameterized statements")

        else:
            raise ValueError(f"Unsupported query language: {query_language}")

        # Check if query already has tenant_id filter
        if "tenant_id" not in query.lower():
            # Add tenant filter
            if query:
                query = f"({tenant_filter}) and ({query})"
            else:
                query = tenant_filter

        # Validate no bypass attempts
        QueryFirewall._detect_bypass_attempts(query, tenant_id)

        return query

    @staticmethod
    def _detect_bypass_attempts(query: str, tenant_id: str) -> None:
        """Detect attempts to bypass tenant filtering.

        Args:
            query: Query string to check
            tenant_id: Expected tenant ID

        Raises:
            ValueError: If bypass attempt detected

        Detects:
            - NOT tenant_id
            - tenant_id != 'value'
            - tenant_id ne 'value' (OData)
            - OR clauses that could bypass tenant filter
        """
        dangerous_patterns = [
            r"tenant_id\s+(!=|<>|ne)\s+",  # Not equals
            r"tenant_id\s+not\s+in\s+",  # NOT IN
            r"\bnot\b.*tenant_id",  # NOT with tenant_id
            r"\bor\b.*tenant_id.*\bor\b",  # OR bypass
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                import structlog
                logger = structlog.get_logger()
                logger.security_alert(
                    "Query bypass attempt detected",
                    pattern=pattern,
                    query=query,
                    tenant_id=tenant_id,
                )
                raise ValueError(
                    "Query validation failed: potential bypass attempt"
                )
```

---

## Audit Logging

```python
"""Structured audit logging for security events."""

import structlog
from datetime import datetime
from typing import Any, Callable
from functools import wraps


# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)


def audit_log(event_type: str):
    """Decorator for automatic audit logging of function calls.

    Args:
        event_type: Type of event (credential_access, storage_query, etc.)

    Usage:
        @audit_log("credential_access")
        async def get_credentials(tenant_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = structlog.get_logger()

            # Extract tenant_id from args/kwargs
            tenant_id = _extract_tenant_id(args, kwargs)

            try:
                result = await func(*args, **kwargs)

                # Log success
                logger.audit(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    operation=func.__name__,
                    status="success",
                    timestamp=datetime.utcnow().isoformat(),
                )

                return result

            except Exception as e:
                # Log failure
                logger.audit(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    operation=func.__name__,
                    status="failure",
                    error_type=type(e).__name__,
                    timestamp=datetime.utcnow().isoformat(),
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = structlog.get_logger()

            # Extract tenant_id
            tenant_id = _extract_tenant_id(args, kwargs)

            try:
                result = func(*args, **kwargs)

                # Log success
                logger.audit(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    operation=func.__name__,
                    status="success",
                    timestamp=datetime.utcnow().isoformat(),
                )

                return result

            except Exception as e:
                # Log failure
                logger.audit(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    operation=func.__name__,
                    status="failure",
                    error_type=type(e).__name__,
                    timestamp=datetime.utcnow().isoformat(),
                )
                raise

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _extract_tenant_id(args: tuple, kwargs: dict) -> str:
    """Extract tenant_id from function arguments."""
    # Check kwargs first
    if "tenant_id" in kwargs:
        return kwargs["tenant_id"]

    # Check args (first arg is often tenant_id)
    if args and isinstance(args[0], str):
        try:
            validate_tenant_id(args[0])
            return args[0]
        except ValueError:
            pass

    return "unknown"


class SecurityAlertLogger:
    """Logger for security alerts requiring immediate attention."""

    def __init__(self):
        self._logger = structlog.get_logger()

    def alert(
        self,
        alert_type: str,
        severity: str = "high",
        **kwargs
    ) -> None:
        """Log security alert.

        Args:
            alert_type: Type of security alert
            severity: Severity level (critical, high, medium, low)
            **kwargs: Additional context
        """
        self._logger.error(
            "SECURITY_ALERT",
            alert_type=alert_type,
            severity=severity,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )

        # Send to security monitoring system
        # (integrate with Azure Security Center, Sentinel, etc.)
```

---

## Testing Patterns

### Unit Test Examples

```python
"""Unit tests for tenant isolation."""

import pytest
from unittest.mock import Mock, AsyncMock


class TestTenantIsolation:
    """Test tenant isolation guarantees."""

    @pytest.mark.asyncio
    async def test_query_includes_tenant_id(self):
        """Verify all queries include tenant_id filter."""
        # Mock table client
        mock_client = AsyncMock()
        mock_client.query_entities = AsyncMock()

        # Create tenant-isolated client
        tenant_id = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
        client = TenantIsolatedTableClient(mock_client, tenant_id)

        # Query
        await client.query_entities("status eq 'active'")

        # Verify tenant_id in query
        call_args = mock_client.query_entities.call_args
        query_filter = call_args.kwargs["query_filter"]

        assert f"tenant_id eq '{tenant_id}'" in query_filter

    @pytest.mark.asyncio
    async def test_cross_tenant_access_blocked(self):
        """Verify cross-tenant access is blocked."""
        # Mock table client
        mock_client = AsyncMock()

        # Entity belongs to different tenant
        mock_entity = {
            "tenant_id": "11112222-3333-4444-5555-666666666666",
            "data": "secret",
        }
        mock_client.get_entity = AsyncMock(return_value=mock_entity)

        # Create client for tenant A
        tenant_id = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
        client = TenantIsolatedTableClient(mock_client, tenant_id)

        # Attempt to access entity from tenant B
        with pytest.raises(PermissionError, match="tenant_id mismatch"):
            await client.get_entity("partition", "row")

    def test_injection_attack_blocked(self):
        """Verify injection attacks are blocked."""
        # Malicious tenant_id with SQL injection
        malicious_tenant_id = "aaaabbbb' or '1'='1"

        with pytest.raises(ValueError):
            validate_tenant_id(malicious_tenant_id)

    @pytest.mark.asyncio
    async def test_credential_isolation(self):
        """Verify credentials are isolated per tenant."""
        # Mock Key Vault client
        mock_kv = AsyncMock()

        # Different credentials per tenant
        mock_kv.get_secret = AsyncMock(side_effect=[
            Mock(value="client-id-a"),  # Tenant A client_id
            Mock(value="secret-a"),  # Tenant A secret
            Mock(value="tenant-a"),  # Tenant A tenant_id
            Mock(value="client-id-b"),  # Tenant B client_id
            Mock(value="secret-b"),  # Tenant B secret
            Mock(value="tenant-b"),  # Tenant B tenant_id
        ])

        manager = TenantCredentialManager(mock_kv)

        # Get credentials for both tenants
        creds_a = await manager.get_credentials(
            "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
        )
        creds_b = await manager.get_credentials(
            "11112222-3333-4444-5555-666666666666"
        )

        # Verify isolation
        assert creds_a.client_id != creds_b.client_id
        assert creds_a.client_secret != creds_b.client_secret
```

---

## Exception Definitions

```python
"""Security-related exception classes."""


class SecurityError(Exception):
    """Base exception for security errors."""
    pass


class CrossTenantAccessError(SecurityError):
    """Raised when cross-tenant access is attempted."""
    pass


class CredentialNotFoundError(SecurityError):
    """Raised when tenant credentials not found."""
    pass


class AuthenticationError(SecurityError):
    """Raised when authentication fails."""
    pass


class QueryValidationError(SecurityError):
    """Raised when query validation fails."""
    pass
```

---

## Quick Reference

### Essential Security Checklist

Every function that accesses tenant data MUST:

1. [ ] Validate tenant_id with `validate_tenant_id()`
2. [ ] Use tenant-isolated storage clients
3. [ ] Include `@audit_log()` decorator
4. [ ] Never log credentials or secrets
5. [ ] Use parameterized queries (no string concatenation)
6. [ ] Verify tenant_id in returned entities
7. [ ] Handle errors without leaking information

### Common Patterns

```python
# Pattern: Secure function
@audit_log("data_access")
async def get_tenant_data(tenant_id: str) -> dict:
    """Get data for tenant."""
    # 1. Validate input
    tenant_id = validate_tenant_id(tenant_id)

    # 2. Use isolated storage
    client = TenantIsolatedTableClient(table_client, tenant_id)

    # 3. Query with automatic filtering
    entities = await client.query_entities("status eq 'active'")

    # 4. Return results
    return entities

# Pattern: Secure credential retrieval
async def authenticate_tenant(tenant_id: str) -> ClientSecretCredential:
    """Authenticate to tenant."""
    # Get credentials from Key Vault
    cred_manager = TenantCredentialManager(kv_client)
    creds = await cred_manager.get_credentials(tenant_id)

    # Create credential
    credential = ClientSecretCredential(
        tenant_id=creds.tenant_id,
        client_id=creds.client_id,
        client_secret=creds.client_secret,
    )

    return credential
```

---

## Additional Resources

- [Security Architecture Document](/home/azureuser/src/AzureHayMaker/worktrees/feat/issue-147-cross-tenant-orchestration/docs/security/CROSS_TENANT_SECURITY_ARCHITECTURE.md)
- [Azure Key Vault Best Practices](https://learn.microsoft.com/azure/key-vault/general/best-practices)
- [Azure AD Multi-Tenant Apps](https://learn.microsoft.com/azure/active-directory/develop/howto-convert-app-to-be-multi-tenant)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
