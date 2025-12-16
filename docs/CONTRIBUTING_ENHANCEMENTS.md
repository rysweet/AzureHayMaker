---
title: Contributing to Enhancements
description: Quick-start guide for contributors working on Azure HayMaker enhancements
last_updated: 2025-11-30
status: active
---

# Contributing to Azure HayMaker Enhancements

Quick-start guide for picking and implementing enhancements to Azure HayMaker.

## Getting Started in 5 Minutes

### 1. Choose Your Enhancement

View the prioritized enhancement list:

```bash
# See all enhancements
cat docs/ENHANCEMENT_ROADMAP.md | grep "^#### [0-9]"

# View specific enhancement specs
cat specs/feature-specifications.md
```

**Enhancement Overview**:

| ID | Name | Priority | Effort | Status |
|---|---|---|---|---|
| 1 | SIEM Telemetry Export Pipeline | P0 | 4 weeks | Ready |
| 2 | Windows VM Security Hardening | P0 | 2 weeks | Ready |
| 3 | Multi-Tenant Resource Isolation | P1 | 10 weeks | Ready |
| 4 | Distributed Tracing | P1 | 6 weeks | Ready |
| 5 | Cost Budget Enforcement | P1 | 5 weeks | Ready |
| 6 | Agent Health Checks | P1 | 5 weeks | Ready |
| 7 | Local Development Mode | P2 | 8 weeks | Ready |
| 8 | GitHub Actions Custom Agent | P2 | 6 weeks | Ready |
| 9 | Analytics Dashboard | P2 | 10 weeks | Ready |
| 10 | Scenario Testing Framework | P2 | 8 weeks | Ready |

**First time?** Start with P0 items—they're critical and have clear requirements.

### 2. Understand the Requirements

Each enhancement has a complete specification:

```bash
# Find your enhancement in feature-specifications.md
grep -A 50 "^## Feature [0-9]:" specs/feature-specifications.md | head -80
```

**Required reading for your enhancement**:

- ✅ **Objective** - What problem it solves
- ✅ **Functional Requirements** - What it must do
- ✅ **Success Criteria** - How to know it's done
- ✅ **Implementation Scope** - What's in/out
- ✅ **Complexity & Effort** - Time estimate
- ✅ **Dependencies** - What it needs
- ✅ **Testing Strategy** - How to verify

### 3. Setup Your Workspace

```bash
# Create a feature branch
git checkout -b enhancement/feature-name

# Create a worktree for isolated work (optional)
git worktree add --detach enhancement-work enhancement/feature-name
cd enhancement-work

# Install dependencies
uv sync

# Verify your setup
uv run pytest --co -q | head -20
```

---

## Understanding the Enhancement Specs

### Location of Specifications

All enhancements defined in single file for consistency:

```
specs/feature-specifications.md
├── Feature 1: SIEM Telemetry Export Pipeline (lines 107-153)
├── Feature 2: Windows VM Security Hardening (lines 155-229)
├── Feature 3: Multi-Tenant Resource Isolation (lines 232-349)
├── Feature 4: Distributed Tracing (lines 351-498)
├── Feature 5: Cost Budget Enforcement (lines 501-674)
├── Feature 6: Agent Health Checks (lines 677-933)
├── Feature 7: Local Development Mode (lines 938-1092)
├── Feature 8: GitHub Actions Custom Agent (lines 1095-1238)
├── Feature 9: Analytics Dashboard (lines 1241-1401)
└── Feature 10: Scenario Testing Framework (lines 1404-1634)
```

### What Each Spec Contains

**Functional Requirements (FR)**:
```markdown
Example: Feature 1, FR1.1
- Load .env file from project root if present
- Use python-dotenv library
- Support comments and empty lines
- Don't override environment variables
```

**Acceptance Criteria (Testable)**:
```markdown
Example: Feature 1, Acceptance Criteria
- [ ] .env file loaded if present
- [ ] Configuration works when .env absent
- [ ] Explicitly set env vars override .env
- [ ] All 15 required + 6 optional variables supported
```

**Implementation Scope** (What to build):
```markdown
Example: Feature 1, In Scope
1. New module: src/azure_haymaker/orchestrator/dotenv_loader.py
2. Modified module: src/azure_haymaker/orchestrator/config.py
3. Files: .env.example, updated .gitignore
4. Tests: tests/unit/orchestrator/test_dotenv_loader.py
```

---

## Development Workflow

### Step 1: Create Issue (Optional but Recommended)

```bash
# Create GitHub issue for tracking
gh issue create --title "Implement Feature N: Enhancement Name" \
  --body "Working on: Feature N from ENHANCEMENT_ROADMAP.md

Specs: specs/feature-specifications.md#feature-n

Timeline: [Your estimate]

Blockers: [Any blockers]"
```

### Step 2: Review Acceptance Criteria

Copy acceptance criteria from spec into a checklist:

```bash
# For Feature 1 (.env support), acceptance criteria at line ~169
# Create a mental checklist:
- [ ] .env file in project root loaded if present
- [ ] Configuration works without .env file
- [ ] Explicitly set env vars override .env values
- [ ] All 15 required + 6 optional variables supported
- [ ] .env file with comments parsed correctly
- [ ] .env in .gitignore
- [ ] .env.example exists with documentation
- [ ] README.md documents .env usage
- [ ] All existing tests pass unchanged
- [ ] New tests achieve 100% coverage
```

### Step 3: Implement According to Scope

Follow the "Implementation Scope" section exactly:

```bash
# For Feature 1 (.env support):
# In Scope:
# 1. New module: src/azure_haymaker/orchestrator/dotenv_loader.py
# 2. Modified module: src/azure_haymaker/orchestrator/config.py
# 3. New files: .env.example, .gitignore update
# 4. New tests: tests/unit/orchestrator/test_dotenv_loader.py

# Create the new module
touch src/azure_haymaker/orchestrator/dotenv_loader.py

# Create the test
touch tests/unit/orchestrator/test_dotenv_loader.py

# Start implementation with code examples from spec
cat specs/feature-specifications.md | grep -A 30 "Code Example"
```

### Step 4: Write Tests Following Spec Strategy

Each spec includes "Testing Strategy" section:

```markdown
Feature 1 Testing Strategy (from spec):
- Unit tests for .env loading logic
- Integration tests verify priority order
- Tests verify backward compatibility
- Tests verify .env loading with comments/empty lines
```

**Example test structure**:

```python
# tests/unit/orchestrator/test_dotenv_loader.py

import pytest
import os
from pathlib import Path
from azure_haymaker.orchestrator.dotenv_loader import load_dotenv_with_priority

def test_dotenv_loads_when_present(tmp_path, monkeypatch):
    """Test .env file is loaded if present"""
    # Create temp .env file
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_VAR=test_value\n")

    # Test loading
    monkeypatch.chdir(tmp_path)
    load_dotenv_with_priority()

    assert os.getenv("TEST_VAR") == "test_value"

def test_env_vars_override_dotenv(tmp_path, monkeypatch):
    """Test explicitly set env vars override .env"""
    # Set env var explicitly
    monkeypatch.setenv("CONFIG_VAR", "env_value")

    # Create .env with different value
    env_file = tmp_path / ".env"
    env_file.write_text("CONFIG_VAR=dotenv_value\n")

    monkeypatch.chdir(tmp_path)
    load_dotenv_with_priority()

    # Env var should win
    assert os.getenv("CONFIG_VAR") == "env_value"
```

### Step 5: Run Tests and Validation

```bash
# Run tests for your feature
uv run pytest tests/unit/orchestrator/test_dotenv_loader.py -v

# Check code quality
uv run ruff check src/azure_haymaker/orchestrator/dotenv_loader.py

# Check types
uv run pyright src/azure_haymaker/orchestrator/dotenv_loader.py

# Run full test suite to verify no regressions
uv run pytest --tb=short

# Check coverage for new code
uv run pytest --cov=src/azure_haymaker/orchestrator/dotenv_loader.py
```

### Step 6: Update Documentation

**Requirement: Every enhancement must update docs**

```bash
# For Feature 1 (.env support):
# Update README.md with usage section
# Create .env.example with all variables
# Add docstrings to new functions

# Example docstring (from spec):
def load_dotenv_with_priority() -> None:
    """Load .env file if present, respecting environment variable priority.

    This function loads a .env file from the project root if it exists.
    It does NOT override environment variables that are already set,
    ensuring production deployments are unaffected.

    Priority:
    - Existing environment variables take precedence
    - .env values are only used if env var not already set
    """
```

### Step 7: Commit and Create PR

```bash
# Commit with clear message
git add .
git commit -m "feat: Implement .env configuration support

- Add dotenv_loader.py module for .env file loading
- Integrate with config.py to load .env at startup
- Respect priority: env vars > .env values
- Add comprehensive tests (100% coverage)
- Update README.md with .env usage
- Create .env.example template

Implements Feature 1 from specs/feature-specifications.md
Closes #[issue-number]"

# Create PR
gh pr create --title "feat: Implement .env configuration support" \
  --body "## Summary

Implements Feature 1: Environment Variable (.env) Configuration Support

- Adds optional .env file support for local development
- Maintains backward compatibility (all existing tests pass)
- Follows priority: env vars > .env values

## Checklist

- [x] All acceptance criteria met
- [x] Tests pass (100% coverage for new code)
- [x] Documentation updated
- [x] No breaking changes
- [x] Code reviewed for quality

## Test Results

\`\`\`
tests/unit/orchestrator/test_dotenv_loader.py: 8 passed
tests/: all passed
coverage: 98%+
\`\`\`"
```

---

## Testing Requirements

### Before Submitting PR: Required Checks

```bash
# 1. Unit tests for new code
uv run pytest tests/unit/ -v

# 2. Integration tests
uv run pytest tests/integration/ -v

# 3. Coverage check (>95% for new code)
uv run pytest --cov=src/azure_haymaker/ --cov-report=term-missing

# 4. Linting
uv run ruff check src/ tests/

# 5. Type checking
uv run pyright src/

# 6. All tests pass
uv run pytest --tb=short
```

### Test Coverage Requirements by Enhancement

| Enhancement | Min Coverage | Priority |
|---|---|---|
| Feature 1 (.env) | 100% | P0 |
| Feature 2 (Security) | 95%+ | P0 |
| Feature 3 (On-Demand API) | 90%+ | P1 |
| Feature 4 (GitOps) | 90%+ | P1 |
| Feature 5 (Tracing) | 85%+ | P1 |
| Feature 6 (Health) | 90%+ | P1 |
| Features 7-10 | 80%+ | P2 |

---

## Code Review Checklist

Reviewers will check for:

### ✅ Acceptance Criteria Met

```markdown
Feature 1 Acceptance Criteria:
- [ ] .env file in project root is loaded if present
- [ ] Configuration works when .env file absent (backward compatible)
- [ ] Explicitly set environment variables override .env values
- [ ] All 15 required + 6 optional variables supported in .env
- [ ] .env file with comments and empty lines parsed correctly
- [ ] .env is in .gitignore
- [ ] .env.example file exists with all variables documented
- [ ] README.md documents .env usage with examples
- [ ] README.md includes security warnings
- [ ] All existing tests pass unchanged
- [ ] New unit tests for dotenv_loader.py achieve 100% coverage
- [ ] Integration test verifies priority order
```

### ✅ Code Quality

- Follows project style (ruff + pyright pass)
- Clear variable/function names
- No magic numbers (use constants)
- Proper error handling
- Docstrings on public functions

### ✅ Testing

- Unit tests for all public functions
- Integration tests for cross-module interaction
- Edge cases covered (missing files, empty files, etc.)
- Coverage meets requirements

### ✅ Documentation

- README/docs updated
- Code comments for complex logic
- Examples provided
- API changes documented

---

## Resources

### Key Files

```
docs/ENHANCEMENT_ROADMAP.md
├── Executive summary
├── Enhancement portfolio (10 enhancements)
├── Implementation phases (Q1-Q4)
└── Success metrics and risks

specs/feature-specifications.md
├── Feature 1-10 detailed specs
├── Each with requirements, scope, testing, examples
└── Code examples provided

docs/CONTRIBUTING.md
└── General contribution guidelines

docs/DEPLOYMENT.md
└── How to deploy changes
```

### Quick Links

- **Enhancement Roadmap**: `docs/ENHANCEMENT_ROADMAP.md`
- **Feature Specs**: `specs/feature-specifications.md`
- **Project Architecture**: `docs/design/DESIGN_DECISIONS.md`
- **API Reference**: `docs/api.md`
- **CLI Guide**: `docs/CLI_GUIDE.md`

### Code Examples in Specs

Each feature spec includes code examples:

```bash
# Find code examples in Feature 1
grep -A 20 "Code Example" specs/feature-specifications.md | head -40

# Feature 1: dotenv_loader.py example (line ~278)
# Feature 3: HTTP endpoint example (line ~1108)
# Feature 5: CLI command example (line ~2385)
```

---

## Troubleshooting

### "All the good enhancements are taken"

Each enhancement can be broken into sub-tasks:

```bash
# Feature 1 (.env support) sub-tasks:
# 1. Core dotenv loading (easy)
# 2. Priority order integration (medium)
# 3. Documentation and examples (medium)
# 4. Security validation (.env in .gitignore) (easy)

# Feature 9 (Analytics Dashboard) sub-tasks:
# 1. Backend API endpoints (2-3 days)
# 2. WebSocket streaming (1-2 days)
# 3. React components (2-3 days)
# 4. Testing and integration (1 day)
```

Coordinate with team to pick sub-tasks.

### "I don't understand the spec"

```bash
# 1. Read the "Context" section first
# 2. Look at code examples in spec
# 3. Review success criteria (testable!)
# 4. Check "Implementation Notes"
# 5. Open issue with specific questions
```

### "Tests are failing"

```bash
# Debug step by step
uv run pytest tests/unit/test_file.py::test_name -vvs

# Check what the test expects
cat tests/unit/test_file.py | grep -A 20 "def test_name"

# Compare with spec requirements
grep -A 10 "Acceptance Criteria" specs/feature-specifications.md
```

### "PR feedback: 'needs more tests'"

```bash
# Add more edge cases
# For Feature 1:
# - .env file with special characters in values
# - .env file with very long lines
# - .env file missing final newline
# - Multiple .env files (edge case)

# For Feature 3 (API):
# - Request with 0 scenarios (error case)
# - Request with 6 scenarios (too many, error)
# - Rate limiting when at limit
# - Concurrent requests
```

---

## Getting Help

### Ask Questions

```bash
# Open GitHub Discussion
gh discussion create --title "Question: How to implement Feature X?" \
  --body "I'm working on Feature X and need clarification on..."

# Or create detailed GitHub Issue
gh issue create --title "[QUESTION] Enhancement spec clarification" \
  --body "Which feature: Feature X

Specific question:
...

What I've tried:
..."
```

### Find Similar Code

```bash
# Look for similar patterns in existing code
grep -r "async def" src/ | head -20
grep -r "Table Storage" src/ | head -20
grep -r "error handling" src/ | head -20

# Check existing test patterns
ls tests/unit/
ls tests/integration/
```

---

## Next Steps

1. **Read** the full spec for your chosen enhancement
2. **Create** feature branch: `git checkout -b enhancement/feature-name`
3. **Implement** following the scope exactly
4. **Test** thoroughly with spec's testing strategy
5. **Document** per spec requirements
6. **Submit** PR with clear description
7. **Iterate** based on review feedback

**Questions?** Open a GitHub Discussion or check the enhancement roadmap FAQ.

---

**Last Updated**: 2025-11-30
**Enhancement Phase**: 5 (Implementation)
**Current Status**: 10 enhancements ready for implementation
