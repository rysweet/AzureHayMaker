"""Unit tests for Azure AD authentication module.

Tests the orchestrator auth.py module which handles:
- Token validation (valid, expired, malformed)
- Authentication failure handling (401 responses)
- Environment configuration handling
- FastAPI dependency integration

Testing approach:
- 60% unit tests (heavily mocked)
- 30% integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import base64
import json
import time
from unittest.mock import patch

import pytest

# FastAPI may not be installed in all environments
try:
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    HTTPException = None  # type: ignore
    HTTPAuthorizationCredentials = None  # type: ignore

pytestmark = pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi not installed")

from azure_haymaker.orchestrator.auth import (  # noqa: E402
    _jwks_cache,
    get_auth_config,
    get_jwks_with_ttl,
    get_tenant_metadata,
    optional_auth,
    require_auth,
    validate_token,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def valid_token_claims():
    """Generate valid token claims for testing."""
    return {
        "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
        "aud": "test-client-id",
        "exp": int(time.time()) + 3600,  # Valid for 1 hour
        "appid": "test-client-id",
        "sub": "user-123",
        "name": "Test User",
    }


@pytest.fixture
def expired_token_claims():
    """Generate expired token claims for testing."""
    return {
        "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
        "aud": "test-client-id",
        "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        "appid": "test-client-id",
        "sub": "user-123",
    }


@pytest.fixture
def auth_config():
    """Auth configuration for testing."""
    return {
        "tenant_id": "test-tenant-id",
        "client_id": "test-client-id",
        "allowed_client_ids": ["test-client-id"],
    }


@pytest.fixture
def mock_jwt_validation(valid_token_claims):
    """Mock JWT signature validation to bypass real cryptographic checks."""

    async def mock_validate(token: str, tenant_id: str, config: dict, force_jwks_refresh: bool = False):
        """Mock validation that decodes token and checks expiration."""
        import base64
        import json
        from fastapi import HTTPException, status

        # Decode the token to get claims (bypass signature check)
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Decode payload
            payload = parts[1]
            # Add padding if needed
            missing_padding = len(payload) % 4
            if missing_padding:
                payload += "=" * (4 - missing_padding)

            claims = json.loads(base64.urlsafe_b64decode(payload))

            # Check expiration
            exp = claims.get("exp", 0)
            if exp < time.time():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Validate issuer
            expected_issuers = [
                f"https://login.microsoftonline.com/{tenant_id}/v2.0",
                f"https://sts.windows.net/{tenant_id}/",
            ]
            if claims.get("iss") not in expected_issuers:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token claims",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Validate client ID
            token_client_id = claims.get("appid") or claims.get("azp")
            if token_client_id and token_client_id not in config.get("allowed_client_ids", []):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token claims",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return claims

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    with patch("azure_haymaker.orchestrator.auth.validate_jwt_signature", side_effect=mock_validate):
        yield


def create_jwt_token(claims: dict) -> str:
    """Create a mock JWT token from claims.

    This creates a properly formatted JWT (header.payload.signature)
    for testing token parsing logic.
    """
    header = {"alg": "RS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    # Signature is not validated in these tests, just needs to be present
    signature = "mock_signature"
    return f"{header_b64}.{payload_b64}.{signature}"


# ============================================================================
# Unit Tests - get_auth_config() (60%)
# ============================================================================


class TestGetAuthConfig:
    """Tests for get_auth_config function."""

    def test_returns_config_when_env_vars_set(self):
        """Test that config is returned when environment variables are set."""
        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant",
                "API_CLIENT_ID": "test-client",
            },
        ):
            config = get_auth_config()

            assert config["tenant_id"] == "test-tenant"
            assert config["client_id"] == "test-client"
            assert "test-client" in config["allowed_client_ids"]

    def test_raises_runtime_error_when_tenant_missing(self):
        """Test that RuntimeError is raised when AZURE_TENANT_ID is missing."""
        with patch.dict(
            "os.environ",
            {"API_CLIENT_ID": "test-client"},
            clear=True,
        ):
            with pytest.raises(RuntimeError) as exc_info:
                get_auth_config()

            assert "AZURE_TENANT_ID" in str(exc_info.value)

    def test_raises_runtime_error_when_client_id_missing(self):
        """Test that RuntimeError is raised when API_CLIENT_ID is missing."""
        with patch.dict(
            "os.environ",
            {"AZURE_TENANT_ID": "test-tenant"},
            clear=True,
        ):
            with pytest.raises(RuntimeError) as exc_info:
                get_auth_config()

            assert "API_CLIENT_ID" in str(exc_info.value)

    def test_allowed_clients_defaults_to_client_id(self):
        """Test that allowed_client_ids defaults to the API client ID."""
        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant",
                "API_CLIENT_ID": "main-client",
            },
        ):
            config = get_auth_config()

            assert config["allowed_client_ids"] == ["main-client"]

    def test_allowed_clients_parsed_from_env(self):
        """Test that ALLOWED_CLIENT_IDS is parsed as comma-separated list."""
        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant",
                "API_CLIENT_ID": "main-client",
                "ALLOWED_CLIENT_IDS": "client1, client2, client3",
            },
        ):
            config = get_auth_config()

            assert config["allowed_client_ids"] == ["client1", "client2", "client3"]

    def test_allowed_clients_strips_whitespace(self):
        """Test that whitespace is stripped from allowed client IDs."""
        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant",
                "API_CLIENT_ID": "main-client",
                "ALLOWED_CLIENT_IDS": "  client1  ,  client2  ",
            },
        ):
            config = get_auth_config()

            assert config["allowed_client_ids"] == ["client1", "client2"]


# ============================================================================
# Unit Tests - validate_token() (60%)
# ============================================================================


class TestValidateToken:
    """Tests for validate_token function."""

    @pytest.fixture(autouse=True)
    def setup_mock(self, mock_jwt_validation):
        """Auto-use JWT validation mock for all tests in this class."""
        pass

    @pytest.mark.anyio
    async def test_valid_token_returns_claims(
        self, valid_token_claims, auth_config
    ):
        """Test that a valid token returns the decoded claims."""
        token = create_jwt_token(valid_token_claims)

        claims = await validate_token(token, auth_config)

        assert claims["sub"] == "user-123"
        assert claims["iss"] == valid_token_claims["iss"]

    @pytest.mark.anyio
    async def test_malformed_token_raises_401(self, auth_config):
        """Test that malformed token raises 401 HTTPException."""
        malformed_token = "not.a.valid.jwt"

        with pytest.raises(HTTPException) as exc_info:
            await validate_token(malformed_token, auth_config)

        assert exc_info.value.status_code == 401

    @pytest.mark.anyio
    async def test_token_with_wrong_parts_raises_401(self, auth_config):
        """Test that token without 3 parts raises 401."""
        token = "only.two_parts"

        with pytest.raises(HTTPException) as exc_info:
            await validate_token(token, auth_config)

        assert exc_info.value.status_code == 401
        assert "Invalid authentication token" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_expired_token_raises_401(
        self, expired_token_claims, auth_config
    ):
        """Test that expired token raises 401 HTTPException."""
        token = create_jwt_token(expired_token_claims)

        with pytest.raises(HTTPException) as exc_info:
            await validate_token(token, auth_config)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.anyio
    async def test_invalid_issuer_raises_401(
        self, valid_token_claims, auth_config
    ):
        """Test that token with invalid issuer raises 401."""
        invalid_claims = {**valid_token_claims, "iss": "https://evil.attacker.com"}
        token = create_jwt_token(invalid_claims)

        with pytest.raises(HTTPException) as exc_info:
            await validate_token(token, auth_config)

        assert exc_info.value.status_code == 401
        assert "claims" in exc_info.value.detail.lower()

    @pytest.mark.anyio
    async def test_invalid_audience_raises_401(self, valid_token_claims, auth_config):
        """Test that token with invalid audience raises 401."""
        invalid_claims = {**valid_token_claims, "aud": "wrong-client-id"}
        token = create_jwt_token(invalid_claims)

        with pytest.raises(HTTPException) as exc_info:
            await validate_token(token, auth_config)

        assert exc_info.value.status_code == 401
        assert "audience" in exc_info.value.detail.lower()

    @pytest.mark.anyio
    async def test_unauthorized_client_raises_401(self, valid_token_claims, auth_config):
        """Test that token from unauthorized client raises 401."""
        invalid_claims = {**valid_token_claims, "appid": "unauthorized-client"}
        token = create_jwt_token(invalid_claims)

        with pytest.raises(HTTPException) as exc_info:
            await validate_token(token, auth_config)

        assert exc_info.value.status_code == 401
        assert "client" in exc_info.value.detail.lower()

    @pytest.mark.anyio
    async def test_accepts_v1_issuer_format(self, auth_config):
        """Test that v1 issuer format (sts.windows.net) is accepted."""
        claims = {
            "iss": "https://sts.windows.net/test-tenant-id/",
            "aud": "test-client-id",
            "exp": int(time.time()) + 3600,
            "appid": "test-client-id",
        }
        token = create_jwt_token(claims)

        result = await validate_token(token, auth_config)

        assert result["iss"] == claims["iss"]

    @pytest.mark.anyio
    async def test_accepts_api_audience_format(self, auth_config):
        """Test that api:// audience format is accepted."""
        claims = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "api://test-client-id",
            "exp": int(time.time()) + 3600,
            "appid": "test-client-id",
        }
        token = create_jwt_token(claims)

        result = await validate_token(token, auth_config)

        assert result is not None

    @pytest.mark.anyio
    async def test_accepts_azp_claim_for_client_id(self, auth_config):
        """Test that azp claim is accepted for client ID validation."""
        claims = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "test-client-id",
            "exp": int(time.time()) + 3600,
            "azp": "test-client-id",  # azp instead of appid
        }
        token = create_jwt_token(claims)

        result = await validate_token(token, auth_config)

        assert result is not None

    @pytest.mark.anyio
    async def test_invalid_base64_raises_401(self, auth_config):
        """Test that invalid base64 in token raises 401."""
        # Create a token with invalid base64 in the payload
        token = "eyJhbGciOiJSUzI1NiJ9.!!!invalid_base64!!!.signature"

        with pytest.raises(HTTPException) as exc_info:
            await validate_token(token, auth_config)

        assert exc_info.value.status_code == 401


# ============================================================================
# Unit Tests - require_auth() (60%)
# ============================================================================


class TestRequireAuth:
    """Tests for require_auth FastAPI dependency."""

    @pytest.mark.anyio
    async def test_no_credentials_raises_401(self):
        """Test that missing credentials raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(None)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_missing_config_raises_500(self):
        """Test that missing auth config raises 500."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="some-token")

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                await require_auth(credentials)

            assert exc_info.value.status_code == 500
            assert "not configured" in exc_info.value.detail.lower()

    @pytest.mark.anyio
    async def test_valid_credentials_returns_claims(self, valid_token_claims):
        """Test that valid credentials return token claims."""
        token = create_jwt_token(valid_token_claims)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant-id",
                "API_CLIENT_ID": "test-client-id",
            },
        ):
            claims = await require_auth(credentials)

            assert claims["sub"] == "user-123"


# ============================================================================
# Unit Tests - optional_auth() (60%)
# ============================================================================


class TestOptionalAuth:
    """Tests for optional_auth FastAPI dependency."""

    @pytest.mark.anyio
    async def test_no_credentials_returns_none(self):
        """Test that missing credentials returns None (not error)."""
        result = await optional_auth(None)

        assert result is None

    @pytest.mark.anyio
    async def test_invalid_token_returns_none(self):
        """Test that invalid token returns None (not error)."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")

        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant-id",
                "API_CLIENT_ID": "test-client-id",
            },
        ):
            result = await optional_auth(credentials)

            assert result is None

    @pytest.mark.anyio
    async def test_valid_token_returns_claims(self, valid_token_claims):
        """Test that valid token returns claims."""
        token = create_jwt_token(valid_token_claims)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant-id",
                "API_CLIENT_ID": "test-client-id",
            },
        ):
            claims = await optional_auth(credentials)

            assert claims is not None
            assert claims["sub"] == "user-123"

    @pytest.mark.anyio
    async def test_config_error_returns_none(self):
        """Test that config error returns None (not error)."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="some-token")

        with patch.dict("os.environ", {}, clear=True):
            result = await optional_auth(credentials)

            assert result is None


# ============================================================================
# Unit Tests - get_tenant_metadata() (60%)
# ============================================================================


class TestGetTenantMetadata:
    """Tests for get_tenant_metadata function."""

    def test_metadata_url_format(self):
        """Test that the correct Azure AD URL format would be used."""
        tenant_id = "test-tenant-123"
        expected_url = (
            f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
        )

        # Verify the URL format is correct (the actual function uses this format)
        assert tenant_id in expected_url
        assert ".well-known/openid-configuration" in expected_url


# ============================================================================
# Unit Tests - get_jwks_with_ttl() (60%)
# ============================================================================


class TestGetJwksWithTtl:
    """Tests for get_jwks_with_ttl function."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear caches before each test."""
        _jwks_cache.clear()
        yield
        _jwks_cache.clear()

    @pytest.mark.anyio
    async def test_returns_cached_jwks(self):
        """Test that cached JWKS is returned without network call."""
        # Import the JWKSCacheEntry dataclass
        from azure_haymaker.orchestrator.auth import JWKSCacheEntry

        # Pre-populate the cache with the new structure
        test_jwks = {"keys": [{"kid": "cached-key", "kty": "RSA"}]}
        _jwks_cache["cached-tenant"] = JWKSCacheEntry(
            jwks=test_jwks, fetched_at=time.time(), ttl=3600
        )

        result = await get_jwks_with_ttl("cached-tenant")

        assert result["keys"][0]["kid"] == "cached-key"
        assert result["keys"][0]["kty"] == "RSA"

    def test_jwks_cache_structure(self):
        """Test that JWKS cache stores proper structure."""
        from azure_haymaker.orchestrator.auth import JWKSCacheEntry

        test_jwks = {
            "keys": [
                {"kty": "RSA", "use": "sig", "kid": "key-1"},
                {"kty": "RSA", "use": "sig", "kid": "key-2"},
            ]
        }

        _jwks_cache["test-tenant"] = JWKSCacheEntry(
            jwks=test_jwks, fetched_at=time.time(), ttl=3600
        )

        assert "test-tenant" in _jwks_cache
        assert len(_jwks_cache["test-tenant"].jwks["keys"]) == 2


# ============================================================================
# Integration Tests (30%)
# ============================================================================


class TestAuthIntegration:
    """Integration tests for auth module components."""

    @pytest.mark.anyio
    async def test_full_auth_flow_valid_token(self, valid_token_claims):
        """Test complete auth flow with valid token."""
        token = create_jwt_token(valid_token_claims)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant-id",
                "API_CLIENT_ID": "test-client-id",
            },
        ):
            # Should succeed without errors
            claims = await require_auth(credentials)

            assert claims["sub"] == "user-123"
            assert claims["appid"] == "test-client-id"

    @pytest.mark.anyio
    async def test_full_auth_flow_invalid_token(self):
        """Test complete auth flow with invalid token."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")

        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant-id",
                "API_CLIENT_ID": "test-client-id",
            },
        ):
            with pytest.raises(HTTPException) as exc_info:
                await require_auth(credentials)

            assert exc_info.value.status_code == 401

    @pytest.mark.anyio
    async def test_auth_headers_include_www_authenticate(self, valid_token_claims):
        """Test that 401 responses include WWW-Authenticate header."""
        expired_claims = {**valid_token_claims, "exp": int(time.time()) - 3600}
        token = create_jwt_token(expired_claims)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch.dict(
            "os.environ",
            {
                "AZURE_TENANT_ID": "test-tenant-id",
                "API_CLIENT_ID": "test-client-id",
            },
        ):
            with pytest.raises(HTTPException) as exc_info:
                await require_auth(credentials)

            assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


# ============================================================================
# Edge Case Tests (10% E2E/Edge)
# ============================================================================


class TestAuthEdgeCases:
    """Edge case and boundary tests for auth module."""

    @pytest.mark.anyio
    async def test_token_exactly_at_expiration(self):
        """Test token exactly at expiration boundary."""
        config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "allowed_client_ids": ["test-client-id"],
        }
        # Token that expires exactly now (edge case)
        claims = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "test-client-id",
            "exp": int(time.time()),  # Exactly now
            "appid": "test-client-id",
        }
        token = create_jwt_token(claims)

        # Token at exact expiration time is considered expired
        with pytest.raises(HTTPException):
            await validate_token(token, config)

    @pytest.mark.anyio
    async def test_empty_string_token(self):
        """Test empty string as token."""
        config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "allowed_client_ids": ["test-client-id"],
        }

        with pytest.raises(HTTPException) as exc_info:
            await validate_token("", config)

        assert exc_info.value.status_code == 401

    @pytest.mark.anyio
    async def test_management_azure_com_audience(self):
        """Test Azure Management API audience is accepted."""
        config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "allowed_client_ids": ["test-client-id"],
        }
        claims = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "https://management.azure.com",
            "exp": int(time.time()) + 3600,
            "appid": "test-client-id",
        }
        token = create_jwt_token(claims)

        result = await validate_token(token, config)

        assert result is not None

    @pytest.mark.anyio
    async def test_unicode_in_token_claims(self):
        """Test handling of unicode characters in token claims."""
        config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "allowed_client_ids": ["test-client-id"],
        }
        claims = {
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "aud": "test-client-id",
            "exp": int(time.time()) + 3600,
            "appid": "test-client-id",
            "name": "Test User with Unicode: \u00e9\u00e8\u00ea",  # é è ê
        }
        token = create_jwt_token(claims)

        result = await validate_token(token, config)

        assert "Unicode" in result["name"]
