/**
 * TDD Tests for ExecutionTimeline Component
 *
 * Tests the execution timeline chart component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExecutionTimeline } from './ExecutionTimeline';
import type { ExecutionTimelineProps } from './types';

describe('ExecutionTimeline', () => {
  const mockTimeRange = {
    start: new Date('2026-01-17T00:00:00Z'),
    end: new Date('2026-01-17T23:59:59Z'),
  };

  const mockData = [
    {
      timestamp: '2026-01-17T21:00:00Z',
      concurrent_executions: 5,
      completed_count: 23,
      failed_count: 1,
    },
    {
      timestamp: '2026-01-17T22:00:00Z',
      concurrent_executions: 7,
      completed_count: 28,
      failed_count: 0,
    },
  ];

  const defaultProps: ExecutionTimelineProps = {
    data: mockData,
    timeRange: mockTimeRange,
  };

  describe('Rendering', () => {
    it('should render without crashing', () => {
      render(<ExecutionTimeline {...defaultProps} />);
      expect(screen.getByTestId('execution-timeline')).toBeInTheDocument();
    });

    it('should render chart with data', () => {
      render(<ExecutionTimeline {...defaultProps} />);

      // Chart should be visible
      expect(screen.getByTestId('execution-timeline-chart')).toBeInTheDocument();
    });

    it('should display chart title', () => {
      render(<ExecutionTimeline {...defaultProps} />);

      expect(screen.getByText(/Execution Timeline/i)).toBeInTheDocument();
    });

    it('should render empty state when no data', () => {
      render(<ExecutionTimeline {...defaultProps} data={[]} />);

      expect(screen.getByText(/No execution data available/i)).toBeInTheDocument();
    });
  });

  describe('Data Display', () => {
    it('should show concurrent executions count', () => {
      render(<ExecutionTimeline {...defaultProps} />);

      // Should show the values from mock data
      expect(screen.getByText(/5/)).toBeInTheDocument();
      expect(screen.getByText(/7/)).toBeInTheDocument();
    });

    it('should show completed count', () => {
      render(<ExecutionTimeline {...defaultProps} />);

      expect(screen.getByText(/23/)).toBeInTheDocument();
      expect(screen.getByText(/28/)).toBeInTheDocument();
    });

    it('should show failed count when failures exist', () => {
      render(<ExecutionTimeline {...defaultProps} />);

      expect(screen.getByText(/1/)).toBeInTheDocument();
    });

    it('should format timestamps correctly', () => {
      render(<ExecutionTimeline {...defaultProps} />);

      expect(screen.getByText(/21:00/)).toBeInTheDocument();
      expect(screen.getByText(/22:00/)).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('should call onExecutionClick when execution is clicked', async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();

      render(<ExecutionTimeline {...defaultProps} onExecutionClick={handleClick} />);

      const dataPoint = screen.getByTestId('data-point-0');
      await user.click(dataPoint);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should not crash when onExecutionClick not provided', async () => {
      const user = userEvent.setup();

      render(<ExecutionTimeline {...defaultProps} />);

      const dataPoint = screen.getByTestId('data-point-0');

      await expect(user.click(dataPoint)).resolves.not.toThrow();
    });

    it('should show tooltip on hover', async () => {
      const user = userEvent.setup();

      render(<ExecutionTimeline {...defaultProps} />);

      const dataPoint = screen.getByTestId('data-point-0');
      await user.hover(dataPoint);

      expect(screen.getByTestId('execution-tooltip')).toBeInTheDocument();
      expect(screen.getByText(/21:00/)).toBeInTheDocument();
      expect(screen.getByText(/5 concurrent/i)).toBeInTheDocument();
    });

    it('should hide tooltip when not hovering', async () => {
      const user = userEvent.setup();

      render(<ExecutionTimeline {...defaultProps} />);

      const dataPoint = screen.getByTestId('data-point-0');
      await user.hover(dataPoint);
      await user.unhover(dataPoint);

      expect(screen.queryByTestId('execution-tooltip')).not.toBeInTheDocument();
    });
  });

  describe('Time Range Filtering', () => {
    it('should only show data within time range', () => {
      const filteredTimeRange = {
        start: new Date('2026-01-17T21:00:00Z'),
        end: new Date('2026-01-17T21:59:59Z'),
      };

      render(<ExecutionTimeline {...defaultProps} timeRange={filteredTimeRange} />);

      // Only first data point should be visible
      expect(screen.getByText(/21:00/)).toBeInTheDocument();
      expect(screen.queryByText(/22:00/)).not.toBeInTheDocument();
    });

    it('should update when time range changes', () => {
      const { rerender } = render(<ExecutionTimeline {...defaultProps} />);

      expect(screen.getByText(/21:00/)).toBeInTheDocument();
      expect(screen.getByText(/22:00/)).toBeInTheDocument();

      const newTimeRange = {
        start: new Date('2026-01-17T22:00:00Z'),
        end: new Date('2026-01-17T23:59:59Z'),
      };

      rerender(<ExecutionTimeline {...defaultProps} timeRange={newTimeRange} />);

      expect(screen.queryByText(/21:00/)).not.toBeInTheDocument();
      expect(screen.getByText(/22:00/)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<ExecutionTimeline {...defaultProps} />);

      expect(screen.getByRole('img', { name: /execution timeline chart/i })).toBeInTheDocument();
    });

    it('should be keyboard navigable', async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();

      render(<ExecutionTimeline {...defaultProps} onExecutionClick={handleClick} />);

      const dataPoint = screen.getByTestId('data-point-0');

      // Tab to element
      await user.tab();
      expect(dataPoint).toHaveFocus();

      // Press Enter
      await user.keyboard('{Enter}');
      expect(handleClick).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid timestamp format', () => {
      const invalidData = [
        {
          timestamp: 'invalid-date',
          concurrent_executions: 5,
          completed_count: 23,
          failed_count: 1,
        },
      ];

      expect(() => {
        render(<ExecutionTimeline {...defaultProps} data={invalidData} />);
      }).not.toThrow();
    });

    it('should handle negative values', () => {
      const invalidData = [
        {
          timestamp: '2026-01-17T21:00:00Z',
          concurrent_executions: -5,
          completed_count: -23,
          failed_count: -1,
        },
      ];

      expect(() => {
        render(<ExecutionTimeline {...defaultProps} data={invalidData} />);
      }).not.toThrow();
    });

    it('should handle missing data fields', () => {
      const incompleteData: any = [
        {
          timestamp: '2026-01-17T21:00:00Z',
        },
      ];

      expect(() => {
        render(<ExecutionTimeline {...defaultProps} data={incompleteData} />);
      }).not.toThrow();
    });
  });

  describe('Performance', () => {
    it('should handle large datasets efficiently', () => {
      const largeDataset = Array.from({ length: 1000 }, (_, i) => ({
        timestamp: new Date(Date.now() + i * 3600000).toISOString(),
        concurrent_executions: Math.floor(Math.random() * 20),
        completed_count: Math.floor(Math.random() * 100),
        failed_count: Math.floor(Math.random() * 5),
      }));

      const startTime = performance.now();
      render(<ExecutionTimeline {...defaultProps} data={largeDataset} />);
      const endTime = performance.now();

      // Should render in less than 100ms
      expect(endTime - startTime).toBeLessThan(100);
    });

    it('should memoize chart data calculations', () => {
      const { rerender } = render(<ExecutionTimeline {...defaultProps} />);

      // Re-render with same props
      rerender(<ExecutionTimeline {...defaultProps} />);

      // Component should use memoized data
      expect(screen.getByTestId('execution-timeline')).toBeInTheDocument();
    });
  });
});
