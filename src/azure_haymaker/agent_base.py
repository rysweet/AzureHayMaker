"""Base class for autonomous goal-seeking agents.

Provides a standardized interface with lifecycle hooks for agent initialization,
execution, and cleanup. All agents should inherit from AgentBase to ensure
consistent behavior and reduce code duplication.
"""

import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent instance.

    Attributes:
        name: Agent name/identifier
        goal: Description of the agent's goal
        max_turns: Maximum execution turns (default: 10)
        working_dir: Working directory for execution
        sdk: SDK to use for execution (default: "claude")
        ui_mode: Whether to run in UI mode (default: False)
        success_criteria: List of success criteria to evaluate
        constraints: List of execution constraints
        extra: Additional configuration parameters
    """

    name: str
    goal: str
    max_turns: int = 10
    working_dir: Path = field(default_factory=Path.cwd)
    sdk: str = "claude"
    ui_mode: bool = False
    success_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary format for AutoMode compatibility."""
        return {
            "max_turns": self.max_turns,
            "working_dir": str(self.working_dir),
            "sdk": self.sdk,
            "ui_mode": self.ui_mode,
            "success_criteria": self.success_criteria,
            "constraints": self.constraints,
            **self.extra,
        }


class AgentBase(ABC):
    """Abstract base class for autonomous goal-seeking agents.

    Provides lifecycle hooks and common functionality for all agents.
    Subclasses must implement get_config() and optionally override
    lifecycle hooks for custom behavior.

    Lifecycle:
        1. on_start() - Called before execution begins
        2. on_execute() - Main execution logic
        3. on_cleanup() - Called after execution completes (success or failure)

    Example:
        >>> class MyAgent(AgentBase):
        ...     def get_config(self) -> AgentConfig:
        ...         return AgentConfig(
        ...             name="my-agent",
        ...             goal="Accomplish a specific task",
        ...             max_turns=5,
        ...         )
        ...
        ...     def on_start(self) -> None:
        ...         print("Starting my agent")
        ...
        >>> agent = MyAgent()
        >>> exit_code = agent.run()
    """

    def __init__(self, prompt_path: Path | None = None):
        """Initialize the agent.

        Args:
            prompt_path: Path to the prompt file. If None, looks for prompt.md
                        in the same directory as the agent module.
        """
        self._config: AgentConfig | None = None
        self._prompt: str | None = None
        self._prompt_path = prompt_path
        self._auto_mode: Any = None

    @property
    def config(self) -> AgentConfig:
        """Get agent configuration, caching on first access."""
        if self._config is None:
            self._config = self.get_config()
        return self._config

    @property
    def prompt(self) -> str:
        """Get agent prompt, loading from file on first access."""
        if self._prompt is None:
            self._prompt = self._load_prompt()
        return self._prompt

    @abstractmethod
    def get_config(self) -> AgentConfig:
        """Return the agent configuration.

        Subclasses must implement this method to provide their configuration.

        Returns:
            AgentConfig instance with agent settings
        """
        ...

    def _load_prompt(self) -> str:
        """Load the prompt from file.

        Returns:
            Prompt content as string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        if self._prompt_path is not None:
            prompt_path = self._prompt_path
        else:
            # Default to prompt.md in the same directory as the subclass
            module_file = sys.modules[self.__class__.__module__].__file__
            if module_file:
                prompt_path = Path(module_file).parent / "prompt.md"
            else:
                prompt_path = Path.cwd() / "prompt.md"

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        return prompt_path.read_text()

    def _get_auto_mode(self) -> Any:
        """Get or create the AutoMode instance.

        Returns:
            AutoMode instance

        Raises:
            ImportError: If amplihack package is not installed
        """
        if self._auto_mode is None:
            try:
                from amplihack.launcher.auto_mode import AutoMode
            except ImportError:
                logger.error("amplihack package not found")
                raise ImportError(
                    "amplihack package not found. Install with: pip install amplihack"
                ) from None

            self._auto_mode = AutoMode(
                sdk=self.config.sdk,
                prompt=self.prompt,
                max_turns=self.config.max_turns,
                working_dir=self.config.working_dir,
                ui_mode=self.config.ui_mode,
            )

        return self._auto_mode

    def on_start(self) -> None:
        """Called before execution begins.

        Override this method to perform setup tasks before the agent starts.
        Default implementation logs the start.
        """
        logger.info(f"Starting agent: {self.config.name}")
        logger.info(f"Goal: {self.config.goal}")

    def on_execute(self) -> int:
        """Main execution logic.

        Override this method for custom execution behavior. Default
        implementation uses AutoMode.

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        auto_mode = self._get_auto_mode()
        return auto_mode.run()

    def on_cleanup(self, exit_code: int) -> None:
        """Called after execution completes.

        Override this method to perform cleanup tasks after the agent
        finishes, regardless of success or failure.

        Args:
            exit_code: The exit code from on_execute()
        """
        if exit_code == 0:
            logger.info(f"Agent {self.config.name} completed successfully")
        else:
            logger.warning(f"Agent {self.config.name} failed with code {exit_code}")

    def run(self) -> int:
        """Execute the agent with full lifecycle management.

        Calls lifecycle hooks in order:
        1. on_start()
        2. on_execute()
        3. on_cleanup()

        Returns:
            Exit code from on_execute() (0 for success, non-zero for failure)
        """
        exit_code = 1

        try:
            self.on_start()
            exit_code = self.on_execute()
        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            exit_code = 1
        finally:
            try:
                self.on_cleanup(exit_code)
            except Exception as e:
                logger.exception(f"Cleanup failed: {e}")

        return exit_code


class SimpleAgent(AgentBase):
    """A simple agent that can be configured without subclassing.

    Useful for quick agent creation where custom lifecycle behavior
    is not needed.

    Example:
        >>> agent = SimpleAgent(
        ...     name="quick-task",
        ...     goal="Complete a quick task",
        ...     prompt="Do the thing",
        ...     max_turns=3,
        ... )
        >>> exit_code = agent.run()
    """

    def __init__(
        self,
        name: str,
        goal: str,
        prompt: str | None = None,
        prompt_path: Path | None = None,
        max_turns: int = 10,
        working_dir: Path | None = None,
        sdk: str = "claude",
        ui_mode: bool = False,
        success_criteria: list[str] | None = None,
        constraints: list[str] | None = None,
        **extra: Any,
    ):
        """Initialize a simple agent.

        Args:
            name: Agent name/identifier
            goal: Description of the agent's goal
            prompt: Direct prompt string (mutually exclusive with prompt_path)
            prompt_path: Path to prompt file
            max_turns: Maximum execution turns
            working_dir: Working directory for execution
            sdk: SDK to use (default: "claude")
            ui_mode: Whether to run in UI mode
            success_criteria: List of success criteria
            constraints: List of constraints
            **extra: Additional configuration parameters
        """
        super().__init__(prompt_path=prompt_path)

        self._simple_config = AgentConfig(
            name=name,
            goal=goal,
            max_turns=max_turns,
            working_dir=working_dir or Path.cwd(),
            sdk=sdk,
            ui_mode=ui_mode,
            success_criteria=success_criteria or [],
            constraints=constraints or [],
            extra=extra,
        )

        if prompt is not None:
            self._prompt = prompt

    def get_config(self) -> AgentConfig:
        """Return the agent configuration."""
        return self._simple_config


__all__ = ["AgentBase", "AgentConfig", "SimpleAgent"]
