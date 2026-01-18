/**
 * Telemetry Volume Component
 *
 * Displays telemetry volume by type (logs, metrics, traces).
 * Shows ingestion rates and anomaly alerts.
 */

import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { TelemetryVolumeProps } from './types';

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
};

export const TelemetryVolume: React.FC<TelemetryVolumeProps> = ({ data, timeRange }) => {
  const chartData = useMemo(() => [
    {
      type: 'Logs',
      volume: data.logs.volume_bytes,
      rate: data.logs.rate_per_second,
    },
    {
      type: 'Metrics',
      volume: data.metrics.volume_bytes,
      rate: data.metrics.rate_per_second,
    },
    {
      type: 'Traces',
      volume: data.traces.volume_bytes,
      rate: data.traces.rate_per_second,
    },
  ], [data]);

  if (!data) {
    return (
      <div role="status" aria-label="No telemetry data available" style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
        No telemetry data available
      </div>
    );
  }

  return (
    <div role="region" aria-label="Telemetry Volume" style={{ padding: '1rem' }}>
      <h3>Telemetry Volume</h3>

      {/* Anomaly Alert */}
      {data.anomaly_detected && (
        <div role="alert" style={{ padding: '0.5rem', backgroundColor: '#ffebee', color: '#c62828', marginBottom: '1rem', borderRadius: '4px' }}>
          ⚠️ Anomaly detected in telemetry volume
        </div>
      )}

      {/* Summary Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
        <div>
          <strong>Logs:</strong>
          <div>{formatBytes(data.logs.volume_bytes)}</div>
          <div style={{ fontSize: '0.85rem', color: '#666' }}>
            {data.logs.rate_per_second.toFixed(2)} events/sec
          </div>
        </div>
        <div>
          <strong>Metrics:</strong>
          <div>{formatBytes(data.metrics.volume_bytes)}</div>
          <div style={{ fontSize: '0.85rem', color: '#666' }}>
            {data.metrics.rate_per_second.toFixed(2)} events/sec
          </div>
        </div>
        <div>
          <strong>Traces:</strong>
          <div>{formatBytes(data.traces.volume_bytes)}</div>
          <div style={{ fontSize: '0.85rem', color: '#666' }}>
            {data.traces.rate_per_second.toFixed(2)} events/sec
          </div>
        </div>
      </div>

      {/* Bar Chart - Volume */}
      <div style={{ height: '300px' }}>
        <h4>Volume by Type</h4>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="type" />
            <YAxis tickFormatter={(value) => formatBytes(value)} />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'volume') return [formatBytes(value), 'Volume'];
                return [`${value.toFixed(2)} /sec`, 'Rate'];
              }}
            />
            <Legend />
            <Bar dataKey="volume" fill="#8884d8" name="Volume" />
            <Bar dataKey="rate" fill="#82ca9d" name="Rate (events/sec)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
