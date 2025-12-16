# Pull Request

## Related Issue
<!-- Link to the GitHub issue this PR addresses -->
Closes #XXX

## Summary
<!-- Brief description of what changed and why (2-3 sentences) -->

## Type of Change
<!-- Check all that apply -->
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Enhancement (improvement to existing functionality)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Security fix

## Changes Made
<!-- Detailed list of changes -->
1. Change 1: Description
2. Change 2: Description
3. Change 3: Description

## Testing Completed
<!-- MANDATORY: Describe how you tested these changes -->

### Unit Tests
- [ ] All unit tests passing
- [ ] New tests added for new functionality
- [ ] Coverage: XX%

### Integration Tests
- [ ] Integration tests passing
- [ ] Tested with real Azure resources (if applicable)

### E2E Testing (MANDATORY)
<!-- Test like a user would, outside-in (not just unit tests) -->
- [ ] Tested user workflow end-to-end
- [ ] Verified in realistic conditions
- [ ] Documented test results below

**E2E Test Results:**
```
<!-- Paste test output or describe what you tested -->
```

### Security Testing (if applicable)
- [ ] Credential sanitization verified
- [ ] No hardcoded secrets
- [ ] Input validation tested
- [ ] Security scan passed

## Breaking Changes
<!-- If breaking changes, describe the impact and migration path -->
N/A or describe here

## Documentation
<!-- Check all that apply -->
- [ ] Implementation spec created/updated
- [ ] API documentation updated
- [ ] README updated
- [ ] Architecture documentation updated
- [ ] Code comments added where needed

## Screenshots
<!-- If UI changes, add screenshots -->

## Checklist
<!-- Ensure all items are checked before requesting review -->
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code where needed (especially complex logic)
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I have completed mandatory E2E testing
- [ ] I have checked for security vulnerabilities
- [ ] I have verified no credentials are exposed
- [ ] Any dependent changes have been merged and published

## Philosophy Compliance
<!-- Azure HayMaker follows the Zero-BS principle -->
- [ ] No TODOs, stubs, or placeholders in production code
- [ ] No swallowed exceptions without proper handling
- [ ] All error paths explicitly handled
- [ ] No commented-out code
- [ ] Ruthless simplicity maintained

## Review Focus
<!-- What should reviewers focus on? -->
1. Area 1: Specific concern or question
2. Area 2: Specific concern or question

---

**For Reviewers:**
- Review against acceptance criteria from related issue
- Verify E2E test results
- Check security implications
- Ensure philosophy compliance (Zero-BS, ruthless simplicity)
- Validate test coverage is adequate
