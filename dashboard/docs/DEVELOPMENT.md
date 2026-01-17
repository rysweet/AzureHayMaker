# Development Guide

This guide covers setting up the development environment, coding standards, and best practices for contributing to the Analytics Dashboard.

## Development Setup

### Prerequisites

- **Node.js**: 20.x or later
- **npm**: 10.x or later
- **Git**: Latest version
- **VS Code** (recommended) or your preferred editor

### Initial Setup

```bash
# Clone repository
git clone https://github.com/rysweet/AzureHayMaker.git
cd AzureHayMaker/dashboard

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Start development server
npm run dev
```

### Environment Configuration

Create `.env` file with these variables:

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/metrics

# Development Settings
VITE_ENABLE_MOCK_DATA=true
VITE_LOG_LEVEL=debug

# Azure AD B2C (optional for local development)
VITE_AAD_CLIENT_ID=
VITE_AAD_TENANT_ID=
```

### VS Code Extensions

Recommended extensions:

```json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-typescript-next",
    "vitest.explorer"
  ]
}
```

## Project Structure

```
dashboard/
├── src/
│   ├── App.tsx                 # Root component
│   ├── main.tsx               # Entry point
│   ├── contexts/              # React Context providers
│   │   └── DashboardContext.tsx
│   ├── components/            # React components
│   │   ├── ExecutionTimeline/
│   │   │   ├── index.tsx       # Public export
│   │   │   ├── ExecutionTimeline.tsx
│   │   │   ├── types.ts
│   │   │   └── ExecutionTimeline.test.tsx
│   │   ├── CostBreakdown/
│   │   ├── AgentStatus/
│   │   ├── TelemetryVolume/
│   │   └── shared/            # Reusable components
│   │       ├── TimeRangeSelector.tsx
│   │       └── AgentFilter.tsx
│   ├── services/              # API clients
│   │   ├── api.ts
│   │   ├── websocket.ts
│   │   ├── api.test.ts
│   │   └── websocket.test.ts
│   ├── types/                 # TypeScript types
│   │   └── index.ts
│   ├── utils/                 # Utility functions
│   │   ├── date.ts
│   │   └── format.ts
│   └── __mocks__/             # Test mocks
│       └── websocket.ts
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── e2e/                   # E2E tests
├── public/                    # Static assets
├── vite.config.ts             # Vite configuration
├── tsconfig.json              # TypeScript configuration
├── package.json
└── README.md
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feat/your-feature-name
```

### 2. Develop with Hot Reload

```bash
# Start dev server
npm run dev

# Open http://localhost:5173
# Changes auto-reload
```

### 3. Run Tests Continuously

```bash
# Run tests in watch mode
npm run test:watch

# Run specific test file
npm run test src/components/ExecutionTimeline/ExecutionTimeline.test.tsx
```

### 4. Lint and Format

```bash
# Check linting
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run format
```

### 5. Type Checking

```bash
# Run TypeScript compiler
npm run type-check
```

## Coding Standards

### TypeScript

#### Component Props

Always define prop interfaces:

```typescript
// types.ts
export interface ExecutionTimelineProps {
  data: ExecutionDataPoint[];
  timeRange: TimeRange;
  onExecutionClick?: (executionId: string) => void;
}

// ExecutionTimeline.tsx
export function ExecutionTimeline({
  data,
  timeRange,
  onExecutionClick
}: ExecutionTimelineProps): JSX.Element {
  // Component implementation
}
```

#### Type Safety

Avoid `any` types - use specific types:

```typescript
// ❌ Bad
function processData(data: any) {
  return data.value;
}

// ✅ Good
interface DataPoint {
  value: number;
  timestamp: string;
}

function processData(data: DataPoint): number {
  return data.value;
}
```

#### Null Safety

Handle null/undefined explicitly:

```typescript
// ❌ Bad
function getAgentName(agent: AgentInfo) {
  return agent.agent_name.toUpperCase();
}

// ✅ Good
function getAgentName(agent: AgentInfo): string {
  return agent.agent_name?.toUpperCase() ?? 'Unknown';
}
```

### React Best Practices

#### Component Organization

```typescript
// 1. Imports
import { useState, useEffect } from 'react';
import { AgentInfo } from '../../types';

// 2. Interface/Type definitions
interface Props {
  agents: AgentInfo[];
}

// 3. Component
export function AgentStatus({ agents }: Props): JSX.Element {
  // 3a. Hooks
  const [filter, setFilter] = useState('');

  // 3b. Event handlers
  const handleFilterChange = (value: string) => {
    setFilter(value);
  };

  // 3c. Effects
  useEffect(() => {
    console.log('Agents updated');
  }, [agents]);

  // 3d. Render helpers
  const filteredAgents = agents.filter(a =>
    a.agent_name.includes(filter)
  );

  // 3e. Return JSX
  return (
    <div>
      {/* Component JSX */}
    </div>
  );
}
```

#### Memoization

Use memoization for expensive computations:

```typescript
import { useMemo } from 'react';

export function CostBreakdown({ data, timeRange }: Props): JSX.Element {
  const chartData = useMemo(() => {
    // Expensive computation
    return data.trend.map(point => ({
      ...point,
      formattedCost: formatCurrency(point.cost)
    }));
  }, [data.trend]); // Only recompute when trend changes

  return <LineChart data={chartData} />;
}
```

#### Event Handlers

Use `useCallback` for event handlers passed to child components:

```typescript
import { useCallback } from 'react';

export function ExecutionTimeline({ data, onExecutionClick }: Props): JSX.Element {
  const handleClick = useCallback((executionId: string) => {
    console.log('Clicked:', executionId);
    onExecutionClick?.(executionId);
  }, [onExecutionClick]);

  return (
    <div onClick={() => handleClick('exec-123')}>
      {/* Component JSX */}
    </div>
  );
}
```

### API Service Layer

#### Service Structure

```typescript
export class DashboardAPI {
  private baseUrl: string;
  private authToken?: string;

  constructor(baseUrl: string, authToken?: string) {
    this.baseUrl = baseUrl;
    this.authToken = authToken;
  }

  private async fetch<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(this.authToken && { Authorization: `Bearer ${this.authToken}` }),
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async getMetrics(): Promise<MetricsResponse> {
    return this.fetch<MetricsResponse>('/metrics');
  }
}
```

#### Error Handling

```typescript
try {
  const data = await api.getMetrics();
  setMetrics(data);
} catch (error) {
  if (error instanceof Error) {
    console.error('Failed to fetch metrics:', error.message);
    setError(error.message);
  }
}
```

## Testing

### Unit Tests

Test individual components and functions:

```typescript
// ExecutionTimeline.test.tsx
import { render, screen } from '@testing-library/react';
import { ExecutionTimeline } from './ExecutionTimeline';

describe('ExecutionTimeline', () => {
  it('renders execution data points', () => {
    const data = [
      { timestamp: '2026-01-17T21:00:00Z', concurrent_executions: 5 }
    ];

    render(<ExecutionTimeline data={data} timeRange={mockTimeRange} />);

    expect(screen.getByText(/5 concurrent/i)).toBeInTheDocument();
  });

  it('calls onExecutionClick when execution is clicked', async () => {
    const handleClick = vi.fn();
    render(
      <ExecutionTimeline
        data={mockData}
        timeRange={mockTimeRange}
        onExecutionClick={handleClick}
      />
    );

    const execution = screen.getByText('exec-123');
    await userEvent.click(execution);

    expect(handleClick).toHaveBeenCalledWith('exec-123');
  });
});
```

### Integration Tests

Test component interactions:

```typescript
// Dashboard.integration.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { DashboardProvider } from './contexts/DashboardContext';
import App from './App';

describe('Dashboard Integration', () => {
  it('fetches and displays metrics on load', async () => {
    render(
      <DashboardProvider>
        <App />
      </DashboardProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Total Cost/i)).toBeInTheDocument();
    });
  });
});
```

### E2E Tests

Test complete workflows with Playwright:

```typescript
// tests/e2e/dashboard.spec.ts
import { test, expect } from '@playwright/test';

test('dashboard loads and displays metrics', async ({ page }) => {
  await page.goto('http://localhost:5173');

  // Wait for authentication redirect
  await page.waitForURL(/dashboard/, { timeout: 10000 });

  // Verify metrics loaded
  await expect(page.locator('[data-testid="execution-timeline"]')).toBeVisible();
  await expect(page.locator('[data-testid="cost-breakdown"]')).toBeVisible();
});

test('time range selector updates all charts', async ({ page }) => {
  await page.goto('http://localhost:5173');

  // Select 7-day range
  await page.click('[data-testid="time-range-selector"]');
  await page.click('text=7 days');

  // Verify charts updated
  await expect(page.locator('[data-testid="execution-timeline"]')).toContainText('7 days');
});
```

### Mock Data for Testing

```typescript
// __mocks__/api.ts
export const mockMetrics: MetricsResponse = {
  timestamp: '2026-01-17T21:45:00Z',
  concurrent_executions: 5,
  total_executions_today: 127,
  active_agents: 12,
  total_cost_today: 45.67,
  telemetry_volume_mb: 1234.56
};

export const mockCostData: CostData = {
  total_cost: 1234.56,
  budget: 2000.00,
  breakdown: {
    compute: 845.32,
    storage: 123.45,
    telemetry: 234.56,
    other: 31.23
  },
  trend: [
    { timestamp: '2026-01-10T00:00:00Z', cost: 35.67 },
    { timestamp: '2026-01-11T00:00:00Z', cost: 38.92 }
  ]
};
```

## Performance Optimization

### Code Splitting

```typescript
// Lazy load components
import { lazy, Suspense } from 'react';

const ExecutionTimeline = lazy(() => import('./components/ExecutionTimeline'));
const CostBreakdown = lazy(() => import('./components/CostBreakdown'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ExecutionTimeline data={data} timeRange={timeRange} />
      <CostBreakdown data={costData} timeRange={timeRange} />
    </Suspense>
  );
}
```

### Debouncing

```typescript
import { debounce } from 'lodash-es';

const debouncedSearch = useMemo(
  () => debounce((query: string) => {
    fetchSearchResults(query);
  }, 300),
  []
);
```

### Virtual Scrolling

For large lists:

```typescript
import { FixedSizeList } from 'react-window';

function AgentList({ agents }: Props) {
  return (
    <FixedSizeList
      height={600}
      itemCount={agents.length}
      itemSize={80}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          <AgentCard agent={agents[index]} />
        </div>
      )}
    </FixedSizeList>
  );
}
```

## Debugging

### React DevTools

Install React DevTools browser extension for component inspection.

### Network Debugging

```typescript
// Enable API logging in development
if (import.meta.env.DEV) {
  console.log('API Request:', endpoint, options);
}
```

### WebSocket Debugging

```typescript
class MetricsWebSocket {
  connect() {
    this.ws = new WebSocket(url);

    this.ws.onmessage = (event) => {
      if (import.meta.env.DEV) {
        console.log('WebSocket Message:', JSON.parse(event.data));
      }
      // Handle message
    };
  }
}
```

## Common Issues

### CORS Errors

Ensure orchestrator allows dashboard origin:

```python
# In orchestrator FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### WebSocket Connection Failures

Check browser console for errors:
```javascript
// Add detailed error logging
ws.onerror = (error) => {
  console.error('WebSocket Error:', error);
  console.log('URL:', ws.url);
  console.log('Ready State:', ws.readyState);
};
```

### Type Errors

Run type checking:
```bash
npm run type-check
```

Fix errors before committing.

## Pre-Commit Checklist

Before committing:

- [ ] All tests pass (`npm run test`)
- [ ] No linting errors (`npm run lint`)
- [ ] Code formatted (`npm run format`)
- [ ] Types valid (`npm run type-check`)
- [ ] Build succeeds (`npm run build`)
- [ ] Manual testing completed

## Commit Message Format

Follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting changes
- `refactor`: Code restructuring
- `test`: Test changes
- `chore`: Build/tooling changes

**Example:**
```
feat(dashboard): add execution timeline component

- Implement time-series chart for executions
- Add interactive tooltips
- Support time range filtering

Closes #132
```

## Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Run pre-commit checklist
4. Push to GitHub
5. Create pull request with description
6. Address review feedback
7. Merge after approval

## Resources

- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)
- [Vitest Documentation](https://vitest.dev)
- [Recharts Documentation](https://recharts.org)
- [Project Issues](https://github.com/rysweet/AzureHayMaker/issues)
