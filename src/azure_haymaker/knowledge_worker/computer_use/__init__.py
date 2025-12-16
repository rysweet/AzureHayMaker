"""Computer Use Knowledge Worker Agent Module.

Browser-based M365 automation for knowledge worker agents using
the Computer Use pattern with Playwright.
"""

from azure_haymaker.knowledge_worker.computer_use.agent import (
    ComputerUseConfig,
    ComputerUseKnowledgeWorkerAgent,
)
from azure_haymaker.knowledge_worker.computer_use.agent_deployer import (
    AgentDeployer,
    DeploymentError,
    DeploymentVerificationError,
)
from azure_haymaker.knowledge_worker.computer_use.browser_automation import (
    BrowserAutomation,
    BrowserAutomationError,
    LoginError,
    NavigationError,
)
from azure_haymaker.knowledge_worker.computer_use.telemetry import (
    ComputerUseTelemetryCollector,
    OperationLog,
    TelemetryMetrics,
)
from azure_haymaker.knowledge_worker.computer_use.winrm_connection import (
    WinRMConnection,
    WinRMConnectionError,
    WinRMTimeoutError,
)

__all__ = [
    # Agent
    "ComputerUseKnowledgeWorkerAgent",
    "ComputerUseConfig",
    # WinRM
    "WinRMConnection",
    "WinRMConnectionError",
    "WinRMTimeoutError",
    # Deployment
    "AgentDeployer",
    "DeploymentError",
    "DeploymentVerificationError",
    # Browser Automation
    "BrowserAutomation",
    "BrowserAutomationError",
    "LoginError",
    "NavigationError",
    # Telemetry
    "ComputerUseTelemetryCollector",
    "OperationLog",
    "TelemetryMetrics",
]
