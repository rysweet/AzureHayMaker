# Analytics Dashboard

Real-time analytics dashboard for monitoring AzureHayMaker orchestrator execution metrics, costs, telemetry volume, and agent health.

## Overview

The Analytics Dashboard provides a comprehensive view of your AzureHayMaker orchestrator's operational metrics through an intuitive web interface. Built with React 18 and TypeScript, it offers real-time updates via WebSocket and historical data analysis through REST APIs.

## Features

### Real-Time Monitoring
- **Live Updates**: WebSocket connection provides sub-second metric updates
- **Execution Timeline**: Visualize concurrent agent executions over time
- **Agent Status**: Real-time status indicators for all agents (Running, Idle, Failed, Queued)
- **Cost Tracking**: Track compute, storage, and telemetry costs in real-time

### Historical Analytics
- **Cost Breakdown**: Analyze costs by service type (Compute, Storage, Telemetry)
- **Telemetry Volume**: Monitor logs, metrics, and traces ingestion rates
- **Trend Analysis**: View cost and execution trends over 7, 30, or 90 days
- **Budget Alerts**: Visual indicators when approaching budget limits

### Interactive Features
- **Time Range Selector**: Filter all charts by time period
- **Agent Filtering**: Focus on specific agents across all views
- **Drill-Down Details**: Click on executions for detailed information
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Quick Start

### Prerequisites

- Node.js 20 or later
- npm 10 or later
- Access to AzureHayMaker orchestrator API

### Installation

```bash
# Clone the repository
git clone https://github.com/rysweet/AzureHayMaker.git
cd AzureHayMaker/dashboard

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API endpoints
```

### Configuration

Create a `.env` file in the dashboard directory:

```env
# API Configuration
VITE_API_BASE_URL=https://your-orchestrator.azurecontainerapps.io
VITE_WS_URL=wss://your-orchestrator.azurecontainerapps.io/ws/metrics

# Azure AD B2C (optional - for authentication)
VITE_AAD_CLIENT_ID=your-client-id
VITE_AAD_TENANT_ID=your-tenant-id
```

### Development

```bash
# Start development server
npm run dev

# Open browser to http://localhost:5173
```

The development server includes:
- Hot module replacement (HMR)
- Source maps for debugging
- Mock WebSocket server (if API unavailable)

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Architecture

### Component Structure

```
dashboard/src/
├── App.tsx                 # Application entry point
├── main.tsx               # React mounting point
├── contexts/
│   └── DashboardContext.tsx  # Global state management
├── components/
│   ├── ExecutionTimeline/    # Time-series execution chart
│   ├── CostBreakdown/        # Cost analysis component
│   ├── AgentStatus/          # Agent health indicators
│   ├── TelemetryVolume/      # Telemetry metrics display
│   └── shared/               # Reusable UI components
├── services/
│   ├── api.ts                # REST API client
│   └── websocket.ts          # WebSocket client
└── types/
    └── index.ts              # TypeScript type definitions
```

### Data Flow

#### Static Data (HTTP)
```
Dashboard Component → API Client → FastAPI Endpoint → Response
```

#### Real-Time Data (WebSocket)
```
Orchestrator Event → WebSocket Broadcast → Dashboard Component → Chart Update
```

## Components

### ExecutionTimeline

Displays time-series visualization of agent executions.

**Props:**
```typescript
interface ExecutionTimelineProps {
  data: ExecutionDataPoint[];
  timeRange: TimeRange;
  onExecutionClick?: (executionId: string) => void;
}
```

**Usage:**
```typescript
import { ExecutionTimeline } from './components/ExecutionTimeline';

<ExecutionTimeline
  data={executionData}
  timeRange={{ start: startDate, end: endDate }}
  onExecutionClick={(id) => console.log('Clicked:', id)}
/>
```

### CostBreakdown

Visualizes cost breakdown by service type with trend analysis.

**Props:**
```typescript
interface CostBreakdownProps {
  data: CostData;
  timeRange: TimeRange;
}
```

**Usage:**
```typescript
import { CostBreakdown } from './components/CostBreakdown';

<CostBreakdown
  data={costData}
  timeRange={{ start: startDate, end: endDate }}
/>
```

### AgentStatus

Displays grid/card layout of all agents with status indicators.

**Props:**
```typescript
interface AgentStatusProps {
  agents: AgentInfo[];
  onAgentClick?: (agentId: string) => void;
}
```

**Usage:**
```typescript
import { AgentStatus } from './components/AgentStatus';

<AgentStatus
  agents={agentList}
  onAgentClick={(id) => console.log('Agent:', id)}
/>
```

### TelemetryVolume

Shows telemetry volume by type with ingestion rates and anomaly detection.

**Props:**
```typescript
interface TelemetryVolumeProps {
  data: TelemetryData;
  timeRange: TimeRange;
}
```

**Usage:**
```typescript
import { TelemetryVolume } from './components/TelemetryVolume';

<TelemetryVolume
  data={telemetryData}
  timeRange={{ start: startDate, end: endDate }}
/>
```

## API Integration

### REST API Client

The dashboard uses a type-safe API client for REST endpoints:

```typescript
import { DashboardAPI } from './services/api';

const api = new DashboardAPI(
  'https://your-orchestrator.azurecontainerapps.io',
  'optional-auth-token'
);

// Fetch metrics
const metrics = await api.getMetrics();

// Get analytics for period
const analytics = await api.getAnalytics('30d');

// Get cost breakdown
const costs = await api.getCostBreakdown('7d');
```

### WebSocket Client

Real-time updates are handled via WebSocket:

```typescript
import { MetricsWebSocket } from './services/websocket';

const ws = new MetricsWebSocket('wss://your-orchestrator.azurecontainerapps.io/ws/metrics');

// Connect and listen for updates
await ws.connect();

const unsubscribe = ws.onMetricUpdate((update) => {
  console.log('Metric update:', update);
  // Update your UI state
});

// Disconnect when done
ws.disconnect();
unsubscribe();
```

## Testing

### Unit Tests

```bash
# Run unit tests
npm run test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

### Integration Tests

```bash
# Run integration tests
npm run test:integration
```

### E2E Tests

```bash
# Run E2E tests
npm run test:e2e

# Run E2E in UI mode
npm run test:e2e:ui
```

## Deployment

### Azure Static Web Apps

The dashboard is designed for deployment to Azure Static Web Apps:

```bash
# Install Azure CLI
az login

# Deploy to Azure Static Web Apps
az staticwebapp create \
  --name haymaker-dashboard \
  --resource-group haymaker-rg \
  --source . \
  --location "West US 2" \
  --branch main \
  --app-location "dashboard" \
  --output-location "dist"
```

### Manual Deployment

```bash
# Build for production
npm run build

# Deploy the dist/ directory to your hosting provider
# Examples: Netlify, Vercel, AWS S3 + CloudFront, etc.
```

### CI/CD Pipeline

The project includes GitHub Actions workflow for automatic deployment:
- `.github/workflows/dashboard-deploy.yml`
- Triggers on push to `main` branch
- Runs tests, builds, and deploys to Azure Static Web Apps

## Performance

### Targets

- **Initial Load**: < 3 seconds (including auth redirect)
- **Chart Render**: < 100ms after data received
- **WebSocket Latency**: < 500ms for metric updates
- **Concurrent Users**: Supports 100+ simultaneous WebSocket connections

### Optimization Features

- Code splitting for lazy component loading
- Memoized chart rendering to prevent unnecessary redraws
- Debounced API calls for filter changes
- WebSocket message batching for high-frequency updates
- Service Worker for offline support (optional)

## Security

### Authentication

The dashboard supports Azure AD B2C authentication:

1. Configure Azure AD B2C application
2. Set environment variables (see Configuration section)
3. Authentication is handled automatically via redirect

### Authorization

All API endpoints require authentication tokens:
- Token obtained from Azure AD B2C
- Automatically included in API requests
- WebSocket connections authenticated via query parameter

### CORS Configuration

Ensure your orchestrator API allows the dashboard origin:

```python
# In your FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-dashboard.azurestaticapps.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### WebSocket Connection Fails

1. **Check WebSocket URL**: Ensure `VITE_WS_URL` uses `wss://` (not `ws://`)
2. **Verify CORS**: Orchestrator must allow WebSocket origin
3. **Authentication**: Ensure token is valid and not expired
4. **Network**: Check firewall/proxy settings

### Charts Not Updating

1. **Check API Connection**: Verify API base URL is correct
2. **Inspect Network Tab**: Look for failed API requests
3. **Check Console**: Look for JavaScript errors
4. **Verify Data Format**: Ensure API returns expected data structure

### Authentication Issues

1. **Azure AD B2C Configuration**: Verify client ID and tenant ID
2. **Redirect URI**: Ensure dashboard URL is registered in Azure AD
3. **Token Expiration**: Implement token refresh logic
4. **CORS**: Check CORS configuration in Azure AD B2C

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## License

MIT License - see [LICENSE](../LICENSE) for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/rysweet/AzureHayMaker/issues
- Documentation: https://github.com/rysweet/AzureHayMaker/tree/main/docs

## Changelog

See [CHANGELOG.md](../CHANGELOG.md) for release history and breaking changes.
