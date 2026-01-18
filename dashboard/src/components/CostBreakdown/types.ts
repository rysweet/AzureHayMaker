import type { TimeRange } from '../../types';

export interface CostBreakdownProps {
  data: CostData;
  timeRange: TimeRange;
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
