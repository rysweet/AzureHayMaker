"""Azure HayMaker - Autonomous Azure Infrastructure Testing Framework."""

from azure_haymaker.agent_base import AgentBase, AgentConfig, SimpleAgent


def hello() -> str:
    return "Hello from azure-haymaker!"


__all__ = [
    "AgentBase",
    "AgentConfig",
    "SimpleAgent",
    "hello",
]

# Trigger dev deployment
# Trigger CI
