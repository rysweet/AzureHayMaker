# Azure HayMaker - Feature Specifications

**Document Version**: 1.0
**Date**: 2025-11-15
**Status**: Ready for Implementation
**Project Phase**: Phase 4 (QA) → Phase 5 (Enhancement)

---

## Overview

This document provides comprehensive, unambiguous specifications for 5 new features for Azure HayMaker orchestration service. Each specification follows Zero-BS Philosophy and includes complete acceptance criteria, measurable success metrics, and implementation scope.

**Project Context**:
- **Current State**: Phase 3 complete (implementation done), Phase 4 in progress (QA)
- **Tech Stack**: Python 3.13, uv, pytest, Azure Functions, Container Apps, Durable Functions
- **Philosophy**: Zero-BS (no stubs/TODOs), ruthless simplicity, modular design
- **Architecture**: Timer-triggered orchestrator (4x daily), autonomous agents in Container Apps

---

## Feature 1: Environment Variable (.env) Configuration Support

### Type
**Enhancement** - Configuration flexibility improvement

### Objective
Add optional .env file support to complement existing environment variable and Azure Key Vault configuration methods, improving local development and testing experience without breaking existing deployments.

### User Requirement (Preserved Exactly)
> "we should also optionally read configuration from .env"

### Context
**Current Configuration Method** (`src/azure_haymaker/orchestrator/config.py`):
- Reads configuration from environment variables (via `os.getenv()`)
- Retrieves secrets from Azure Key Vault
- 15 required environment variables
- 6 optional environment variables
- Fails fast on missing required config (Zero-BS compliance)

**Why This Feature**:
- Simplifies local development and testing
- Eliminates need to manually set 15+ environment variables
- Industry standard practice (12-factor app methodology)
- Does NOT replace existing methods - adds optional convenience layer

### Requirements

#### Functional Requirements

**FR1.1: .env File Loading**
- Load configuration from `.env` file in project root if file exists
- Use `python-dotenv` library (industry standard)
- File format: Standard KEY=VALUE pairs, one per line
- Support comments (lines starting with `#`)
- Support empty lines (ignored)

**FR1.2: Priority Order (Explicit Hierarchy)**
- **Highest Priority**: Explicitly set environment variables
- **Medium Priority**: Azure Key Vault values (for secrets only)
- **Lowest Priority**: .env file values
- Rationale: Production deployments use env vars, .env is development convenience

**FR1.3: Backward Compatibility**
- Existing deployments without .env file MUST work unchanged
- All current tests MUST pass without modification
- No breaking changes to `OrchestratorConfig` model
- Configuration validation remains identical

**FR1.4: .env File Contents**
All current required and optional environment variables supported:

```env
# Target Azure Environment
AZURE_TENANT_ID=your-tenant-id
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_CLIENT_ID=your-client-id

# Key Vault (secrets retrieved from here)
KEY_VAULT_URL=https://your-keyvault.vault.azure.net

# Azure Service Configuration
SERVICE_BUS_NAMESPACE=your-servicebus-namespace
CONTAINER_REGISTRY=yourregistry.azurecr.io
CONTAINER_IMAGE=azure-haymaker-agent:latest
SIMULATION_SIZE=small

# Storage Configuration
STORAGE_ACCOUNT_NAME=yourstorageaccount
TABLE_STORAGE_ACCOUNT_NAME=yourtablestorageaccount

# Cosmos DB Configuration
COSMOSDB_ENDPOINT=https://your-cosmosdb.documents.azure.com:443/
COSMOSDB_DATABASE=haymaker

# Log Analytics Configuration
LOG_ANALYTICS_WORKSPACE_ID=your-workspace-id

# Optional Configuration
RESOURCE_GROUP_NAME=azure-haymaker-rg
SERVICE_BUS_TOPIC=agent-logs
VNET_INTEGRATION_ENABLED=false
VNET_RESOURCE_GROUP=your-vnet-rg
VNET_NAME=your-vnet
SUBNET_NAME=your-subnet
```

**FR1.5: Security Considerations**
- .env file MUST be in `.gitignore` (prevent accidental commit)
- .env file MUST NOT contain secrets in production deployments
- Secrets MUST still come from Azure Key Vault in production
- Documentation MUST warn against committing .env file
- Provide `.env.example` template with placeholder values

#### Non-Functional Requirements

**NFR1.1: Performance**
- .env file parsing adds < 100ms to startup time
- No impact on runtime performance (loaded once at startup)

**NFR1.2: Testability**
- New unit tests for .env loading logic
- Integration tests verify priority order
- Tests verify backward compatibility

**NFR1.3: Documentation**
- README.md updated with .env usage instructions
- .env.example file provided
- Security warnings prominently displayed

### Implementation Scope

#### In Scope

1. **New Module**: `src/azure_haymaker/orchestrator/dotenv_loader.py`
   - Function: `load_dotenv_with_priority() -> None`
   - Loads .env file if exists
   - Does NOT override existing environment variables

2. **Modified Module**: `src/azure_haymaker/orchestrator/config.py`
   - Add `load_dotenv_with_priority()` call at top of `load_config_from_env_and_keyvault()`
   - No other changes to existing logic

3. **New Files**:
   - `.env.example` in project root (template)
   - `.gitignore` update (ensure .env excluded)

4. **Updated Files**:
   - `README.md` - Quick Start section
   - `pyproject.toml` - Add `python-dotenv` dependency
   - `.gitignore` - Ensure .env excluded

5. **New Tests**:
   - `tests/unit/orchestrator/test_dotenv_loader.py`
   - `tests/integration/orchestrator/test_config_priority.py`

#### Out of Scope

- .env files for other purposes (only orchestrator config)
- Multiple .env files or profiles (.env.dev, .env.prod)
- Automatic .env file generation
- .env file validation beyond what Python-dotenv provides
- GUI or CLI tool for .env management

### Success Criteria

#### Acceptance Criteria (Testable)

- [ ] .env file in project root is loaded if present
- [ ] Configuration works when .env file absent (backward compatible)
- [ ] Explicitly set environment variables override .env values
- [ ] All 15 required + 6 optional variables supported in .env
- [ ] .env file with comments and empty lines parsed correctly
- [ ] .env is in .gitignore
- [ ] .env.example file exists with all variables documented
- [ ] README.md documents .env usage with examples
- [ ] README.md includes security warnings about .env files
- [ ] All existing tests pass unchanged
- [ ] New unit tests for dotenv_loader.py achieve 100% coverage
- [ ] Integration test verifies priority order (env var > .env)
- [ ] pytest runs successfully with .env present
- [ ] pytest runs successfully with .env absent

#### Quality Metrics

- **Code Coverage**: 100% for new dotenv_loader.py module
- **Test Coverage**: Minimum 95% for modified config.py
- **Backward Compatibility**: 100% (all existing tests pass)
- **Performance**: < 100ms .env load time (measured)
- **Documentation**: .env usage documented in 3 places (README, .env.example, inline comments)

### Dependencies

**Internal Dependencies**:
- `src/azure_haymaker/orchestrator/config.py` (modify)
- `pyproject.toml` (add dependency)

**External Dependencies**:
- `python-dotenv>=1.0.0` (new PyPI package)
- No Azure service changes required

**Blockers**:
- None (can implement immediately)

### Risk Assessment

**Risk Level**: **Low**

**Risks Identified**:

1. **Risk**: Developers accidentally commit .env with secrets
   - **Impact**: High (secret exposure)
   - **Probability**: Medium (common mistake)
   - **Mitigation**: .gitignore, pre-commit hook check, clear documentation
   - **Residual Risk**: Low

2. **Risk**: Priority order confusion (which value takes precedence?)
   - **Impact**: Medium (wrong config used)
   - **Probability**: Low (clear documentation)
   - **Mitigation**: Explicit docs, integration tests, clear error messages
   - **Residual Risk**: Very Low

3. **Risk**: .env file used in production instead of proper env vars
   - **Impact**: Medium (deployment anti-pattern)
   - **Probability**: Low (Azure Functions don't use .env by default)
   - **Mitigation**: Documentation emphasizes .env is for development only
   - **Residual Risk**: Low

**Security Considerations**:
- .env file is a local development convenience ONLY
- Production deployments MUST use environment variables + Key Vault
- No changes to secret management (Key Vault remains source of truth)

### Complexity Assessment

**Complexity**: **Simple**

**Justification**:
- Single new module with 1 function
- Minimal changes to existing code (1 function call added)
- Well-established library (python-dotenv)
- No API changes
- No database changes
- No architecture changes
- Clear requirements

**Effort Estimate**: **2-4 hours**

**Breakdown**:
- Implementation: 1 hour
- Testing: 1 hour
- Documentation: 1 hour
- Review: 1 hour

### Priority

**Priority**: **Medium**

**Rationale**:
- Improves developer experience
- Low risk, high value for development workflow
- Does not block other features
- Non-breaking enhancement

### Implementation Notes

**Suggested Implementation Order**:
1. Add python-dotenv to pyproject.toml
2. Create .env.example with all variables
3. Update .gitignore (verify .env excluded)
4. Implement dotenv_loader.py module
5. Add unit tests for dotenv_loader.py
6. Integrate into config.py (1 line addition)
7. Add integration test for priority order
8. Update README.md
9. Run full test suite to verify backward compatibility

**Code Example** (dotenv_loader.py):
```python
"""Optional .env file loading for local development convenience.

This module provides .env file support for Azure HayMaker configuration.
.env files are loaded ONLY if present and do NOT override explicitly set
environment variables, ensuring production deployments are unaffected.

Priority Order (highest to lowest):
1. Explicitly set environment variables
2. Azure Key Vault values (secrets only)
3. .env file values
"""

import os
from pathlib import Path

def load_dotenv_with_priority() -> None:
    """Load .env file if present, respecting environment variable priority.

    This function loads a .env file from the project root if it exists.
    It does NOT override environment variables that are already set,
    ensuring production deployments are unaffected.

    Priority:
    - Existing environment variables take precedence
    - .env values are only used if env var not already set

    Returns:
        None

    Raises:
        None (silently skips if .env not found)
    """
    try:
        from dotenv import load_dotenv

        # Find project root (where .env should be)
        project_root = Path(__file__).parent.parent.parent.parent
        dotenv_path = project_root / ".env"

        # Load .env if exists, but DON'T override existing env vars
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path, override=False)

    except ImportError:
        # python-dotenv not installed, skip silently
        # This allows deployments without the dev dependency
        pass
```

**Integration Point** (config.py):
```python
async def load_config_from_env_and_keyvault() -> OrchestratorConfig:
    """Load configuration from environment variables and Azure Key Vault."""

    # NEW: Load .env file if present (development convenience)
    from azure_haymaker.orchestrator.dotenv_loader import load_dotenv_with_priority
    load_dotenv_with_priority()

    # Existing code continues unchanged...
    try:
        target_tenant_id = _get_required_env("AZURE_TENANT_ID")
        # ... rest of existing implementation
```

### Documentation Requirements

**README.md Section**:
```markdown
## Configuration

Azure HayMaker supports three configuration methods:

### Production: Environment Variables + Key Vault (Recommended)

```bash
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
# ... other variables
```

Secrets are retrieved from Azure Key Vault.

### Development: .env File (Optional)

For local development convenience, create a `.env` file in the project root:

```bash
cp .env.example .env
# Edit .env with your values
```

**IMPORTANT**:
- .env files are for LOCAL DEVELOPMENT ONLY
- NEVER commit .env files to git
- Production deployments MUST use environment variables
- Secrets should still come from Key Vault (not .env)

Priority order:
1. Explicitly set environment variables (highest)
2. Azure Key Vault values (secrets)
3. .env file values (lowest)
```

---

## Feature 2: GitOps Deployment Pipeline

### Type
**Feature** - CI/CD automation

### Objective
Implement GitOps deployment workflow enabling automated orchestrator deployment from GitHub releases with secrets injected from GitHub Secrets, eliminating manual deployment steps and improving release reliability.

### User Requirements (Preserved Exactly)
> "setup gitops so that we can deploy the orchestrator from a git release"
> "inject its secrets from GH secrets configuration in the repo"

### Context
**Current Deployment Method**:
- Manual deployment required
- No automated release process
- No infrastructure-as-code for orchestrator deployment
- Secrets managed manually

**Why This Feature**:
- Automate deployment process (eliminate manual steps)
- Version-controlled infrastructure
- Reproducible deployments
- Secrets managed securely via GitHub Secrets
- Support for multiple environments (dev, staging, prod)
- Rollback capability via GitHub releases

### Requirements

#### Functional Requirements

**FR2.1: GitHub Actions Workflow**
- Workflow triggered on GitHub Release publication
- Workflow file: `.github/workflows/deploy-orchestrator.yml`
- Support semantic versioning tags (v1.0.0, v1.1.0, etc.)
- Deploy orchestrator to Azure Functions
- Deploy infrastructure if needed (resource group, storage, etc.)

**FR2.2: Infrastructure-as-Code**
- Use Azure Bicep for infrastructure definition
- Bicep templates in `infra/` directory
- Deploy:
  - Azure Functions (orchestrator host)
  - Storage Account (logs, state, reports, scenarios)
  - Table Storage (execution tracking)
  - Cosmos DB (real-time metrics)
  - Service Bus (agent logging)
  - Container Registry (agent images)
  - Key Vault (secret storage)
  - Log Analytics Workspace (monitoring)
  - Application Insights (telemetry)
  - VNet + Subnet (if VNet integration enabled)

**FR2.3: Secret Management**
- All secrets stored as GitHub Secrets (repository level)
- Secrets injected as environment variables during deployment
- Secrets pushed to Azure Key Vault during deployment
- No secrets in git repository (ever)

**FR2.4: Deployment Environments**
- Support 3 environments: `dev`, `staging`, `prod`
- Environment selected via GitHub Release tag convention:
  - `v1.0.0-dev` → deploy to dev
  - `v1.0.0-rc1` → deploy to staging
  - `v1.0.0` → deploy to prod
- Each environment has separate Azure resources
- Each environment has separate GitHub Environment configuration

**FR2.5: Rollback Support**
- Re-running deployment for previous release tag rolls back
- Azure Functions deployment slots for zero-downtime deployment
- Previous deployment artifacts retained for 30 days

#### Non-Functional Requirements

**NFR2.1: Security**
- GitHub OIDC authentication to Azure (no long-lived credentials)
- Least privilege: deployment identity has only required permissions
- Secrets encrypted at rest (GitHub Secrets, Azure Key Vault)
- Audit trail: all deployments logged to Azure Monitor

**NFR2.2: Reliability**
- Deployment failures do not leave environment in broken state
- Idempotent deployments (can run multiple times safely)
- Pre-deployment validation (config checks, quota checks)
- Post-deployment smoke tests (validate deployment succeeded)

**NFR2.3: Observability**
- Deployment logs captured in GitHub Actions
- Deployment events sent to Azure Monitor
- Deployment status visible in GitHub UI
- Deployment metrics tracked (duration, success rate)

**NFR2.4: Performance**
- Full deployment completes in < 15 minutes
- Incremental deployment (code-only) in < 5 minutes

### Implementation Scope

#### In Scope

1. **GitHub Actions Workflows**:
   - `.github/workflows/deploy-orchestrator.yml` (main deployment)
   - `.github/workflows/validate-infra.yml` (PR validation)

2. **Infrastructure-as-Code**:
   - `infra/main.bicep` (root template)
   - `infra/modules/functions.bicep` (Azure Functions)
   - `infra/modules/storage.bicep` (Storage + Table Storage)
   - `infra/modules/cosmosdb.bicep` (Cosmos DB)
   - `infra/modules/servicebus.bicep` (Service Bus)
   - `infra/modules/keyvault.bicep` (Key Vault)
   - `infra/modules/monitoring.bicep` (Log Analytics + App Insights)
   - `infra/modules/network.bicep` (VNet + Subnet, optional)
   - `infra/modules/container-registry.bicep` (Container Registry)
   - `infra/parameters/dev.json` (dev environment parameters)
   - `infra/parameters/staging.json` (staging parameters)
   - `infra/parameters/prod.json` (prod parameters)

3. **Deployment Scripts**:
   - `scripts/deploy.sh` (orchestrates deployment steps)
   - `scripts/validate-deployment.sh` (post-deployment checks)
   - `scripts/push-secrets-to-keyvault.sh` (secret synchronization)

4. **Documentation**:
   - `docs/deployment-guide.md` (complete deployment instructions)
   - `docs/github-secrets-setup.md` (secret configuration guide)
   - `docs/rollback-procedure.md` (rollback instructions)

5. **GitHub Configuration**:
   - GitHub Environments: `dev`, `staging`, `prod`
   - Environment protection rules (prod requires approval)
   - GitHub Secrets configured per environment

#### Out of Scope

- Multi-region deployments (single region only)
- Database migration management (Cosmos DB is schema-less)
- Cost optimization automation (manual tuning required)
- Performance testing in pipeline (manual testing only)
- Automated rollback on failure (manual rollback only)
- Blue-green deployment strategy (future enhancement)

### Success Criteria

#### Acceptance Criteria (Testable)

**Deployment**:
- [ ] GitHub Release publication triggers workflow automatically
- [ ] Workflow deploys to correct environment based on tag convention
- [ ] All infrastructure resources created in correct resource group
- [ ] Azure Functions deployed with latest code
- [ ] Environment variables configured correctly in Functions
- [ ] Secrets injected from GitHub Secrets to Azure Key Vault
- [ ] Post-deployment smoke test passes (validate-deployment.sh succeeds)
- [ ] Deployment completes in < 15 minutes

**Secret Management**:
- [ ] No secrets in git repository (verified by scan)
- [ ] All required secrets defined in GitHub Secrets
- [ ] Secrets successfully pushed to Azure Key Vault
- [ ] Functions can retrieve secrets from Key Vault
- [ ] Secret rotation workflow documented

**Environments**:
- [ ] Dev environment deploys from `*-dev` tags
- [ ] Staging environment deploys from `*-rc*` tags
- [ ] Prod environment deploys from `v*` tags (no suffix)
- [ ] Prod deployments require manual approval
- [ ] Each environment has isolated resources

**Rollback**:
- [ ] Re-running deployment with older release tag succeeds
- [ ] Previous version restored successfully
- [ ] No data loss during rollback
- [ ] Rollback documented in deployment guide

**Validation**:
- [ ] PR validation workflow runs on infrastructure changes
- [ ] Bicep templates pass validation (az bicep build)
- [ ] Parameter files are valid JSON
- [ ] Pre-deployment checks catch configuration errors

#### Quality Metrics

- **Deployment Success Rate**: > 95% (manual remediation for failures)
- **Deployment Duration**: < 15 minutes (full), < 5 minutes (code-only)
- **Secret Security Score**: 100% (no secrets in git, audit pass)
- **Infrastructure Coverage**: 100% (all resources defined in Bicep)
- **Rollback Success Rate**: > 90% (tested quarterly)

### Dependencies

**Internal Dependencies**:
- Azure subscription with appropriate quotas
- Azure service principals with deployment permissions
- GitHub repository admin access (configure secrets)

**External Dependencies**:
- GitHub Actions (included with GitHub)
- Azure CLI (latest version)
- Azure Bicep CLI (latest version)

**Prerequisite Configuration**:
1. Azure subscription created
2. Azure AD app registration for GitHub OIDC
3. Federated credentials configured for GitHub Actions
4. GitHub Environments created (dev, staging, prod)
5. GitHub Secrets configured (see github-secrets-setup.md)

**Blockers**:
- Azure subscription required (user must provide)
- GitHub repository permissions (user must grant)

### Risk Assessment

**Risk Level**: **Medium**

**Risks Identified**:

1. **Risk**: Deployment failure leaves environment in inconsistent state
   - **Impact**: High (manual remediation required)
   - **Probability**: Medium (complex infrastructure)
   - **Mitigation**: Idempotent Bicep templates, pre-deployment validation
   - **Residual Risk**: Low

2. **Risk**: Secret leakage during deployment
   - **Impact**: Critical (security breach)
   - **Probability**: Low (GitHub Secrets encrypted)
   - **Mitigation**: No secrets in logs, audit workflow, secret scanning
   - **Residual Risk**: Very Low

3. **Risk**: Accidental production deployment
   - **Impact**: High (production impact)
   - **Probability**: Low (manual approval required)
   - **Mitigation**: Environment protection rules, tag convention, approval gates
   - **Residual Risk**: Very Low

4. **Risk**: Infrastructure drift (manual changes)
   - **Impact**: Medium (state inconsistency)
   - **Probability**: Medium (human error)
   - **Mitigation**: Document "no manual changes" policy, drift detection (future)
   - **Residual Risk**: Medium

5. **Risk**: GitHub Actions service outage
   - **Impact**: Medium (cannot deploy)
   - **Probability**: Low (GitHub SLA 99.9%)
   - **Mitigation**: Manual deployment procedure documented as backup
   - **Residual Risk**: Low

**Security Considerations**:
- OIDC authentication prevents credential leakage
- Least privilege for deployment identity
- Secrets never in git (verified by pre-commit hook)
- All deployments audited to Azure Monitor

### Complexity Assessment

**Complexity**: **Complex**

**Justification**:
- Multiple components (GitHub Actions, Bicep templates, scripts)
- Cross-system integration (GitHub ↔ Azure)
- Secret management across systems
- Multiple environments with different configurations
- Infrastructure-as-code learning curve
- Deployment orchestration logic
- Rollback procedures
- Security configuration (OIDC)

**Effort Estimate**: **5-7 days**

**Breakdown**:
- GitHub Actions workflows: 1 day
- Bicep infrastructure templates: 2 days
- Deployment scripts: 1 day
- Testing (3 environments): 1 day
- Documentation: 1 day
- Review and refinement: 1 day

### Priority

**Priority**: **High**

**Rationale**:
- Eliminates manual deployment toil
- Enables reliable, repeatable deployments
- Foundation for continuous delivery
- Improves security (OIDC, no long-lived credentials)
- Required for production-grade operations

### Implementation Notes

**GitHub Secrets Required**:

```yaml
# Azure Authentication (OIDC)
AZURE_CLIENT_ID: "00000000-0000-0000-0000-000000000000"
AZURE_TENANT_ID: "00000000-0000-0000-0000-000000000000"
AZURE_SUBSCRIPTION_ID: "00000000-0000-0000-0000-000000000000"

# Application Secrets (pushed to Key Vault)
MAIN_SP_CLIENT_SECRET: "super-secret-value"
ANTHROPIC_API_KEY: "sk-ant-api03-..."
LOG_ANALYTICS_WORKSPACE_KEY: "base64-encoded-key"

# Environment-Specific (separate per environment)
RESOURCE_GROUP_NAME: "azure-haymaker-dev-rg"
KEY_VAULT_NAME: "haymaker-dev-kv"
FUNCTIONS_APP_NAME: "haymaker-dev-func"
```

**Bicep Template Structure**:

```
infra/
├── main.bicep                  # Root template, orchestrates modules
├── parameters/
│   ├── dev.json                # Dev environment parameters
│   ├── staging.json            # Staging environment parameters
│   └── prod.json               # Prod environment parameters
└── modules/
    ├── functions.bicep         # Azure Functions deployment
    ├── storage.bicep           # Storage + Table Storage
    ├── cosmosdb.bicep          # Cosmos DB
    ├── servicebus.bicep        # Service Bus
    ├── keyvault.bicep          # Key Vault
    ├── monitoring.bicep        # Log Analytics + App Insights
    ├── network.bicep           # VNet + Subnet (optional)
    └── container-registry.bicep # Container Registry
```

**Deployment Workflow High-Level**:

```yaml
name: Deploy Orchestrator

on:
  release:
    types: [published]

jobs:
  determine-environment:
    # Parse tag to determine target environment
    # v1.0.0-dev → dev
    # v1.0.0-rc1 → staging
    # v1.0.0 → prod

  validate:
    # Run pre-deployment checks
    # Validate Bicep templates
    # Check Azure quotas
    # Verify secrets configured

  deploy-infrastructure:
    # Deploy Bicep templates
    # Create/update Azure resources
    # Configure networking

  push-secrets:
    # Push secrets from GitHub to Key Vault
    # Verify Key Vault accessibility

  deploy-functions:
    # Build Python package
    # Deploy to Azure Functions
    # Configure environment variables

  validate-deployment:
    # Run smoke tests
    # Verify Functions responding
    # Check secret access

  notify:
    # Send deployment notification
    # Update deployment tracking
```

**Implementation Order**:
1. Create Bicep templates for each module (start with functions.bicep)
2. Create parameter files for dev environment
3. Test Bicep deployment manually (az deployment group create)
4. Create GitHub Actions workflow (start with deploy-orchestrator.yml)
5. Configure GitHub OIDC authentication
6. Test deployment to dev environment via GitHub Actions
7. Create staging and prod parameter files
8. Configure environment protection rules
9. Test full release flow (dev → staging → prod)
10. Write comprehensive documentation

**Testing Strategy**:
- Test Bicep templates locally with `az bicep build` and `az deployment group validate`
- Test deployment scripts locally before integrating into workflow
- Use dev environment for deployment testing (iterate rapidly)
- Test rollback procedure at least once before production use
- Verify secret injection manually after first deployment

### Documentation Requirements

**docs/deployment-guide.md** (complete step-by-step guide):
1. Prerequisites (Azure subscription, permissions)
2. GitHub repository setup (fork/clone)
3. Azure OIDC configuration (detailed steps)
4. GitHub Secrets configuration (what to set, how to get values)
5. GitHub Environments setup (protection rules)
6. First deployment (create initial release)
7. Monitoring deployment (GitHub Actions UI)
8. Post-deployment verification (smoke tests)
9. Troubleshooting common issues

**docs/github-secrets-setup.md**:
- Complete list of required secrets
- How to obtain each value
- Security best practices
- Secret rotation procedures

**docs/rollback-procedure.md**:
- When to rollback (decision criteria)
- How to rollback (step-by-step)
- Validation after rollback
- Incident communication template

---

## Feature 3: On-Demand Agent Execution API

### Type
**Feature** - API endpoint for manual agent execution

### Objective
Enable on-demand execution of specific agents outside the scheduled 4x daily runs, providing flexibility for testing, demonstrations, and ad-hoc scenario execution without waiting for the next scheduled run.

### User Requirement (Preserved Exactly)
> "optional to use the orchestrator ability to run a particular agent without running the schedule"

### Context
**Current Execution Model**:
- Timer-triggered orchestration (4x daily: 00:00, 06:00, 12:00, 18:00 UTC)
- Automatically selects N random scenarios based on simulation_size
- No manual intervention possible
- Cannot run specific scenarios on demand

**Why This Feature**:
- Testing: Run specific scenario during development
- Demonstrations: Show specific scenarios to stakeholders
- Troubleshooting: Reproduce issues with specific scenarios
- Flexibility: Don't wait up to 6 hours for next scheduled run
- Validation: Test single scenario after code changes

### Requirements

#### Functional Requirements

**FR3.1: HTTP Trigger Function**
- New Azure Function with HTTP trigger
- Endpoint: `POST /api/execute-agent`
- Authentication required (Function Key or Azure AD token)
- Request body specifies which agent(s) to run
- Returns execution tracking ID immediately (async execution)

**FR3.2: Request Schema**
```json
{
  "scenarios": ["ai-ml-01-cognitive-services-vision", "databases-01-mysql-wordpress"],
  "execution_duration_hours": 8,
  "run_mode": "immediate",
  "tags": {
    "purpose": "testing",
    "requestor": "user@example.com"
  }
}
```

- **scenarios**: Array of scenario names (1-5 scenarios, validated)
- **execution_duration_hours**: Optional, default 8, range 1-10
- **run_mode**: "immediate" or "scheduled" (default "immediate")
- **tags**: Optional key-value pairs for tracking

**FR3.3: Response Schema**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "scenarios_count": 2,
  "scenarios": ["ai-ml-01-cognitive-services-vision", "databases-01-mysql-wordpress"],
  "execution_duration_hours": 8,
  "estimated_completion": "2025-11-15T18:00:00Z",
  "status_url": "https://haymaker-func.azurewebsites.net/api/status/550e8400-e29b-41d4-a716-446655440000",
  "message": "Execution started. Use status_url to track progress."
}
```

**FR3.4: Validation**
- Scenario names validated (must exist in `docs/scenarios/`)
- Maximum 5 scenarios per request (prevent resource exhaustion)
- Execution duration validated (1-10 hours)
- Request rate limiting (max 10 requests/hour)
- Concurrent execution limit (max 3 on-demand runs simultaneously)

**FR3.5: Execution Workflow**
Same as scheduled execution, but triggered manually:
1. Validate request
2. Create service principals for specified scenarios
3. Deploy Container Apps for specified scenarios
4. Monitor execution
5. Cleanup verification
6. Generate report

**FR3.6: Status Tracking**
- Status endpoint: `GET /api/status/{run_id}`
- Returns current execution status:
  - `accepted`: Request accepted, provisioning starting
  - `provisioning`: Creating SPs and Container Apps
  - `running`: Agents executing
  - `cleanup`: Cleaning up resources
  - `completed`: Execution finished successfully
  - `failed`: Execution failed (includes error details)
- Status includes:
  - Current phase
  - Scenario-level status
  - Resource counts
  - Log summary
  - Errors (if any)

**FR3.7: Integration with Scheduled Runs**
- On-demand runs tracked separately from scheduled runs
- On-demand runs do NOT interfere with scheduled runs
- Shared resource limits respected (total containers across all runs)
- On-demand runs tagged with `ExecutionType=OnDemand` in Table Storage

#### Non-Functional Requirements

**NFR3.1: Security**
- Authentication required (Function Key minimum, Azure AD preferred)
- Authorization: Only authorized users can trigger on-demand runs
- Rate limiting to prevent abuse
- Audit trail: all requests logged to Azure Monitor

**NFR3.2: Performance**
- API response time < 2 seconds (returns immediately, execution is async)
- Status endpoint response time < 500ms
- No impact on scheduled runs performance

**NFR3.3: Reliability**
- Request validation prevents invalid executions
- Failures do not crash orchestrator
- Failed on-demand runs do not affect scheduled runs
- Cleanup always runs (even if execution fails)

**NFR3.4: Observability**
- All on-demand requests logged with requestor info
- Execution metrics tracked separately (on-demand vs scheduled)
- Dashboards show on-demand vs scheduled run breakdown

### Implementation Scope

#### In Scope

1. **New Azure Functions**:
   - `execute_agent_http` (POST /api/execute-agent) - Trigger on-demand execution
   - `get_execution_status_http` (GET /api/status/{run_id}) - Get status

2. **New Module**: `src/azure_haymaker/orchestrator/on_demand.py`
   - `validate_on_demand_request()` - Request validation
   - `start_on_demand_execution()` - Start execution workflow
   - `get_execution_status()` - Retrieve status

3. **Modified Module**: `src/azure_haymaker/orchestrator/orchestrator.py`
   - Add `execution_type` parameter to `orchestrate_haymaker_run()` ("scheduled" or "on-demand")
   - Tag executions with execution type in Table Storage

4. **New Models**: `src/azure_haymaker/models/execution.py`
   - `OnDemandRequest` (Pydantic model for request validation)
   - `ExecutionStatus` (Pydantic model for status response)

5. **Updated Infrastructure** (infra/modules/functions.bicep):
   - Add HTTP trigger bindings
   - Configure authentication
   - Configure rate limiting

6. **New Tests**:
   - `tests/unit/orchestrator/test_on_demand.py`
   - `tests/integration/orchestrator/test_on_demand_api.py`
   - `tests/e2e/test_on_demand_execution.py`

#### Out of Scope

- Web UI for triggering on-demand runs (API only)
- Scenario search/filter API (must know scenario name)
- Execution cancellation (cannot cancel once started)
- Execution pause/resume
- Scheduled execution via API (timer trigger only)
- Priority/queue management (first-come-first-served)

### Success Criteria

#### Acceptance Criteria (Testable)

**API Functionality**:
- [ ] POST /api/execute-agent accepts valid requests
- [ ] POST /api/execute-agent returns 202 Accepted with run_id
- [ ] POST /api/execute-agent rejects invalid scenario names
- [ ] POST /api/execute-agent rejects > 5 scenarios
- [ ] POST /api/execute-agent rejects execution_duration > 10 hours
- [ ] GET /api/status/{run_id} returns current status
- [ ] GET /api/status/{run_id} returns 404 for unknown run_id

**Execution**:
- [ ] On-demand execution creates SPs for specified scenarios only
- [ ] On-demand execution deploys Container Apps for specified scenarios
- [ ] On-demand execution runs for specified duration
- [ ] On-demand execution performs cleanup
- [ ] On-demand execution generates report

**Integration**:
- [ ] On-demand runs tagged with ExecutionType=OnDemand
- [ ] On-demand runs do not interfere with scheduled runs
- [ ] Multiple concurrent on-demand runs supported (up to limit)
- [ ] Resource limits respected across all runs

**Security**:
- [ ] Unauthenticated requests rejected (401)
- [ ] Rate limiting enforced (max 10 req/hour)
- [ ] All requests logged to Azure Monitor
- [ ] Audit trail includes requestor information

**Documentation**:
- [ ] API documented in docs/api-reference.md
- [ ] Examples provided for common use cases
- [ ] Authentication setup documented
- [ ] Rate limits documented

#### Quality Metrics

- **API Response Time**: < 2 seconds (95th percentile)
- **Status Endpoint Response Time**: < 500ms (95th percentile)
- **Request Validation Accuracy**: 100% (no invalid requests accepted)
- **Test Coverage**: > 90% for on_demand.py module
- **Documentation Coverage**: All API endpoints documented

### Dependencies

**Internal Dependencies**:
- `src/azure_haymaker/orchestrator/orchestrator.py` (modify)
- `src/azure_haymaker/models/execution.py` (new)
- `src/azure_haymaker/orchestrator/on_demand.py` (new)

**External Dependencies**:
- Azure Functions HTTP trigger (existing)
- Azure Table Storage (existing - for status tracking)

**Blockers**:
- None (can implement immediately)

### Risk Assessment

**Risk Level**: **Medium**

**Risks Identified**:

1. **Risk**: Resource exhaustion (too many concurrent on-demand runs)
   - **Impact**: High (quota exceeded, failures)
   - **Probability**: Medium (without limits)
   - **Mitigation**: Concurrent execution limit (3 on-demand runs max), validation
   - **Residual Risk**: Low

2. **Risk**: API abuse (malicious/accidental repeated requests)
   - **Impact**: Medium (cost increase, quota exhaustion)
   - **Probability**: Low (authentication + rate limiting)
   - **Mitigation**: Rate limiting (10 req/hour), authentication required
   - **Residual Risk**: Low

3. **Risk**: On-demand run interferes with scheduled run
   - **Impact**: High (scheduled run fails)
   - **Probability**: Low (separate tracking)
   - **Mitigation**: Separate ExecutionType tagging, shared resource limit awareness
   - **Residual Risk**: Very Low

4. **Risk**: Invalid scenario execution (typo in scenario name)
   - **Impact**: Low (execution fails quickly)
   - **Probability**: Medium (user error)
   - **Mitigation**: Scenario name validation, clear error messages
   - **Residual Risk**: Very Low

**Security Considerations**:
- Authentication required (Function Key minimum)
- Rate limiting prevents abuse
- Audit trail for accountability
- No privilege escalation (same permissions as scheduled runs)

### Complexity Assessment

**Complexity**: **Medium**

**Justification**:
- New HTTP endpoints (standard Azure Functions pattern)
- Request validation logic (moderate)
- Integration with existing orchestrator (parameter passing)
- Status tracking (Table Storage queries)
- No new Azure services required
- Well-defined scope

**Effort Estimate**: **2-3 days**

**Breakdown**:
- API endpoints implementation: 1 day
- Request validation and status tracking: 1 day
- Testing (unit, integration, e2e): 1 day
- Documentation: 0.5 day

### Priority

**Priority**: **High**

**Rationale**:
- High value for testing and development
- Unblocks scenario validation during development
- Enables demonstrations and troubleshooting
- Relatively quick to implement
- Complements scheduled execution model

### Implementation Notes

**Azure Function Code Example** (execute_agent_http):

```python
@app.route(route="execute-agent", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
@app.durable_client_input(client_name="durable_client")
async def execute_agent_http(
    req: func.HttpRequest,
    durable_client: Any,
) -> func.HttpResponse:
    """HTTP endpoint for on-demand agent execution.

    Request Body:
    {
      "scenarios": ["scenario-name-1", "scenario-name-2"],
      "execution_duration_hours": 8,
      "run_mode": "immediate",
      "tags": {"purpose": "testing"}
    }

    Returns:
    202 Accepted with run_id and status_url
    """
    try:
        # Parse and validate request
        request_body = req.get_json()
        on_demand_req = validate_on_demand_request(request_body)

        # Check rate limit
        if not check_rate_limit(req.headers.get("X-Forwarded-For")):
            return func.HttpResponse(
                json.dumps({"error": "Rate limit exceeded. Max 10 requests/hour."}),
                status_code=429,
                mimetype="application/json",
            )

        # Check concurrent execution limit
        active_count = await get_active_on_demand_count()
        if active_count >= 3:
            return func.HttpResponse(
                json.dumps({"error": "Concurrent execution limit reached. Max 3 on-demand runs."}),
                status_code=429,
                mimetype="application/json",
            )

        # Generate run ID
        run_id = str(uuid4())

        # Start orchestration
        await durable_client.start_new(
            orchestration_function_name="orchestrate_haymaker_run",
            instance_id=run_id,
            input_={
                "run_id": run_id,
                "started_at": datetime.now(UTC).isoformat(),
                "execution_type": "on_demand",
                "scenarios": on_demand_req.scenarios,
                "execution_duration_hours": on_demand_req.execution_duration_hours,
                "tags": on_demand_req.tags,
            },
        )

        # Log request
        logger.info(
            f"On-demand execution started: run_id={run_id}, "
            f"scenarios={on_demand_req.scenarios}, "
            f"requestor={req.headers.get('X-MS-CLIENT-PRINCIPAL-NAME', 'unknown')}"
        )

        # Return response
        estimated_completion = datetime.now(UTC) + timedelta(
            hours=on_demand_req.execution_duration_hours + 1
        )

        response = {
            "run_id": run_id,
            "status": "accepted",
            "scenarios_count": len(on_demand_req.scenarios),
            "scenarios": on_demand_req.scenarios,
            "execution_duration_hours": on_demand_req.execution_duration_hours,
            "estimated_completion": estimated_completion.isoformat(),
            "status_url": f"{req.url.rstrip('/execute-agent')}/status/{run_id}",
            "message": "Execution started. Use status_url to track progress.",
        }

        return func.HttpResponse(
            json.dumps(response),
            status_code=202,
            mimetype="application/json",
        )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": f"Invalid request: {str(e)}"}),
            status_code=400,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"On-demand execution failed: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json",
        )
```

**Request Validation Example** (on_demand.py):

```python
from pydantic import BaseModel, Field, field_validator

class OnDemandRequest(BaseModel):
    """Request model for on-demand agent execution."""

    scenarios: list[str] = Field(..., min_length=1, max_length=5)
    execution_duration_hours: int = Field(default=8, ge=1, le=10)
    run_mode: str = Field(default="immediate")
    tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("scenarios")
    @classmethod
    def validate_scenario_names(cls, v: list[str]) -> list[str]:
        """Validate scenario names exist."""
        from pathlib import Path

        scenarios_dir = Path(__file__).parent.parent.parent / "docs" / "scenarios"
        available_scenarios = {
            f.stem for f in scenarios_dir.glob("*.md") if f.is_file()
        }

        invalid_scenarios = set(v) - available_scenarios
        if invalid_scenarios:
            raise ValueError(
                f"Invalid scenario names: {', '.join(invalid_scenarios)}. "
                f"Available scenarios: {', '.join(sorted(available_scenarios))}"
            )

        return v

    @field_validator("run_mode")
    @classmethod
    def validate_run_mode(cls, v: str) -> str:
        """Validate run mode."""
        if v not in ("immediate", "scheduled"):
            raise ValueError(f"Invalid run_mode: {v}. Must be 'immediate' or 'scheduled'.")
        return v
```

**Testing Strategy**:
- Unit tests for request validation (valid/invalid scenarios)
- Unit tests for rate limiting logic
- Integration tests for HTTP endpoints (mock Durable Functions client)
- E2E test: trigger on-demand run, poll status, verify completion
- Load test: verify rate limiting and concurrent execution limits

**Documentation Requirements**:

Create `docs/api-reference.md`:

```markdown
# Azure HayMaker API Reference

## Execute Agent (On-Demand)

Trigger on-demand execution of specific scenarios.

### Endpoint

POST /api/execute-agent

### Authentication

Function Key (provided in query string or header)

### Request Body

{
  "scenarios": ["scenario-name-1", "scenario-name-2"],
  "execution_duration_hours": 8,
  "run_mode": "immediate",
  "tags": {
    "purpose": "testing",
    "requestor": "user@example.com"
  }
}

### Response

202 Accepted

{
  "run_id": "uuid",
  "status": "accepted",
  "scenarios_count": 2,
  "status_url": "https://...com/api/status/{run_id}",
  ...
}

### Rate Limits

- 10 requests per hour per IP
- Maximum 3 concurrent on-demand runs
- Maximum 5 scenarios per request

### Examples

# Trigger single scenario
curl -X POST "https://haymaker-func.azurewebsites.net/api/execute-agent?code=FUNCTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "scenarios": ["ai-ml-01-cognitive-services-vision"],
    "execution_duration_hours": 2,
    "tags": {"purpose": "testing"}
  }'

# Check status
curl "https://haymaker-func.azurewebsites.net/api/status/{run_id}?code=FUNCTION_KEY"
```

---

## Feature 4: Documentation Fixes

### Type
**Bug Fix** - Documentation corrections

### Objective
Fix incorrect, broken, or missing documentation discovered during Phase 4 QA review, ensuring all documentation is accurate, complete, and references correct resources.

### User Requirements (From Investigation)
Multiple documentation issues identified:
1. `.claude/skills/azure-haymaker/ARCHITECTURE_GUIDE.md` covers wrong topic (Azure patterns, not project architecture)
2. Missing MS Learn references throughout skill documentation
3. Broken references to `examples/` directory (does not exist)

### Context
**Current Documentation State**:
- README.md: Accurate, up-to-date
- specs/requirements.md: Comprehensive, correct
- .claude/skills/azure-haymaker/: Multiple issues identified

**Why This Feature**:
- Accurate documentation is critical for development and operations
- Broken references cause confusion
- MS Learn is authoritative source for Azure knowledge
- Skill documentation guides Claude Code in scenario generation

### Requirements

#### Functional Requirements

**FR4.1: Fix ARCHITECTURE_GUIDE.md**

**Issue**: Current file contains Azure Architecture Center patterns (50 scenarios), NOT project architecture.

**Fix**: Rename and create correct files:
1. Rename `ARCHITECTURE_GUIDE.md` → `AZURE_PATTERNS_REFERENCE.md`
2. Update title and description to clarify purpose
3. Create NEW `ARCHITECTURE_GUIDE.md` with actual project architecture:
   - System architecture diagram (components, data flow)
   - Orchestrator design (timer trigger, durable functions)
   - Agent design (Container Apps, autonomous execution)
   - Storage architecture (Blob, Table, Cosmos, Service Bus)
   - Security architecture (Key Vault, Managed Identity, VNet)
   - Deployment architecture (Azure Functions, Infrastructure)

**FR4.2: Add MS Learn References**

**Issue**: Skill documentation lacks authoritative Azure documentation links.

**Fix**: Add MS Learn references to all skill documentation files:
- SKILL.md: Add "References" section with key MS Learn links
- ENTRA_ID_GUIDE.md: Add MS Learn Entra ID documentation
- TROUBLESHOOTING.md: Link to Azure troubleshooting guides
- AZURE_PATTERNS_REFERENCE.md: Ensure all patterns link to MS Learn

**Required MS Learn Links**:
```markdown
### Core Azure Documentation
- [Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/)
- [Azure CLI Reference](https://learn.microsoft.com/en-us/cli/azure/)
- [Azure Bicep Documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [Terraform on Azure](https://learn.microsoft.com/en-us/azure/developer/terraform/)

### Azure Services
- [Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Storage](https://learn.microsoft.com/en-us/azure/storage/)
- [Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/)
- [Azure Service Bus](https://learn.microsoft.com/en-us/azure/service-bus-messaging/)
- [Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/)

### Entra ID (Identity)
- [Entra ID Documentation](https://learn.microsoft.com/en-us/entra/identity/)
- [Service Principals](https://learn.microsoft.com/en-us/entra/identity-platform/app-objects-and-service-principals)
- [RBAC](https://learn.microsoft.com/en-us/azure/role-based-access-control/)
```

**FR4.3: Fix/Remove Broken Examples References**

**Issue**: Documentation references `examples/` directory that doesn't exist.

**Fix**: Search all documentation for `examples/` references:
- If example is relevant: Create the example file
- If example is not needed: Remove the reference
- Update documentation to reflect actual file locations

**Files to Check**:
- All `.md` files in `.claude/skills/azure-haymaker/`
- All `.md` files in `docs/`
- All `.md` files in `specs/`

**FR4.4: Documentation Consistency Review**

Ensure all documentation follows consistent structure:
- Proper markdown formatting
- Working internal links (verify with markdown linter)
- Consistent heading hierarchy
- Code blocks properly formatted with language tags
- Tables properly formatted

#### Non-Functional Requirements

**NFR4.1: Accuracy**
- All links must be valid (checked with link validator)
- All code examples must be syntactically correct
- All file references must point to existing files

**NFR4.2: Completeness**
- All Azure services used by project documented
- All configuration options documented
- All troubleshooting scenarios documented

**NFR4.3: Maintainability**
- Documentation structure makes updates easy
- Links use canonical URLs (MS Learn, not temporary redirects)
- Version information included where applicable

### Implementation Scope

#### In Scope

1. **Renamed Files**:
   - `ARCHITECTURE_GUIDE.md` → `AZURE_PATTERNS_REFERENCE.md`

2. **New Files**:
   - `.claude/skills/azure-haymaker/ARCHITECTURE_GUIDE.md` (NEW - actual project architecture)
   - `.claude/skills/azure-haymaker/MS_LEARN_REFERENCES.md` (NEW - consolidated reference links)

3. **Modified Files**:
   - `.claude/skills/azure-haymaker/SKILL.md` (add MS Learn references)
   - `.claude/skills/azure-haymaker/ENTRA_ID_GUIDE.md` (add MS Learn references)
   - `.claude/skills/azure-haymaker/TROUBLESHOOTING.md` (add MS Learn references)
   - `.claude/skills/azure-haymaker/AZURE_PATTERNS_REFERENCE.md` (update title/description)
   - All files with broken `examples/` references

4. **Validation**:
   - Run markdown linter on all .md files
   - Run link validator on all documentation
   - Manual review of all changes

#### Out of Scope

- Rewriting scenario documents (already correct)
- Adding diagrams (future enhancement)
- Video tutorials
- Interactive documentation
- Automated documentation generation

### Success Criteria

#### Acceptance Criteria (Testable)

**File Structure**:
- [ ] ARCHITECTURE_GUIDE.md contains project architecture (not Azure patterns)
- [ ] AZURE_PATTERNS_REFERENCE.md contains Azure patterns (renamed correctly)
- [ ] MS_LEARN_REFERENCES.md exists with all key Azure documentation links

**MS Learn References**:
- [ ] SKILL.md includes "References" section with MS Learn links
- [ ] ENTRA_ID_GUIDE.md links to MS Learn Entra ID docs
- [ ] TROUBLESHOOTING.md links to Azure troubleshooting guides
- [ ] All Azure service names link to MS Learn documentation

**Broken References**:
- [ ] Zero references to non-existent `examples/` directory
- [ ] All file references point to existing files
- [ ] All internal links work (verified by linter)

**Quality**:
- [ ] All external links are valid (verified by link checker)
- [ ] All code blocks have language tags
- [ ] Markdown formatting is consistent
- [ ] No broken images or diagrams
- [ ] All tables render correctly

**Validation**:
- [ ] Markdown linter passes (0 errors, 0 warnings)
- [ ] Link validator passes (0 broken links)
- [ ] Manual review completed and approved

#### Quality Metrics

- **Link Validity**: 100% (all links checked and working)
- **Markdown Lint Score**: 100% (zero errors)
- **Documentation Completeness**: All Azure services documented
- **Reference Coverage**: All skill docs include MS Learn references

### Dependencies

**Internal Dependencies**:
- None (pure documentation changes)

**External Dependencies**:
- Markdown linter (markdownlint-cli)
- Link validator (markdown-link-check)

**Blockers**:
- None (can implement immediately)

### Risk Assessment

**Risk Level**: **Low**

**Risks Identified**:

1. **Risk**: Breaking existing documentation links
   - **Impact**: Medium (user confusion)
   - **Probability**: Low (validation tools catch broken links)
   - **Mitigation**: Link validator, manual review
   - **Residual Risk**: Very Low

2. **Risk**: Incorrect project architecture documentation
   - **Impact**: Medium (misleading developers)
   - **Probability**: Low (review by project lead)
   - **Mitigation**: Technical review, comparison with actual implementation
   - **Residual Risk**: Very Low

3. **Risk**: MS Learn links become outdated
   - **Impact**: Low (MS Learn maintains redirects)
   - **Probability**: Medium (Microsoft reorganizes docs)
   - **Mitigation**: Use canonical URLs, periodic link validation
   - **Residual Risk**: Low

**Security Considerations**:
- None (documentation only)

### Complexity Assessment

**Complexity**: **Simple**

**Justification**:
- Documentation changes only (no code)
- Clear issues identified
- Straightforward fixes
- Validation tools available
- Low risk of breaking changes

**Effort Estimate**: **1-2 days**

**Breakdown**:
- Rename and update ARCHITECTURE_GUIDE.md: 2 hours
- Create new ARCHITECTURE_GUIDE.md: 3 hours
- Add MS Learn references (all files): 2 hours
- Fix broken examples/ references: 1 hour
- Run validation tools: 1 hour
- Manual review and corrections: 2 hours

### Priority

**Priority**: **Medium**

**Rationale**:
- Improves documentation quality
- Low effort, high value
- Fixes discovered during QA
- Not blocking other features
- Should be fixed before production launch

### Implementation Notes

**New ARCHITECTURE_GUIDE.md Structure**:

```markdown
# Azure HayMaker Architecture Guide

## Overview

Azure HayMaker is an orchestration service that simulates realistic Azure tenant activity by deploying and managing 50+ operational scenarios using autonomous goal-seeking agents.

## System Architecture

### Components

1. **Orchestrator** (Azure Functions)
   - Timer Trigger: 4x daily execution
   - Durable Functions: Long-running workflow orchestration
   - Activities: Validation, provisioning, monitoring, cleanup

2. **Agents** (Azure Container Apps)
   - Autonomous execution (8 hours)
   - Scenario-specific infrastructure deployment
   - Self-healing and troubleshooting
   - Resource cleanup

3. **Storage Layer**
   - Blob Storage: Logs, state, reports, scenarios
   - Table Storage: Execution tracking, resource inventory
   - Cosmos DB: Real-time metrics

4. **Messaging** (Azure Service Bus)
   - Agent log ingestion
   - Real-time status updates

5. **Secrets Management** (Azure Key Vault)
   - Service principal credentials
   - API keys
   - Connection strings

### Data Flow

[Diagram showing: Timer → Orchestrator → SP Creation → Container Deployment → Agent Execution → Cleanup]

## Orchestrator Design

### Workflow Phases

1. **Validation**: Verify credentials, quotas, prerequisites
2. **Selection**: Random scenario selection based on simulation_size
3. **Provisioning**: Create SPs, deploy Container Apps (parallel)
4. **Monitoring**: 8-hour execution period with status checks
5. **Cleanup**: Verify agent cleanup, force-delete remaining resources
6. **Reporting**: Generate execution summary

### Durable Functions Orchestration

[Details about orchestration pattern, checkpointing, retry logic]

## Agent Design

### Agent Lifecycle

1. **Instantiation**: Container App created with scenario document
2. **Deployment**: Agent deploys infrastructure using CLI/Terraform/Bicep
3. **Operation**: Benign management operations (8 hours)
4. **Troubleshooting**: Goal-seeking behavior for issue resolution
5. **Cleanup**: Complete resource teardown

### Agent Architecture

- Base Container Image (includes Azure CLI, Terraform, Bicep)
- Claude Code integration for autonomous decision-making
- Logging infrastructure (Service Bus client)
- Resource tagging (all resources tagged AzureHayMaker-managed)

## Storage Architecture

[Details about storage containers, tables, Cosmos DB containers]

## Security Architecture

[Details about Managed Identity, Key Vault, VNet integration, RBAC]

## Deployment Architecture

[Details about GitOps, Infrastructure-as-Code, environments]

## References

- [Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [Azure Durable Functions](https://learn.microsoft.com/en-us/azure/azure-functions/durable/)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)
```

**Validation Commands**:

```bash
# Install tools
npm install -g markdownlint-cli markdown-link-check

# Run markdown linter
markdownlint '**/*.md' --ignore node_modules --ignore .venv

# Run link checker
find . -name '*.md' -not -path './node_modules/*' -not -path './.venv/*' \
  -exec markdown-link-check {} \;

# Check for broken examples/ references
grep -r "examples/" --include="*.md" .
```

**Testing Strategy**:
- Run validation tools before committing
- Manual review of each modified file
- Check all MS Learn links manually (sample 20%)
- Verify renamed file doesn't break existing references
- Test documentation rendering (GitHub markdown preview)

---

## Feature 5: CLI Client for Service Management

### Type
**Feature** - Command-line interface for service operations

### Objective
Build a comprehensive CLI client for Azure HayMaker that provides visibility into service operations, metrics, running agents, and resource inventory, plus ability to inject new operations like cleanup and agent deployment, with corresponding backend services.

### User Requirements (Preserved Exactly)
> "show service metrics"
> "show which agents are running"
> "show all resources that are tagged by the service (grouped by type)"
> "inject new operations such as cleanup or deploy new agents"
> "you will need backend services for each of these"

### Context
**Current Management Interface**: None
- No visibility into service operations
- No ability to query metrics or status
- No resource inventory visibility
- No manual operation injection
- Azure Portal is only way to check service status

**Why This Feature**:
- Operational visibility: See what the service is doing
- Troubleshooting: Understand issues quickly
- Resource management: Know what resources exist
- Manual operations: Trigger cleanup or deployments when needed
- Developer experience: No need to navigate Azure Portal

### Requirements

#### Functional Requirements

**FR5.1: CLI Installation and Configuration**

**Installation**:
- Python package installable via `pip install azure-haymaker-cli`
- Entry point: `haymaker` command
- Global installation or venv installation supported

**Configuration**:
- Configuration file: `~/.haymaker/config.toml`
- Environment variables: `HAYMAKER_*` prefix
- Configuration includes:
  - Azure subscription ID
  - Azure tenant ID
  - Orchestrator API endpoint
  - Authentication method (Azure AD, Function Key)

**FR5.2: Command: `haymaker metrics`**

**Purpose**: Show service execution metrics and statistics.

**Output**:
```
Azure HayMaker - Service Metrics
=================================

Execution Summary:
  Total Runs:               156
  Successful Runs:          148 (94.9%)
  Failed Runs:              8 (5.1%)
  Average Duration:         8h 12m

Scenario Execution (Last 30 Days):
  Scenarios Executed:       2,340
  Unique Scenarios:         47
  Most Executed:            ai-ml-01-cognitive-services-vision (68 times)

Resource Statistics:
  Total Resources Created:  12,458
  Resources Cleaned Up:     12,450 (99.9%)
  Orphaned Resources:       8 (0.1%)

Cost (Estimated):
  Last Run:                 $47.23
  Last 7 Days:              $324.56
  Last 30 Days:             $1,389.12

Last 5 Runs:
  2025-11-15 12:00 UTC  [COMPLETED]  5 scenarios, 8h 15m, $47.23
  2025-11-15 06:00 UTC  [COMPLETED]  5 scenarios, 8h 11m, $45.67
  2025-11-15 00:00 UTC  [FAILED]    2 scenarios, 3h 45m, $12.34
  2025-11-14 18:00 UTC  [COMPLETED]  5 scenarios, 8h 09m, $46.12
  2025-11-14 12:00 UTC  [COMPLETED]  5 scenarios, 8h 13m, $48.01
```

**Data Sources**:
- Table Storage (ExecutionRuns table)
- Cosmos DB (metrics container)
- Azure Cost Management API

**FR5.3: Command: `haymaker agents`**

**Purpose**: Show currently running agents and their status.

**Usage**:
```bash
haymaker agents                    # Show running agents
haymaker agents --all              # Show all agents (including completed)
haymaker agents --run-id <uuid>    # Show agents for specific run
```

**Output**:
```
Azure HayMaker - Active Agents
===============================

Run ID: 550e8400-e29b-41d4-a716-446655440000
Started: 2025-11-15 12:00:00 UTC
Status: RUNNING (4h 23m elapsed)

Agents:
  ai-ml-01-cognitive-services-vision
    Container: haymaker-550e8400-ai-ml-01
    Status: RUNNING
    Phase: OPERATION (Mid-Day Operations)
    Resources: 7 created, 0 errors
    Last Update: 2025-11-15 16:15:23 UTC

  databases-01-mysql-wordpress
    Container: haymaker-550e8400-databases-01
    Status: RUNNING
    Phase: OPERATION (Mid-Day Operations)
    Resources: 12 created, 0 errors
    Last Update: 2025-11-15 16:18:45 UTC

  compute-03-app-service-python
    Container: haymaker-550e8400-compute-03
    Status: RUNNING
    Phase: OPERATION (Mid-Day Operations)
    Resources: 5 created, 0 errors
    Last Update: 2025-11-15 16:20:12 UTC

Total: 3 agents running, 24 resources deployed
```

**Data Sources**:
- Table Storage (ScenarioStatus table)
- Azure Container Apps API (container status)
- Service Bus (agent log messages)

**FR5.4: Command: `haymaker resources`**

**Purpose**: Show all resources tagged by the service, grouped by type.

**Usage**:
```bash
haymaker resources                    # Show all managed resources
haymaker resources --group-by type    # Group by resource type (default)
haymaker resources --group-by scenario # Group by scenario
haymaker resources --run-id <uuid>    # Show resources for specific run
haymaker resources --orphaned         # Show only orphaned resources
```

**Output**:
```
Azure HayMaker - Managed Resources
===================================

Resource Group: azure-haymaker-rg
Tagged: AzureHayMaker-managed

Grouped by Resource Type:
--------------------------

Virtual Machines (3):
  haymaker-compute-01-vm-20251115120045
    Scenario: compute-01-linux-vm-web-server
    Run ID: 550e8400-e29b-41d4-a716-446655440000
    Created: 2025-11-15 12:15:23 UTC
    Status: Running
    Size: Standard_D2s_v3
    Cost/Day: $2.34

  haymaker-compute-02-vm-20251115120112
    Scenario: compute-02-windows-vm-iis
    Run ID: 550e8400-e29b-41d4-a716-446655440000
    Created: 2025-11-15 12:17:45 UTC
    Status: Running
    Size: Standard_D2s_v3
    Cost/Day: $2.34

Storage Accounts (5):
  [List of storage accounts with details]

SQL Databases (2):
  [List of databases with details]

Container Apps (3):
  [List of container apps with details]

Total: 45 resources across 12 resource types
Estimated Cost/Day: $87.23
```

**Data Sources**:
- Azure Resource Graph API (tagged resources)
- Table Storage (ResourceInventory table)
- Azure Cost Management API (cost estimates)

**FR5.5: Command: `haymaker cleanup`**

**Purpose**: Manually trigger cleanup operation for specific run or all orphaned resources.

**Usage**:
```bash
haymaker cleanup --run-id <uuid>    # Cleanup specific run
haymaker cleanup --orphaned         # Cleanup all orphaned resources
haymaker cleanup --dry-run          # Show what would be cleaned up
```

**Output**:
```
Azure HayMaker - Cleanup Operation
===================================

Target: Orphaned resources (no active run)
Mode: DRY RUN (no resources will be deleted)

Resources to Clean Up:
  Virtual Machines (2):
    haymaker-compute-01-vm-20251114060034
    haymaker-compute-02-vm-20251114060112

  Storage Accounts (1):
    haymakerstorage20251114060145

  SQL Databases (1):
    haymaker-db-20251114060223

Total: 4 resources, estimated $12.45/day

Run cleanup without --dry-run to delete these resources.

Proceed with cleanup? [y/N]:
```

**Safety**:
- Dry-run mode by default
- Confirmation prompt before deletion
- Cannot delete resources from active runs (safety check)
- Audit trail logged to Azure Monitor

**FR5.6: Command: `haymaker deploy`**

**Purpose**: Manually trigger deployment of specific scenarios (on-demand execution).

**Usage**:
```bash
haymaker deploy --scenario ai-ml-01-cognitive-services-vision
haymaker deploy --scenarios ai-ml-01,databases-01,compute-03
haymaker deploy --scenario-file scenarios.txt
haymaker deploy --duration 2h
```

**Output**:
```
Azure HayMaker - Manual Deployment
===================================

Scenarios: ai-ml-01-cognitive-services-vision, databases-01-mysql-wordpress
Duration: 8 hours
Run Mode: On-Demand

Initiating deployment...

Run ID: 7c9e6679-7425-40de-944b-e07fc1f9056b
Status: ACCEPTED

Provisioning:
  Creating service principals... DONE (2 SPs created)
  Deploying container apps...   DONE (2 containers deployed)

Agents started successfully!

Monitor progress:
  haymaker agents --run-id 7c9e6679-7425-40de-944b-e07fc1f9056b

Estimated completion: 2025-11-15 20:15:00 UTC
```

**Delegates to**: On-Demand Agent Execution API (Feature 3)

**FR5.7: Additional Commands**

**`haymaker status`**: Overall service health and status
```bash
haymaker status
```

**`haymaker logs`**: Retrieve agent logs
```bash
haymaker logs --run-id <uuid>
haymaker logs --agent <scenario-name>
haymaker logs --tail
```

**`haymaker config`**: Manage CLI configuration
```bash
haymaker config set api-endpoint <url>
haymaker config get api-endpoint
haymaker config list
```

#### Non-Functional Requirements

**NFR5.1: Usability**
- Intuitive command structure (follows Unix conventions)
- Helpful error messages
- Progress indicators for long operations
- Colorized output (optional, can disable)
- JSON output option for scripting (--json flag)

**NFR5.2: Performance**
- Commands respond in < 3 seconds (95th percentile)
- Pagination for large result sets
- Caching for repeated queries (TTL: 30 seconds)

**NFR5.3: Security**
- Authentication required (Azure AD or Function Key)
- Credentials stored securely (OS keychain)
- No secrets in command history
- Audit trail for all operations

**NFR5.4: Reliability**
- Graceful handling of API failures
- Retry logic with exponential backoff
- Offline mode (show cached data if API unavailable)
- Clear error messages with remediation steps

### Implementation Scope

#### In Scope

**CLI Package**:
1. **New Repository**: `azure-haymaker-cli` (separate from main repo)
   - Python package structure
   - Entry point: `haymaker` command
   - Click framework for CLI
   - Rich library for formatted output

2. **CLI Commands** (`src/haymaker_cli/commands/`):
   - `metrics.py` - Service metrics command
   - `agents.py` - Running agents command
   - `resources.py` - Resource inventory command
   - `cleanup.py` - Manual cleanup command
   - `deploy.py` - Manual deployment command
   - `status.py` - Service status command
   - `logs.py` - Agent logs command
   - `config.py` - Configuration management

3. **API Client** (`src/haymaker_cli/client/`):
   - `api_client.py` - HTTP client for backend APIs
   - `auth.py` - Azure AD authentication
   - `cache.py` - Response caching

4. **Backend APIs** (new Azure Functions):
   - `GET /api/metrics` - Service metrics
   - `GET /api/agents` - Running agents list
   - `GET /api/resources` - Resource inventory
   - `POST /api/cleanup` - Trigger cleanup
   - `POST /api/deploy` - Trigger deployment (delegates to Feature 3)
   - `GET /api/status` - Service health status
   - `GET /api/logs/{run_id}` - Agent logs

5. **Backend Modules** (`src/azure_haymaker/orchestrator/api/`):
   - `metrics_service.py` - Metrics aggregation
   - `agents_service.py` - Agent status tracking
   - `resources_service.py` - Resource inventory queries
   - `cleanup_service.py` - Cleanup orchestration
   - `logs_service.py` - Log retrieval

#### Out of Scope

- Web UI (CLI only for now)
- Real-time streaming (polling only)
- Cost optimization recommendations (show costs only)
- Alerting/notifications (separate feature)
- Multi-tenant support (single tenant only)
- Agent log search (retrieve logs only, no search)
- Historical trend analysis (show metrics only)

### Success Criteria

#### Acceptance Criteria (Testable)

**CLI Installation**:
- [ ] `pip install azure-haymaker-cli` succeeds
- [ ] `haymaker --version` returns correct version
- [ ] `haymaker --help` shows all commands

**CLI Configuration**:
- [ ] `haymaker config set` stores configuration
- [ ] `haymaker config get` retrieves configuration
- [ ] Configuration file created at `~/.haymaker/config.toml`

**Metrics Command**:
- [ ] `haymaker metrics` shows execution summary
- [ ] Metrics include success rate, duration, scenario stats
- [ ] Cost estimates displayed (last run, 7 days, 30 days)
- [ ] Last 5 runs displayed with status

**Agents Command**:
- [ ] `haymaker agents` shows currently running agents
- [ ] Agent details include status, phase, resource counts
- [ ] `haymaker agents --run-id <uuid>` filters by run ID
- [ ] `haymaker agents --all` includes completed agents

**Resources Command**:
- [ ] `haymaker resources` lists all managed resources
- [ ] Resources grouped by type by default
- [ ] `haymaker resources --orphaned` shows orphaned resources only
- [ ] Resource details include scenario, run ID, created time, cost

**Cleanup Command**:
- [ ] `haymaker cleanup --dry-run` shows resources without deleting
- [ ] `haymaker cleanup --orphaned` prompts for confirmation
- [ ] Cleanup operation logged to Azure Monitor
- [ ] Cannot delete resources from active runs

**Deploy Command**:
- [ ] `haymaker deploy --scenario <name>` triggers deployment
- [ ] Deployment returns run ID for tracking
- [ ] Progress displayed during provisioning
- [ ] Estimated completion time shown

**Backend APIs**:
- [ ] All 7 backend API endpoints implemented
- [ ] APIs return correct data format
- [ ] APIs require authentication
- [ ] APIs respond in < 3 seconds (95th percentile)

**Quality**:
- [ ] All CLI commands have help text
- [ ] Error messages are clear and actionable
- [ ] JSON output mode works (`--json` flag)
- [ ] Unit tests for all CLI commands
- [ ] Integration tests for API endpoints

#### Quality Metrics

- **CLI Test Coverage**: > 80%
- **Backend API Test Coverage**: > 90%
- **API Response Time**: < 3 seconds (95th percentile)
- **CLI Command Success Rate**: > 95% (valid inputs)
- **Documentation Coverage**: All commands documented

### Dependencies

**Internal Dependencies**:
- Feature 3 (On-Demand Execution API) - for deploy command
- Table Storage schema - for metrics and agents queries
- Cosmos DB schema - for metrics queries
- Service Bus - for log retrieval

**External Dependencies**:
- Click (CLI framework)
- Rich (formatted output)
- Azure SDK for Python (API calls)
- Requests or httpx (HTTP client)

**Blockers**:
- None (can implement immediately)

### Risk Assessment

**Risk Level**: **Medium**

**Risks Identified**:

1. **Risk**: API performance degradation (slow queries)
   - **Impact**: High (poor user experience)
   - **Probability**: Medium (complex queries)
   - **Mitigation**: Response caching, query optimization, pagination
   - **Residual Risk**: Low

2. **Risk**: Accidental resource deletion via cleanup
   - **Impact**: Critical (data loss)
   - **Probability**: Low (confirmation prompts)
   - **Mitigation**: Dry-run default, confirmation prompt, cannot delete active runs
   - **Residual Risk**: Very Low

3. **Risk**: CLI version compatibility with backend API
   - **Impact**: Medium (CLI breaks)
   - **Probability**: Medium (API changes)
   - **Mitigation**: API versioning, backward compatibility, version checking
   - **Residual Risk**: Low

4. **Risk**: Authentication token expiration during operation
   - **Impact**: Medium (operation fails)
   - **Probability**: Low (token refresh)
   - **Mitigation**: Automatic token refresh, clear error messages
   - **Residual Risk**: Very Low

**Security Considerations**:
- All API calls authenticated
- Credentials stored in OS keychain (not plaintext)
- Audit trail for destructive operations (cleanup, deploy)
- No secrets displayed in output

### Complexity Assessment

**Complexity**: **Complex**

**Justification**:
- Two components (CLI + Backend APIs)
- Multiple commands with rich functionality
- Cross-service data aggregation (Table Storage + Cosmos DB + Azure APIs)
- Authentication and authorization
- Output formatting and user experience
- Error handling across distributed system
- Separate package/repository

**Effort Estimate**: **7-10 days**

**Breakdown**:
- Backend API endpoints: 3 days
- CLI framework and commands: 3 days
- Authentication and configuration: 1 day
- Testing (CLI + APIs): 2 days
- Documentation: 1 day

### Priority

**Priority**: **Medium**

**Rationale**:
- High value for operations and troubleshooting
- Not blocking other features
- Nice-to-have for initial launch, essential for production operations
- Can be delivered incrementally (start with read-only commands)

### Implementation Notes

**CLI Technology Stack**:
- **Framework**: Click (Python CLI framework)
- **Output**: Rich (formatted tables, colors, progress bars)
- **HTTP Client**: httpx (async HTTP client)
- **Authentication**: azure-identity (Azure AD)
- **Configuration**: TOML format (simple, readable)

**CLI Package Structure**:

```
azure-haymaker-cli/
├── src/
│   └── haymaker_cli/
│       ├── __init__.py
│       ├── cli.py                 # Main CLI entry point
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── metrics.py
│       │   ├── agents.py
│       │   ├── resources.py
│       │   ├── cleanup.py
│       │   ├── deploy.py
│       │   ├── status.py
│       │   ├── logs.py
│       │   └── config.py
│       ├── client/
│       │   ├── __init__.py
│       │   ├── api_client.py      # HTTP client
│       │   ├── auth.py            # Authentication
│       │   └── cache.py           # Response caching
│       ├── formatters/
│       │   ├── __init__.py
│       │   ├── table.py           # Table output
│       │   ├── json.py            # JSON output
│       │   └── tree.py            # Tree output
│       └── config/
│           ├── __init__.py
│           └── manager.py         # Config management
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   ├── installation.md
│   ├── commands.md
│   └── configuration.md
├── pyproject.toml
└── README.md
```

**Backend API Example** (metrics_service.py):

```python
"""Service for aggregating and computing execution metrics."""

from datetime import UTC, datetime, timedelta
from typing import Any

from azure.data.tables import TableServiceClient
from azure.cosmos import CosmosClient


class MetricsService:
    """Service for retrieving execution metrics and statistics."""

    def __init__(
        self,
        table_service_client: TableServiceClient,
        cosmos_client: CosmosClient,
    ):
        self.table_client = table_service_client
        self.cosmos_client = cosmos_client

    async def get_execution_summary(
        self,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get execution summary statistics.

        Args:
            days: Number of days to include in summary

        Returns:
            Dictionary with execution summary:
            {
                "total_runs": int,
                "successful_runs": int,
                "failed_runs": int,
                "average_duration_hours": float,
                "last_5_runs": [...]
            }
        """
        # Query ExecutionRuns table
        table = self.table_client.get_table_client("ExecutionRuns")

        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        query = f"Timestamp ge datetime'{cutoff_date.isoformat()}'"
        runs = table.query_entities(query)

        # Aggregate statistics
        total_runs = 0
        successful_runs = 0
        failed_runs = 0
        total_duration_seconds = 0

        for run in runs:
            total_runs += 1
            if run.get("Status") == "completed":
                successful_runs += 1
            elif run.get("Status") == "failed":
                failed_runs += 1

            duration = run.get("DurationSeconds", 0)
            total_duration_seconds += duration

        average_duration_hours = (
            total_duration_seconds / total_runs / 3600 if total_runs > 0 else 0
        )

        # Get last 5 runs
        recent_runs_query = "$top=5&$orderby=Timestamp desc"
        recent_runs = list(table.query_entities(recent_runs_query))

        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
            "average_duration_hours": average_duration_hours,
            "last_5_runs": [
                {
                    "run_id": run["RowKey"],
                    "started_at": run["Timestamp"],
                    "status": run["Status"],
                    "scenario_count": run.get("ScenarioCount", 0),
                    "duration_hours": run.get("DurationSeconds", 0) / 3600,
                }
                for run in recent_runs
            ],
        }
```

**CLI Command Example** (metrics.py):

```python
"""CLI command for displaying service metrics."""

import click
from rich.console import Console
from rich.table import Table

from haymaker_cli.client import APIClient


@click.command()
@click.option(
    "--days",
    default=30,
    type=int,
    help="Number of days to include in summary (default: 30)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_context
def metrics(ctx: click.Context, days: int, output_json: bool) -> None:
    """Show service execution metrics and statistics.

    Examples:
        haymaker metrics
        haymaker metrics --days 7
        haymaker metrics --json
    """
    console = Console()

    try:
        # Get API client from context
        api_client: APIClient = ctx.obj["api_client"]

        # Fetch metrics
        with console.status("[bold blue]Fetching metrics..."):
            metrics_data = api_client.get_metrics(days=days)

        # Output JSON if requested
        if output_json:
            import json
            click.echo(json.dumps(metrics_data, indent=2))
            return

        # Display formatted output
        console.print("\n[bold cyan]Azure HayMaker - Service Metrics[/bold cyan]")
        console.print("=" * 60)

        # Execution Summary
        console.print("\n[bold]Execution Summary:[/bold]")
        console.print(f"  Total Runs:        {metrics_data['total_runs']}")
        console.print(
            f"  Successful Runs:   {metrics_data['successful_runs']} "
            f"({metrics_data['success_rate'] * 100:.1f}%)"
        )
        console.print(f"  Failed Runs:       {metrics_data['failed_runs']}")
        console.print(
            f"  Average Duration:  {metrics_data['average_duration_hours']:.1f}h"
        )

        # Last 5 Runs
        console.print("\n[bold]Last 5 Runs:[/bold]")
        runs_table = Table(show_header=True, header_style="bold magenta")
        runs_table.add_column("Started", style="dim")
        runs_table.add_column("Status")
        runs_table.add_column("Scenarios", justify="right")
        runs_table.add_column("Duration", justify="right")

        for run in metrics_data["last_5_runs"]:
            status_color = "green" if run["status"] == "completed" else "red"
            runs_table.add_row(
                run["started_at"],
                f"[{status_color}]{run['status'].upper()}[/{status_color}]",
                str(run["scenario_count"]),
                f"{run['duration_hours']:.1f}h",
            )

        console.print(runs_table)
        console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort()
```

**Implementation Order**:
1. Define backend API schemas (request/response models)
2. Implement backend API endpoints (start with metrics)
3. Test backend APIs with curl/Postman
4. Implement CLI framework and configuration
5. Implement read-only commands (metrics, agents, resources)
6. Implement destructive commands (cleanup, deploy)
7. Add authentication and error handling
8. Write comprehensive tests (CLI + APIs)
9. Write documentation (installation, commands, examples)

**Testing Strategy**:
- **Backend APIs**: Unit tests (mock Azure SDKs), integration tests (real Azure services)
- **CLI Commands**: Unit tests (mock API client), integration tests (real backend APIs)
- **E2E Tests**: Full workflow (configure CLI → run command → verify output)
- **Manual Testing**: Test all commands with real service

---

## Implementation Priority and Sequencing

### Recommended Implementation Order

Based on dependencies, complexity, and value:

1. **Feature 4: Documentation Fixes** (1-2 days, Low Risk, Medium Priority)
   - Unblocks other work (clarifies architecture)
   - Low complexity, immediate value
   - No dependencies

2. **Feature 1: .env Configuration Support** (2-4 hours, Low Risk, Medium Priority)
   - Simple implementation
   - Improves developer experience immediately
   - No dependencies

3. **Feature 3: On-Demand Agent Execution API** (2-3 days, Medium Risk, High Priority)
   - Required by Feature 5 (CLI deploy command)
   - Enables testing of other features
   - High value for development workflow

4. **Feature 2: GitOps Deployment Pipeline** (5-7 days, Medium Risk, High Priority)
   - Complex but critical for production
   - Enables automated deployments
   - Foundation for reliable operations

5. **Feature 5: CLI Client** (7-10 days, Medium Risk, Medium Priority)
   - Most complex feature
   - Depends on Feature 3
   - High value but not blocking

### Total Effort Estimate

**Total Development Time**: **18-27 days** (approximately 3.5-5.5 weeks)

**Breakdown**:
- Feature 1: 0.5 days
- Feature 2: 6 days (average)
- Feature 3: 2.5 days (average)
- Feature 4: 1.5 days (average)
- Feature 5: 8.5 days (average)

**With Testing, Review, and Buffer**: **4-6 weeks**

---

## Risk Summary Across All Features

### High-Risk Items Requiring Attention

1. **Feature 2: Deployment failure leaves inconsistent state**
   - Mitigation: Idempotent Bicep templates, pre-deployment validation

2. **Feature 5: Accidental resource deletion**
   - Mitigation: Dry-run default, confirmation prompts, active run checks

### Security Considerations Across Features

- **Feature 1**: .env files must not be committed (pre-commit hook)
- **Feature 2**: OIDC authentication, secrets never in git
- **Feature 3**: API authentication required, rate limiting
- **Feature 5**: Audit trail for destructive operations

### Cost Considerations

- **Feature 3**: On-demand runs could increase costs (rate limiting mitigates)
- **Feature 5**: Resource queries may increase API costs (caching mitigates)

---

## Success Metrics Summary

### Feature-Specific Metrics

**Feature 1** (.env support):
- Zero secrets committed to git: **100%**
- Backward compatibility: **100%** (all tests pass)

**Feature 2** (GitOps):
- Deployment success rate: **> 95%**
- Deployment duration: **< 15 minutes**

**Feature 3** (On-Demand API):
- API response time: **< 2 seconds**
- Request validation accuracy: **100%**

**Feature 4** (Documentation):
- Link validity: **100%**
- Markdown lint score: **100%**

**Feature 5** (CLI):
- CLI test coverage: **> 80%**
- API response time: **< 3 seconds**

### Overall Project Health Metrics

After all features implemented:
- **Feature Completeness**: 100% (5/5 features)
- **Test Coverage**: > 85% (across all new code)
- **Documentation Coverage**: 100% (all features documented)
- **Zero-BS Compliance**: 100% (no stubs, TODOs, or placeholders)
- **Production Readiness Score**: 95%+

---

## Next Steps

### Immediate Actions

1. **Review & Approval**: Stakeholder review of this specification document
2. **Resource Allocation**: Assign developers to features
3. **Environment Setup**: Ensure dev/staging/prod environments ready
4. **Kickoff Meeting**: Review specifications with implementation team

### Implementation Sequence

1. Start Feature 4 (Documentation Fixes) - Quick win, unblocks clarity
2. Parallel track: Feature 1 (.env support) - Quick, improves DX
3. Feature 3 (On-Demand API) - Required for Feature 5
4. Feature 2 (GitOps) - Critical for production
5. Feature 5 (CLI) - Final piece, most complex

### Quality Gates

Each feature must pass before merging:
- [ ] All acceptance criteria met
- [ ] Test coverage meets minimum thresholds
- [ ] Documentation complete
- [ ] Code review approved
- [ ] Zero-BS compliance verified
- [ ] Manual testing completed

---

## Appendices

### A. Glossary

- **GitOps**: Git-based operations, infrastructure-as-code via git commits
- **On-Demand Execution**: Manual triggering of agent execution outside schedule
- **Zero-BS Philosophy**: No stubs, TODOs, faked APIs, or placeholder implementations
- **Durable Functions**: Azure Functions pattern for long-running workflows
- **Service Principal**: Azure AD identity for applications/services

### B. References

- [Azure Functions Documentation](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [Azure Durable Functions](https://learn.microsoft.com/en-us/azure/azure-functions/durable/)
- [Azure Bicep Documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Click CLI Framework](https://click.palletsprojects.com/)
- [12-Factor App Methodology](https://12factor.net/)

### C. Document History

| Version | Date       | Author | Changes                          |
|---------|------------|--------|----------------------------------|
| 1.0     | 2025-11-15 | Claude | Initial comprehensive specification |

---

**End of Feature Specifications Document**
