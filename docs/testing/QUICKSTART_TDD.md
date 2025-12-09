# Cross-Tenant Orchestration TDD Quickstart

## Current Status: RED Phase ✅

All tests are written and will **FAIL** initially. This is **CORRECT** for TDD!

## Quick Verification

### 1. Verify Tests Exist

```bash
cd /home/azureuser/src/AzureHayMaker/worktrees/feat/issue-147-cross-tenant-orchestration

# List test files
ls -la tests/unit/orchestrator/
ls -la tests/security/
ls -la tests/fixtures/
```

Expected output:
```
tests/fixtures/tenant_configs.py  ✅
tests/fixtures/mock_clients.py    ✅
tests/fixtures/test_data.py       ✅
tests/unit/orchestrator/test_multi_tenant_config.py  ✅
tests/unit/orchestrator/test_tenant_auth.py          ✅
tests/unit/orchestrator/services/test_tenant_storage.py  ✅
tests/security/test_tenant_isolation.py              ✅
```

### 2. Run Tests (Expected to FAIL)

```bash
# Try running config tests
pytest tests/unit/orchestrator/test_multi_tenant_config.py -v

# Expected output:
# ===== SKIPPED: Models not yet implemented =====
# This is CORRECT for TDD RED phase!
```

### 3. Check Test Count

```bash
# Count tests in each file
pytest tests/unit/orchestrator/test_multi_tenant_config.py --collect-only
pytest tests/unit/orchestrator/test_tenant_auth.py --collect-only
pytest tests/unit/orchestrator/services/test_tenant_storage.py --collect-only
pytest tests/security/test_tenant_isolation.py --collect-only
```

Expected:
- Configuration tests: 29 tests
- Authentication tests: 17 tests
- Storage tests: 15 tests
- Security tests: 15 tests

**Total: 76+ tests**

---

## Implementation Roadmap

### Step 1: Configuration Models (Priority 1)

**File to Create**: `src/azure_haymaker/orchestrator/models.py`

**Test File**: `tests/unit/orchestrator/test_multi_tenant_config.py`

**What to Implement**:
```python
from pydantic import BaseModel, UUID4, field_validator
from typing import Optional, List

class TenantContext(BaseModel):
    """Context for a specific tenant."""
    tenant_id: UUID4
    tenant_name: str
    subscription_id: UUID4
    region: str

    def get_storage_prefix(self) -> str:
        """Generate storage prefix for this tenant."""
        return str(self.tenant_id)

class TargetTenantConfig(BaseModel):
    """Configuration for a target tenant."""
    name: str
    tenant_id: UUID4
    subscription_id: UUID4
    region: str = "eastus"
    credentials: dict
    enabled: bool = True
    scenarios: List[str]
    # Add remaining fields from test_multi_tenant_config.py

class MetaOrchestratorConfig(BaseModel):
    """Meta-orchestrator configuration."""
    name: str
    infrastructure_tenant_id: UUID4
    max_concurrent_tenants: int = 5
    target_tenants: List[TargetTenantConfig] = []

    @field_validator('max_concurrent_tenants')
    def validate_max_concurrent(cls, v):
        if not 1 <= v <= 20:
            raise ValueError("max_concurrent_tenants must be between 1 and 20")
        return v

    def is_multi_tenant_mode(self) -> bool:
        return len(self.target_tenants) > 0

    def is_single_tenant_mode(self) -> bool:
        return len(self.target_tenants) == 0
```

**Verify**:
```bash
pytest tests/unit/orchestrator/test_multi_tenant_config.py -v
```

Expected: All 29 tests PASS ✅

---

### Step 2: Tenant Authentication (Priority 2)

**File to Create**: `src/azure_haymaker/orchestrator/tenant_auth.py`

**Test File**: `tests/unit/orchestrator/test_tenant_auth.py`

**What to Implement**:
```python
from dataclasses import dataclass
from typing import Dict, List
from azure.keyvault.secrets import SecretClient

@dataclass
class TenantCredential:
    client_id: str
    client_secret: str
    tenant_id: str
    subscription_id: str

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "tenant_id": self.tenant_id,
            "subscription_id": self.subscription_id,
        }

    def __str__(self) -> str:
        return f"TenantCredential(client_id={self.client_id}, secret=***REDACTED***)"

class CredentialNotFoundError(Exception):
    pass

class InvalidCredentialError(Exception):
    pass

class TenantCredentialManager:
    def __init__(self, keyvault_client: SecretClient):
        self.kv_client = keyvault_client
        self._cache: Dict[str, TenantCredential] = {}

    async def get_tenant_credential(self, tenant_name: str) -> TenantCredential:
        """Retrieve tenant credentials from Key Vault (with caching)."""
        if tenant_name in self._cache:
            return self._cache[tenant_name]

        try:
            client_id = self.kv_client.get_secret(f"{tenant_name}-client-id").value
            client_secret = self.kv_client.get_secret(f"{tenant_name}-client-secret").value
            tenant_id = self.kv_client.get_secret(f"{tenant_name}-tenant-id").value
            subscription_id = self.kv_client.get_secret(f"{tenant_name}-subscription-id").value

            credential = TenantCredential(
                client_id=client_id,
                client_secret=client_secret,
                tenant_id=tenant_id,
                subscription_id=subscription_id,
            )

            self._cache[tenant_name] = credential
            return credential

        except Exception as e:
            raise CredentialNotFoundError(f"Credentials not found for tenant: {tenant_name}") from e

    def invalidate_cache(self, tenant_name: str) -> None:
        """Invalidate cached credentials for a tenant."""
        if tenant_name in self._cache:
            del self._cache[tenant_name]

    async def validate_tenant_access(self, tenant_name: str) -> bool:
        """Validate that credentials exist and are valid."""
        try:
            credential = await self.get_tenant_credential(tenant_name)
            return bool(credential.client_secret)
        except:
            return False

    async def store_tenant_credentials(
        self,
        tenant_name: str,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        subscription_id: str,
    ) -> None:
        """Store tenant credentials in Key Vault."""
        self.kv_client.set_secret(f"{tenant_name}-client-id", client_id)
        self.kv_client.set_secret(f"{tenant_name}-client-secret", client_secret)
        self.kv_client.set_secret(f"{tenant_name}-tenant-id", tenant_id)
        self.kv_client.set_secret(f"{tenant_name}-subscription-id", subscription_id)

    async def rotate_credentials(self, tenant_name: str, new_client_secret: str) -> None:
        """Rotate credentials and invalidate cache."""
        self.kv_client.set_secret(f"{tenant_name}-client-secret", new_client_secret)
        self.invalidate_cache(tenant_name)

    async def get_all_tenant_names(self) -> List[str]:
        """Get all configured tenant names from Key Vault."""
        secrets = self.kv_client.list_secrets()
        tenant_names = set()
        for secret in secrets:
            if "-client-id" in secret["name"]:
                tenant_name = secret["name"].replace("-client-id", "")
                tenant_names.add(tenant_name)
        return list(tenant_names)
```

**Verify**:
```bash
pytest tests/unit/orchestrator/test_tenant_auth.py -v
```

Expected: All 17 tests PASS ✅

---

### Step 3: Storage Partitioning (Priority 3)

**File to Create**: `src/azure_haymaker/orchestrator/services/tenant_storage.py`

**Test File**: `tests/unit/orchestrator/services/test_tenant_storage.py`

**What to Implement**: See `tests/CROSS_TENANT_TEST_SUMMARY.md` for complete implementation guide.

**Verify**:
```bash
pytest tests/unit/orchestrator/services/test_tenant_storage.py -v
```

Expected: All 15 tests PASS ✅

---

### Step 4: Security Validation (Priority 4)

**Test File**: `tests/security/test_tenant_isolation.py`

**Verify**:
```bash
pytest tests/security/test_tenant_isolation.py -v -m security
```

Expected: All 15 tests PASS ✅

---

## Test Execution Guide

### Run Individual Test Files

```bash
# Configuration models
pytest tests/unit/orchestrator/test_multi_tenant_config.py -v

# Authentication
pytest tests/unit/orchestrator/test_tenant_auth.py -v

# Storage
pytest tests/unit/orchestrator/services/test_tenant_storage.py -v

# Security
pytest tests/security/test_tenant_isolation.py -v
```

### Run by Category

```bash
# All unit tests
pytest tests/unit/ -v

# All security tests
pytest tests/security/ -v -m security
```

### Run with Coverage

```bash
# Coverage report
pytest tests/unit/orchestrator/ --cov=azure_haymaker.orchestrator --cov-report=html

# Open report
open htmlcov/index.html
```

---

## Success Criteria

### ✅ Configuration Models (29 tests)
- [ ] TenantContext creation and validation
- [ ] TargetTenantConfig validation
- [ ] MetaOrchestratorConfig validation
- [ ] Duplicate detection
- [ ] Serialization/deserialization

### ✅ Tenant Authentication (17 tests)
- [ ] Credential retrieval from Key Vault
- [ ] Credential caching
- [ ] Cache invalidation
- [ ] Missing secret handling
- [ ] Credential validation
- [ ] Credential storage
- [ ] Credential rotation

### ✅ Storage Partitioning (15 tests)
- [ ] Blob path prefixing
- [ ] Table partition key generation
- [ ] Cosmos DB tenant_id filtering
- [ ] Single-tenant mode compatibility

### ✅ Security Isolation (15 tests)
- [ ] Blob Storage isolation
- [ ] Table Storage isolation
- [ ] Cosmos DB isolation
- [ ] Credential isolation
- [ ] Injection prevention

---

## Quick Commands Reference

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/unit/orchestrator/test_multi_tenant_config.py::TestTenantContext::test_tenant_context_creation_with_valid_data_succeeds -v

# Run with markers
pytest -m security -v

# Skip integration tests
pytest -m "not integration" -v

# Coverage report
pytest tests/ --cov=azure_haymaker --cov-report=html

# List all tests (without running)
pytest tests/ --collect-only
```

---

## Troubleshooting

### Tests Won't Run

```bash
# Check pytest installation
pytest --version

# Reinstall dependencies
uv pip install -e ".[dev]"
```

### Import Errors

```bash
# Verify PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"

# Check pytest config
cat pyproject.toml | grep -A 10 pytest.ini_options
```

### Async Tests Failing

```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Verify async mode
cat pyproject.toml | grep asyncio_mode
```

---

## Documentation Links

- **Test Suite README**: `tests/README_CROSS_TENANT_TESTS.md`
- **Implementation Summary**: `tests/CROSS_TENANT_TEST_SUMMARY.md`
- **This Quickstart**: `tests/QUICKSTART_TDD.md`
- **Architectural Design**: `docs/architecture/orchestrator.md`
- **Security Guide**: `docs/security/cross-tenant-security.md`
- **Configuration Reference**: `docs/configuration/multi-tenant-config.md`

---

## Next Steps

1. ✅ Tests created (RED phase complete)
2. ⏳ Implement configuration models
3. ⏳ Implement tenant authentication
4. ⏳ Implement storage partitioning
5. ⏳ Verify security tests pass
6. ⏳ Add integration tests
7. ⏳ Add E2E tests

**Current Phase**: RED ✅
**Next Phase**: GREEN (implementation)

---

**Created**: 2025-12-09
**Status**: Ready for implementation
**Tests**: 76+ tests across 7 files
**Test Code**: 2,413 lines
