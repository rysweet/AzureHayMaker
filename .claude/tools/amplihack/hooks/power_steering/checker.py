#!/usr/bin/env python3
"""
Main power-steering checker interface.

Orchestrates session analysis by coordinating strategies and generating results.
"""

import json
import os
import signal
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .models import (
    CheckerResult,
    ConsiderationAnalysis,
    PowerSteeringRedirect,
    PowerSteeringResult,
)
from .strategies import FeatureChecker, SessionDetector
from .templates import ChecklistTemplate

# Try to import Claude SDK integration
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from claude_power_steering import analyze_consideration_sync

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

# Security: Maximum transcript size to prevent memory exhaustion
MAX_TRANSCRIPT_LINES = 50000  # Limit transcript to 50K lines (~10-20MB typical)

# Timeout for individual checker execution (seconds)
CHECKER_TIMEOUT = 10


@contextmanager
def _timeout(seconds: int):
    """Context manager for operation timeout.

    Args:
        seconds: Timeout in seconds

    Raises:
        TimeoutError: If operation exceeds timeout
    """

    def handler(signum, frame):
        raise TimeoutError("Operation timed out")

    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


class PowerSteeringChecker:
    """Analyzes session completeness using consideration checkers.

    Orchestrates the entire power-steering process:
    - Configuration management
    - Session type detection
    - Consideration checking
    - Result generation
    """

    # Phase 1 fallback: Hardcoded considerations (top 5 critical)
    PHASE1_CONSIDERATIONS = [
        {
            "id": "todos_complete",
            "category": "Session Completion & Progress",
            "question": "Were all TODO items completed?",
            "severity": "blocker",
            "checker": "check_todos_complete",
        },
        {
            "id": "dev_workflow_complete",
            "category": "Workflow Process Adherence",
            "question": "Was full DEFAULT_WORKFLOW followed?",
            "severity": "blocker",
            "checker": "check_dev_workflow_complete",
        },
        {
            "id": "philosophy_compliance",
            "category": "Code Quality & Philosophy",
            "question": "PHILOSOPHY adherence (zero-BS)?",
            "severity": "blocker",
            "checker": "check_philosophy_compliance",
        },
        {
            "id": "local_testing",
            "category": "Testing & Local Validation",
            "question": "Sure agent tested locally?",
            "severity": "blocker",
            "checker": "check_local_testing",
        },
        {
            "id": "ci_status",
            "category": "CI/CD & Mergeability",
            "question": "CI passing/mergeable?",
            "severity": "blocker",
            "checker": "check_ci_status",
        },
    ]

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize power-steering checker.

        Args:
            project_root: Project root directory (auto-detected if None)
        """
        if project_root is None:
            project_root = self._detect_project_root()

        self.project_root = project_root
        self.runtime_dir = project_root / ".claude" / "runtime" / "power-steering"
        self.config_path = (
            project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        self.considerations_path = (
            project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        )

        # Ensure runtime directory exists
        try:
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # Fail-open

        # Load configuration and considerations
        self.config = self._load_config()
        self.considerations = self._load_considerations_yaml()

        # Initialize strategies
        self.session_detector = SessionDetector()
        self.feature_checker = FeatureChecker()
        self.template = ChecklistTemplate()

    def check(
        self,
        transcript_path: Path,
        session_id: str,
        progress_callback: Optional[callable] = None,
    ) -> PowerSteeringResult:
        """Main entry point - analyze transcript and make decision.

        Args:
            transcript_path: Path to session transcript JSONL file
            session_id: Unique session identifier
            progress_callback: Optional callback for progress events

        Returns:
            PowerSteeringResult with decision and prompt/summary
        """
        try:
            self._emit_progress(progress_callback, "start", "Starting power-steering analysis...")

            # Check if disabled or already ran
            if self._is_disabled():
                return PowerSteeringResult(
                    decision="approve", reasons=["disabled"], continuation_prompt=None, summary=None
                )

            if self._already_ran(session_id):
                return PowerSteeringResult(
                    decision="approve", reasons=["already_ran"], continuation_prompt=None, summary=None
                )

            # Load transcript and detect session type
            transcript = self._load_transcript(transcript_path)
            session_type = self.session_detector.detect_session_type(transcript)
            self._log(f"Session classified as: {session_type}", "INFO")
            self._emit_progress(
                progress_callback,
                "session_type",
                f"Session type: {session_type}",
                {"session_type": session_type},
            )

            # Backward compatibility: Check Q&A session
            if self._is_qa_session(transcript):
                return PowerSteeringResult(
                    decision="approve", reasons=["qa_session"], continuation_prompt=None, summary=None
                )

            # Analyze considerations
            analysis = self._analyze_considerations(
                transcript, session_id, session_type, progress_callback
            )

            # Make decision
            if analysis.has_blockers:
                prompt = self.template.generate_continuation_prompt(analysis)
                failed_ids = [r.consideration_id for r in analysis.failed_blockers]
                self._save_redirect(
                    session_id=session_id,
                    failed_considerations=failed_ids,
                    continuation_prompt=prompt,
                    work_summary=None,
                )
                return PowerSteeringResult(
                    decision="block",
                    reasons=failed_ids,
                    continuation_prompt=prompt,
                    summary=None,
                )

            # Generate summary and mark complete
            summary = self.template.generate_summary(analysis, session_id, self.considerations)
            self._mark_complete(session_id)
            self._write_summary(session_id, summary)

            self._emit_progress(
                progress_callback,
                "complete",
                "Power-steering analysis complete - all checks passed",
            )

            return PowerSteeringResult(
                decision="approve",
                reasons=["all_considerations_satisfied"],
                continuation_prompt=None,
                summary=summary,
            )

        except Exception as e:
            # Fail-open: On any error, approve and log
            self._log(f"Power-steering error (fail-open): {e}", "ERROR")
            return PowerSteeringResult(
                decision="approve",
                reasons=["error_failopen"],
                continuation_prompt=None,
                summary=None,
            )

    def detect_session_type(self, transcript: List[Dict]) -> str:
        """Detect session type (delegates to SessionDetector).

        Args:
            transcript: List of message dictionaries

        Returns:
            Session type string
        """
        return self.session_detector.detect_session_type(transcript)

    def get_applicable_considerations(self, session_type: str) -> List[Dict[str, Any]]:
        """Get considerations applicable to a specific session type.

        Args:
            session_type: Session type

        Returns:
            List of applicable consideration dictionaries
        """
        applicable = []
        for consideration in self.considerations:
            applicable_types = consideration.get("applicable_session_types", [])
            if not applicable_types:
                # Phase 1 considerations: only apply to DEVELOPMENT
                if session_type == "DEVELOPMENT":
                    applicable.append(consideration)
            elif session_type in applicable_types or "*" in applicable_types:
                applicable.append(consideration)
        return applicable

    def _analyze_considerations(
        self,
        transcript: List[Dict],
        session_id: str,
        session_type: str = None,
        progress_callback: Optional[callable] = None,
    ) -> ConsiderationAnalysis:
        """Analyze transcript against all enabled considerations.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier
            session_type: Session type for selective consideration application
            progress_callback: Optional callback for progress events

        Returns:
            ConsiderationAnalysis with results
        """
        analysis = ConsiderationAnalysis()

        if session_type is None:
            session_type = self.session_detector.detect_session_type(transcript)

        applicable_considerations = self.get_applicable_considerations(session_type)
        categories_seen = set()

        for consideration in applicable_considerations:
            if not consideration.get("enabled", True):
                continue

            if not self.config.get("checkers_enabled", {}).get(consideration["id"], True):
                continue

            # Emit progress events
            category = consideration.get("category", "Unknown")
            if category not in categories_seen:
                categories_seen.add(category)
                self._emit_progress(
                    progress_callback, "category", f"Checking {category}", {"category": category}
                )

            self._emit_progress(
                progress_callback,
                "consideration",
                f"Checking: {consideration['question']}",
                {"consideration_id": consideration["id"], "question": consideration["question"]},
            )

            # Run checker with timeout
            try:
                with _timeout(CHECKER_TIMEOUT):
                    satisfied = self._run_checker(consideration, transcript, session_id)
                result = CheckerResult(
                    consideration_id=consideration["id"],
                    satisfied=satisfied,
                    reason=consideration["question"],
                    severity=consideration["severity"],
                )
                analysis.add_result(result)
            except TimeoutError:
                self._log(f"Checker timed out ({CHECKER_TIMEOUT}s)", "WARNING")
                result = CheckerResult(
                    consideration_id=consideration["id"],
                    satisfied=True,  # Fail-open
                    reason=f"Timeout after {CHECKER_TIMEOUT}s",
                    severity=consideration["severity"],
                )
                analysis.add_result(result)
            except Exception as e:
                self._log(f"Checker failed: {e}", "ERROR")
                result = CheckerResult(
                    consideration_id=consideration["id"],
                    satisfied=True,  # Fail-open
                    reason=f"Error: {e}",
                    severity=consideration["severity"],
                )
                analysis.add_result(result)

        return analysis

    def _run_checker(
        self, consideration: Dict[str, Any], transcript: List[Dict], session_id: str
    ) -> bool:
        """Run checker for a consideration.

        Args:
            consideration: Consideration dictionary
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if satisfied, False otherwise
        """
        checker_name = consideration["checker"]

        # Try SDK first if available
        if SDK_AVAILABLE and checker_name.startswith("check_"):
            try:
                return analyze_consideration_sync(
                    conversation=transcript,
                    consideration=consideration,
                    project_root=self.project_root,
                )
            except Exception as e:
                self._log(f"SDK analysis failed for '{consideration['id']}': {e}", "WARNING")

        # Fall back to heuristic checker
        if checker_name == "generic":
            return self.feature_checker.generic_analyzer(transcript, consideration)

        checker_method = getattr(self.feature_checker, checker_name, None)
        if checker_method is None:
            self._log(f"Checker not found: {checker_name}, using generic", "WARNING")
            return self.feature_checker.generic_analyzer(transcript, consideration)

        return checker_method(transcript)

    # Configuration and state management
    def _detect_project_root(self) -> Path:
        """Auto-detect project root by finding .claude marker."""
        current = Path(__file__).resolve().parent
        for _ in range(10):
            if (current / ".claude").exists():
                return current
            if current == current.parent:
                break
            current = current.parent
        raise ValueError("Could not find project root with .claude marker")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file with defaults."""
        defaults = {
            "enabled": True,
            "version": "1.0.0",
            "phase": 1,
            "checkers_enabled": {
                "todos_complete": True,
                "dev_workflow_complete": True,
                "philosophy_compliance": True,
                "local_testing": True,
                "ci_status": True,
            },
        }

        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    user_config = json.load(f)
                    if self._validate_config_integrity(user_config):
                        defaults.update(user_config)
                    else:
                        self._log("Config integrity check failed, using defaults", "WARNING")
        except (OSError, json.JSONDecodeError) as e:
            self._log(f"Config load error ({e}), using defaults", "WARNING")

        return defaults

    def _validate_config_integrity(self, config: Dict) -> bool:
        """Validate configuration integrity."""
        if "enabled" not in config or not isinstance(config["enabled"], bool):
            return False
        if "phase" in config and not isinstance(config["phase"], int):
            return False
        if "checkers_enabled" in config:
            if not isinstance(config["checkers_enabled"], dict):
                return False
            if not all(isinstance(v, bool) for v in config["checkers_enabled"].values()):
                return False
        return True

    def _load_considerations_yaml(self) -> List[Dict[str, Any]]:
        """Load considerations from YAML file with fallback to Phase 1."""
        try:
            if not self.considerations_path.exists():
                script_dir = Path(__file__).parent.parent
                fallback_yaml = script_dir / "considerations.yaml"
                if fallback_yaml.exists():
                    self._log(f"Using fallback considerations from {fallback_yaml}", "INFO")
                    with open(fallback_yaml) as f:
                        yaml_data = yaml.safe_load(f)
                else:
                    self._log("Considerations YAML not found, using Phase 1 fallback", "WARNING")
                    return self.PHASE1_CONSIDERATIONS
            else:
                with open(self.considerations_path) as f:
                    yaml_data = yaml.safe_load(f)

            if not isinstance(yaml_data, list):
                self._log("Invalid YAML structure, using Phase 1 fallback", "ERROR")
                return self.PHASE1_CONSIDERATIONS

            valid_considerations = [
                item for item in yaml_data if self._validate_consideration_schema(item)
            ]

            if not valid_considerations:
                self._log("No valid considerations in YAML, using Phase 1 fallback", "ERROR")
                return self.PHASE1_CONSIDERATIONS

            self._log(f"Loaded {len(valid_considerations)} considerations from YAML", "INFO")
            return valid_considerations

        except (OSError, yaml.YAMLError) as e:
            self._log(f"Error loading YAML ({e}), using Phase 1 fallback", "ERROR")
            return self.PHASE1_CONSIDERATIONS

    def _validate_consideration_schema(self, consideration: Any) -> bool:
        """Validate consideration has required fields."""
        if not isinstance(consideration, dict):
            return False
        required_fields = ["id", "category", "question", "severity", "checker", "enabled"]
        if not all(field in consideration for field in required_fields):
            return False
        if consideration["severity"] not in ["blocker", "warning"]:
            return False
        if not isinstance(consideration["enabled"], bool):
            return False
        if "applicable_session_types" in consideration:
            if not isinstance(consideration["applicable_session_types"], list):
                return False
        return True

    def _is_disabled(self) -> bool:
        """Check if power-steering is disabled."""
        disabled_file = self.runtime_dir / ".disabled"
        if disabled_file.exists():
            return True
        if os.getenv("AMPLIHACK_SKIP_POWER_STEERING"):
            return True
        if not self.config.get("enabled", False):
            return True
        return False

    def _already_ran(self, session_id: str) -> bool:
        """Check if power-steering already ran for this session."""
        semaphore = self.runtime_dir / f".{session_id}_completed"
        return semaphore.exists()

    def _mark_complete(self, session_id: str) -> None:
        """Create semaphore to prevent re-running."""
        try:
            semaphore = self.runtime_dir / f".{session_id}_completed"
            semaphore.parent.mkdir(parents=True, exist_ok=True)
            semaphore.touch()
            semaphore.chmod(0o600)
        except OSError:
            pass  # Fail-open

    def _load_transcript(self, transcript_path: Path) -> List[Dict]:
        """Load transcript from JSONL file with size limits."""
        if not self._validate_path(transcript_path, self.project_root):
            raise ValueError(
                f"Transcript path {transcript_path} is outside project root {self.project_root}"
            )

        messages = []
        truncated = False

        with open(transcript_path) as f:
            for line_num, line in enumerate(f, 1):
                if line_num > MAX_TRANSCRIPT_LINES:
                    truncated = True
                    break
                line = line.strip()
                if not line:
                    continue
                messages.append(json.loads(line))

        if truncated:
            self._log(
                f"Transcript truncated at {MAX_TRANSCRIPT_LINES} lines (original: {line_num})",
                "WARNING",
            )

        return messages

    def _validate_path(self, path: Path, allowed_parent: Path) -> bool:
        """Validate path is safe to read."""
        import tempfile

        try:
            path_resolved = path.resolve()
            parent_resolved = allowed_parent.resolve()

            # Check if within project root
            try:
                path_resolved.relative_to(parent_resolved)
                return True
            except ValueError:
                pass

            # Check if within user home
            try:
                home = Path.home().resolve()
                path_resolved.relative_to(home)
                return True
            except ValueError:
                pass

            # Check if in temp directories
            temp_dirs = [Path("/tmp"), Path("/var/tmp"), Path(tempfile.gettempdir())]
            for temp_dir in temp_dirs:
                try:
                    path_resolved.relative_to(temp_dir.resolve())
                    return True
                except ValueError:
                    continue

            return False

        except (OSError, RuntimeError):
            return False

    def _is_qa_session(self, transcript: List[Dict]) -> bool:
        """Detect if session is interactive Q&A (backward compatibility)."""
        tool_uses = sum(
            1
            for msg in transcript
            if msg.get("type") == "assistant"
            for block in msg.get("message", {}).get("content", [])
            if isinstance(block, dict)
            and (block.get("type") == "tool_use" or "name" in block)
        )

        if tool_uses >= 2:
            return False

        if tool_uses == 0:
            user_messages = [m for m in transcript if m.get("type") == "user"]
            if len(user_messages) == 0:
                return True
            questions = sum(
                1 for m in user_messages if "?" in str(m.get("message", {}).get("content", ""))
            )
            if questions / len(user_messages) > 0.5:
                return True

        if len(transcript) < 5 and tool_uses < 2:
            return True

        return False

    def _save_redirect(
        self,
        session_id: str,
        failed_considerations: List[str],
        continuation_prompt: str,
        work_summary: Optional[str] = None,
    ) -> None:
        """Save a redirect record to persistent storage."""
        try:
            existing = self._load_redirects(session_id)
            redirect_number = len(existing) + 1

            redirect = PowerSteeringRedirect(
                redirect_number=redirect_number,
                timestamp=datetime.now().isoformat(),
                failed_considerations=failed_considerations,
                continuation_prompt=continuation_prompt,
                work_summary=work_summary,
            )

            redirects_file = self._get_redirect_file(session_id)
            redirects_file.parent.mkdir(parents=True, exist_ok=True)

            redirect_dict = {
                "redirect_number": redirect.redirect_number,
                "timestamp": redirect.timestamp,
                "failed_considerations": redirect.failed_considerations,
                "continuation_prompt": redirect.continuation_prompt,
                "work_summary": redirect.work_summary,
            }

            with open(redirects_file, "a") as f:
                f.write(json.dumps(redirect_dict) + "\n")

            if redirect_number == 1:
                redirects_file.chmod(0o600)

            self._log(f"Saved redirect #{redirect_number} for session {session_id}", "INFO")

        except OSError as e:
            self._log(f"Failed to save redirect: {e}", "ERROR")

    def _get_redirect_file(self, session_id: str) -> Path:
        """Get path to redirects file for a session."""
        session_dir = self.runtime_dir / session_id
        return session_dir / "redirects.jsonl"

    def _load_redirects(self, session_id: str) -> List[PowerSteeringRedirect]:
        """Load redirect history for a session."""
        redirects_file = self._get_redirect_file(session_id)
        if not redirects_file.exists():
            return []

        redirects = []
        try:
            with open(redirects_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        redirect = PowerSteeringRedirect(
                            redirect_number=data["redirect_number"],
                            timestamp=data["timestamp"],
                            failed_considerations=data["failed_considerations"],
                            continuation_prompt=data["continuation_prompt"],
                            work_summary=data.get("work_summary"),
                        )
                        redirects.append(redirect)
                    except (json.JSONDecodeError, KeyError) as e:
                        self._log(f"Skipping malformed redirect entry: {e}", "WARNING")
                        continue
        except OSError as e:
            self._log(f"Error loading redirects: {e}", "WARNING")
            return []

        return redirects

    def _write_summary(self, session_id: str, summary: str) -> None:
        """Write summary to file."""
        try:
            summary_dir = self.runtime_dir / session_id
            summary_dir.mkdir(parents=True, exist_ok=True)
            summary_path = summary_dir / "summary.md"
            summary_path.write_text(summary)
            summary_path.chmod(0o644)
        except OSError:
            pass  # Fail-open

    def _emit_progress(
        self,
        progress_callback: Optional[callable],
        event_type: str,
        message: str,
        details: Optional[Dict] = None,
    ) -> None:
        """Emit progress event to callback if provided."""
        if progress_callback is None:
            return
        try:
            progress_callback(event_type, message, details)
        except Exception as e:
            self._log(f"Progress callback error: {e}", "WARNING")

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log message to power-steering log file."""
        try:
            log_file = self.runtime_dir / "power_steering.log"
            timestamp = datetime.now().isoformat()
            is_new = not log_file.exists()

            with open(log_file, "a") as f:
                f.write(f"[{timestamp}] {level}: {message}\n")

            if is_new:
                log_file.chmod(0o600)
        except OSError:
            pass  # Fail silently

    # ========================================================================
    # Backward Compatibility Methods (for tests)
    # ========================================================================

    def _check_todos_complete(self, transcript: List[Dict], session_id: str) -> bool:
        """Backward compatibility wrapper for check_todos_complete."""
        return self.feature_checker.check_todos_complete(transcript)

    def _check_dev_workflow_complete(self, transcript: List[Dict], session_id: str) -> bool:
        """Backward compatibility wrapper for check_dev_workflow_complete."""
        return self.feature_checker.check_dev_workflow_complete(transcript)

    def _check_philosophy_compliance(self, transcript: List[Dict], session_id: str) -> bool:
        """Backward compatibility wrapper for check_philosophy_compliance."""
        return self.feature_checker.check_philosophy_compliance(transcript)

    def _check_local_testing(self, transcript: List[Dict], session_id: str) -> bool:
        """Backward compatibility wrapper for check_local_testing."""
        return self.feature_checker.check_local_testing(transcript)

    def _check_ci_status(self, transcript: List[Dict], session_id: str) -> bool:
        """Backward compatibility wrapper for check_ci_status."""
        return self.feature_checker.check_ci_status(transcript)

    def _generate_continuation_prompt(self, analysis: ConsiderationAnalysis) -> str:
        """Backward compatibility wrapper for generate_continuation_prompt."""
        return self.template.generate_continuation_prompt(analysis)

    def _generate_summary(
        self, transcript: List[Dict], analysis: ConsiderationAnalysis, session_id: str
    ) -> str:
        """Backward compatibility wrapper for generate_summary."""
        return self.template.generate_summary(analysis, session_id, self.considerations)


def check_session(
    transcript_path: Path, session_id: str, project_root: Optional[Path] = None
) -> PowerSteeringResult:
    """Convenience function to check session completeness.

    Args:
        transcript_path: Path to transcript JSONL file
        session_id: Session identifier
        project_root: Project root (auto-detected if None)

    Returns:
        PowerSteeringResult with decision
    """
    checker = PowerSteeringChecker(project_root)
    return checker.check(transcript_path, session_id)
