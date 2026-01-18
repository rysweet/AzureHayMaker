import type { TimeRange } from '../../types';

export interface TelemetryVolumeProps {
  data: TelemetryData;
  timeRange: TimeRange;
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
