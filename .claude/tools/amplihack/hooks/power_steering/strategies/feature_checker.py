#!/usr/bin/env python3
"""
Feature checkers for power-steering considerations.

Contains all heuristic checker methods that analyze transcripts
for specific consideration criteria.
"""

import re
from typing import Any, Dict, List


class FeatureChecker:
    """Collection of feature-specific checker methods."""

    # File extension constants
    CODE_FILE_EXTENSIONS = [
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java",
        ".go", ".rs", ".c", ".cpp", ".h",
    ]
    DOC_FILE_EXTENSIONS = [".md", ".txt", ".rst", "README", "CHANGELOG"]
    TEST_COMMAND_PATTERNS = [
        "pytest", "npm test", "cargo test", "go test",
        "python -m pytest", "python -m unittest",
    ]

    def check_todos_complete(self, transcript: List[Dict]) -> bool:
        """Check if all TODO items completed.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if all TODOs completed, False otherwise
        """
        # Find last TodoWrite tool call
        last_todo_write = self._find_last_todo_write(transcript)

        # If no TodoWrite found, consider satisfied
        if not last_todo_write:
            return True

        # Check todos in last TodoWrite
        todos = last_todo_write.get("todos", [])
        if not todos:
            return True

        # Check if any todos are not completed
        return all(todo.get("status") == "completed" for todo in todos)

    def check_dev_workflow_complete(self, transcript: List[Dict]) -> bool:
        """Check if full DEFAULT_WORKFLOW followed.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if workflow complete, False otherwise
        """
        tools_used = self._extract_tool_names(transcript)

        # Check for signs of workflow completion
        has_tests = "Bash" in tools_used
        has_file_ops = any(t in tools_used for t in ["Edit", "Write", "Read"])

        # If no file operations, likely not a development task
        if not has_file_ops:
            return True

        # For development tasks, we expect tests to be run
        return has_tests

    def check_philosophy_compliance(self, transcript: List[Dict]) -> bool:
        """Check for PHILOSOPHY adherence (zero-BS).

        Args:
            transcript: List of message dictionaries

        Returns:
            True if compliant, False otherwise
        """
        anti_patterns = [
            (r"\b(TODO|FIXME|XXX)\b", "TODO/FIXME markers"),
            ("NotImplementedError", "stub implementations"),
            (r"def\s+\w+\([^)]*\):\s*pass\s*$", "stub functions"),
        ]

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") in ["Write", "Edit"]:
                                code_content = self._extract_code_content(block)
                                if self._has_anti_patterns(code_content, anti_patterns):
                                    return False
        return True

    def check_local_testing(self, transcript: List[Dict]) -> bool:
        """Check if agent tested locally.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if tests run and passed, False otherwise
        """
        for msg in transcript:
            if msg.get("type") == "tool_result" and "message" in msg:
                if self._is_successful_test_result(msg, transcript):
                    return True
        return False

    def check_ci_status(self, transcript: List[Dict]) -> bool:
        """Check if CI passing/mergeable.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if CI passing or not applicable, False if CI failing
        """
        ci_mentioned = False
        ci_passing = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", "")).lower()
                            if self._has_ci_keywords(text):
                                ci_mentioned = True
                                if self._has_passing_keywords(text):
                                    ci_passing = True
                                if self._has_failure_keywords(text):
                                    return False

        # If CI not mentioned, consider satisfied
        return not ci_mentioned or ci_passing

    def check_documentation_updates(self, transcript: List[Dict]) -> bool:
        """Check if relevant documentation files were updated.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if docs updated or not applicable, False if needed but missing
        """
        code_files_modified = False
        doc_files_modified = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") in ["Write", "Edit"]:
                                file_path = block.get("input", {}).get("file_path", "")
                                if any(ext in file_path for ext in self.CODE_FILE_EXTENSIONS):
                                    code_files_modified = True
                                if any(ext in file_path for ext in self.DOC_FILE_EXTENSIONS):
                                    doc_files_modified = True

        # If code was modified but no docs updated, flag as issue
        return not code_files_modified or doc_files_modified

    def check_objective_completion(self, transcript: List[Dict]) -> bool:
        """Check if original user objective was fully accomplished.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if objective appears complete, False otherwise
        """
        # Get first user message
        first_user_msg = next((m for m in transcript if m.get("type") == "user"), None)
        if not first_user_msg:
            return True

        # Look for completion indicators in recent assistant messages
        completion_indicators = [
            "complete", "finished", "done", "implemented",
            "successfully", "all tests pass",
        ]

        for msg in reversed(transcript[-10:]):
            if msg.get("type") == "assistant":
                text = self._extract_assistant_text(msg)
                if any(indicator in text.lower() for indicator in completion_indicators):
                    return True

        return False

    def generic_analyzer(self, transcript: List[Dict], consideration: Dict[str, Any]) -> bool:
        """Generic analyzer for considerations without specific checkers.

        Args:
            transcript: List of message dictionaries
            consideration: Consideration dictionary with question

        Returns:
            True if satisfied (fail-open default), False if potential issues detected
        """
        # Extract keywords from question
        question = consideration.get("question", "").lower()
        keywords = [
            word for word in re.findall(r"\b\w+\b", question)
            if len(word) > 3 and word not in ["were", "does", "need", "that", "this", "with"]
        ]

        if not keywords:
            return True

        # Build transcript text for searching
        transcript_text = self._build_transcript_text(transcript)

        # Check if keywords appear in transcript
        keyword_found = any(keyword in transcript_text for keyword in keywords)

        # Default to satisfied (fail-open)
        return True

    # Helper methods
    def _find_last_todo_write(self, transcript: List[Dict]) -> Dict:
        """Find last TodoWrite tool call in transcript."""
        for msg in reversed(transcript):
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "TodoWrite":
                                return block.get("input", {})
        return {}

    def _extract_tool_names(self, transcript: List[Dict]) -> set:
        """Extract all tool names used in transcript."""
        tools_used = set()
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tools_used.add(block.get("name", ""))
        return tools_used

    def _extract_code_content(self, tool_block: Dict) -> str:
        """Extract code content from Write/Edit tool block."""
        tool_input = tool_block.get("input", {})
        content_parts = []
        if "content" in tool_input:
            content_parts.append(str(tool_input["content"]))
        if "new_string" in tool_input:
            content_parts.append(str(tool_input["new_string"]))
        return " ".join(content_parts)

    def _has_anti_patterns(self, content: str, patterns: List[tuple]) -> bool:
        """Check if content has any anti-patterns."""
        for pattern, _ in patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

    def _is_successful_test_result(self, msg: Dict, transcript: List[Dict]) -> bool:
        """Check if message is a successful test result."""
        msg_data = msg["message"]
        tool_use_id = msg_data.get("tool_use_id")
        if not tool_use_id:
            return False

        # Find corresponding tool_use
        for prev_msg in transcript:
            if prev_msg.get("type") == "assistant" and "message" in prev_msg:
                content = prev_msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "tool_use" and block.get("id") == tool_use_id:
                                if block.get("name") == "Bash":
                                    command = block.get("input", {}).get("command", "")
                                    if any(pattern in command for pattern in self.TEST_COMMAND_PATTERNS):
                                        return self._check_test_output_success(msg_data)
        return False

    def _check_test_output_success(self, msg_data: Dict) -> bool:
        """Check if test output indicates success."""
        result_content = msg_data.get("content", [])
        if isinstance(result_content, list):
            for result_block in result_content:
                if isinstance(result_block, dict):
                    if result_block.get("type") == "tool_result":
                        output = str(result_block.get("content", "")).lower()
                        if "passed" in output or "ok" in output:
                            if "failed" not in output:
                                return True
        return False

    def _has_ci_keywords(self, text: str) -> bool:
        """Check if text mentions CI."""
        return any(keyword in text for keyword in ["ci", "github actions", "continuous integration"])

    def _has_passing_keywords(self, text: str) -> bool:
        """Check if text indicates CI passing."""
        return any(keyword in text for keyword in ["passing", "success", "mergeable"])

    def _has_failure_keywords(self, text: str) -> bool:
        """Check if text indicates CI failure."""
        return any(keyword in text for keyword in ["failing", "failed", "error"])

    def _extract_assistant_text(self, msg: Dict) -> str:
        """Extract text content from assistant message."""
        content = msg.get("message", {}).get("content", [])
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(str(block.get("text", "")))
            return " ".join(text_parts)
        return ""

    def _build_transcript_text(self, transcript: List[Dict]) -> str:
        """Build searchable text from transcript."""
        text_parts = []
        for msg in transcript:
            if msg.get("type") in ["user", "assistant"]:
                content = msg.get("message", {}).get("content", "")
                if isinstance(content, str):
                    text_parts.append(content.lower())
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(str(block.get("text", "")).lower())
        return " ".join(text_parts)
