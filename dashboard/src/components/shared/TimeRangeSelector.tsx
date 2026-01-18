/**
 * Time Range Selector Component
 *
 * Allows users to select time range (7d, 30d, 90d) for dashboard data.
 */

import React from 'react';
import type { TimeRange } from '../../types';

export interface TimeRangeSelectorProps {
  selected: '7d' | '30d' | '90d';
  onChange: (range: '7d' | '30d' | '90d') => void;
}

const TIME_RANGES: Array<{ value: '7d' | '30d' | '90d'; label: string; duration: number }> = [
  { value: '7d', label: '7 Days', duration: 7 * 24 * 60 * 60 },
  { value: '30d', label: '30 Days', duration: 30 * 24 * 60 * 60 },
  { value: '90d', label: '90 Days', duration: 90 * 24 * 60 * 60 },
];

export const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({ selected, onChange }) => {
  return (
    <div role="group" aria-label="Time Range Selector" style={{ display: 'flex', gap: '0.5rem' }}>
      {TIME_RANGES.map((range) => (
        <button
          key={range.value}
          onClick={() => onChange(range.value)}
          aria-pressed={selected === range.value}
          aria-label={`Select ${range.label}`}
          style={{
            padding: '0.5rem 1rem',
            border: '1px solid #ccc',
            borderRadius: '4px',
            backgroundColor: selected === range.value ? '#1976d2' : '#fff',
            color: selected === range.value ? '#fff' : '#000',
            cursor: 'pointer',
            fontWeight: selected === range.value ? 'bold' : 'normal',
          }}
        >
          {range.label}
        </button>
      ))}
    </div>
  );
};
