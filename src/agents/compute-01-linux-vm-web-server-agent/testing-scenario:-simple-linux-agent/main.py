#!/usr/bin/env python3
"""
Linux VM Web Server Agent - Autonomous Goal-Seeking Agent

Uses the AgentBase class for lifecycle management and reduced boilerplate.
"""

import sys
from pathlib import Path

# Add src directory to path for azure_haymaker imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from azure_haymaker.agent_base import AgentBase, AgentConfig


class LinuxVMWebServerAgent(AgentBase):
    """Agent for deploying and testing Linux VM web servers on Azure.

    Demonstrates the AgentBase lifecycle hooks with custom startup and
    cleanup behavior.
    """

    def get_config(self) -> AgentConfig:
        """Return agent configuration."""
        return AgentConfig(
            name="linux-vm-web-server-agent",
            goal="Deploy a Linux VM running Nginx web server on Azure",
            max_turns=6,
            working_dir=Path(__file__).parent,
            sdk="claude",
            ui_mode=False,
            success_criteria=[
                "Linux VM is deployed and running",
                "Nginx web server is accessible via HTTP",
                "All Azure resources are properly tagged",
            ],
            constraints=[
                "Use Azure CLI for all operations",
                "Tag all resources with AzureHayMaker-managed=true",
            ],
        )

    def on_start(self) -> None:
        """Called before execution begins."""
        super().on_start()
        print(f"Starting {self.config.name}...")
        print(f"Goal: {self.config.goal}")
        print("Estimated duration: 22 minutes")
        print()

    def on_cleanup(self, exit_code: int) -> None:
        """Called after execution completes."""
        super().on_cleanup(exit_code)
        if exit_code == 0:
            print("\nGoal achieved successfully!")
        else:
            print(f"\nGoal execution failed with code {exit_code}")


def main() -> int:
    """Execute the goal-seeking agent."""
    agent = LinuxVMWebServerAgent()
    return agent.run()


if __name__ == "__main__":
    sys.exit(main())
