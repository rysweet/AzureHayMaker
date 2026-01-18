/**
 * Dashboard Context
 *
 * Manages global dashboard state including time range, selected agents,
 * refresh rate, and WebSocket connection state.
 */

import React, { createContext, useContext, useState, useCallback, PropsWithChildren } from 'react';

export interface DashboardState {
  timeRange: '7d' | '30d' | '90d';
  selectedAgents: string[];
  refreshRate: number; // seconds
  isConnected: boolean;
}

interface DashboardContextValue extends DashboardState {
  setTimeRange: (range: '7d' | '30d' | '90d') => void;
  setSelectedAgents: (agents: string[]) => void;
  setRefreshRate: (rate: number) => void;
  setIsConnected: (connected: boolean) => void;
}

const DashboardContext = createContext<DashboardContextValue | undefined>(undefined);

export const DashboardProvider: React.FC<PropsWithChildren> = ({ children }) => {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [refreshRate, setRefreshRate] = useState<number>(30); // 30 seconds default
  const [isConnected, setIsConnected] = useState<boolean>(false);

  const value: DashboardContextValue = {
    timeRange,
    selectedAgents,
    refreshRate,
    isConnected,
    setTimeRange: useCallback((range: '7d' | '30d' | '90d') => setTimeRange(range), []),
    setSelectedAgents: useCallback((agents: string[]) => setSelectedAgents(agents), []),
    setRefreshRate: useCallback((rate: number) => setRefreshRate(rate), []),
    setIsConnected: useCallback((connected: boolean) => setIsConnected(connected), []),
  };

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboard = (): DashboardContextValue => {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboard must be used within DashboardProvider');
  }
  return context;
};
