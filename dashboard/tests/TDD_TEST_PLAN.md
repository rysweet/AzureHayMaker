# TDD Test Plan for Analytics Dashboard

This document outlines the complete TDD test suite. Tests marked ✅ are complete, tests marked ⏳ need to be implemented.

## Test Coverage Summary

**Target**: 60% Unit / 30% Integration / 10% E2E

### Services Layer (Unit Tests - 60%)

#### ✅ API Client (`src/services/api.test.ts`)
- Constructor and initialization
- getMetrics() endpoint
- getAnalytics() endpoint with periods (7d, 30d, 90d)
- getCostBreakdown() endpoint
- getAgentStatus() endpoint
- getTelemetryVolume() endpoint
- Authentication header handling
- Error handling (HTTP errors, network errors, JSON parsing)

**Total**: 25 test cases

#### ✅ WebSocket Client (`src/services/websocket.test.ts`)
- Constructor
- connect() method
- disconnect() method
- onMetricUpdate() callback registration
- Multiple callbacks support
- Unsubscribe functionality
- isConnected property
- Reconnection with exponential backoff
- Heartbeat message handling
- Message parsing
- Error handling

**Total**: 22 test cases

### Components Layer (Unit Tests - 60%)

#### ✅ ExecutionTimeline (`src/components/ExecutionTimeline/ExecutionTimeline.test.tsx`)
- Rendering (empty state, with data, title)
- Data display (concurrent executions, completed count, failed count, timestamps)
- Interactions (onClick, tooltip on hover)
- Time range filtering
- Accessibility (ARIA labels, keyboard navigation)
- Error handling (invalid timestamps, negative values, missing fields)
- Performance (large datasets, memoization)

**Total**: 20 test cases

#### ⏳ CostBreakdown (`src/components/CostBreakdown/CostBreakdown.test.tsx`)
**Needs Implementation**:
- Rendering (empty state, with data, title)
- Cost display (total, budget, breakdown by service, budget percentage)
- Trend chart rendering
- Budget alert indicators
- Time range filtering
- Currency formatting
- Accessibility
- Error handling

**Target**: ~18 test cases

#### ⏳ AgentStatus (`src/components/AgentStatus/AgentStatus.test.tsx`)
**Needs Implementation**:
- Rendering (empty state, grid layout, agent cards)
- Status indicators (running, idle, failed, queued)
- Agent details (name, last execution, duration, error messages)
- Click interactions
- Filtering/sorting
- Accessibility
- Error handling

**Target**: ~15 test cases

#### ⏳ TelemetryVolume (`src/components/TelemetryVolume/TelemetryVolume.test.tsx`)
**Needs Implementation**:
- Rendering (empty state, with data, title)
- Volume display by type (logs, metrics, traces)
- Rate per second display
- Anomaly detection indicators
- Time range filtering
- Byte formatting
- Accessibility
- Error handling

**Target**: ~16 test cases

#### ⏳ Shared Components
**TimeRangeSelector** (`src/components/shared/TimeRangeSelector.test.tsx`):
- Rendering options (7d, 30d, 90d)
- Selection change events
- Active state indication
- Accessibility

**Target**: ~8 test cases

**AgentFilter** (`src/components/shared/AgentFilter.test.tsx`):
- Rendering agent list
- Multi-select functionality
- Select all/none
- Filter change events
- Accessibility

**Target**: ~10 test cases

### Context Layer (Unit Tests)

#### ⏳ DashboardContext (`src/contexts/DashboardContext.test.tsx`)
**Needs Implementation**:
- Provider initialization
- useDashboard hook
- State updates (time range, agent filter, refresh rate)
- WebSocket connection state
- Error handling

**Target**: ~12 test cases

### Integration Tests (30%)

#### ⏳ Dashboard Integration (`tests/integration/dashboard.integration.test.tsx`)
**Needs Implementation**:
- App loads and fetches initial data
- Time range selector updates all components
- Agent filter applies across components
- WebSocket updates reflect in UI
- Error states propagate correctly
- Authentication flow

**Target**: ~15 test cases

#### ⏳ API Integration (`tests/integration/api.integration.test.tsx`)
**Needs Implementation**:
- Multiple API calls in sequence
- Error recovery and retry logic
- Token refresh flow
- Rate limiting handling

**Target**: ~8 test cases

### E2E Tests (10%)

#### ⏳ E2E Scenarios (`tests/e2e/dashboard.spec.ts`)
**Needs Implementation**:
- User logs in and sees dashboard
- Time range selection updates all charts
- Agent filter focuses on specific agents
- Real-time updates appear from WebSocket
- Execution click opens details
- Error states show user-friendly messages

**Target**: ~8 test cases

## Test Data Fixtures

### Mock Data Files

#### ⏳ `tests/fixtures/metrics.json`
- Sample metrics response
- Various states (high load, low load, errors)

#### ⏳ `tests/fixtures/analytics.json`
- Sample analytics for 7d, 30d, 90d periods

#### ⏳ `tests/fixtures/costs.json`
- Sample cost breakdown
- Budget scenarios (under, at, over budget)

#### ⏳ `tests/fixtures/agents.json`
- Sample agent statuses
- All status types (running, idle, failed, queued)

#### ⏳ `tests/fixtures/telemetry.json`
- Sample telemetry volume data
- With and without anomalies

## Test Utilities

### ⏳ `tests/utils/test-utils.tsx`
**Needs Implementation**:
- Custom render function with providers
- Mock WebSocket factory
- Mock API factory
- Wait for utilities

### ⏳ `tests/utils/mocks.ts`
**Needs Implementation**:
- Mock data generators
- Faker-based random data
- State builders for complex scenarios

## Running Tests

```bash
# Run all tests
npm test

# Run specific test file
npm test src/components/ExecutionTimeline/ExecutionTimeline.test.tsx

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch

# Integration tests only
npm run test:integration

# E2E tests
npm run test:e2e
```

## Coverage Targets

- **Overall**: >80%
- **Services**: >90% (critical path)
- **Components**: >85% (UI logic)
- **Utils**: >95% (pure functions)

## Test Implementation Priority

1. ✅ API Client (Complete)
2. ✅ WebSocket Client (Complete)
3. ✅ ExecutionTimeline Component (Complete)
4. ⏳ CostBreakdown Component (Next)
5. ⏳ AgentStatus Component
6. ⏳ TelemetryVolume Component
7. ⏳ Shared Components
8. ⏳ DashboardContext
9. ⏳ Integration Tests
10. ⏳ E2E Tests

## Notes

- All tests should follow TDD methodology: write tests first, then implementation
- Tests should be independent and not rely on execution order
- Use descriptive test names that explain the scenario
- Mock external dependencies (API, WebSocket, timers)
- Test edge cases and error conditions
- Ensure accessibility testing in all component tests
