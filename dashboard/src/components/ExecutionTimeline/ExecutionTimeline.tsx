/**
 * Execution Timeline Component
 *
 * Displays time-series visualization of agent executions using Recharts.
 * Shows concurrent executions, completed count, and failed count over time.
 */

import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { ExecutionDataPoint, ExecutionTimelineProps, TimeRange } from './types';

export const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({
  data,
  timeRange,
  onExecutionClick,
}) => {
  // Filter data based on time range
  const filteredData = useMemo(() => {
    if (!timeRange) return data;

    const now = new Date();
    const startDate = new Date(now.getTime() - timeRange.duration * 1000);

    return data.filter((point) => {
      const pointDate = new Date(point.timestamp);
      return pointDate >= startDate && pointDate <= now;
    });
  }, [data, timeRange]);

  // Validate and sanitize data
  const sanitizedData = useMemo(() => {
    return filteredData.map((point) => ({
      ...point,
      concurrent_executions: Math.max(0, point.concurrent_executions || 0),
      completed_count: Math.max(0, point.completed_count || 0),
      failed_count: Math.max(0, point.failed_count || 0),
    }));
  }, [filteredData]);

  if (!data || data.length === 0) {
    return (
      <div
        role="status"
        aria-label="No execution data available"
        style={{
          padding: '2rem',
          textAlign: 'center',
          color: '#666',
        }}
      >
        No execution data available
      </div>
    );
  }

  const handleClick = (data: any) => {
    if (onExecutionClick && data && data.activePayload && data.activePayload[0]) {
      const point = data.activePayload[0].payload;
      if (point.execution_id) {
        onExecutionClick(point.execution_id);
      }
    }
  };

  return (
    <div
      role="region"
      aria-label="Execution Timeline"
      style={{ width: '100%', height: '400px' }}
    >
      <h3 style={{ marginBottom: '1rem' }}>Execution Timeline</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={sanitizedData}
          onClick={handleClick}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(value) => {
              const date = new Date(value);
              return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }}
            aria-label="Time"
          />
          <YAxis aria-label="Count" />
          <Tooltip
            labelFormatter={(value) => {
              const date = new Date(value as string);
              return date.toLocaleString();
            }}
            formatter={(value: number) => [value, '']}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="concurrent_executions"
            stroke="#8884d8"
            name="Concurrent Executions"
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
            aria-label="Concurrent executions line"
          />
          <Line
            type="monotone"
            dataKey="completed_count"
            stroke="#82ca9d"
            name="Completed"
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
            aria-label="Completed executions line"
          />
          <Line
            type="monotone"
            dataKey="failed_count"
            stroke="#ff7c7c"
            name="Failed"
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
            aria-label="Failed executions line"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
