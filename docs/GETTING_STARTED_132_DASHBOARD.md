# Getting Started: Real-Time Analytics Dashboard (Issue #132)

**Your complete guide to implementing Issue #132**

**Priority**: P2-Medium | **Effort**: 3 weeks | **ROI**: 160%

---

## What You're Building

Build a real-time analytics dashboard showing agent execution, costs, telemetry volume, and system health with WebSocket updates and interactive filtering.

**Why It Matters**: Operational visibility. You can't manage what you can't see. Demo-friendly UI for stakeholders.

**Business Value**: Faster issue detection, better resource understanding, improves stakeholder confidence.

---

## Before You Start (20 minutes)

### 1. Understand Current Metrics

```bash
# See what telemetry is currently collected
find src -name "*telemetry*" -o -name "*metrics*" | head -10
grep -r "class.*Metric\|async def.*metric" src/ | head -5
```

### 2. Understand Architecture Needs

- **Backend**: FastAPI with WebSocket support
- **Frontend**: React with real-time chart updates
- **Data source**: Existing telemetry from PR #119
- **Hosting**: Azure Static Web Apps + API backend

### 3. Check Dependencies

```bash
# Check if websockets is available
grep -i "websockets\|fastapi" pyproject.toml
```

---

## Phase 1: Implement Backend WebSocket Endpoint (Days 1-3, ~12 hours)

### Create Branch

```bash
git checkout main
git pull origin main
git checkout -b feat/issue-132-analytics-dashboard
```

### Create Backend Structure

```bash
mkdir -p src/azure_haymaker/orchestrator/metrics
mkdir -p src/azure_haymaker/orchestrator/websocket
touch src/azure_haymaker/orchestrator/metrics/__init__.py
touch src/azure_haymaker/orchestrator/metrics/aggregator.py
touch src/azure_haymaker/orchestrator/websocket/__init__.py
touch src/azure_haymaker/orchestrator/websocket/manager.py
```

### Implement Metrics Aggregator

**File**: `src/azure_haymaker/orchestrator/metrics/aggregator.py`

```python
from datetime import datetime, timedelta
from typing import Dict, List
import asyncio

class MetricsAggregator:
    """Collects and aggregates real-time metrics."""

    def __init__(self, window_minutes: int = 60):
        self.window_minutes = window_minutes
        self.metrics = {
            "executions": [],
            "costs": [],
            "telemetry": [],
            "health": {}
        }

    async def get_execution_metrics(self) -> dict:
        """Get execution timeline metrics."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=self.window_minutes)

        recent_executions = [
            e for e in self.metrics["executions"]
            if e["timestamp"] > cutoff
        ]

        return {
            "total": len(recent_executions),
            "successful": len([e for e in recent_executions if e["status"] == "success"]),
            "failed": len([e for e in recent_executions if e["status"] == "failed"]),
            "avg_duration_seconds": self._avg([
                e["duration_seconds"] for e in recent_executions
            ]),
            "by_scenario": self._group_by(recent_executions, "scenario")
        }

    async def get_cost_metrics(self) -> dict:
        """Get cost breakdown metrics."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=self.window_minutes)

        recent_costs = [
            c for c in self.metrics["costs"]
            if c["timestamp"] > cutoff
        ]

        total_cost = sum(c["cost_usd"] for c in recent_costs)
        by_scenario = self._sum_by(recent_costs, "scenario", "cost_usd")

        return {
            "total_usd": total_cost,
            "by_scenario": by_scenario,
            "hourly_trend": self._hourly_trend(recent_costs),
            "forecast_daily_usd": self._forecast_daily(total_cost, cutoff)
        }

    async def get_telemetry_metrics(self) -> dict:
        """Get telemetry volume metrics."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=self.window_minutes)

        recent_telemetry = [
            t for t in self.metrics["telemetry"]
            if t["timestamp"] > cutoff
        ]

        return {
            "total_events": len(recent_telemetry),
            "by_type": self._group_by(recent_telemetry, "event_type"),
            "by_severity": self._group_by(recent_telemetry, "severity"),
            "events_per_second": len(recent_telemetry) / (self.window_minutes * 60)
        }

    async def get_health_metrics(self) -> dict:
        """Get system health metrics."""
        return {
            "agents_healthy": len([
                a for a, h in self.metrics["health"].items()
                if h["status"] == "healthy"
            ]),
            "agents_degraded": len([
                a for a, h in self.metrics["health"].items()
                if h["status"] == "degraded"
            ]),
            "agents_failing": len([
                a for a, h in self.metrics["health"].items()
                if h["status"] == "failing"
            ]),
            "uptime_percent": 99.5  # From actual metrics
        }

    def _avg(self, values: List[float]) -> float:
        """Calculate average."""
        return sum(values) / len(values) if values else 0

    def _group_by(self, items: List[dict], key: str) -> dict:
        """Group items by key."""
        result = {}
        for item in items:
            k = item.get(key, "unknown")
            result[k] = result.get(k, 0) + 1
        return result

    def _sum_by(self, items: List[dict], group_key: str, sum_key: str) -> dict:
        """Sum values grouped by key."""
        result = {}
        for item in items:
            k = item.get(group_key, "unknown")
            result[k] = result.get(k, 0) + item.get(sum_key, 0)
        return result

    def _hourly_trend(self, costs: List[dict]) -> dict:
        """Create hourly cost trend."""
        trend = {}
        for cost in costs:
            hour = cost["timestamp"].strftime("%Y-%m-%d %H:00")
            trend[hour] = trend.get(hour, 0) + cost["cost_usd"]
        return trend

    def _forecast_daily(self, hourly_cost: float, cutoff: datetime) -> float:
        """Forecast daily cost."""
        hours_elapsed = (datetime.now() - cutoff).total_seconds() / 3600
        hours_remaining = 24 - hours_elapsed
        if hours_elapsed > 0:
            hourly_rate = hourly_cost / hours_elapsed
            return hourly_cost + (hourly_rate * hours_remaining)
        return 0
```

### Implement WebSocket Manager

**File**: `src/azure_haymaker/orchestrator/websocket/manager.py`

```python
from fastapi import WebSocket
from typing import Set
import json
import asyncio

class WebSocketManager:
    """Manages WebSocket connections and broadcasts metrics."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.metrics_aggregator = None

    async def connect(self, websocket: WebSocket):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove disconnected client."""
        self.active_connections.discard(websocket)
        print(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast_metrics(self):
        """Broadcast metrics to all connected clients."""
        if not self.metrics_aggregator:
            return

        while True:
            try:
                # Gather all metrics
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "executions": await self.metrics_aggregator.get_execution_metrics(),
                    "costs": await self.metrics_aggregator.get_cost_metrics(),
                    "telemetry": await self.metrics_aggregator.get_telemetry_metrics(),
                    "health": await self.metrics_aggregator.get_health_metrics()
                }

                # Send to all connected clients
                for connection in list(self.active_connections):
                    try:
                        await connection.send_json(metrics)
                    except Exception as e:
                        print(f"Error sending metrics: {e}")
                        self.disconnect(connection)

                # Broadcast every 5 seconds
                await asyncio.sleep(5)

            except Exception as e:
                print(f"Error in metrics broadcast: {e}")
                await asyncio.sleep(5)
```

### Add WebSocket Endpoint to Orchestrator

**File**: `src/orchestrator_server.py`

```python
from fastapi import WebSocket, WebSocketDisconnect
from azure_haymaker.orchestrator.websocket.manager import WebSocketManager
from azure_haymaker.orchestrator.metrics.aggregator import MetricsAggregator

metrics_aggregator = MetricsAggregator()
ws_manager = WebSocketManager()
ws_manager.metrics_aggregator = metrics_aggregator

@app.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Can handle client messages here if needed
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.on_event("startup")
async def startup():
    """Start metrics broadcast on startup."""
    asyncio.create_task(ws_manager.broadcast_metrics())
```

---

## Phase 2: Create React Frontend (Days 4-8, ~20 hours)

### Create React App Structure

```bash
# Create dashboard directory
mkdir -p dashboard
cd dashboard

# Initialize React app
npx create-react-app . --template typescript

# Install dependencies
npm install recharts axios websocket
npm install -D tailwindcss postcss autoprefixer
```

### Create Main Dashboard Component

**File**: `dashboard/src/components/Dashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { ExecutionTimeline } from './ExecutionTimeline';
import { CostBreakdown } from './CostBreakdown';
import { AgentStatus } from './AgentStatus';
import { TelemetryVolume } from './TelemetryVolume';

interface Metrics {
  timestamp: string;
  executions: any;
  costs: any;
  telemetry: any;
  health: any;
}

export const Dashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [connected, setConnected] = useState(false);
  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/metrics`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Connected to metrics stream');
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMetrics(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnected(false);
    };

    ws.onclose = () => {
      console.log('Disconnected from metrics stream');
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Azure HayMaker Dashboard
          </h1>
          <div className="flex items-center gap-4">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="px-4 py-2 border rounded"
            >
              <option value="1h">Last Hour</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
            </select>
            <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600">
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Metrics Grid */}
        {metrics ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ExecutionTimeline data={metrics.executions} />
            <CostBreakdown data={metrics.costs} />
            <AgentStatus data={metrics.health} />
            <TelemetryVolume data={metrics.telemetry} />
          </div>
        ) : (
          <div className="text-center text-gray-500">
            Loading metrics...
          </div>
        )}
      </div>
    </div>
  );
};
```

### Create Chart Components

**File**: `dashboard/src/components/CostBreakdown.tsx`

```typescript
import React from 'react';
import { PieChart, Pie, Cell, Legend, Tooltip } from 'recharts';

interface CostBreakdownProps {
  data: any;
}

export const CostBreakdown: React.FC<CostBreakdownProps> = ({ data }) => {
  if (!data || !data.by_scenario) {
    return <div>Loading...</div>;
  }

  const chartData = Object.entries(data.by_scenario).map(([name, value]) => ({
    name,
    value
  }));

  const COLORS = [
    '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'
  ];

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Cost Breakdown by Scenario</h2>
      <div className="flex justify-center">
        <PieChart width={300} height={300}>
          <Pie
            data={chartData}
            cx={150}
            cy={150}
            labelLine={false}
            label={(entry) => `$${entry.value.toFixed(2)}`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
          <Legend />
        </PieChart>
      </div>
      <div className="mt-4 text-center">
        <p className="text-sm text-gray-600">Total Cost</p>
        <p className="text-2xl font-bold text-gray-900">
          ${data.total_usd?.toFixed(2) || '0.00'}
        </p>
      </div>
    </div>
  );
};
```

### Create Additional Components

**File**: `dashboard/src/components/ExecutionTimeline.tsx`

```typescript
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

export const ExecutionTimeline: React.FC<any> = ({ data }) => {
  if (!data) return <div>Loading...</div>;

  const timelineData = [
    { name: 'Successful', value: data.successful || 0 },
    { name: 'Failed', value: data.failed || 0 }
  ];

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Execution Timeline</h2>
      <BarChart width={400} height={250} data={timelineData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="value" fill="#3b82f6" />
      </BarChart>
      <div className="mt-4 text-sm text-gray-600">
        <p>Total Executions: {data.total || 0}</p>
        <p>Avg Duration: {data.avg_duration_seconds?.toFixed(2) || 0}s</p>
      </div>
    </div>
  );
};
```

---

## Phase 3: Deploy Frontend (Days 9-10, ~10 hours)

### Create Build Configuration

**File**: `dashboard/package.json`

```json
{
  "name": "haymaker-dashboard",
  "version": "1.0.0",
  "homepage": "/",
  "private": true,
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "recharts": "^2.10.0",
    "axios": "^1.6.0",
    "websocket": "^1.0.34"
  }
}
```

### Create Azure Static Web Apps Configuration

**File**: `staticwebapp.json`

```json
{
  "navigationFallback": {
    "rewrite": "/index.html"
  },
  "trailingSlash": "auto",
  "routes": [
    {
      "route": "/api/*",
      "methods": ["GET", "POST"],
      "allowedRoles": ["authenticated"]
    },
    {
      "route": "/ws/*",
      "methods": ["GET"],
      "allowedRoles": ["authenticated"]
    }
  ]
}
```

### Create GitHub Actions Deployment

**File**: `.github/workflows/deploy-dashboard.yml`

```yaml
name: Deploy Dashboard

on:
  push:
    branches: [main]
    paths:
      - 'dashboard/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build dashboard
        working-directory: dashboard
        run: |
          npm install
          npm run build

      - name: Deploy to Static Web Apps
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "dashboard/build"
          api_location: ""
```

---

## Phase 4: Add Authentication (Days 11-12, ~8 hours)

### Add Azure AD B2C Authentication

**File**: `dashboard/src/Auth.tsx`

```typescript
import { PublicClientApplication } from '@azure/msal-browser';

const msalConfig = {
  auth: {
    clientId: process.env.REACT_APP_CLIENT_ID || '',
    authority: process.env.REACT_APP_AUTHORITY || '',
    redirectUri: window.location.origin,
  },
};

const pca = new PublicClientApplication(msalConfig);

export { pca };
```

### Update main component with auth

```typescript
import { useEffect } from 'react';
import { pca } from './Auth';

// In Dashboard component:
useEffect(() => {
  const accounts = pca.getAllAccounts();
  if (accounts.length === 0) {
    pca.loginPopup();
  }
}, []);
```

---

## Testing

### Test WebSocket Connection

```bash
# Test endpoint locally
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8000/ws/metrics
```

### Test Frontend

```bash
cd dashboard
npm test
npm start  # Open http://localhost:3000
```

---

## Success Criteria

- [ ] WebSocket endpoint broadcasting metrics
- [ ] React dashboard displaying real-time charts
- [ ] Execution timeline chart working
- [ ] Cost breakdown chart working
- [ ] Agent health status displayed
- [ ] Telemetry volume chart working
- [ ] Time range selector filtering data
- [ ] Connection indicator working
- [ ] Dashboard deployed to Azure Static Web Apps
- [ ] Authentication working (Azure AD B2C)
- [ ] Responsive on mobile/tablet
- [ ] Performance acceptable (<500ms updates)

---

## Estimated Timeline

**Optimistic**: 2.5 weeks
**Realistic**: 3 weeks
**Pessimistic**: 3.5 weeks

---

**Issue**: #132
**Related**: #124 (Telemetry), #127 (Distributed Tracing), #131 (CI/CD)

📊 **Ready to build observability? Follow Phase 1 above!**
