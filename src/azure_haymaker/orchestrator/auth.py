"""Azure AD authentication for the orchestrator API.

This module provides Azure AD token validation for securing API endpoints.
Clients must authenticate using a service principal and provide a Bearer token.
"""

import logging
import os
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)

# Cache for JWKS keys and tenant metadata
_jwks_cache: dict[str, dict] = {}
_tenant_metadata_cache: dict[str, dict] = {}


def get_auth_config() -> dict[str, str | list[str]]:
    """Get authentication configuration from environment.

    Returns:
        Dictionary with tenant_id, client_id, and optional allowed_client_ids

    Raises:
        RuntimeError: If required environment variables are not set
    """
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")

    if not tenant_id or not client_id:
        raise RuntimeError(
            "AZURE_TENANT_ID and AZURE_CLIENT_ID must be set for authentication. "
            "The orchestrator requires Azure AD authentication."
        )

    # Allow the configured service principal and optionally other client IDs
    allowed_clients = os.getenv("ALLOWED_CLIENT_IDS", client_id)

    return {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "allowed_client_ids": [c.strip() for c in allowed_clients.split(",")],
    }


async def get_tenant_metadata(tenant_id: str) -> dict:
    """Fetch Azure AD tenant metadata (OpenID configuration).

    Args:
        tenant_id: Azure AD tenant ID

    Returns:
        OpenID configuration dictionary
    """
    if tenant_id in _tenant_metadata_cache:
        return _tenant_metadata_cache[tenant_id]

    url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        metadata = response.json()
        _tenant_metadata_cache[tenant_id] = metadata
        return metadata


async def get_jwks(tenant_id: str) -> dict:
    """Fetch JSON Web Key Set for token validation.

    Args:
        tenant_id: Azure AD tenant ID

    Returns:
        JWKS dictionary with keys
    """
    if tenant_id in _jwks_cache:
        return _jwks_cache[tenant_id]

    metadata = await get_tenant_metadata(tenant_id)
    jwks_uri = metadata["jwks_uri"]

    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_uri)
        response.raise_for_status()
        jwks = response.json()
        _jwks_cache[tenant_id] = jwks
        return jwks


async def validate_token(token: str, config: dict) -> dict:
    """Validate an Azure AD access token.

    This performs basic validation. For production, consider using
    a library like python-jose or msal for full JWT validation.

    Args:
        token: JWT access token
        config: Auth configuration with tenant_id and allowed_client_ids

    Returns:
        Decoded token claims

    Raises:
        HTTPException: If token is invalid
    """
    import base64
    import json as json_module

    try:
        # Decode token parts (header.payload.signature)
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        # Decode payload (add padding if needed)
        payload = parts[1]
        payload += "=" * (4 - len(payload) % 4)
        claims = json_module.loads(base64.urlsafe_b64decode(payload))

        # Validate issuer (must be from our tenant)
        expected_issuers = [
            f"https://login.microsoftonline.com/{config['tenant_id']}/v2.0",
            f"https://sts.windows.net/{config['tenant_id']}/",
        ]
        if claims.get("iss") not in expected_issuers:
            logger.warning(f"Invalid issuer: {claims.get('iss')}")
            raise ValueError("Invalid token issuer")

        # Validate audience (must be for our app or Microsoft Graph)
        valid_audiences = [
            config["client_id"],
            f"api://{config['client_id']}",
            "https://management.azure.com",
            "https://management.core.windows.net/",
        ]
        token_aud = claims.get("aud")
        if token_aud not in valid_audiences:
            logger.warning(f"Invalid audience: {token_aud}")
            raise ValueError("Invalid token audience")

        # Validate expiration
        import time

        if claims.get("exp", 0) < time.time():
            raise ValueError("Token has expired")

        # Validate client ID (appid or azp claim)
        token_client_id = claims.get("appid") or claims.get("azp")
        if token_client_id not in config["allowed_client_ids"]:
            logger.warning(f"Unauthorized client: {token_client_id}")
            raise ValueError("Unauthorized client application")

        logger.debug(f"Token validated for client: {token_client_id}")
        return claims

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict:
    """FastAPI dependency that requires valid Azure AD authentication.

    Use this as a dependency on protected endpoints:

        @app.get("/api/protected")
        async def protected_endpoint(claims: dict = Depends(require_auth)):
            return {"user": claims.get("sub")}

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        Validated token claims

    Raises:
        HTTPException 401: If no credentials or invalid token
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        config = get_auth_config()
    except RuntimeError as e:
        logger.error(f"Auth not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured on server",
        ) from e

    return await validate_token(credentials.credentials, config)


# Optional auth - allows unauthenticated access but provides claims if authenticated
async def optional_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict | None:
    """FastAPI dependency that optionally validates authentication.

    Returns claims if valid token provided, None otherwise.
    Use for endpoints that work with or without auth.

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        Validated token claims or None
    """
    if credentials is None:
        return None

    try:
        config = get_auth_config()
        return await validate_token(credentials.credentials, config)
    except Exception:
        return None
