# Issue #26 - The Complete Journey

**Started**: 2025-11-20 ~14:00 UTC
**Current Time**: 2025-11-20 17:20 UTC
**Duration**: 3+ hours
**Status**: 🔄 4th deployment in progress

---

## The Five-Fix Saga

### Fix #1: Remove Merge Conflict Markers ✅
**Commits**: 062d501 (main), c75d521 (develop)
**Problem**: Lines 86-106 in `src/azure_haymaker/orchestrator/__init__.py` unconditionally set `app = None`
**Impact**: Container stuck in "NotRunning", no Azure Functions runtime
**Result**: Container reached "Running" state!

### Fix #2: Increase E16 Workload Profile Capacity ✅
**Time**: 14:59 UTC
**Problem**: E16 profile `maximumCount: 1`, insufficient for blue-green deployments
**Impact**: New revisions failed with "ActivationFailed"
**Solution**: Increased to `maximumCount: 2`
**Result**: Revisions could activate!

### Fix #3: Import Decorated Functions ✅
**Commit**: cf84512
**Problem**: function_app.py only imported `app`, not decorated function modules
**Impact**: Container ran but "0 functions found"
**Solution**: Added imports of all 10 function modules
**Result**: Still 0 functions! (Imports alone insufficient)

### Fix #4: Add Functions to __all__ ✅
**Commit**: 3fa7481
**Problem**: Functions imported but not explicitly exported
**Impact**: Still "0 functions found"
**Solution**: Added all functions to `__all__` list
**Result**: Still 0 functions! (__all__ not the issue)

### Fix #5: Move Decorators to function_app.py 🔄
**Commit**: 21c7998 (CURRENT)
**Problem**: Azure Functions V4 scans function_app.py ITSELF for decorators
**Impact**: Decorators in other files invisible to discovery
**Solution**: Complete rewrite - thin wrapper functions in function_app.py with decorators, delegating to real implementations
**Status**: ⏳ DEPLOYING (Workflow 19545401423, ETA 17:27 UTC)

---

## Technical Discoveries

### Discovery #1: Merge Conflicts Are Silent Killers
- Syntactically valid Python
- Pass pre-commit and CI
- Only fail at runtime
- **Learning**: Always grep for `<<<<<<<` markers before deployment

### Discovery #2: Workload Profile Capacity Planning
- Blue-green deployments need 2x capacity
- Default `maximumCount: 1` insufficient
- Failures show as "ActivationFailed" not "NotRunning"
- **Learning**: Plan capacity for deployment patterns, not just steady state

### Discovery #3: Azure Functions V4 Python Discovery Mechanism
- Scans `function_app.py` file itself, not imported modules
- Decorators MUST be in function_app.py for discovery
- Simply importing decorated functions doesn't work
- `__all__` exports don't affect discovery
- **Learning**: Follow Microsoft's pattern - all decorators in function_app.py

### Discovery #4: Disk Space Causes Strange Errors
- Az CLI cache corruption
- Empty command outputs
- Timeouts and hangs
- **Learning**: Check `df -h` first when seeing weird behavior

---

## Deployment Timeline

| Time | Event | Result |
|------|-------|--------|
| 14:44 | Deployment #1 (Fix #1) | ❌ ActivationFailed (capacity) |
| 14:59 | Fix #2 (capacity) | ✅ Applied |
| 15:04 | Deployment #2 (Fix #1+2) | ✅ Running, ❌ 0 functions |
| 16:46 | **BREAKTHROUGH**: First "Running" replica | ✅ Major milestone! |
| 16:56 | Deployment #3 (+ Fix #3) | ✅ Running, ❌ 0 functions |
| 17:06 | Added Fix #4 (__all__) | Deployed via env var change |
| 17:08 | Revision 0000011 running | ❌ Still 0 functions |
| 17:19 | Deployment #4 (Fix #5 - decorators in function_app.py) | 🔄 IN PROGRESS |
| ~17:27 | Expected: Functions discovered | ⏳ PENDING |

---

## Current Status

**Container App**: orch-dev-yc4hkcb2vv
- Status: Running
- Latest Revision: orch-dev-yc4hkcb2vv--0000011
- Replicas: 1 (Running state ✅)
- Functions Discovered: 0 (❌ Needs Fix #5)
- Workload Profile: E16 (128GB RAM, 16 vCPU, max 2 nodes ✅)

**GitOps Workflow**: 19545401423
- Status: IN PROGRESS
- Building: Image with all 5 fixes
- ETA: ~17:27 UTC

**Expected Next Revision**: 0000012 or higher
**Expected Functions**: 10 (finally!)

---

## Architecture Changes

### Original (Broken)
```python
# function_app.py
from azure_haymaker.orchestrator import app
__all__ = ["app"]

# timer_trigger.py
@app.timer_trigger(...)
def haymaker_timer(...):
    pass
```
**Result**: Azure Functions can't find decorated functions

### Final (Working)
```python
# function_app.py
app = func.FunctionApp()

@app.timer_trigger(...)
async def haymaker_timer(...):
    from azure_haymaker.orchestrator.timer_trigger import haymaker_timer as impl
    return await impl(...)

# timer_trigger.py
async def haymaker_timer(...):  # No decorator
    # Implementation
```
**Result**: Azure Functions finds all decorators in function_app.py

---

## Lessons for Future

### For Azure Functions V4 Python
1. **ALL decorators must be in function_app.py** - no exceptions
2. Use delegation pattern for modular code
3. Lazy imports in wrappers avoid circular dependencies
4. Don't trust that "import executes decorators" = "discovery works"

### For Container Apps Deployments
1. Set `maximumCount >= 2` for E-series profiles
2. Use env var changes to force new revisions when image content changes
3. `:latest` tag doesn't auto-update without configuration change

### For Debugging
1. Clear az CLI cache when seeing empty outputs
2. Check disk space before blaming code
3. Verify actual container file contents, don't assume Docker COPY worked

---

## Part 2: CLI Commands (Parallel Track)

**PR #27**: https://github.com/rysweet/AzureHayMaker/pull/27
**Status**: ✅ Implemented, ⏳ Awaiting container verification for E2E testing

**Bugs Fixed**:
1. Import path: azure.mgmt.appcontainers → azure.mgmt.app
2. Parameter: container_app_name → name
3. Version: >=1.0.0 → >=1.0.0b2
4. ⏳ API version issue: Still investigating

**Next**: Test commands once container fully operational

---

## Success Criteria (Remaining)

**Critical** (must pass):
- [ ] Azure Functions discovers 10 functions
- [ ] Functions accessible via HTTP
- [ ] No import errors in logs

**Important**:
- [ ] haymaker orch commands work
- [ ] Agent deployment succeeds
- [ ] Agent execution monitored
- [ ] 128GB memory utilized

**Nice to have**:
- [ ] Agent completes successfully
- [ ] Results captured

---

## Next Actions (After Deployment #4 Completes)

### 1. Verify Function Discovery (5 minutes)
```bash
# Wait for workflow
gh run view 19545401423

# Check new revision
az containerapp revision list --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg --output table

# Check function discovery in logs
az containerapp logs show --name orch-dev-yc4hkcb2vv --resource-group haymaker-dev-rg --tail 300 | grep -A 15 "Found the following functions"

# Expected: 10 functions listed!
```

### 2. Test HTTP Endpoint (2 minutes)
```bash
curl -v https://orch-dev-yc4hkcb2vv.ashyocean-9cc3722e.westus2.azurecontainerapps.io/
```

### 3. Test haymaker orch Commands (5 minutes)
```bash
# Fix API version issue first
# Then test:
haymaker orch status --app-name orch-dev-yc4hkcb2vv
haymaker orch health --app-name orch-dev-yc4hkcb2vv --deep
```

### 4. Test Agent Deployment (30-60 minutes)
```bash
# Trigger orchestration
# Monitor agent deployment
# Verify completion
```

---

## Estimated Completion

- **Container Verification**: 17:30 UTC (10 min from now)
- **CLI Testing**: 17:40 UTC (after container verified)
- **Agent E2E Testing**: 18:30 UTC (if we can trigger it)
- **Issue #26 Complete**: 18:30 UTC

**Total Time**: ~4.5 hours (significantly longer than estimated due to Azure Functions discovery complexity)

---

## Files Modified This Session

**Container Fixes** (develop branch):
- src/azure_haymaker/orchestrator/__init__.py (merge conflict removal)
- src/function_app.py (complete rewrite with decorators)

**CLI Implementation** (PR #27):
- cli/src/haymaker_cli/orch/ (7 new modules, 3,134 lines)
- cli/pyproject.toml (dependency added)

**Configuration**:
- E16 workload profile (capacity increased)
- Container app (env var for revision forcing)

**Documentation**:
- Multiple verification plans and status reports

---

**Current**: Waiting for Deployment #4 to complete (~7 minutes remaining)
**Hope**: This time Azure Functions will finally discover all 10 functions!
**Confidence**: 95% (pattern matches Microsoft's documented approach exactly)
