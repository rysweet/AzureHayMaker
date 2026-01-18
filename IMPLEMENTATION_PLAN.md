# Analytics Dashboard Part 2 - Implementation Plan

## Overview
Complete implementation of Issue #132 analytics dashboard based on Part 1 foundation.

## Current Status
- ✅ Architecture: specs/analytics-dashboard-architecture.md
- ✅ Documentation: ~1,831 lines (README, DEPLOYMENT, API, DEVELOPMENT)
- ✅ Test Infrastructure: Vitest, React Testing Library, Playwright configured
- ✅ Existing Tests: 67 tests (API 25, WebSocket 22, ExecutionTimeline 20)
- ⏳ Remaining: ~4,800-5,500 lines implementation + 106 tests

## Phase 1: Complete TDD Tests (Step 7)

### Write Remaining 106 Tests:
1. CostBreakdown component tests (18 tests) - `src/components/CostBreakdown/CostBreakdown.test.tsx`
2. AgentStatus component tests (15 tests) - `src/components/AgentStatus/AgentStatus.test.tsx`
3. TelemetryVolume component tests (16 tests) - `src/components/TelemetryVolume/TelemetryVolume.test.tsx`
4. TimeRangeSelector tests (8 tests) - `src/components/shared/TimeRangeSelector.test.tsx`
5. AgentFilter tests (10 tests) - `src/components/shared/AgentFilter.test.tsx`
6. DashboardContext tests (12 tests) - `src/contexts/DashboardContext.test.tsx`
7. Integration tests (15 tests) - `tests/integration/dashboard.integration.test.tsx`
8. E2E tests (8 tests) - `tests/e2e/dashboard.spec.ts`
9. Test fixtures - `tests/fixtures/*.json`
10. Test utilities - `tests/utils/test-utils.tsx`, `tests/utils/mocks.ts`

**Total**: 106 new tests + fixtures + utilities

## Phase 2: Frontend Implementation (Step 8a)

### Services Layer (~300 lines):
1. `src/services/api.ts` - REST API client (to pass 25 existing tests)
2. `src/services/websocket.ts` - WebSocket client (to pass 22 existing tests)

### Components (~1,800 lines):
3. `src/components/ExecutionTimeline/ExecutionTimeline.tsx` (to pass 20 existing tests)
4. `src/components/ExecutionTimeline/index.tsx`
5. `src/components/CostBreakdown/CostBreakdown.tsx` (to pass 18 new tests)
6. `src/components/CostBreakdown/types.ts`
7. `src/components/CostBreakdown/index.tsx`
8. `src/components/AgentStatus/AgentStatus.tsx` (to pass 15 new tests)
9. `src/components/AgentStatus/types.ts`
10. `src/components/AgentStatus/index.tsx`
11. `src/components/TelemetryVolume/TelemetryVolume.tsx` (to pass 16 new tests)
12. `src/components/TelemetryVolume/types.ts`
13. `src/components/TelemetryVolume/index.tsx`

### Shared Components (~300 lines):
14. `src/components/shared/TimeRangeSelector.tsx` (to pass 8 new tests)
15. `src/components/shared/AgentFilter.tsx` (to pass 10 new tests)

### Context & App (~400 lines):
16. `src/contexts/DashboardContext.tsx` (to pass 12 new tests)
17. `src/App.tsx`
18. `src/main.tsx`

### Utilities (~100 lines):
19. `src/utils/date.ts`
20. `src/utils/format.ts`

**Frontend Total**: ~2,900 lines

## Phase 3: Backend Implementation (Step 8b)

### WebSocket Routes (~250 lines):
1. `src/azure_haymaker/orchestrator/routes/websocket_routes.py`
   - WebSocket endpoint /ws/metrics
   - Client connection management
   - Broadcast mechanism

### REST Endpoints (~550 lines):
2. `src/azure_haymaker/orchestrator/routes/cost_routes.py`
   - GET /cost/breakdown
3. `src/azure_haymaker/orchestrator/routes/agent_routes.py`
   - GET /agents/status
4. `src/azure_haymaker/orchestrator/routes/telemetry_routes.py`
   - GET /telemetry/volume

### Integration (~100 lines):
5. Update main FastAPI app to register new routes
6. Configure CORS for dashboard origin
7. Enable WebSocket support

**Backend Total**: ~900 lines

## Implementation Order

### Priority 1: Test Foundation
1. Write all 106 remaining tests
2. Create test fixtures and utilities
3. Verify all tests properly structured

### Priority 2: Services (Foundation)
4. Implement `src/services/api.ts` - passes 25 tests
5. Implement `src/services/websocket.ts` - passes 22 tests

### Priority 3: Components
6. Implement ExecutionTimeline - passes 20 tests
7. Implement CostBreakdown - passes 18 tests
8. Implement AgentStatus - passes 15 tests
9. Implement TelemetryVolume - passes 16 tests

### Priority 4: Shared & Context
10. Implement TimeRangeSelector - passes 8 tests
11. Implement AgentFilter - passes 10 tests
12. Implement DashboardContext - passes 12 tests

### Priority 5: Application
13. Implement App.tsx
14. Implement main.tsx
15. Implement utilities (date, format)

### Priority 6: Backend
16. Implement WebSocket routes
17. Implement REST endpoints
18. Integrate with main app

### Priority 7: Integration & E2E
19. Run integration tests (15 tests)
20. Run E2E tests (8 tests)

## Success Criteria

- [ ] All 173 tests passing (67 existing + 106 new)
- [ ] >80% code coverage
- [ ] Build succeeds without errors or warnings
- [ ] No TypeScript errors
- [ ] No linting errors
- [ ] Dashboard renders all 4 components
- [ ] WebSocket connection works
- [ ] Real-time updates display
- [ ] Time range selector functional
- [ ] Agent filter functional

## Philosophy Compliance

- Ruthless simplicity: Recharts (not D3), Context API (not Redux)
- Zero-BS: No stubs, all code functional
- TDD: Tests written BEFORE implementation
- Modular: Each component self-contained
- Regeneratable: Can rebuild from specs

## Delegation Strategy

1. **Tester Agent**: Write all 106 remaining tests (Step 7)
2. **Builder Agent**: Implement all code to pass tests (Step 8)
3. **Reviewer Agent**: Code review (Step 10)
4. **Cleanup Agent**: Simplification (Step 9)

## Estimated Effort

- Tests: 106 tests + fixtures/utilities = ~1,500 lines
- Frontend: ~2,900 lines
- Backend: ~900 lines
- **Total**: ~5,300 lines of production code + tests

