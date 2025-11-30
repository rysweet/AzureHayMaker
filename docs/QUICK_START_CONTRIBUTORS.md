# Quick Start for Enhancement Contributors

**Goal**: Get you from zero to first contribution in 15 minutes.

## Prerequisites (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/rysweet/AzureHayMaker.git
cd AzureHayMaker

# 2. Install dependencies
uv sync --all-extras

# 3. Run tests to verify setup
pytest tests/unit -x
```

## Pick Your Enhancement (2 minutes)

**View available enhancements:**
- [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md) - Full strategic overview
- [Quick Reference Card](ENHANCEMENT_QUICK_REFERENCE.md) - One-page summary
- [GitHub Issues](https://github.com/rysweet/AzureHayMaker/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement) - All issues

**Priority levels:**
- **P0-Critical** (Start here!) - SIEM Export (#124), Windows VM Security (#125)
- **P1-High** - Multi-Tenant (#126), Tracing (#127), Cost Enforcement (#128), Circuit Breakers (#129)
- **P2-Medium** - Local Dev (#130), GitHub Actions (#131), Dashboard, Testing

**Choose based on:**
1. Your skillset (security, infrastructure, frontend, testing)
2. Time available (Low=1 week, Medium=2-3 weeks, High=4+ weeks)
3. Dependencies (check if any PRs need to merge first)

## Read the Spec (3 minutes)

**All specs are in** `specs/` **directory:**

```bash
# Example: Reading SIEM export spec
cat specs/SIEM_TELEMETRY_EXPORT.md

# Look for these sections:
# - Requirements (what needs to be built)
# - Scope (detailed breakdown)
# - Testing Strategy (how to verify)
# - Success Criteria (definition of done)
```

**Tip**: Specs include code examples and file locations!

## Create Your Branch (1 minute)

```bash
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feat/issue-XXX-brief-description

# Example:
git checkout -b feat/issue-124-siem-export
```

## Implement & Test (Your Time)

**Follow TDD (Test-Driven Development):**

```bash
# 1. Write failing tests first
# Example: tests/unit/test_siem_export.py

# 2. Run tests (should fail)
pytest tests/unit/test_siem_export.py -v

# 3. Implement feature
# Example: src/azure_haymaker/knowledge_worker/telemetry/exporter.py

# 4. Run tests (should pass)
pytest tests/unit/test_siem_export.py -v

# 5. E2E testing (MANDATORY)
# Test like a user would - see spec for test scenarios
```

**Code quality checks:**
```bash
# Linting
ruff check .

# Type checking
pyright

# Pre-commit hooks
pre-commit run --all-files
```

## Create Pull Request (4 minutes)

```bash
# 1. Commit your changes
git add .
git commit -m "feat: Implement SIEM telemetry export (#124)

- Add TelemetryExporter with Sentinel connector
- Implement CEF/JSON/Syslog formatters
- Add comprehensive unit tests (95% coverage)
- E2E tested with real Sentinel instance

Closes #124"

# 2. Push to your fork
git push origin feat/issue-124-siem-export

# 3. Create PR via GitHub CLI
gh pr create --title "feat: Implement SIEM Telemetry Export" \
  --body "Closes #124. See implementation spec: specs/SIEM_TELEMETRY_EXPORT.md" \
  --assignee @me
```

**PR will be automatically labeled** by GitHub Actions!

## Resources

**Documentation:**
- [Enhancement Roadmap](ENHANCEMENT_ROADMAP.md) - Strategic overview
- [Contributing Guide](CONTRIBUTING_ENHANCEMENTS.md) - Detailed workflow
- [Roadmap Status](ROADMAP_STATUS.md) - Track progress
- [Specs Directory](../specs/README.md) - All specifications

**GitHub:**
- [All Enhancement Issues](https://github.com/rysweet/AzureHayMaker/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
- [Quarterly Milestones](https://github.com/rysweet/AzureHayMaker/milestones)
- [Open Pull Requests](https://github.com/rysweet/AzureHayMaker/pulls)

**Getting Help:**
- Comment on GitHub issue
- Check spec for implementation guidance
- Review existing code patterns in `src/azure_haymaker/`

---

**Ready?** Pick an enhancement, read the spec, and start coding! 🚀
