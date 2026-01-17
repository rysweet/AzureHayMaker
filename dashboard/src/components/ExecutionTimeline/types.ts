import type { ExecutionDataPoint, TimeRange } from '../../types';

export interface ExecutionTimelineProps {
  data: ExecutionDataPoint[];
  timeRange: TimeRange;
  onExecutionClick?: (executionId: string) => void;
}
