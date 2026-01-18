/**
 * Analytics Dashboard Application
 *
 * Main application component that coordinates all dashboard functionality.
 */

import React, { useState, useEffect } from 'react';
import { DashboardProvider, useDashboard } from './contexts/DashboardContext';
import { DashboardAPI } from './services/api';
import { MetricsWebSocket } from './services/websocket';
import { ExecutionTimeline } from './components/ExecutionTimeline';
import { CostBreakdown } from './components/CostBreakdown';
import { AgentStatus } from './components/AgentStatus';
import { TelemetryVolume } from './components/TelemetryVolume';
import { TimeRangeSelector } from './components/shared/TimeRangeSelector';
import { AgentFilter } from './components/shared/AgentFilter';
import type {
  ExecutionDataPoint,
  CostData,
  AgentInfo,
  TelemetryData,
  TimeRange,
} from './types';

const DashboardContent: React.FC = () => {
  const { timeRange, selectedAgents, setTimeRange, setSelectedAgents, setIsConnected } = useDashboard();

  const [executionData, setExecutionData] = useState<ExecutionDataPoint[]>([]);
  const [costData, setCostData] = useState<CostData | null>(null);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [telemetryData, setTelemetryData] = useState<TelemetryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize API client
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const apiToken = import.meta.env.VITE_API_TOKEN;
  const api = new DashboardAPI(apiBaseUrl, apiToken);

  // Initialize WebSocket
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/metrics';
  const ws = new MetricsWebSocket(wsUrl);

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [metrics, cost, agentStatus, telemetry] = await Promise.all([
          api.getAnalytics(timeRange),
          api.getCostBreakdown(timeRange),
          api.getAgentStatus(),
          api.getTelemetryVolume(timeRange),
        ]);

        // Transform metrics to execution data points
        const execData: ExecutionDataPoint[] = metrics.execution_timeline || [];
        setExecutionData(execData);
        setCostData(cost);
        setAgents(agentStatus);
        setTelemetryData(telemetry);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [timeRange]);

  // Connect WebSocket for real-time updates
  useEffect(() => {
    ws.connect()
      .then(() => {
        setIsConnected(true);
        // Subscribe to updates
        ws.onMetricUpdate((update) => {
          // Handle real-time updates
          if (update.type === 'execution') {
            setExecutionData((prev) => [...prev, update.data]);
          } else if (update.type === 'cost') {
            setCostData((prev) => ({ ...prev!, ...update.data }));
          } else if (update.type === 'agent') {
            setAgents((prev) => {
              const index = prev.findIndex((a) => a.agent_id === update.data.agent_id);
              if (index >= 0) {
                const newAgents = [...prev];
                newAgents[index] = update.data;
                return newAgents;
              }
              return [...prev, update.data];
            });
          } else if (update.type === 'telemetry') {
            setTelemetryData((prev) => ({ ...prev!, ...update.data }));
          }
        });
      })
      .catch((err) => {
        console.error('WebSocket connection failed:', err);
        setIsConnected(false);
      });

    return () => {
      ws.disconnect();
      setIsConnected(false);
    };
  }, []);

  // Get available agent IDs
  const availableAgents = agents.map((a) => a.agent_id);

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading dashboard...</div>;
  }

  if (error) {
    return (
      <div role="alert" style={{ padding: '2rem', textAlign: 'center', color: '#f44336' }}>
        Error: {error}
      </div>
    );
  }

  const timeRangeObj: TimeRange = {
    start: new Date(Date.now() - getTimeRangeDuration(timeRange) * 1000).toISOString(),
    end: new Date().toISOString(),
    duration: getTimeRangeDuration(timeRange),
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1>Analytics Dashboard</h1>
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', marginTop: '1rem' }}>
          <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
          {availableAgents.length > 0 && (
            <AgentFilter
              availableAgents={availableAgents}
              selectedAgents={selectedAgents}
              onChange={setSelectedAgents}
            />
          )}
        </div>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        <div>
          <ExecutionTimeline
            data={executionData}
            timeRange={timeRangeObj}
            onExecutionClick={(id) => console.log('Execution clicked:', id)}
          />
        </div>
        {costData && (
          <div>
            <CostBreakdown data={costData} timeRange={timeRangeObj} />
          </div>
        )}
        <div>
          <AgentStatus
            agents={agents}
            onAgentClick={(id) => console.log('Agent clicked:', id)}
          />
        </div>
        {telemetryData && (
          <div>
            <TelemetryVolume data={telemetryData} timeRange={timeRangeObj} />
          </div>
        )}
      </div>
    </div>
  );
};

const getTimeRangeDuration = (range: '7d' | '30d' | '90d'): number => {
  const days = { '7d': 7, '30d': 30, '90d': 90 };
  return days[range] * 24 * 60 * 60;
};

export const App: React.FC = () => {
  return (
    <DashboardProvider>
      <DashboardContent />
    </DashboardProvider>
  );
};
