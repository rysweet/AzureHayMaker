# Container Apps Startup Failure Investigation

## Current Status (2025-11-22 00:30 PST)

**Blocker**: Azure Functions container will NOT start in Container Apps despite:
- ✅ Code compiles (17/17 functions)
- ✅ All 279 tests passing
- ✅ Docker builds successfully  
- ✅ Deployment succeeds
- ❌ Container never reaches Running state

## Test Matrix

| Revision | Change | Result |
|----------|--------|--------|
| 0000002 | Baseline (works) | ✅ Running |
| 0000019 | +function_app.py +host.json (Bundle V1) | ❌ NotRunning |
| 0000020 | +host.json | ❌ NotRunning |
| 0000021 | +minReplicas=1 | ❌ NotRunning |
| 0000022 | +WEBSITES_PORT env var | ❌ NotRunning |
| 0000023 | Extension Bundle V1→V4 | ❌ NotRunning |

## Hypothesis

Adding function_app.py (2159 lines, 17 functions) breaks container startup.

Possible causes:
1. Import errors in function_app.py
2. Azure Functions runtime can't handle 17 functions in Container Apps
3. Memory exhaustion during initialization
4. Extension bundle incompatibility

## Evidence

**What Works**: Revision 0000002 (no function_app.py)
**What Fails**: All revisions with function_app.py

**Container Details**:
- Image builds: ✅
- Deployment succeeds: ✅
- Container starts: ❌
- Logs available: ❌
- HTTP responds: ❌

## Recommendation

Test with minimal function_app.py (1-2 functions) to isolate if it's:
- File size issue
- Specific function causing crash
- General Azure Functions + Container Apps incompatibility
