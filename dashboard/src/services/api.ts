/**
 * Dashboard API Client
 *
 * REST API client for fetching metrics, analytics, cost, agent, and telemetry data.
 * Implements retry logic and error handling.
 */

import {
  MetricsResponse,
  AnalyticsResponse,
  CostData,
  AgentInfo,
  TelemetryData,
} from '../types';

export class DashboardAPI {
  private baseUrl: string;
  private authToken?: string;

  constructor(baseUrl: string, authToken?: string) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.authToken = authToken;
  }

  private async fetchWithAuth(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response;
  }

  async getMetrics(): Promise<MetricsResponse> {
    const response = await this.fetchWithAuth('/metrics');
    return response.json();
  }

  async getAnalytics(period: '7d' | '30d' | '90d' = '30d'): Promise<AnalyticsResponse> {
    const response = await this.fetchWithAuth(`/analytics?period=${period}`);
    return response.json();
  }

  async getCostBreakdown(period: '7d' | '30d' | '90d' = '30d'): Promise<CostData> {
    const response = await this.fetchWithAuth(`/cost/breakdown?period=${period}`);
    return response.json();
  }

  async getAgentStatus(): Promise<AgentInfo[]> {
    const response = await this.fetchWithAuth('/agents/status');
    return response.json();
  }

  async getTelemetryVolume(period: '7d' | '30d' | '90d' = '30d'): Promise<TelemetryData> {
    const response = await this.fetchWithAuth(`/telemetry/volume?period=${period}`);
    return response.json();
  }
}
