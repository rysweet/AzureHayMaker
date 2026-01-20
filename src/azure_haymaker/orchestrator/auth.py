"""Azure AD authentication for the orchestrator API.

This module provides Azure AD token validation with full cryptographic
signature verification using python-jose library.

Security Features:
- Full JWT signature verification using JWKS from Azure AD
- Token replay protection via JTI (JWT ID) tracking
- JWKS caching with TTL-based refresh (1 hour default)
- Comprehensive claim validation (iss, aud, exp, nbf, iat, jti)
- Secure error handling (generic user messages, detailed logs)
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


# Cache for JWKS keys with TTL
@dataclass
class JWKSCacheEntry:
    """JWKS cache entry with TTL tracking."""

    jwks: dict
    fetched_at: float
    ttl: int = 3600  # 1 hour default


_jwks_cache: dict[str, JWKSCacheEntry] = {}


# JTI (JWT ID) tracking for replay protection
@dataclass
class TokenRecord:
    """Token tracking record for replay detection."""

    jti: str
    exp: int  # Expiration timestamp


_jti_cache: dict[str, TokenRecord] = {}
_JTI_CACHE_MAX_SIZE = 10000  # Max 10,000 concurrent tokens


class TokenReplayError(HTTPException):
    """Raised when token replay is detected."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token replay detected",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_auth_config() -> dict[str, str | list[str]]:
    """Get authentication configuration from environment.

    Returns:
        Dictionary with tenant_id, client_id, and optional allowed_client_ids

    Raises:
        RuntimeError: If required environment variables are not set
    """
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("API_CLIENT_ID")

    if not tenant_id or not client_id:
        raise RuntimeError(
            "AZURE_TENANT_ID and API_CLIENT_ID must be set for authentication. "
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
    url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def get_jwks_with_ttl(tenant_id: str, force_refresh: bool = False) -> dict:
    """Fetch JSON Web Key Set with TTL-based caching.

    Implements TTL-based refresh (1 hour default) to handle key rotation scenarios.

    Args:
        tenant_id: Azure AD tenant ID
        force_refresh: Force refresh even if cache is valid (for key rotation)

    Returns:
        JWKS dictionary with keys
    """
    now = time.time()

    # Check cache unless force refresh
    if not force_refresh and tenant_id in _jwks_cache:
        entry = _jwks_cache[tenant_id]
        cache_age = now - entry.fetched_at

        # Return cached if still valid
        if cache_age < entry.ttl:
            logger.debug(f"JWKS cache hit for tenant {tenant_id} (age: {cache_age:.0f}s)")
            return entry.jwks

        logger.debug(f"JWKS cache expired for tenant {tenant_id} (age: {cache_age:.0f}s)")

    # Fetch fresh JWKS
    logger.info(f"Fetching JWKS for tenant {tenant_id}")
    metadata = await get_tenant_metadata(tenant_id)
    jwks_uri = metadata["jwks_uri"]

    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_uri)
        response.raise_for_status()
        jwks = response.json()

    # Update cache
    _jwks_cache[tenant_id] = JWKSCacheEntry(jwks=jwks, fetched_at=now)

    return jwks


def cleanup_expired_jtis() -> None:
    """Remove expired JTI entries from replay cache.

    Called periodically to prevent memory leaks.
    Removes entries where token has expired.
    """
    now = time.time()
    expired = [jti for jti, record in _jti_cache.items() if record.exp < now]

    if expired:
        for jti in expired:
            del _jti_cache[jti]
        logger.debug(f"Cleaned up {len(expired)} expired JTI entries")


def check_token_replay(jti: str | None, exp: int) -> None:
    """Check for token replay and track JTI.

    Args:
        jti: JWT ID claim (unique token identifier)
        exp: Token expiration timestamp

    Raises:
        TokenReplayError: If token has already been used
    """
    # Skip replay check if no JTI (some tokens might not have it)
    if not jti:
        logger.warning("Token missing JTI claim - replay protection skipped")
        return

    # Check if JTI already seen
    if jti in _jti_cache:
        logger.warning(f"Token replay detected: jti={jti}")
        raise TokenReplayError()

    # Clean up if cache is getting large
    if len(_jti_cache) >= _JTI_CACHE_MAX_SIZE:
        cleanup_expired_jtis()

    # Track this JTI
    _jti_cache[jti] = TokenRecord(jti=jti, exp=exp)
    logger.debug(f"Tracking token: jti={jti}, cache_size={len(_jti_cache)}")


async def validate_jwt_signature(
    token: str, tenant_id: str, config: dict, force_jwks_refresh: bool = False
) -> dict:
    """Validate JWT signature and all claims using python-jose.

    This performs FULL cryptographic validation:
    - Signature verification using JWKS from Azure AD
    - Issuer validation (must be from our tenant)
    - Audience validation (must be for our API)
    - Expiration check
    - Not-before-time check
    - Issued-at-time check

    Args:
        token: JWT access token
        tenant_id: Azure AD tenant ID
        config: Auth configuration with client_id and allowed_client_ids
        force_jwks_refresh: Force JWKS refresh (for key rotation)

    Returns:
        Decoded and validated token claims

    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Fetch JWKS for signature verification
        jwks = await get_jwks_with_ttl(tenant_id, force_refresh=force_jwks_refresh)

        # Expected issuer values
        expected_issuers = [
            f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            f"https://sts.windows.net/{tenant_id}/",
        ]

        # Valid audience values
        valid_audiences = [
            config["client_id"],
            f"api://{config['client_id']}",
            "https://management.azure.com",
            "https://management.core.windows.net/",
        ]

        # Decode and validate token with full verification
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=valid_audiences,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iat": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iss": False,  # Manual issuer check below for multi-issuer
            },
        )

        # Manually validate issuer (multi-value check)
        if claims.get("iss") not in expected_issuers:
            logger.warning(f"Invalid issuer: {claims.get('iss')}")
            raise JWTClaimsError("Invalid token issuer")

        # Validate client ID (appid or azp claim)
        token_client_id = claims.get("appid") or claims.get("azp")
        if token_client_id not in config["allowed_client_ids"]:
            logger.warning(f"Unauthorized client: {token_client_id}")
            raise JWTClaimsError("Unauthorized client application")

        logger.debug(f"Token signature validated for client: {token_client_id}")
        return claims

    except ExpiredSignatureError as e:
        logger.warning("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    except JWTClaimsError as e:
        logger.warning(f"Token claims validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    except JWTError as e:
        # Signature validation failure - try refreshing JWKS once
        # This handles key rotation scenarios
        if not force_jwks_refresh:
            logger.info("Signature validation failed - refreshing JWKS and retrying")
            return await validate_jwt_signature(token, tenant_id, config, force_jwks_refresh=True)

        logger.error(f"JWT validation error after JWKS refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    except Exception as e:
        logger.error(f"Unexpected token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def validate_token(token: str, config: dict) -> dict:
    """Validate an Azure AD access token with full security checks.

    This implements:
    - Full cryptographic signature verification
    - Token replay protection via JTI tracking
    - All standard JWT claim validation
    - JWKS caching with TTL-based refresh

    Args:
        token: JWT access token
        config: Auth configuration with tenant_id and allowed_client_ids

    Returns:
        Validated token claims

    Raises:
        HTTPException: If token is invalid
    """
    tenant_id = config["tenant_id"]

    # Validate signature and all claims
    claims = await validate_jwt_signature(token, tenant_id, config)

    # Check for token replay
    jti = claims.get("jti")
    exp = claims.get("exp", 0)
    check_token_replay(jti, exp)

    return claims


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


__all__ = [
    "require_auth",
    "optional_auth",
    "get_auth_config",
    "validate_token",
    "validate_jwt_signature",
    "check_token_replay",
    "cleanup_expired_jtis",
    "get_jwks_with_ttl",
    "TokenReplayError",
]
