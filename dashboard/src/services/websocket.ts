/**
 * WebSocket Service for Real-Time Metrics
 *
 * Establishes and maintains WebSocket connection with reconnection logic.
 * Handles metric updates and broadcasts to subscribers.
 */

export interface MetricUpdate {
  type: 'execution' | 'cost' | 'telemetry' | 'agent';
  timestamp: string;
  data: any;
}

type MetricCallback = (data: MetricUpdate) => void;
type UnsubscribeFn = () => void;

export class MetricsWebSocket {
  private url: string;
  private ws: WebSocket | null = null;
  private callbacks: Set<MetricCallback> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start at 1 second
  private heartbeatInterval: number | null = null;
  private _isConnected = false;

  constructor(url: string) {
    this.url = url;
  }

  get isConnected(): boolean {
    return this._isConnected && this.ws?.readyState === WebSocket.OPEN;
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this._isConnected = true;
          this.reconnectAttempts = 0;
          this.reconnectDelay = 1000;
          this.startHeartbeat();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);

            // Handle heartbeat/ping messages
            if (message.type === 'heartbeat' || message.type === 'ping' || message.type === 'pong') {
              return;
            }

            // Broadcast metric updates to all subscribers
            const update: MetricUpdate = {
              type: message.metric_type || message.type,
              timestamp: message.timestamp,
              data: message.data || message,
            };

            this.callbacks.forEach((callback) => callback(update));
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.ws.onclose = (event) => {
          this._isConnected = false;
          this.stopHeartbeat();

          // Attempt reconnection if not a normal closure
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      this._isConnected = false;
      this.ws.close(1000); // Normal closure
      this.ws = null;
    }
  }

  onMetricUpdate(callback: MetricCallback): UnsubscribeFn {
    this.callbacks.add(callback);
    return () => {
      this.callbacks.delete(callback);
    };
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // 30 second heartbeat
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval !== null) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private attemptReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff

    setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      this.connect().catch((error) => {
        console.error('Reconnection failed:', error);
      });
    }, delay);
  }
}
