# Analytics Dashboard Architecture

## Overview
Real-time analytics dashboard for monitoring AzureHayMaker orchestrator execution metrics, costs, telemetry volume, and agent health.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure Static Web App                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            React Dashboard (TypeScript)                │  │
│  │                                                         │  │
│  │  ┌──────────────┐  ┌──────────────┐                  │  │
│  │  │ Execution    │  │  Cost        │                  │  │
│  │  │ Timeline     │  │  Breakdown   │                  │  │
│  │  └──────────────┘  └──────────────┘                  │  │
│  │                                                         │  │
│  │  ┌──────────────┐  ┌──────────────┐                  │  │
│  │  │ Agent        │  │  Telemetry   │                  │  │
│  │  │ Status       │  │  Volume      │                  │  │
│  │  └──────────────┘  └──────────────┘                  │  │
│  │                                                         │  │
│  │  ┌──────────────────────────────────────────────┐    │  │
│  │  │      Dashboard State (React Context)          │    │  │
│  │  │  - Time range, filters, WebSocket connection │    │  │
│  │  └──────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                    │                    │
                    │ HTTPS              │ WebSocket (wss://)
                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Orchestrator Server                     │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ GET /metrics │  │ GET          │  │ WS /ws/      │      │
│  │ GET /analytics  │ /analytics   │  │ metrics      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │               │
│         └──────────────────┴──────────────────┘               │
│                            │                                  │
│                            ▼                                  │
│               ┌────────────────────────┐                     │
│               │  Executions State Dict  │                     │
│               │  (In-Memory)            │                     │
│               └────────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │  Azure Table Storage     │
              │  (ExecutionRuns)         │
              └─────────────────────────┘
```

## Module Specifications

### Frontend Modules

#### 1. Dashboard Application (Root)
**Location**: `dashboard/`

**Responsibilities**:
- Application entry point
- Route configuration
- Global state management
- WebSocket lifecycle management

**Public API**:
```typescript
// dashboard/src/App.tsx
export function App(): JSX.Element

// dashboard/src/contexts/DashboardContext.tsx
export interface DashboardState {
  timeRange: TimeRange;
  selectedAgents: string[];
  refreshRate: number;
  isConnected: boolean;
}

export function DashboardProvider({ children }: PropsWithChildren): JSX.Element
export function useDashboard(): DashboardState
```

#### 2. ExecutionTimeline Component
**Location**: `dashboard/src/components/ExecutionTimeline/`

**Responsibilities**:
- Display time-series visualization of agent executions
- Show concurrent execution counts over time
- Interactive tooltips with execution details

**Public API**:
```typescript
export interface ExecutionTimelineProps {
  data: ExecutionDataPoint[];
  timeRange: TimeRange;
  onExecutionClick?: (executionId: string) => void;
}

export function ExecutionTimeline(props: ExecutionTimelineProps): JSX.Element
```

**Data Model**:
```typescript
interface ExecutionDataPoint {
  timestamp: string; // ISO8601
  concurrent_executions: number;
  completed_count: number;
  failed_count: number;
}
```

#### 3. CostBreakdown Component
**Location**: `dashboard/src/components/CostBreakdown/`

**Responsibilities**:
- Display cost breakdown by service (Compute, Storage, Telemetry)
- Show cost trend over time (line chart)
- Display budget vs actual indicators

**Public API**:
```typescript
export interface CostBreakdownProps {
  data: CostData;
  timeRange: TimeRange;
}

export function CostBreakdown(props: CostBreakdownProps): JSX.Element
```

**Data Model**:
```typescript
interface CostData {
  total_cost: number;
  budget: number;
  breakdown: {
    compute: number;
    storage: number;
    telemetry: number;
    other: number;
  };
  trend: Array<{
    timestamp: string;
    cost: number;
  }>;
}
```

#### 4. AgentStatus Component
**Location**: `dashboard/src/components/AgentStatus/`

**Responsibilities**:
- Display grid/card layout of all agents
- Show status indicators (Running, Idle, Failed, Queued)
- Display last execution timestamp and duration

**Public API**:
```typescript
export interface AgentStatusProps {
  agents: AgentInfo[];
  onAgentClick?: (agentId: string) => void;
}

export function AgentStatus(props: AgentStatusProps): JSX.Element
```

**Data Model**:
```typescript
interface AgentInfo {
  agent_id: string;
  agent_name: string;
  status: 'running' | 'idle' | 'failed' | 'queued';
  last_execution_at?: string;
  last_duration_seconds?: number;
  error_message?: string;
}
```

#### 5. TelemetryVolume Component
**Location**: `dashboard/src/components/TelemetryVolume/`

**Responsibilities**:
- Display telemetry volume by type (logs, metrics, traces)
- Show ingestion rate (events/second)
- Alert indicators for anomalies

**Public API**:
```typescript
export interface TelemetryVolumeProps {
  data: TelemetryData;
  timeRange: TimeRange;
}

export function TelemetryVolume(props: TelemetryVolumeProps): JSX.Element
```

**Data Model**:
```typescript
interface TelemetryData {
  logs: {
    volume_bytes: number;
    rate_per_second: number;
  };
  metrics: {
    volume_bytes: number;
    rate_per_second: number;
  };
  traces: {
    volume_bytes: number;
    rate_per_second: number;
  };
  anomaly_detected: boolean;
}
```

#### 6. WebSocket Service
**Location**: `dashboard/src/services/websocket.ts`

**Responsibilities**:
- Establish and maintain WebSocket connection
- Handle reconnection with exponential backoff
- Parse and validate incoming messages
- Broadcast updates to components via callbacks

**Public API**:
```typescript
export class MetricsWebSocket {
  constructor(url: string);
  connect(): Promise<void>;
  disconnect(): void;
  onMetricUpdate(callback: (data: MetricUpdate) => void): () => void;
  get isConnected(): boolean;
}

export interface MetricUpdate {
  type: 'execution' | 'cost' | 'telemetry' | 'agent';
  timestamp: string;
  data: any;
}
```

#### 7. API Client
**Location**: `dashboard/src/services/api.ts`

**Responsibilities**:
- HTTP client for REST API calls
- Request/response transformation
- Error handling and retry logic

**Public API**:
```typescript
export class DashboardAPI {
  constructor(baseUrl: string, authToken?: string);

  async getMetrics(): Promise<MetricsResponse>;
  async getAnalytics(period: '7d' | '30d' | '90d'): Promise<AnalyticsResponse>;
  async getCostBreakdown(period: '7d' | '30d' | '90d'): Promise<CostData>;
  async getAgentStatus(): Promise<AgentInfo[]>;
  async getTelemetryVolume(period: '7d' | '30d' | '90d'): Promise<TelemetryData>;
}
```

### Backend Modules

#### 1. WebSocket Metrics Endpoint
**Location**: `src/azure_haymaker/orchestrator/routes/websocket_routes.py`

**Responsibilities**:
- Accept WebSocket connections
- Stream real-time metric updates
- Handle client disconnections gracefully

**Public API**:
```python
@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """Stream real-time metrics to connected clients."""
    pass

def broadcast_metric_update(metric_type: str, data: dict) -> None:
    """Broadcast metric update to all connected WebSocket clients."""
    pass
```

**Message Format**:
```json
{
  "type": "metric_update",
  "timestamp": "2026-01-17T21:45:00Z",
  "data": {
    "metric_name": "execution.started|execution.completed|cost.updated|telemetry.volume",
    "execution_id": "exec-123",
    "agent_id": "agent-456",
    "value": 42.5,
    "metadata": {}
  }
}
```

#### 2. Cost Breakdown Endpoint
**Location**: `src/azure_haymaker/orchestrator/routes/cost_routes.py`

**Responsibilities**:
- Aggregate cost data by service type
- Calculate cost trends over time
- Compare against budget

**Public API**:
```python
@router.get("/cost/breakdown")
async def get_cost_breakdown(
    period: Literal["7d", "30d", "90d"] = "30d",
    _: AuthDep = Depends(require_auth)
) -> CostBreakdownResponse:
    """Get cost breakdown by service type."""
    pass
```

#### 3. Agent Status Endpoint
**Location**: `src/azure_haymaker/orchestrator/routes/agent_routes.py`

**Responsibilities**:
- Return current status of all agents
- Provide last execution details
- Include error information for failed agents

**Public API**:
```python
@router.get("/agents/status")
async def get_agent_status(
    _: AuthDep = Depends(require_auth)
) -> list[AgentStatusResponse]:
    """Get status of all agents."""
    pass
```

#### 4. Telemetry Volume Endpoint
**Location**: `src/azure_haymaker/orchestrator/routes/telemetry_routes.py`

**Responsibilities**:
- Aggregate telemetry volume by type
- Calculate ingestion rates
- Detect anomalies

**Public API**:
```python
@router.get("/telemetry/volume")
async def get_telemetry_volume(
    period: Literal["7d", "30d", "90d"] = "30d",
    _: AuthDep = Depends(require_auth)
) -> TelemetryVolumeResponse:
    """Get telemetry volume statistics."""
    pass
```

## Deployment Architecture

### Azure Static Web Apps Configuration
**Location**: `dashboard/staticwebapp.config.json`

```json
{
  "routes": [
    {
      "route": "/api/*",
      "allowedRoles": ["authenticated"]
    }
  ],
  "navigationFallback": {
    "rewrite": "/index.html"
  },
  "responseOverrides": {
    "401": {
      "redirect": "/.auth/login/aad",
      "statusCode": 302
    }
  }
}
```

### CI/CD Pipeline
**Location**: `.github/workflows/dashboard-deploy.yml`

**Triggers**: Push to `main` branch, changes in `dashboard/**`

**Steps**:
1. Checkout code
2. Setup Node.js 20
3. Install dependencies (`npm ci`)
4. Build dashboard (`npm run build`)
5. Deploy to Azure Static Web Apps
6. Run E2E tests against deployed app

## Data Flow

### Static Data Flow (HTTP)
```
Dashboard Component → API Client → FastAPI Endpoint → Table Storage → Response
```

### Real-Time Data Flow (WebSocket)
```
Orchestrator Event → WebSocket Broadcast → Dashboard Component → Chart Update
```

## Technology Stack

### Frontend
- **Framework**: React 18 + TypeScript 5
- **Build Tool**: Vite 5
- **Charts**: Recharts 2
- **State**: React Context API
- **HTTP Client**: Fetch API
- **WebSocket**: Native WebSocket API
- **Testing**: Vitest + React Testing Library
- **E2E**: Playwright

### Backend
- **Framework**: FastAPI (existing)
- **WebSocket**: Starlette WebSocket
- **Authentication**: Azure AD B2C (existing)
- **Storage**: Azure Table Storage (existing)

### Deployment
- **Frontend**: Azure Static Web Apps
- **Backend**: Azure Container Apps (existing)
- **CI/CD**: GitHub Actions

## File Structure

```
dashboard/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── staticwebapp.config.json
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── contexts/
│   │   └── DashboardContext.tsx
│   ├── components/
│   │   ├── ExecutionTimeline/
│   │   │   ├── index.tsx
│   │   │   ├── ExecutionTimeline.tsx
│   │   │   └── types.ts
│   │   ├── CostBreakdown/
│   │   │   ├── index.tsx
│   │   │   ├── CostBreakdown.tsx
│   │   │   └── types.ts
│   │   ├── AgentStatus/
│   │   │   ├── index.tsx
│   │   │   ├── AgentStatus.tsx
│   │   │   └── types.ts
│   │   ├── TelemetryVolume/
│   │   │   ├── index.tsx
│   │   │   ├── TelemetryVolume.tsx
│   │   │   └── types.ts
│   │   └── shared/
│   │       ├── TimeRangeSelector.tsx
│   │       └── AgentFilter.tsx
│   ├── services/
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── types/
│   │   └── index.ts
│   └── utils/
│       └── date.ts
├── tests/
│   ├── unit/
│   │   └── components/
│   └── e2e/
│       └── dashboard.spec.ts
└── public/
    └── favicon.ico

src/azure_haymaker/orchestrator/routes/
├── websocket_routes.py (NEW)
├── cost_routes.py (NEW)
├── agent_routes.py (NEW)
├── telemetry_routes.py (NEW)
└── analytics_routes.py (EXISTING - minimal changes)
```

## Security Considerations

1. **Authentication**: All API endpoints require Azure AD B2C authentication
2. **WebSocket Security**: Token-based authentication for WebSocket connections
3. **CORS**: Configure CORS to allow Static Web App origin only
4. **Rate Limiting**: Apply rate limiting to WebSocket connections
5. **Input Validation**: Validate all query parameters and message payloads

## Performance Targets

- **Initial Load**: < 3 seconds (including auth redirect)
- **Chart Render**: < 100ms after data received
- **WebSocket Latency**: < 500ms for metric updates
- **Concurrent Users**: Support 100+ simultaneous WebSocket connections

## Testing Strategy

### Unit Tests (60%)
- Component rendering tests
- Service layer tests
- Utility function tests

### Integration Tests (30%)
- API client integration tests
- WebSocket connection tests
- Component interaction tests

### E2E Tests (10%)
- Full dashboard workflow
- Real-time update verification
- Authentication flow

## Implementation Phases

### Phase 1: Frontend Core (Week 1)
- React app structure
- Four dashboard components (static data)
- API client implementation
- Local development setup

### Phase 2: Real-Time Updates (Week 2)
- WebSocket endpoint in FastAPI
- WebSocket client in React
- Real-time chart updates
- Reconnection logic

### Phase 3: Deployment (Week 3)
- Azure Static Web Apps configuration
- CI/CD pipeline
- Azure AD B2C integration
- Production deployment

## Success Criteria

1. All four components render without errors
2. WebSocket connection establishes and receives updates
3. Time range selector updates all charts
4. Agent filter applies across all components
5. Authentication flow works end-to-end
6. Dashboard deployed to Azure Static Web Apps
7. CI/CD pipeline runs successfully
8. 80%+ test coverage
