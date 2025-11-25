#!/usr/bin/env python3
"""
Container Apps Web Agent - Autonomous Goal-Seeking Agent

Uses the AgentBase class for lifecycle management and reduced boilerplate.
"""

import sys
from pathlib import Path

# Add src directory to path for azure_haymaker imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from azure_haymaker.agent_base import AgentBase, AgentConfig


class ContainerAppsWebAgent(AgentBase):
    """Agent for deploying containerized web applications on Azure.

    Demonstrates the AgentBase lifecycle hooks with custom startup and
    cleanup behavior for Azure Container Apps scenarios.
    """

    def get_config(self) -> AgentConfig:
        """Return agent configuration."""
        return AgentConfig(
            name="container-apps-web-agent",
            goal="Deploy a containerized web application on Azure Container Apps",
            max_turns=6,
            working_dir=Path(__file__).parent,
            sdk="claude",
            ui_mode=False,
            success_criteria=[
                "Container App is deployed and running",
                "Web application is accessible via HTTPS",
                "Auto-scaling is configured",
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
    agent = ContainerAppsWebAgent()
    return agent.run()


if __name__ == "__main__":
    sys.exit(main())
