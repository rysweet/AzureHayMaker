/**
 * Cost Breakdown Component
 *
 * Displays cost breakdown by service type with trend visualization.
 * Shows budget vs actual with alert indicators.
 */

import React, { useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { CostBreakdownProps } from './types';

const COLORS = {
  compute: '#0088FE',
  storage: '#00C49F',
  telemetry: '#FFBB28',
  other: '#FF8042',
};

export const CostBreakdown: React.FC<CostBreakdownProps> = ({ data, timeRange }) => {
  const pieData = useMemo(() => [
    { name: 'Compute', value: data.breakdown.compute },
    { name: 'Storage', value: data.breakdown.storage },
    { name: 'Telemetry', value: data.breakdown.telemetry },
    { name: 'Other', value: data.breakdown.other },
  ], [data.breakdown]);

  const budgetPercentage = useMemo(() => {
    return (data.total_cost / data.budget) * 100;
  }, [data.total_cost, data.budget]);

  const isOverBudget = budgetPercentage > 100;
  const isNearBudget = budgetPercentage > 80 && budgetPercentage <= 100;

  if (!data) {
    return (
      <div role="status" aria-label="No cost data available" style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
        No cost data available
      </div>
    );
  }

  return (
    <div role="region" aria-label="Cost Breakdown" style={{ padding: '1rem' }}>
      <h3>Cost Breakdown</h3>

      {/* Budget Alert */}
      {isOverBudget && (
        <div role="alert" style={{ padding: '0.5rem', backgroundColor: '#ffebee', color: '#c62828', marginBottom: '1rem', borderRadius: '4px' }}>
          ⚠️ Over budget by ${(data.total_cost - data.budget).toFixed(2)}
        </div>
      )}
      {isNearBudget && (
        <div role="status" style={{ padding: '0.5rem', backgroundColor: '#fff3e0', color: '#e65100', marginBottom: '1rem', borderRadius: '4px' }}>
          ⚠️ Approaching budget limit ({budgetPercentage.toFixed(1)}%)
        </div>
      )}

      {/* Total Cost and Budget */}
      <div style={{ marginBottom: '1rem' }}>
        <div><strong>Total Cost:</strong> ${data.total_cost.toFixed(2)}</div>
        <div><strong>Budget:</strong> ${data.budget.toFixed(2)}</div>
        <div><strong>Usage:</strong> {budgetPercentage.toFixed(1)}%</div>
      </div>

      {/* Pie Chart - Cost Breakdown */}
      <div style={{ height: '300px', marginBottom: '2rem' }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({name, value}) => `${name}: $${value.toFixed(2)}`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {pieData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[entry.name.toLowerCase() as keyof typeof COLORS]} />
              ))}
            </Pie>
            <Tooltip formatter={(value: number) => `$${value.toFixed(2)}`} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Line Chart - Cost Trend */}
      {data.trend && data.trend.length > 0 && (
        <div style={{ height: '300px' }}>
          <h4>Cost Trend</h4>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.trend} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(value) => new Date(value).toLocaleDateString()}
              />
              <YAxis tickFormatter={(value) => `$${value}`} />
              <Tooltip
                labelFormatter={(value) => new Date(value as string).toLocaleString()}
                formatter={(value: number) => [`$${value.toFixed(2)}`, 'Cost']}
              />
              <Legend />
              <Line type="monotone" dataKey="cost" stroke="#8884d8" activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};
