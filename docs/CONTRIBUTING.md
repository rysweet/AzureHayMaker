# Contributing to Azure HayMaker

**Thank you for your interest in contributing!**

---

## Quick Start for Contributors

### 1. Review Existing Work
```bash
# See what's been delivered
cat START_HERE.md
cat MASTER_TREASURE_MAP.md

# Review code
gh pr view 11

# Check issues
gh issue list
```

### 2. Setup Development Environment
```bash
# Clone repo
git clone https://github.com/rysweet/AzureHayMaker.git
cd AzureHayMaker

# Install dependencies
uv sync

# Configure .env
cp .env.example .env
# Edit .env with your Azure credentials
```

### 3. Run Tests
```bash
uv run pytest
```

---

## Areas for Contribution

### High Priority
- **VM Deployment** (Issue #13) - 3 hours
- **Cost Cleanup** (Issue #14) - URGENT, 5 min
- **Test Coverage** - Increase from 99% to 100%

### Documentation
- Add more CLI examples
- Create video tutorials
- Translate to other languages

### Features
- Additional Azure scenarios
- Enhanced monitoring
- Performance optimizations

---

## Development Workflow

1. **Create Issue** - Describe what you want to add
2. **Branch** - `git checkout -b feat/your-feature`
3. **Implement** - Follow existing patterns
4. **Test** - Ensure 80%+ coverage
5. **Document** - Update relevant docs
6. **PR** - Submit for review

---

## Code Standards

- **Python**: 3.11+
- **Style**: Follow existing code (ruff + pyright)
- **Tests**: 80%+ coverage required
- **Docs**: Update README and relevant guides
- **Commits**: Descriptive messages

---

## Testing Requirements

### Before Submitting PR
```bash
# Run all tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run pyright
```

### Test Coverage
- Unit tests: 60%+
- Integration tests: 30%+
- E2E tests: 10%+

---

## Documentation Standards

- **Clear**: Simple language
- **Complete**: Cover all scenarios
- **Tested**: Verify commands work
- **Examples**: Show real usage

---

## Review Process

1. **Automated Checks**: Must pass CI/CD
2. **Code Review**: Maintainer approval required
3. **Security Review**: For security-related changes
4. **Documentation**: Must be updated

**Target**: 7-10 day turnaround

---

## Getting Help

- **Questions**: Create GitHub Discussion
- **Bugs**: Use bug report template
- **Features**: Use feature request template
- **Urgent**: Tag with `help-wanted`

---

## Recognition

Contributors will be:
- Listed in CHANGELOG.md
- Mentioned in release notes
- Added to contributors list

---

## Code of Conduct

- Be respectful
- Be collaborative
- Focus on code quality
- Help others

---

**Thank you for contributing to Azure HayMaker!** 🏴‍☠️
