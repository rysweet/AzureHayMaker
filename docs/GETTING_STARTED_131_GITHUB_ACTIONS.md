# Getting Started: GitHub Actions CI/CD Pipeline (Issue #131)

**Your complete guide to implementing Issue #131**

**Priority**: P2-Medium | **Effort**: 2.5 weeks | **ROI**: 180%

---

## What You're Building

Build comprehensive GitHub Actions workflows for automated testing, building, and deploying with real-time status checks and PR integration.

**Why It Matters**: Manual testing and deployment is slow and error-prone. Automate the entire pipeline.

**Business Value**: Reduces deployment time from hours to 15 minutes, catches bugs before PR merge, enables confident continuous deployment.

---

## Before You Start (15 minutes)

### 1. Understand GitHub Actions

**Resources**:
- GitHub Actions Docs: https://docs.github.com/en/actions
- Workflows: https://docs.github.com/en/actions/workflow-syntax-for-github-actions

### 2. Check Current Workflows

```bash
ls -la .github/workflows/
cat .github/workflows/*.yml
```

### 3. Understand Project Structure

```bash
# See what needs to be tested/built
ls -la src/
find . -name "pytest.ini" -o -name "setup.py" -o -name "pyproject.toml" | head -5
```

---

## Phase 1: Create Workflow Structure (Days 1-2, ~8 hours)

### Create Branch

```bash
git checkout main
git pull origin main
git checkout -b feat/issue-131-github-actions
```

### Create Workflows Directory

```bash
mkdir -p .github/workflows
touch .github/workflows/test.yml
touch .github/workflows/build.yml
touch .github/workflows/deploy.yml
touch .github/workflows/security.yml
```

---

## Phase 2: Create Test Workflow (Days 3-4, ~12 hours)

### Create Test Workflow

**File**: `.github/workflows/test.yml`

```yaml
name: Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install uv
          uv sync

      - name: Lint with ruff
        run: ruff check src/ tests/

      - name: Format check
        run: ruff format --check src/ tests/

      - name: Type check with mypy
        run: mypy src/ || true  # Make non-blocking for now

      - name: Run unit tests
        run: |
          pytest tests/unit/ \
            -v \
            --tb=short \
            --cov=src \
            --cov-report=xml \
            --cov-report=term-missing

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  integration-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: haymaker_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/haymaker_test
          AZURE_CLIENT_MODE: mock
        run: |
          pytest tests/integration/ \
            -v \
            --tb=short \
            -m "not requires_cloud"

  security-scan:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install bandit safety

      - name: Security scan
        run: |
          bandit -r src/ -f json -o bandit-report.json || true
          safety check --json > safety-report.json || true

      - name: Upload security reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: |
            bandit-report.json
            safety-report.json

  test-summary:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, security-scan]
    if: always()
    steps:
      - name: Check test status
        run: |
          if [ "${{ needs.unit-tests.result }}" != "success" ]; then
            echo "Unit tests failed"
            exit 1
          fi
          echo "All tests passed"
```

---

## Phase 3: Create Build Workflow (Days 5-6, ~10 hours)

### Create Build Workflow

**File**: `.github/workflows/build.yml`

```yaml
name: Build

on:
  push:
    branches: [main]
    tags: ['v*']
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-container:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  build-artifacts:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install build wheel

      - name: Build distribution
        run: python -m build

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: python-dist
          path: dist/
          retention-days: 7

  build-docs:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install mkdocs mkdocs-material

      - name: Build documentation
        run: mkdocs build

      - name: Upload docs
        uses: actions/upload-artifact@v3
        with:
          name: docs-build
          path: site/
          retention-days: 7
```

---

## Phase 4: Create Deploy Workflow (Days 7-9, ~12 hours)

### Create Deploy Workflow

**File**: `.github/workflows/deploy.yml`

```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

env:
  REGISTRY: ghcr.io

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: staging
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to staging
        env:
          AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID_STAGING }}
          AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
          AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
        run: |
          # Install Azure CLI
          curl -sL https://aka.ms/InstallAzureCLIDeb | bash

          # Login to Azure
          az login --service-principal \
            -u $AZURE_CLIENT_ID \
            -p $AZURE_CLIENT_SECRET \
            --tenant $AZURE_TENANT_ID

          # Deploy container apps
          az containerapp create \
            --name haymaker-staging \
            --resource-group haymaker-staging \
            --image ${{ env.REGISTRY }}/${{ github.repository }}:main \
            --target-port 8000 \
            --ingress external

      - name: Run smoke tests
        run: |
          # Wait for deployment
          sleep 10

          # Run smoke tests
          curl -f https://haymaker-staging.azurecontainerapps.io/health || exit 1
          echo "Smoke tests passed"

  deploy-production:
    runs-on: ubuntu-latest
    if: github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/v')
    environment: production
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - name: Approval check
        run: |
          echo "Deployment requires manual approval"

      - name: Deploy to production
        env:
          AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID_PROD }}
          AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
          AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
        run: |
          # Similar to staging, but for production environment
          curl -sL https://aka.ms/InstallAzureCLIDeb | bash

          az login --service-principal \
            -u $AZURE_CLIENT_ID \
            -p $AZURE_CLIENT_SECRET \
            --tenant $AZURE_TENANT_ID

          az containerapp create \
            --name haymaker-prod \
            --resource-group haymaker-prod \
            --image ${{ env.REGISTRY }}/${{ github.repository }}:${{ github.ref_name }} \
            --target-port 8000 \
            --ingress external

      - name: Verify deployment
        run: |
          # Health check
          for i in {1..30}; do
            if curl -f https://haymaker-prod.azurecontainerapps.io/health; then
              echo "Production deployment verified"
              exit 0
            fi
            sleep 5
          done
          exit 1

  notify:
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    if: always()
    steps:
      - name: Notify deployment
        run: |
          if [ "${{ needs.deploy-staging.result }}" = "success" ]; then
            echo "Staging deployment successful"
          else
            echo "Staging deployment failed"
          fi
```

---

## Phase 5: Create Security Workflow (Days 10-11, ~8 hours)

### Create Security Workflow

**File**: `.github/workflows/security.yml`

```yaml
name: Security Checks

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * *'  # Daily 2 AM UTC

jobs:
  dependency-check:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install uv safety pip-audit

      - name: Check vulnerabilities
        run: |
          pip-audit --desc
          safety check || true

  code-scanning:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install tools
        run: |
          pip install bandit semgrep

      - name: Run Bandit
        run: bandit -r src/ -f json -o bandit.json || true

      - name: Run Semgrep
        run: semgrep --json src/ > semgrep.json || true

      - name: Upload results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: bandit.json

  container-scan:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t haymaker:scan .

      - name: Scan image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'haymaker:scan'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

---

## Phase 6: Create Workflow Templates (Days 12-13, ~8 hours)

### Create Reusable Workflow for PR Checks

**File**: `.github/workflows/pr-checks.yml`

```yaml
name: PR Checks

on:
  pull_request:
    branches: [main, develop]

jobs:
  pr-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Check PR title
        run: |
          TITLE="${{ github.event.pull_request.title }}"
          if [[ ! $TITLE =~ ^(feat|fix|docs|test|chore|refactor)(\(.+\))?!?: ]]; then
            echo "PR title must follow conventional commits"
            exit 1
          fi

      - name: Check for breaking changes
        run: |
          if grep -q "BREAKING CHANGE" "${{ github.event.pull_request.body }}"; then
            echo "Breaking change detected - requires version bump"
          fi

      - name: Validate files changed
        run: |
          # Check what files changed
          git diff --name-only origin/main...HEAD

          # Example: If docs changed, PR title should mention docs
          FILES_CHANGED=$(git diff --name-only origin/main...HEAD)
          if echo "$FILES_CHANGED" | grep -q "^src/"; then
            if [[ ! "${{ github.event.pull_request.title }}" =~ ^(feat|fix|refactor) ]]; then
              echo "Source files changed but PR type not appropriate"
              exit 1
            fi
          fi

  auto-comments:
    runs-on: ubuntu-latest
    steps:
      - name: Add testing reminder
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ Automated checks running. Tests must pass before merge.'
            })
```

---

## Phase 7: Create Actions Documentation (Days 14, ~6 hours)

### Create Workflow Documentation

**File**: `docs/GITHUB_ACTIONS.md`

```markdown
# GitHub Actions Workflows

## Overview

Automated CI/CD pipelines for testing, building, and deploying.

## Workflows

### test.yml
Runs on every push and PR:
- Unit tests (Python 3.11, 3.12)
- Integration tests
- Security scanning
- Code coverage

### build.yml
Builds on main branch:
- Docker container image
- Python distribution packages
- Documentation site

### deploy.yml
Deploys to staging/production:
- Deploys to Azure Container Apps
- Smoke tests
- Requires manual approval for production

### security.yml
Daily security checks:
- Dependency vulnerabilities
- Code scanning
- Container image scanning

## Adding Secrets

Required secrets in GitHub Settings:

```bash
AZURE_SUBSCRIPTION_ID_STAGING
AZURE_SUBSCRIPTION_ID_PROD
AZURE_TENANT_ID
AZURE_CLIENT_ID
AZURE_CLIENT_SECRET
```

## Triggering Workflows

```bash
# Test (automatic on PR/push)
git push origin branch-name

# Manual production deployment
gh workflow run deploy.yml \
  -f environment=production
```

## Viewing Results

- GitHub Actions tab: see workflow runs
- PR checks: pass/fail indicators
- Artifacts: downloadable build outputs
```

---

## Phase 8: Set Up Status Checks (Day 15, ~4 hours)

### Configure Branch Protection

In GitHub repo Settings:

1. Branch protection rules for `main`:
   - Require status checks: `test.yml`, `build.yml`, `security.yml`
   - Require code review
   - Dismiss stale reviews
   - Require conversation resolution

### Update README with Badges

**File**: `README.md`

```markdown
# Azure HayMaker

[![Test](https://github.com/YOUR_ORG/haymaker/workflows/Test/badge.svg)](https://github.com/YOUR_ORG/haymaker/actions/workflows/test.yml)
[![Build](https://github.com/YOUR_ORG/haymaker/workflows/Build/badge.svg)](https://github.com/YOUR_ORG/haymaker/actions/workflows/build.yml)
[![Deploy](https://github.com/YOUR_ORG/haymaker/workflows/Deploy/badge.svg)](https://github.com/YOUR_ORG/haymaker/actions/workflows/deploy.yml)
[![Security](https://github.com/YOUR_ORG/haymaker/workflows/Security%20Checks/badge.svg)](https://github.com/YOUR_ORG/haymaker/actions/workflows/security.yml)
```

---

## Testing

### Test Workflow Locally

```bash
# Install act (run GitHub Actions locally)
brew install act

# Run test workflow
act -j unit-tests

# Run specific workflow
act -W .github/workflows/test.yml
```

### Verify Workflows

```bash
# Syntax check
yamllint .github/workflows/

# Check workflows file
gh workflow list
gh workflow view test.yml
```

---

## Success Criteria

- [ ] test.yml running on PR/push
- [ ] build.yml building containers
- [ ] deploy.yml deploying to staging
- [ ] security.yml scanning for vulnerabilities
- [ ] PR checks enforcing status
- [ ] Branch protection configured
- [ ] All workflow syntax valid
- [ ] Badges working in README
- [ ] Developers understand workflow process
- [ ] Deployment takes <15 minutes

---

## Estimated Timeline

**Optimistic**: 2 weeks
**Realistic**: 2.5 weeks
**Pessimistic**: 3 weeks

---

**Issue**: #131
**Related**: #124 (Telemetry), #130 (Local Dev), #133 (Testing)

⚙️ **Ready to automate? Follow Phase 1 above!**
