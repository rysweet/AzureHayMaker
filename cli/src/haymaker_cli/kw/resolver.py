"""Run ID resolution for KW monitoring commands.

Provides multi-source run_id resolution with the following priority:
1. Command-line flag (--run-id)
2. Environment variable (HAYMAKER_RUN_ID)
3. Active deployment file (~/.azure_haymaker/active_deployment)

This allows users to:
- Explicitly specify run_id on each command
- Set a persistent run_id in environment
- Automatically use the most recent active deployment
"""

import os
from pathlib import Path


class RunIdResolver:
    """Resolves run_id from multiple sources with priority order."""

    # Default state directory
    STATE_DIR = Path.home() / ".azure_haymaker"
    ACTIVE_FILE = STATE_DIR / "active_deployment"
    ENV_VAR = "HAYMAKER_RUN_ID"

    @classmethod
    def resolve(cls, flag_value: str | None = None) -> str | None:
        """Resolve run_id from available sources.

        Priority order:
        1. flag_value (--run-id from CLI)
        2. HAYMAKER_RUN_ID environment variable
        3. ~/.azure_haymaker/active_deployment file

        Args:
            flag_value: Run ID from --run-id flag (highest priority)

        Returns:
            Resolved run_id or None if not found in any source

        Example:
            >>> run_id = RunIdResolver.resolve(flag_value="kw-abc123")
            >>> if not run_id:
            ...     print("No run_id found")
        """
        # 1. Check command-line flag
        if flag_value:
            return flag_value.strip()

        # 2. Check environment variable
        env_value = os.environ.get(cls.ENV_VAR, "").strip()
        if env_value:
            return env_value

        # 3. Check active deployment file
        if cls.ACTIVE_FILE.exists():
            try:
                run_id = cls.ACTIVE_FILE.read_text().strip()
                if run_id:
                    return run_id
            except Exception:
                # File read failed, fall through to None
                pass

        return None

    @classmethod
    def set_active(cls, run_id: str) -> None:
        """Set the active deployment run_id.

        Creates ~/.azure_haymaker/ directory if needed and writes
        run_id to active_deployment file.

        Args:
            run_id: Run ID to set as active

        Raises:
            OSError: If directory creation or file write fails

        Example:
            >>> RunIdResolver.set_active("kw-abc123")
        """
        cls.STATE_DIR.mkdir(parents=True, exist_ok=True)
        cls.ACTIVE_FILE.write_text(run_id)

    @classmethod
    def clear_active(cls) -> None:
        """Clear the active deployment.

        Removes the active_deployment file if it exists.

        Example:
            >>> RunIdResolver.clear_active()
        """
        if cls.ACTIVE_FILE.exists():
            cls.ACTIVE_FILE.unlink()

    @classmethod
    def get_active(cls) -> str | None:
        """Get the currently active run_id.

        Returns:
            Active run_id or None if no active deployment

        Example:
            >>> active = RunIdResolver.get_active()
            >>> print(f"Active: {active or 'none'}")
        """
        if cls.ACTIVE_FILE.exists():
            try:
                return cls.ACTIVE_FILE.read_text().strip() or None
            except Exception:
                return None
        return None


def resolve_run_id(flag_value: str | None = None) -> str | None:
    """Convenience function for run_id resolution.

    Args:
        flag_value: Run ID from --run-id flag

    Returns:
        Resolved run_id or None
    """
    return RunIdResolver.resolve(flag_value)


__all__ = ["RunIdResolver", "resolve_run_id"]
