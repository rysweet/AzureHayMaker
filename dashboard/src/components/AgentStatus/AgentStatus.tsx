/**
 * Agent Status Component
 *
 * Displays grid of agent cards with status indicators.
 * Shows running, idle, failed, and queued agents with details.
 */

import React from 'react';
import type { AgentStatusProps, AgentInfo } from './types';

const STATUS_COLORS = {
  running: '#4caf50',
  idle: '#9e9e9e',
  failed: '#f44336',
  queued: '#ff9800',
};

const STATUS_LABELS = {
  running: '🟢 Running',
  idle: '⚪ Idle',
  failed: '🔴 Failed',
  queued: '🟡 Queued',
};

export const AgentStatus: React.FC<AgentStatusProps> = ({ agents, onAgentClick }) => {
  if (!agents || agents.length === 0) {
    return (
      <div role="status" aria-label="No agents available" style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
        No agents available
      </div>
    );
  }

  const handleAgentClick = (agentId: string) => {
    if (onAgentClick) {
      onAgentClick(agentId);
    }
  };

  return (
    <div role="region" aria-label="Agent Status" style={{ padding: '1rem' }}>
      <h3>Agent Status</h3>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
          gap: '1rem',
          marginTop: '1rem',
        }}
      >
        {agents.map((agent) => (
          <div
            key={agent.agent_id}
            onClick={() => handleAgentClick(agent.agent_id)}
            role="button"
            tabIndex={0}
            aria-label={`Agent ${agent.agent_name} - ${agent.status}`}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                handleAgentClick(agent.agent_id);
              }
            }}
            style={{
              border: `2px solid ${STATUS_COLORS[agent.status]}`,
              borderRadius: '8px',
              padding: '1rem',
              cursor: onAgentClick ? 'pointer' : 'default',
              backgroundColor: '#fff',
              transition: 'transform 0.2s',
            }}
            onMouseEnter={(e) => {
              if (onAgentClick) {
                e.currentTarget.style.transform = 'translateY(-2px)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <div style={{ marginBottom: '0.5rem', fontWeight: 'bold' }}>
              {agent.agent_name}
            </div>
            <div style={{ color: STATUS_COLORS[agent.status], marginBottom: '0.5rem' }}>
              {STATUS_LABELS[agent.status]}
            </div>
            {agent.last_execution_at && (
              <div style={{ fontSize: '0.85rem', color: '#666' }}>
                Last: {new Date(agent.last_execution_at).toLocaleString()}
              </div>
            )}
            {agent.last_duration_seconds !== undefined && (
              <div style={{ fontSize: '0.85rem', color: '#666' }}>
                Duration: {agent.last_duration_seconds}s
              </div>
            )}
            {agent.error_message && (
              <div role="alert" style={{ fontSize: '0.85rem', color: '#f44336', marginTop: '0.5rem' }}>
                Error: {agent.error_message}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
