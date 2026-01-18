export interface AgentStatusProps {
  agents: AgentInfo[];
  onAgentClick?: (agentId: string) => void;
}

export interface AgentInfo {
  agent_id: string;
  agent_name: string;
  status: 'running' | 'idle' | 'failed' | 'queued';
  last_execution_at?: string;
  last_duration_seconds?: number;
  error_message?: string;
}
