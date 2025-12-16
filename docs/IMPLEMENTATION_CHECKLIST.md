# Enhancement Implementation Checklist

**Use this checklist when implementing any enhancement from the roadmap.**

**For**: Developers, Contributors, Engineering Team

---

## Pre-Implementation (Before Starting)

### Planning & Preparation

- [ ] **Read the implementation spec** (specs/ directory)
  - Understand requirements and scope
  - Review acceptance criteria
  - Note dependencies and prerequisites

- [ ] **Check dependencies**
  - Are any PRs blocking this? (check issue comments)
  - Are any other enhancements prerequisites?
  - Review dependency graph in `specs/ENHANCEMENT_DEPENDENCIES.md`

- [ ] **Review related code**
  - Find similar patterns in existing codebase
  - Identify files that will need modification
  - Check for existing tests to use as templates

- [ ] **Set up workspace**
  - Create feature branch: `feat/issue-XXX-brief-description`
  - Install any new dependencies
  - Verify development environment works

- [ ] **Estimate and track time**
  - Note start date in GitHub issue
  - Set up time tracking (if required)
  - Plan daily/weekly goals

---

## Implementation Phase

### Test-Driven Development (TDD)

**ALWAYS write tests first** before implementation:

- [ ] **Write failing unit tests**
  - Test happy path scenarios
  - Test error cases
  - Test edge cases
  - Run tests - should FAIL initially

- [ ] **Implement feature to make tests pass**
  - Start with simplest implementation
  - Refactor for clarity
  - Follow existing code patterns

- [ ] **Write integration tests**
  - Test interaction with real Azure services (if applicable)
  - Test interaction with other HayMaker components
  - Use fixtures and mocks appropriately

- [ ] **Write security tests** (if security-sensitive)
  - Test credential sanitization
  - Test input validation
  - Test authorization boundaries (multi-tenant)

---

### Code Quality

- [ ] **Follow Python best practices**
  - Type hints on all functions
  - Google-style docstrings
  - PEP 8 compliant (via ruff)

- [ ] **Follow HayMaker patterns**
  - Zero-BS: No TODOs, stubs, or placeholders
  - Modular design: Clear boundaries
  - Ruthless simplicity: No over-engineering

- [ ] **Run code quality checks**
  ```bash
  # Linting
  ruff check .

  # Type checking
  pyright

  # Security scanning
  bandit -r src/

  # Pre-commit hooks
  pre-commit run --all-files
  ```

- [ ] **Achieve coverage targets**
  - Unit tests: >85% coverage
  - Integration tests: Critical paths covered
  - Run: `pytest --cov=src --cov-report=term-missing`

---

### Documentation

- [ ] **Update implementation spec** (if deviations from original)
  - Document why you deviated
  - Update spec with final approach

- [ ] **Add code comments**
  - Explain WHY, not WHAT
  - Comment complex logic
  - Add references to specs or issues

- [ ] **Update API documentation** (if applicable)
  - FastAPI endpoints auto-document
  - Add usage examples
  - Document error responses

- [ ] **Update relevant guides**
  - Deployment guide (if infrastructure changes)
  - Architecture docs (if architectural changes)
  - README (if user-facing changes)

---

## Testing Phase (MANDATORY)

### E2E Testing - Test Like a User

**This is MANDATORY per user preferences** - see PROJECT.md

- [ ] **Test simple use cases**
  - Basic functionality verification
  - Happy path end-to-end
  - Document results

- [ ] **Test complex use cases**
  - Edge cases
  - Longer operations
  - Error scenarios

- [ ] **Test integration points**
  - External dependencies
  - Other HayMaker components
  - Azure services

- [ ] **Verify no regressions**
  - Existing functionality still works
  - No breaking changes (unless documented)
  - All existing tests pass

- [ ] **Document test results**
  - What was tested
  - Results (pass/fail)
  - Save for PR description

**Example for #124 (SIEM Export)**:
```bash
# E2E test: Send telemetry to real Sentinel workspace
python -c "from azure_haymaker.telemetry import TelemetryExporter; ..."

# Verify in Sentinel:
# - Events appear in Log Analytics
# - Correct schema and format
# - Latency <1 second
# - All fields populated correctly
```

---

## Review Phase

### Self-Review

- [ ] **Review your own code**
  - Read every file changed
  - Check for debugging code left behind
  - Verify no credentials hardcoded
  - Check for TODO comments (should be none)

- [ ] **Run full test suite**
  ```bash
  pytest
  ```

- [ ] **Check philosophy compliance**
  - No stubs or placeholders?
  - No swallowed exceptions?
  - No unimplemented functions?
  - All error paths handled?

---

### Security Review (Self)

- [ ] **No secrets in code**
  ```bash
  pre-commit run detect-secrets --all-files
  ```

- [ ] **Credentials properly managed**
  - Azure credentials from environment or Key Vault
  - No plaintext passwords
  - No API keys in code

- [ ] **Input validation**
  - All user input validated
  - SQL injection prevented (if applicable)
  - Path traversal prevented

- [ ] **Logging sanitization**
  - No credentials logged
  - No sensitive data in logs
  - Audit trail complete

---

## Pull Request Phase

### Create PR

- [ ] **Use PR template** (.github/PULL_REQUEST_TEMPLATE.md)
  - Fill out all sections
  - Link to enhancement issue (Closes #XXX)
  - Include E2E test results

- [ ] **Write clear PR description**
  - What changed and why
  - How it was tested
  - Any breaking changes
  - Screenshots (if UI)

- [ ] **Add appropriate labels**
  - Will be auto-labeled by GitHub Action
  - Verify labels are correct

- [ ] **Request reviewers**
  - Tag relevant team members
  - Request security review if needed

---

### Respond to Feedback

- [ ] **Address all review comments**
  - Implement requested changes
  - Explain if you disagree (politely)
  - Mark conversations as resolved when done

- [ ] **Re-run tests after changes**
  - All tests still passing
  - No new regressions introduced

- [ ] **Update PR**
  - Push additional commits
  - Respond to reviewers

---

## Merge & Deploy Phase

### Before Merge

- [ ] **All CI checks passing**
  - Tests: ✅
  - Linting: ✅
  - Type checking: ✅
  - Security scanning: ✅

- [ ] **All review comments addressed**
  - No unresolved conversations
  - Approvals from required reviewers

- [ ] **Rebase if needed**
  - Resolve merge conflicts
  - Ensure clean git history

---

### After Merge

- [ ] **Update Roadmap Status**
  - Mark enhancement as Complete ✅
  - Update docs/ROADMAP_STATUS.md

- [ ] **Update OKRs**
  - Mark relevant Key Results as achieved
  - Calculate OKR completion percentage

- [ ] **Measure actual results**
  - Compare actual effort to estimated
  - Track actual costs vs. planned (BUDGET_TRACKING_TEMPLATE.md)
  - Begin measuring ROI (if quantifiable)

- [ ] **Deploy to production**
  - Follow deployment guide
  - Monitor for issues
  - Verify success metrics

- [ ] **Document learnings**
  - Add to DISCOVERIES.md if non-obvious solutions
  - Update PATTERNS.md if reusable patterns emerge
  - Share with team

- [ ] **Celebrate!**
  - Update CHANGELOG.md with achievement
  - Share in team communication
  - Thank reviewers and contributors

---

## Common Mistakes to Avoid

### ❌ DON'T
- ❌ Skip E2E testing ("unit tests are enough") - MANDATORY requirement
- ❌ Leave TODOs in production code - violates Zero-BS principle
- ❌ Skip security review for "low-risk" changes - all changes need review
- ❌ Hardcode configuration - use environment variables or config files
- ❌ Swallow exceptions without handling - explicit error handling required
- ❌ Merge without addressing review comments - disrespectful to reviewers
- ❌ Skip documentation updates - code without docs is incomplete

### ✅ DO
- ✅ Write tests before code (TDD)
- ✅ Test like a user would (E2E from outside-in)
- ✅ Follow existing patterns in codebase
- ✅ Ask questions early (comment on issue)
- ✅ Commit frequently with clear messages
- ✅ Run pre-commit hooks before pushing
- ✅ Document assumptions and trade-offs

---

## Time Estimates by Phase

**Typical timeline for Medium complexity enhancement** (like #124):

| Phase | Time | % of Total |
|-------|------|------------|
| Planning & Preparation | 0.5 days | 5% |
| Writing Tests | 2 days | 20% |
| Implementation | 4 days | 40% |
| E2E Testing | 1.5 days | 15% |
| Documentation | 1 day | 10% |
| Review & Revisions | 1 day | 10% |
| **Total** | **10 days** | **100%** |

**Adjust for complexity**:
- Low (like #125): ~5 days (1 week)
- Medium (like #124): ~10 days (2 weeks)
- High (like #126): ~25-30 days (5-6 weeks)

---

## Quality Gates

**Must pass ALL gates before considering "done"**:

### Gate 1: Code Complete
- [ ] All scope items implemented
- [ ] No TODOs or placeholders
- [ ] All tests passing locally

### Gate 2: Quality Verified
- [ ] Code review completed
- [ ] Security review passed (if applicable)
- [ ] Performance acceptable (if applicable)
- [ ] Documentation complete

### Gate 3: Production Ready
- [ ] E2E testing completed successfully
- [ ] CI/CD passing
- [ ] Deployment tested in staging
- [ ] Monitoring configured

### Gate 4: Value Delivered
- [ ] Deployed to production
- [ ] Success metrics being collected
- [ ] Customer validation (if applicable)
- [ ] OKR Key Results achieved

**Only after Gate 4**: Mark enhancement as Complete ✅

---

## Related Documentation

- [Contributing to Enhancements](CONTRIBUTING_ENHANCEMENTS.md) - Detailed workflow
- [Quick Start Guide](QUICK_START_CONTRIBUTORS.md) - 15-minute onboarding
- [Enhancement FAQ](ENHANCEMENT_FAQ.md) - Common questions
- [Implementation Specs](../specs/README.md) - All technical specifications

---

**Print this checklist and keep it visible** while working on enhancements. Check off items as you complete them!
