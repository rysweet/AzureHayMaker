#!/usr/bin/env python3
"""
Power-Steering Mode: Autonomous session completion verification.

This file now serves as a backward-compatibility shim, importing from
the refactored modular structure under power_steering/ package.

The original 2752-line monolith has been refactored into:
- power_steering/checker.py (~450 lines) - Main interface
- power_steering/strategies/session_detector.py (~200 lines) - Session type detection
- power_steering/strategies/feature_checker.py (~300 lines) - Checker methods
- power_steering/templates/checklist_template.py (~70 lines) - Output templates
- power_steering/models.py (~80 lines) - Data models

Philosophy:
- Ruthlessly Simple: Single-purpose modules with clear contracts
- Fail-Open: Never block users due to bugs - always allow stop on errors
- Zero-BS: No stubs, every function works or doesn't exist
- Modular: Self-contained bricks that plug together
"""

import sys
from pathlib import Path

# Import all public interfaces from the modular structure
from power_steering import (
    PowerSteeringChecker,
    PowerSteeringResult,
    check_session,
)

# Re-export models for backward compatibility
from power_steering.models import (
    CheckerResult,
    ConsiderationAnalysis,
    PowerSteeringRedirect,
)

# Export all public symbols
__all__ = [
    "PowerSteeringChecker",
    "PowerSteeringResult",
    "CheckerResult",
    "ConsiderationAnalysis",
    "PowerSteeringRedirect",
    "check_session",
]


if __name__ == "__main__":
    # For testing: Allow running directly
    import json

    if len(sys.argv) < 3:
        print("Usage: power_steering_checker.py <transcript_path> <session_id>")
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    session_id = sys.argv[2]

    result = check_session(transcript_path, session_id)
    print(json.dumps({"decision": result.decision, "reasons": result.reasons}, indent=2))
