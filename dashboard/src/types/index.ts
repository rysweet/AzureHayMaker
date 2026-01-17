// Common types used across the dashboard

export interface TimeRange {
  start: Date;
  end: Date;
}

export interface ExecutionDataPoint {
  timestamp: string; // ISO8601
  concurrent_executions: number;
  completed_count: number;
  failed_count: number;
}

export interface CostData {
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

export interface AgentInfo {
  agent_id: string;
  agent_name: string;
  status: 'running' | 'idle' | 'failed' | 'queued';
  last_execution_at?: string;
  last_duration_seconds?: number;
  error_message?: string;
}

export interface TelemetryData {
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

export interface MetricUpdate {
  type: 'execution' | 'cost' | 'telemetry' | 'agent';
  timestamp: string;
  data: any;
}

export interface MetricsResponse {
  timestamp: string;
  concurrent_executions: number;
  total_executions_today: number;
  active_agents: number;
  total_cost_today: number;
  telemetry_volume_mb: number;
}

export interface AnalyticsResponse {
  period: string;
  start_date: string;
  end_date: string;
  total_executions: number;
  success_rate: number;
  average_duration_seconds: number;
  peak_concurrent_executions: number;
  total_cost: number;
  cost_per_execution: number;
}
