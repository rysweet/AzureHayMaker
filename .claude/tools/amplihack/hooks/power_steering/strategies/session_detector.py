#!/usr/bin/env python3
"""
Session type detection strategy.

Classifies sessions into types (DEVELOPMENT, INFORMATIONAL, MAINTENANCE, INVESTIGATION)
to enable selective application of considerations.
"""

import os
from typing import Dict, List


class SessionDetector:
    """Detects session type from transcript analysis."""

    # File extension constants
    CODE_FILE_EXTENSIONS = [
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java",
        ".go", ".rs", ".c", ".cpp", ".h",
    ]
    DOC_FILE_EXTENSIONS = [".md", ".txt", ".rst", "README", "CHANGELOG"]
    CONFIG_FILE_EXTENSIONS = [".yml", ".yaml", ".json"]
    TEST_COMMAND_PATTERNS = [
        "pytest", "npm test", "cargo test", "go test",
        "python -m pytest", "python -m unittest",
    ]

    def detect_session_type(self, transcript: List[Dict]) -> str:
        """Detect session type for selective consideration application.

        Session Types:
        - DEVELOPMENT: Code changes, tests, PR operations
        - INFORMATIONAL: Q&A, help queries, capability questions
        - MAINTENANCE: Documentation and configuration updates only
        - INVESTIGATION: Read-only exploration and analysis

        Args:
            transcript: List of message dictionaries

        Returns:
            Session type string
        """
        # Check for environment override first
        env_override = os.getenv("AMPLIHACK_SESSION_TYPE", "").upper()
        if env_override in ["DEVELOPMENT", "INFORMATIONAL", "MAINTENANCE", "INVESTIGATION"]:
            return env_override

        # Empty transcript defaults to INFORMATIONAL (fail-open)
        if not transcript:
            return "INFORMATIONAL"

        # Collect indicators
        indicators = self._collect_indicators(transcript)

        # Decision logic (priority order)
        if self._is_development(indicators):
            return "DEVELOPMENT"

        if self._is_informational(indicators):
            return "INFORMATIONAL"

        if self._is_investigation(indicators):
            return "INVESTIGATION"

        if self._is_maintenance(indicators):
            return "MAINTENANCE"

        # Default to INFORMATIONAL if unclear (fail-open, conservative)
        return "INFORMATIONAL"

    def _collect_indicators(self, transcript: List[Dict]) -> Dict:
        """Collect all indicators from transcript.

        Args:
            transcript: List of message dictionaries

        Returns:
            Dictionary of indicator flags and counts
        """
        indicators = {
            "code_files_modified": False,
            "doc_files_only": True,
            "write_edit_operations": 0,
            "read_grep_operations": 0,
            "test_executions": 0,
            "pr_operations": False,
            "git_operations": False,
            "question_count": 0,
            "user_messages_count": 0,
        }

        # Count questions in user messages
        user_messages = [m for m in transcript if m.get("type") == "user"]
        indicators["user_messages_count"] = len(user_messages)
        for msg in user_messages:
            content = str(msg.get("message", {}).get("content", ""))
            indicators["question_count"] += content.count("?")

        # Analyze tool usage
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if not isinstance(content, list):
                    content = [content]

                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        self._analyze_tool_use(block, indicators)

        return indicators

    def _analyze_tool_use(self, tool_block: Dict, indicators: Dict) -> None:
        """Analyze a single tool use block and update indicators.

        Args:
            tool_block: Tool use block dictionary
            indicators: Indicators dictionary to update
        """
        tool_name = tool_block.get("name", "")
        tool_input = tool_block.get("input", {})

        # Write/Edit operations
        if tool_name in ["Write", "Edit"]:
            indicators["write_edit_operations"] += 1
            file_path = tool_input.get("file_path", "")

            # Check if code file
            if any(ext in file_path for ext in self.CODE_FILE_EXTENSIONS):
                indicators["code_files_modified"] = True
                indicators["doc_files_only"] = False

            # Check if non-doc/config file
            if not any(ext in file_path for ext in self.DOC_FILE_EXTENSIONS):
                if not any(ext in file_path for ext in self.CONFIG_FILE_EXTENSIONS):
                    indicators["doc_files_only"] = False

        # Read/Grep operations
        elif tool_name in ["Read", "Grep", "Glob"]:
            indicators["read_grep_operations"] += 1

        # Test execution and git operations
        elif tool_name == "Bash":
            command = tool_input.get("command", "")

            if any(pattern in command for pattern in self.TEST_COMMAND_PATTERNS):
                indicators["test_executions"] += 1

            if "gh pr create" in command or "gh pr" in command:
                indicators["pr_operations"] = True

            if "git commit" in command or "git push" in command:
                indicators["git_operations"] = True

    def _is_development(self, indicators: Dict) -> bool:
        """Check if indicators show development session.

        Args:
            indicators: Collected indicators

        Returns:
            True if development session
        """
        return (
            indicators["code_files_modified"]
            or indicators["test_executions"] > 0
            or indicators["pr_operations"]
        )

    def _is_informational(self, indicators: Dict) -> bool:
        """Check if indicators show informational session.

        Args:
            indicators: Collected indicators

        Returns:
            True if informational session
        """
        # No tool usage or only Read tools with high question density
        if indicators["write_edit_operations"] == 0:
            if indicators["read_grep_operations"] <= 1 and indicators["question_count"] > 0:
                if indicators["user_messages_count"] > 0:
                    # High question density indicates INFORMATIONAL
                    question_ratio = indicators["question_count"] / indicators["user_messages_count"]
                    return question_ratio > 0.5
        return False

    def _is_investigation(self, indicators: Dict) -> bool:
        """Check if indicators show investigation session.

        Args:
            indicators: Collected indicators

        Returns:
            True if investigation session
        """
        # Multiple Read/Grep without modifications
        return (
            indicators["read_grep_operations"] >= 2
            and indicators["write_edit_operations"] == 0
        )

    def _is_maintenance(self, indicators: Dict) -> bool:
        """Check if indicators show maintenance session.

        Args:
            indicators: Collected indicators

        Returns:
            True if maintenance session
        """
        # Only doc/config files modified
        if indicators["write_edit_operations"] > 0 and indicators["doc_files_only"]:
            return True

        # Git operations without code changes
        if (
            indicators["git_operations"]
            and not indicators["code_files_modified"]
            and indicators["write_edit_operations"] == 0
        ):
            return True

        return False
