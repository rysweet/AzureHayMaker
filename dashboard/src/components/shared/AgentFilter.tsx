/**
 * Agent Filter Component
 *
 * Multi-select filter for choosing which agents to display.
 */

import React from 'react';

export interface AgentFilterProps {
  availableAgents: string[];
  selectedAgents: string[];
  onChange: (selected: string[]) => void;
}

export const AgentFilter: React.FC<AgentFilterProps> = ({
  availableAgents,
  selectedAgents,
  onChange,
}) => {
  const handleToggle = (agentId: string) => {
    if (selectedAgents.includes(agentId)) {
      onChange(selectedAgents.filter((id) => id !== agentId));
    } else {
      onChange([...selectedAgents, agentId]);
    }
  };

  const handleSelectAll = () => {
    onChange(availableAgents);
  };

  const handleSelectNone = () => {
    onChange([]);
  };

  return (
    <div role="group" aria-label="Agent Filter" style={{ padding: '1rem', border: '1px solid #ccc', borderRadius: '4px' }}>
      <div style={{ marginBottom: '0.5rem', display: 'flex', gap: '0.5rem' }}>
        <button onClick={handleSelectAll} style={{ padding: '0.25rem 0.5rem', fontSize: '0.85rem' }}>
          Select All
        </button>
        <button onClick={handleSelectNone} style={{ padding: '0.25rem 0.5rem', fontSize: '0.85rem' }}>
          Clear
        </button>
      </div>
      <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
        {availableAgents.map((agentId) => (
          <label
            key={agentId}
            style={{ display: 'block', padding: '0.25rem 0', cursor: 'pointer' }}
          >
            <input
              type="checkbox"
              checked={selectedAgents.includes(agentId)}
              onChange={() => handleToggle(agentId)}
              style={{ marginRight: '0.5rem' }}
            />
            {agentId}
          </label>
        ))}
      </div>
    </div>
  );
};
