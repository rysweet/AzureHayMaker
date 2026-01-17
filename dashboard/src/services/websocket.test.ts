/**
 * TDD Tests for WebSocket Service
 *
 * Tests the MetricsWebSocket class for real-time metric updates.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MetricsWebSocket } from './websocket';

// Mock WebSocket
class MockWebSocket {
  public readyState: number = 0;
  public onopen: ((event: any) => void) | null = null;
  public onclose: ((event: any) => void) | null = null;
  public onmessage: ((event: any) => void) | null = null;
  public onerror: ((event: any) => void) | null = null;
  public url: string;

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  static instances: MockWebSocket[] = [];

  send(data: string): void {
    // Mock send
  }

  close(code?: number): void {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({ code: code || 1000, reason: '' });
    }
  }

  // Helper to simulate connection
  simulateOpen(): void {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) {
      this.onopen({});
    }
  }

  // Helper to simulate message
  simulateMessage(data: any): void {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }

  // Helper to simulate error
  simulateError(error: any): void {
    if (this.onerror) {
      this.onerror(error);
    }
  }
}

describe('MetricsWebSocket', () => {
  let ws: MetricsWebSocket;
  const testUrl = 'wss://test-orchestrator.example.com/ws/metrics';

  beforeEach(() => {
    MockWebSocket.instances = [];
    (global as any).WebSocket = MockWebSocket;
    ws = new MetricsWebSocket(testUrl);
  });

  afterEach(() => {
    ws.disconnect();
  });

  describe('Constructor', () => {
    it('should create instance with URL', () => {
      expect(ws).toBeInstanceOf(MetricsWebSocket);
    });

    it('should not connect automatically', () => {
      expect(MockWebSocket.instances.length).toBe(0);
    });
  });

  describe('connect', () => {
    it('should create WebSocket connection', async () => {
      const connectPromise = ws.connect();

      expect(MockWebSocket.instances.length).toBe(1);
      expect(MockWebSocket.instances[0].url).toBe(testUrl);

      // Simulate connection success
      MockWebSocket.instances[0].simulateOpen();

      await connectPromise;
    });

    it('should resolve promise on successful connection', async () => {
      const connectPromise = ws.connect();

      MockWebSocket.instances[0].simulateOpen();

      await expect(connectPromise).resolves.toBeUndefined();
    });

    it('should reject promise on connection error', async () => {
      const connectPromise = ws.connect();

      const error = new Error('Connection failed');
      MockWebSocket.instances[0].simulateError(error);

      await expect(connectPromise).rejects.toThrow('Connection failed');
    });

    it('should not create multiple connections if already connected', async () => {
      const connectPromise1 = ws.connect();
      MockWebSocket.instances[0].simulateOpen();
      await connectPromise1;

      const connectPromise2 = ws.connect();
      await connectPromise2;

      expect(MockWebSocket.instances.length).toBe(1);
    });
  });

  describe('disconnect', () => {
    it('should close WebSocket connection', async () => {
      const connectPromise = ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();
      await connectPromise;

      const closeSpy = vi.spyOn(mockWs, 'close');

      ws.disconnect();

      expect(closeSpy).toHaveBeenCalledWith(1000);
    });

    it('should handle disconnect when not connected', () => {
      expect(() => ws.disconnect()).not.toThrow();
    });

    it('should update isConnected property', async () => {
      const connectPromise = ws.connect();
      MockWebSocket.instances[0].simulateOpen();
      await connectPromise;

      expect(ws.isConnected).toBe(true);

      ws.disconnect();

      expect(ws.isConnected).toBe(false);
    });
  });

  describe('onMetricUpdate', () => {
    it('should register callback for metric updates', async () => {
      const callback = vi.fn();

      const unsubscribe = ws.onMetricUpdate(callback);

      expect(typeof unsubscribe).toBe('function');
    });

    it('should call callback when metric update received', async () => {
      const callback = vi.fn();

      ws.onMetricUpdate(callback);

      await ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();

      const metricUpdate = {
        type: 'metric_update',
        timestamp: '2026-01-17T21:45:00Z',
        data: {
          metric_name: 'execution.started',
          execution_id: 'exec-123',
        },
      };

      mockWs.simulateMessage(metricUpdate);

      expect(callback).toHaveBeenCalledWith(metricUpdate.data);
    });

    it('should support multiple callbacks', async () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();

      ws.onMetricUpdate(callback1);
      ws.onMetricUpdate(callback2);

      await ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();

      const metricUpdate = {
        type: 'metric_update',
        timestamp: '2026-01-17T21:45:00Z',
        data: { value: 42 },
      };

      mockWs.simulateMessage(metricUpdate);

      expect(callback1).toHaveBeenCalledWith(metricUpdate.data);
      expect(callback2).toHaveBeenCalledWith(metricUpdate.data);
    });

    it('should unsubscribe callback when unsubscribe function called', async () => {
      const callback = vi.fn();

      const unsubscribe = ws.onMetricUpdate(callback);

      await ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();

      unsubscribe();

      const metricUpdate = {
        type: 'metric_update',
        timestamp: '2026-01-17T21:45:00Z',
        data: { value: 42 },
      };

      mockWs.simulateMessage(metricUpdate);

      expect(callback).not.toHaveBeenCalled();
    });

    it('should handle heartbeat messages without calling callbacks', async () => {
      const callback = vi.fn();

      ws.onMetricUpdate(callback);

      await ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();

      const heartbeat = {
        type: 'heartbeat',
        timestamp: '2026-01-17T21:45:00Z',
        data: { uptime_seconds: 86400 },
      };

      mockWs.simulateMessage(heartbeat);

      expect(callback).not.toHaveBeenCalled();
    });
  });

  describe('isConnected', () => {
    it('should return false when not connected', () => {
      expect(ws.isConnected).toBe(false);
    });

    it('should return true when connected', async () => {
      const connectPromise = ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();
      await connectPromise;

      expect(ws.isConnected).toBe(true);
    });

    it('should return false after disconnect', async () => {
      const connectPromise = ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();
      await connectPromise;

      ws.disconnect();

      expect(ws.isConnected).toBe(false);
    });
  });

  describe('Reconnection', () => {
    it('should attempt to reconnect on unexpected close', async () => {
      vi.useFakeTimers();

      const connectPromise = ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();
      await connectPromise;

      // Simulate unexpected close (code !== 1000)
      mockWs.close(1006);

      // Fast-forward past reconnect delay
      await vi.advanceTimersByTimeAsync(2000);

      // Should have created a new WebSocket for reconnection
      expect(MockWebSocket.instances.length).toBeGreaterThan(1);

      vi.useRealTimers();
    });

    it('should use exponential backoff for reconnection', async () => {
      vi.useFakeTimers();

      const connectPromise = ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();
      await connectPromise;

      const initialCount = MockWebSocket.instances.length;

      // First disconnect
      mockWs.close(1006);
      await vi.advanceTimersByTimeAsync(1000); // Initial delay: 1s
      expect(MockWebSocket.instances.length).toBe(initialCount + 1);

      // Second disconnect
      MockWebSocket.instances[1].close(1006);
      await vi.advanceTimersByTimeAsync(2000); // Double delay: 2s
      expect(MockWebSocket.instances.length).toBe(initialCount + 2);

      vi.useRealTimers();
    });

    it('should not reconnect on normal close', async () => {
      vi.useFakeTimers();

      const connectPromise = ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();
      await connectPromise();

      const initialCount = MockWebSocket.instances.length;

      // Normal close (code 1000)
      mockWs.close(1000);

      await vi.advanceTimersByTimeAsync(5000);

      expect(MockWebSocket.instances.length).toBe(initialCount);

      vi.useRealTimers();
    });
  });

  describe('Message Parsing', () => {
    it('should parse JSON messages', async () => {
      const callback = vi.fn();

      ws.onMetricUpdate(callback);

      await ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();

      const message = {
        type: 'metric_update',
        data: { value: 123 },
      };

      mockWs.simulateMessage(message);

      expect(callback).toHaveBeenCalledWith({ value: 123 });
    });

    it('should handle malformed JSON gracefully', async () => {
      const callback = vi.fn();

      ws.onMetricUpdate(callback);

      await ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();

      // Simulate malformed JSON
      if (mockWs.onmessage) {
        expect(() => {
          mockWs.onmessage({ data: 'invalid json' } as any);
        }).not.toThrow();
      }

      expect(callback).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should handle connection errors', async () => {
      const connectPromise = ws.connect();

      const error = new Error('Connection refused');
      MockWebSocket.instances[0].simulateError(error);

      await expect(connectPromise).rejects.toThrow('Connection refused');
    });

    it('should handle errors during active connection', async () => {
      const connectPromise = ws.connect();
      const mockWs = MockWebSocket.instances[0];
      mockWs.simulateOpen();
      await connectPromise;

      const errorSpy = vi.fn();
      ws.onMetricUpdate(errorSpy);

      // Simulate error during active connection
      mockWs.simulateError(new Error('Runtime error'));

      // Should not crash
      expect(ws.isConnected).toBe(true);
    });
  });
});
