# Getting Started: Multi-Tenant Resource Isolation (Issue #126)

**Your complete guide to implementing Issue #126**

**Priority**: P1-High | **Effort**: 6 weeks | **ROI**: 233%

---

## ⚠️ IMPORTANT: Architecture Review Required FIRST

**DO NOT start implementation without architecture review!**

This is a complex architectural change affecting the entire system. A 2-week architecture spike and review is **MANDATORY** before full implementation.

---

## What You're Building

Transform Azure HayMaker from single-tenant to multi-tenant, enabling:
- SaaS deployment model (multiple customers)
- MSP service offerings (manage multiple client tenants)
- Tenant isolation (complete resource and data separation)
- Per-tenant cost allocation and billing

**Business Value**: $450K/year (10 tenants @ $2,500/month) + $150K/year MSP contracts

---

## Before You Start (Architecture Spike: Weeks 1-2)

### Phase 0: Architecture Review (MANDATORY, 2 weeks)

**Goal**: Design multi-tenant approach, validate feasibility, get approval

#### Step 1: Design Options Analysis (Week 1)

**Three architectural approaches to evaluate**:

**Option A: Full Multi-Tenant (Shared Infrastructure)**
- Single orchestrator, single database
- Tenant context in all requests
- Row-level security in database
- **Pros**: Most cost-efficient, easiest to operate
- **Cons**: Highest security risk, complex isolation guarantees
- **Effort**: 6 weeks

**Option B: Namespace Isolation (Separate Resource Groups)**
- Separate Azure resource groups per tenant
- Separate service principals per tenant
- Shared orchestrator with tenant routing
- **Pros**: Strong isolation, moderate complexity
- **Cons**: Higher Azure costs, more operational overhead
- **Effort**: 4 weeks

**Option C: Full Isolation (Separate Deployments)**
- Complete separate deployment per tenant
- **Pros**: Perfect isolation, simple to reason about
- **Cons**: Highest cost, operational nightmare
- **Effort**: 2 weeks (but ongoing ops burden)

**Create comparison document** evaluating all 3 options.

#### Step 2: Prototype (Week 2)

**Build minimal PoC** for chosen approach:

```bash
# Create prototype branch
git checkout -b spike/multi-tenant-poc

# Implement bare-minimum multi-tenant support
# - Add tenant_id to 2-3 models
# - Implement tenant context middleware
# - Create 2 test tenants
# - Verify isolation

# Test with 2-3 tenants for 2-3 days
# - Measure performance impact
# - Verify isolation
# - Identify gotchas
```

**Success Criteria for PoC**:
- [ ] 2 tenants can coexist without interference
- [ ] Data isolation verified (Tenant A can't see Tenant B's data)
- [ ] Performance impact <10%
- [ ] No breaking changes to existing single-tenant mode

#### Step 3: Architecture Review Meeting

**Present to engineering team**:
- Chosen approach with rationale
- PoC results and learnings
- Implementation plan
- Risk assessment
- Resource requirements

**Get approval** before proceeding to full implementation.

**If PoC fails**: Pivot to Option B (namespace isolation) or defer to later quarter

---

## Implementation Phase (Weeks 3-8, only after approval)

### Week 3: Data Model Changes

**Files to modify**:
```
src/azure_haymaker/models/execution.py
src/azure_haymaker/models/schedule.py
src/azure_haymaker/models/worker.py
src/azure_haymaker/knowledge_worker/models/
```

**Add tenant_id field everywhere**:
```python
from pydantic import BaseModel

class ExecutionRequest(BaseModel):
    tenant_id: str  # NEW: Tenant identifier
    scenarios: list[str]
    duration_hours: int

class Schedule(BaseModel):
    id: str
    tenant_id: str  # NEW: Tenant isolation
    name: str
    cron_expression: str
    # ...
```

**Database migration** (if using persistent storage):
```sql
-- Add tenant_id column to all tables
ALTER TABLE executions ADD COLUMN tenant_id VARCHAR(50) NOT NULL DEFAULT 'default';
ALTER TABLE schedules ADD COLUMN tenant_id VARCHAR(50) NOT NULL DEFAULT 'default';
-- Add indexes for tenant queries
CREATE INDEX idx_executions_tenant ON executions(tenant_id);
```

### Week 4: Tenant Context Middleware

**File**: `src/azure_haymaker/orchestrator/tenant_context.py` (NEW)

```python
from fastapi import Request, HTTPException
from typing import Optional

class TenantContext:
    """Thread-local tenant context for request scope."""

    def __init__(self):
        self._tenant_id: Optional[str] = None

    @property
    def current_tenant(self) -> str:
        if self._tenant_id is None:
            raise HTTPException(status_code=401, detail="No tenant context")
        return self._tenant_id

    def set_tenant(self, tenant_id: str):
        self._tenant_id = tenant_id

# Global instance
tenant_context = TenantContext()

# FastAPI dependency
async def get_tenant_id(request: Request) -> str:
    """Extract tenant ID from request (header, JWT claim, or subdomain)."""

    # Option 1: From Authorization header (JWT)
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        # Decode JWT, extract tenant_id claim
        tenant_id = extract_tenant_from_jwt(token)
        tenant_context.set_tenant(tenant_id)
        return tenant_id

    # Option 2: From X-Tenant-ID header
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        tenant_context.set_tenant(tenant_id)
        return tenant_id

    # Option 3: From subdomain (tenant1.haymaker.com)
    host = request.headers.get("Host", "")
    if "." in host:
        subdomain = host.split(".")[0]
        tenant_context.set_tenant(subdomain)
        return subdomain

    raise HTTPException(status_code=400, detail="Tenant ID required")
```

**Add to orchestrator**:
```python
from fastapi import Depends
from azure_haymaker.orchestrator.tenant_context import get_tenant_id

@app.post("/api/execute")
async def execute(
    request: ExecutionRequest,
    tenant_id: str = Depends(get_tenant_id)  # NEW: Tenant context
):
    # Validate tenant has access to requested scenarios
    # Execute with tenant isolation
```

### Week 5: Tenant Registry & Credentials

**File**: `src/azure_haymaker/orchestrator/tenant_registry.py` (NEW)

```python
@dataclass
class TenantConfig:
    """Per-tenant configuration."""
    tenant_id: str
    tenant_name: str
    azure_subscription_id: str
    keyvault_name: str
    resource_group_prefix: str
    max_concurrent_scenarios: int = 10
    budget_limit_monthly: float = 1000.0

class TenantRegistry:
    """Manages tenant configurations and credentials."""

    def __init__(self):
        self.tenants: dict[str, TenantConfig] = {}

    def register_tenant(self, config: TenantConfig):
        """Register a new tenant."""
        self.tenants[config.tenant_id] = config

    def get_tenant(self, tenant_id: str) -> TenantConfig:
        """Get tenant configuration."""
        if tenant_id not in self.tenants:
            raise ValueError(f"Tenant {tenant_id} not registered")
        return self.tenants[tenant_id]

    def get_tenant_credentials(self, tenant_id: str) -> DefaultAzureCredential:
        """Get tenant-scoped Azure credentials."""
        # Return credential for this tenant's service principal
```

### Week 6: Query Filtering & Isolation

**Modify all data access to filter by tenant**:

```python
# BEFORE (single-tenant)
def get_executions(self):
    return self.db.query("SELECT * FROM executions")

# AFTER (multi-tenant)
def get_executions(self, tenant_id: str):
    return self.db.query(
        "SELECT * FROM executions WHERE tenant_id = ?",
        tenant_id
    )
```

**Add tenant filtering to**:
- All FastAPI endpoints
- All database queries
- All Azure resource queries
- All cost queries

### Week 7-8: Testing & Validation

**Create comprehensive multi-tenant tests**:

```python
# tests/security/test_tenant_isolation.py

def test_tenant_cannot_see_other_tenant_data():
    """CRITICAL: Verify Tenant A cannot access Tenant B's data."""

    # Create execution as Tenant A
    tenant_a_execution = create_execution(tenant_id="tenant-a")

    # Try to access as Tenant B
    with pytest.raises(PermissionError):
        get_execution(tenant_a_execution.id, tenant_id="tenant-b")

def test_tenant_cannot_modify_other_tenant_resources():
    """CRITICAL: Verify Tenant A cannot modify Tenant B's resources."""
    # Similar cross-tenant attack test

def test_tenant_cost_isolation():
    """Verify costs properly allocated per tenant."""
    # Create resources for Tenant A and B
    # Query costs
    # Verify no cross-contamination
```

**Run security penetration testing**:
- Attempt cross-tenant access attacks
- Verify all isolation boundaries hold
- External security audit recommended ($15K budget)

---

## Success Criteria

**MUST achieve before marking complete**:
- [ ] 10+ tenants working simultaneously
- [ ] Zero cross-tenant data leakage (security audit passed)
- [ ] External security penetration test passed
- [ ] Performance impact <10% (vs single-tenant)
- [ ] First SaaS customer successfully onboarded
- [ ] Per-tenant cost tracking accurate
- [ ] All existing functionality still works (no regressions)

---

## Risks & Mitigation

**High Risk**: Architectural complexity may balloon

**Mitigation**:
- **Week 2 checkpoint**: If PoC shows major issues, pivot to Option B (namespace isolation)
- **Week 4 checkpoint**: If implementation falling behind, reduce scope (defer cost isolation)
- **Week 6 checkpoint**: If security issues found, bring in external consultant

**Budget**: Reserve 20% contingency ($28K from $143K) for complexity overruns

---

## Timeline

| Phase | Weeks | Cumulative | Checkpoint |
|-------|-------|------------|------------|
| 0: Architecture Review | 2 | Week 2 | ✅ PoC successful? |
| 1: Data Models | 1 | Week 3 | |
| 2: Tenant Context | 1 | Week 4 | ✅ Performance OK? |
| 3: Tenant Registry | 1 | Week 5 | |
| 4: Query Filtering | 1 | Week 6 | ✅ Security audit? |
| 5: Testing | 2 | Week 8 | ✅ Ready for production? |

**Total**: 8 weeks (including 2-week spike)

---

**Full Details**: See [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md) - Multi-Tenant section

**Issue**: [#126](https://github.com/rysweet/AzureHayMaker/issues/126)

**Milestone**: [Q2 2026](https://github.com/rysweet/AzureHayMaker/milestone/2)

⚠️ **Remember**: Architecture review FIRST, implementation SECOND!
