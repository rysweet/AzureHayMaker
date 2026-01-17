/**
 * TDD Tests for Dashboard API Client
 *
 * Following the 60/30/10 testing pyramid:
 * - 60% Unit tests (this file)
 * - 30% Integration tests
 * - 10% E2E tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { DashboardAPI } from './api';

describe('DashboardAPI', () => {
  let api: DashboardAPI;
  const baseUrl = 'https://test-orchestrator.example.com';
  const authToken = 'test-token-123';

  beforeEach(() => {
    // Reset fetch mock before each test
    global.fetch = vi.fn();
    api = new DashboardAPI(baseUrl, authToken);
  });

  describe('Constructor', () => {
    it('should create instance with baseUrl and authToken', () => {
      expect(api).toBeInstanceOf(DashboardAPI);
    });

    it('should work without authToken', () => {
      const apiWithoutAuth = new DashboardAPI(baseUrl);
      expect(apiWithoutAuth).toBeInstanceOf(DashboardAPI);
    });
  });

  describe('getMetrics', () => {
    it('should fetch metrics from /metrics endpoint', async () => {
      const mockResponse = {
        timestamp: '2026-01-17T21:45:00Z',
        concurrent_executions: 5,
        total_executions_today: 127,
        active_agents: 12,
        total_cost_today: 45.67,
        telemetry_volume_mb: 1234.56,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.getMetrics();

      expect(global.fetch).toHaveBeenCalledWith(
        `${baseUrl}/metrics`,
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authToken}`,
          }),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('should throw error on failed request', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        statusText: 'Internal Server Error',
      });

      await expect(api.getMetrics()).rejects.toThrow('API Error: Internal Server Error');
    });

    it('should handle network errors', async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      await expect(api.getMetrics()).rejects.toThrow('Network error');
    });
  });

  describe('getAnalytics', () => {
    it('should fetch analytics for 7d period', async () => {
      const mockResponse = {
        period: '7d',
        start_date: '2026-01-10T00:00:00Z',
        end_date: '2026-01-17T23:59:59Z',
        total_executions: 890,
        success_rate: 0.987,
        average_duration_seconds: 12.3,
        peak_concurrent_executions: 15,
        total_cost: 345.67,
        cost_per_execution: 0.39,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.getAnalytics('7d');

      expect(global.fetch).toHaveBeenCalledWith(
        `${baseUrl}/analytics?period=7d`,
        expect.any(Object)
      );

      expect(result).toEqual(mockResponse);
    });

    it('should fetch analytics for 30d period', async () => {
      const mockResponse = {
        period: '30d',
        total_executions: 3845,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await api.getAnalytics('30d');

      expect(global.fetch).toHaveBeenCalledWith(
        `${baseUrl}/analytics?period=30d`,
        expect.any(Object)
      );
    });

    it('should fetch analytics for 90d period', async () => {
      const mockResponse = {
        period: '90d',
        total_executions: 11535,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await api.getAnalytics('90d');

      expect(global.fetch).toHaveBeenCalledWith(
        `${baseUrl}/analytics?period=90d`,
        expect.any(Object)
      );
    });
  });

  describe('getCostBreakdown', () => {
    it('should fetch cost breakdown with default 30d period', async () => {
      const mockResponse = {
        period: '30d',
        total_cost: 1234.56,
        budget: 2000.0,
        budget_percentage: 61.7,
        breakdown: {
          compute: 845.32,
          storage: 123.45,
          telemetry: 234.56,
          other: 31.23,
        },
        trend: [],
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.getCostBreakdown();

      expect(global.fetch).toHaveBeenCalledWith(
        `${baseUrl}/cost/breakdown?period=30d`,
        expect.any(Object)
      );

      expect(result).toEqual(mockResponse);
    });

    it('should fetch cost breakdown for specified period', async () => {
      const mockResponse = {
        period: '7d',
        total_cost: 345.67,
        breakdown: {},
        trend: [],
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await api.getCostBreakdown('7d');

      expect(global.fetch).toHaveBeenCalledWith(
        `${baseUrl}/cost/breakdown?period=7d`,
        expect.any(Object)
      );
    });
  });

  describe('getAgentStatus', () => {
    it('should fetch status of all agents', async () => {
      const mockResponse = [
        {
          agent_id: 'agent-001',
          agent_name: 'knowledge-worker-1',
          status: 'running' as const,
          last_execution_at: '2026-01-17T21:40:15Z',
          last_duration_seconds: 45.2,
          error_message: null,
        },
        {
          agent_id: 'agent-002',
          agent_name: 'knowledge-worker-2',
          status: 'idle' as const,
          last_execution_at: '2026-01-17T21:30:00Z',
          last_duration_seconds: 120.5,
          error_message: null,
        },
      ];

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.getAgentStatus();

      expect(global.fetch).toHaveBeenCalledWith(
        `${baseUrl}/agents/status`,
        expect.any(Object)
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle empty agent list', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      const result = await api.getAgentStatus();
      expect(result).toEqual([]);
    });
  });

  describe('getTelemetryVolume', () => {
    it('should fetch telemetry volume with default period', async () => {
      const mockResponse = {
        period: '30d',
        logs: { volume_bytes: 12345678900, rate_per_second: 142.5 },
        metrics: { volume_bytes: 2345678900, rate_per_second: 28.3 },
        traces: { volume_bytes: 5678900123, rate_per_second: 67.2 },
        anomaly_detected: false,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.getTelemetryVolume();

      expect(global.fetch).toHaveBeenCalledWith(
        `${baseUrl}/telemetry/volume?period=30d`,
        expect.any(Object)
      );

      expect(result).toEqual(mockResponse);
    });

    it('should fetch telemetry volume for specified period', async () => {
      const mockResponse = {
        period: '7d',
        logs: { volume_bytes: 100, rate_per_second: 1 },
        metrics: { volume_bytes: 200, rate_per_second: 2 },
        traces: { volume_bytes: 300, rate_per_second: 3 },
        anomaly_detected: false,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await api.getTelemetryVolume('7d');

      expect(global.fetch).toHaveBeenCalledWith(
        `${baseUrl}/telemetry/volume?period=7d`,
        expect.any(Object)
      );
    });
  });

  describe('Authentication', () => {
    it('should include Authorization header when token provided', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await api.getMetrics();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: `Bearer ${authToken}`,
          }),
        })
      );
    });

    it('should not include Authorization header when token not provided', async () => {
      const apiWithoutAuth = new DashboardAPI(baseUrl);

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await apiWithoutAuth.getMetrics();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            Authorization: expect.anything(),
          }),
        })
      );
    });
  });

  describe('Error Handling', () => {
    it('should throw with status text on HTTP error', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        statusText: 'Unauthorized',
      });

      await expect(api.getMetrics()).rejects.toThrow('API Error: Unauthorized');
    });

    it('should propagate network errors', async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error('Connection refused'));

      await expect(api.getMetrics()).rejects.toThrow('Connection refused');
    });

    it('should handle JSON parse errors', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      await expect(api.getMetrics()).rejects.toThrow('Invalid JSON');
    });
  });
});
