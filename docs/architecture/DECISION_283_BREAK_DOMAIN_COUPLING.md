# Architecture Decision: Break Domain Coupling (Issue #283)

## Executive Summary

After analyzing the codebase, there is **NO actual Python circular import**. The issue is **architectural coupling** where `orchestrator` domain imports from `knowledge_worker` domain, creating a one-way dependency that violates domain independence.

**Recommendation**: Move `TeamsIntegration` to shared module (Option 4 - Simplest Solution)

## Problem Analysis

### Current State
```
orchestrator/activities/teams_setup.py
    ↓ (imports)
knowledge_worker/teams_integration.py

knowledge_worker/orchestrator.py
    ↓ (no import of orchestrator domain)
```

### Root Cause
1. `TeamsIntegration` is in `knowledge_worker` domain but used by `orchestrator` domain
2. This creates one-way coupling: orchestrator → knowledge_worker
3. `knowledge_worker` domain DOES NOT import from `orchestrator` - no circular import!
4. The `KnowledgeWorkerOrchestrator` naming is confusing but not actually a coupling issue

### Impact Assessment
- **Modularity**: DEGRADED - orchestrator depends on knowledge_worker unnecessarily
- **Testability**: ACCEPTABLE - no circular dependency prevents testing
- **Maintainability**: MEDIUM RISK - coupling exists but manageable
- **Philosophy Compliance**: VIOLATED - one domain shouldn't depend on another

## Solution Evaluation

### Option 1: Event Bus Pattern ❌
**Verdict**: OVER-ENGINEERED
- **Pros**: Complete decoupling
- **Cons**: High complexity, async coordination, 500+ LOC new code
- **Philosophy**: Violates ruthless simplicity

### Option 2: Contract Layer Pattern ❌
**Verdict**: OVER-ENGINEERED  
- **Pros**: Explicit contracts
- **Cons**: Runtime wiring, dependency injection framework, 300+ LOC
- **Philosophy**: Unnecessary abstraction

### Option 3: Hybrid Approach ❌
**Verdict**: MOST OVER-ENGINEERED
- **Pros**: "Best of both worlds"
- **Cons**: TWO patterns to maintain, 800+ LOC
- **Philosophy**: Complexity without proportional value

### Option 4: Move to Shared Module ✅ **RECOMMENDED**
**Verdict**: RUTHLESSLY SIMPLE
- **Pros**: 
  - Minimal code changes (~50 LOC total)
  - Clear dependency flow
  - Follows Python packaging best practices
  - Easy to understand and maintain
- **Cons**: 
  - Creates new module (justified by breaking coupling)
- **Philosophy**: ✅ Ruthless simplicity, ✅ Minimal abstraction, ✅ Clear module boundaries

## Recommended Solution: Shared Teams Module

### Architecture

```
src/azure_haymaker/
├── shared/               # NEW: Shared utilities
│   └── teams/           # NEW: Teams integration
│       ├── __init__.py
│       └── integration.py  # Moved from knowledge_worker/teams_integration.py
├── orchestrator/
│   └── activities/
│       └── teams_setup.py  # Imports from shared.teams
└── knowledge_worker/
    ├── __init__.py          # No longer exports TeamsIntegration
    └── (no orchestrator imports)
```

### Dependency Flow
```
orchestrator → shared.teams
knowledge_worker → shared.teams (if needed)

NO: orchestrator → knowledge_worker
NO: knowledge_worker → orchestrator
```

### Module Specifications

#### Module: `src/azure_haymaker/shared/teams/integration.py`

**Purpose**: Microsoft Teams integration utilities shared across domains

**Contract**:
- **Inputs**: GraphServiceClient, run_id, team configuration
- **Outputs**: Team creation results, channel setup results
- **Side Effects**: Creates Teams teams, channels, posts messages via Graph API

**Public API** (`__all__`):
- `TeamsIntegration` - Main integration class
- `TeamsIntegrationError` - Exception for Teams operations

**Dependencies**:
- `msgraph.graph_service_client` (external)
- Standard library only (logging, typing)
- NO dependencies on orchestrator or knowledge_worker domains

**Test Requirements**:
- Unit tests for all public methods
- Mock Graph API calls
- Test error handling and retry logic
- Verify no domain coupling

## Implementation Plan

### Phase 1: Create Shared Module Structure
1. Create `src/azure_haymaker/shared/__init__.py`
2. Create `src/azure_haymaker/shared/teams/__init__.py`
3. Add `__all__` exports for public API

### Phase 2: Move TeamsIntegration
1. Move `knowledge_worker/teams_integration.py` → `shared/teams/integration.py`
2. Update imports in moved file (remove any domain-specific imports)
3. Update `shared/teams/__init__.py` to export `TeamsIntegration`, `TeamsIntegrationError`

### Phase 3: Update Import Statements (8 files)
1. `orchestrator/activities/teams_setup.py`:
   - Change: `from azure_haymaker.knowledge_worker.teams_integration import`
   - To: `from azure_haymaker.shared.teams import`

2. `knowledge_worker/__init__.py`:
   - Change: `from azure_haymaker.knowledge_worker.teams_integration import`
   - To: `from azure_haymaker.shared.teams import`
   - Keep exporting for backward compatibility (optional)

3. `knowledge_worker/teams_integration_README.md`:
   - Update import examples to use `shared.teams`

4. `knowledge_worker/content/fallback.py`:
   - Update comments referencing orchestrator (lines 584-585)

5-8. Other affected files (if they import TeamsIntegration):
   - Update imports to use `shared.teams`

### Phase 4: Testing
1. Write new tests for `shared.teams.integration`
2. Update existing tests to import from `shared.teams`
3. Verify no circular imports: `python -c "import azure_haymaker.orchestrator; import azure_haymaker.knowledge_worker"`
4. Run full test suite to ensure no regressions

### Phase 5: Documentation
1. Create `src/azure_haymaker/shared/teams/README.md`
2. Document the architectural decision
3. Update affected module docstrings

## Files Requiring Changes

### New Files (3)
1. `src/azure_haymaker/shared/__init__.py` (new, ~10 LOC)
2. `src/azure_haymaker/shared/teams/__init__.py` (new, ~15 LOC)
3. `src/azure_haymaker/shared/teams/integration.py` (moved from knowledge_worker, ~340 LOC)

### Modified Files (5)
1. `src/azure_haymaker/orchestrator/activities/teams_setup.py` (import change, ~2 LOC)
2. `src/azure_haymaker/knowledge_worker/__init__.py` (import change, ~2 LOC)
3. `src/azure_haymaker/knowledge_worker/teams_integration_README.md` (documentation, ~10 LOC)
4. `src/azure_haymaker/knowledge_worker/content/fallback.py` (comments, ~2 LOC)
5. `specs/MODULE_TEAMS_INTEGRATION.md` (if exists, update paths)

### Deleted Files (1)
1. `src/azure_haymaker/knowledge_worker/teams_integration.py` (moved to shared)

## Success Criteria

### Technical Validation
- [ ] `python -c "import azure_haymaker.orchestrator"` succeeds
- [ ] `python -c "import azure_haymaker.knowledge_worker"` succeeds
- [ ] `python -c "import azure_haymaker.shared.teams"` succeeds
- [ ] Both domains can be imported independently
- [ ] No circular imports detected by import checker
- [ ] All existing tests pass
- [ ] New tests verify shared module works correctly

### Philosophy Compliance
- [ ] ✅ Ruthless simplicity - minimal code changes
- [ ] ✅ Clear module boundaries - shared module is self-contained
- [ ] ✅ Bricks & Studs - TeamsIntegration has clear public API
- [ ] ✅ Regeneratable - module can be rebuilt from spec
- [ ] ✅ Zero-BS - no stubs, no placeholders, fully functional

### Design Quality
- [ ] Clear dependency flow: domains → shared (not domains → domains)
- [ ] Self-contained shared module with no domain dependencies
- [ ] Explicit `__all__` exports define public API
- [ ] Comprehensive tests verify functionality
- [ ] Documentation explains architectural decision

## Migration Path

### Step 1: Create Shared Module (No Breaking Changes)
- Create new shared module structure
- Move TeamsIntegration to shared location
- Both old and new import paths work temporarily

### Step 2: Update Imports (Breaking Change Point)
- Update all import statements in one commit
- Remove old `knowledge_worker/teams_integration.py`
- This is the breaking change point

### Step 3: Verify & Test
- Run full test suite
- Verify import independence
- Check for any missed import statements

## Trade-offs & Justification

### Why Not Event Bus or Contracts?
- **Proportionality Principle**: Effort must match complexity
- **Current Complexity**: One class (TeamsIntegration) used by two domains
- **Event Bus Cost**: 500+ LOC, async complexity, testing overhead
- **Contracts Cost**: 300+ LOC, runtime wiring, DI framework
- **Moving to Shared Cost**: ~50 LOC changes, simple refactoring
- **Ratio**: Event bus = 10x more complex for same benefit

### Why Create `shared` Module?
- **Python Best Practice**: Shared code goes in shared module
- **Clear Intent**: "shared" signals cross-domain utilities
- **Future-Proof**: Can add other shared utilities as needed
- **No Over-Engineering**: Only creates what's needed now

### Naming: Why `shared.teams` not `integrations.teams`?
- **Simplicity**: "shared" is clear and unambiguous
- **Flexibility**: "shared" can contain utilities, integrations, models, etc.
- **Philosophy**: Name reflects purpose, not implementation

## Conclusion

This architectural decision follows the ruthless simplicity principle by choosing the simplest solution that solves the problem completely. Moving `TeamsIntegration` to a shared module:

1. Eliminates domain coupling completely
2. Requires minimal code changes (~50 LOC)
3. Follows Python packaging best practices
4. Makes dependencies explicit and unidirectional
5. Maintains 100% functionality with zero regressions

**Estimated Implementation Time**: 4-6 hours (vs 40-60 hours for event bus)

**Risk Level**: LOW (simple refactoring, easy to rollback)

**Philosophy Compliance**: ✅✅✅ PERFECT

---

## Appendix: Rejected Naming Considerations

### Why Not `knowledge_worker/orchestrator.py` → Rename/Move?
- **Not Actually a Problem**: Despite confusing name, it doesn't import from orchestrator domain
- **Scope Creep**: Issue #283 is about domain coupling, not naming
- **Separate Concern**: Naming can be addressed in separate issue if needed
- **No Value**: Renaming doesn't solve the coupling problem

### Why Not Keep TeamsIntegration in knowledge_worker?
- **Violates Independence**: orchestrator shouldn't depend on knowledge_worker
- **Asymmetric**: One domain depending on another breaks modularity
- **Future Risk**: knowledge_worker might eventually need orchestrator features
- **Philosophy**: Domains should be peers, not hierarchical

