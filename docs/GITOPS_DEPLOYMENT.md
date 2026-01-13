# GitOps Deployment

Fully automated GitOps deployment fer AzureHayMaker with secret injection, integration testin', and deployment verification.

## Quick Start

Push to any tracked branch - GitOps handles the rest automatically:

```bash
git push origin develop    # Deploys to dev environment
git push origin main        # Deploys to staging environment
```

The workflow automatically:
- Builds and deploys infrastructure
- Injects secrets with RBAC handling
- Runs integration tests
- Verifies deployment health
- Rolls back on any failure

## How It Works

### Automated Secret Injection

During GitHub Actions workflow deployment, the Secret Injection Handler automatically:

1. Waits for RBAC propagation (after managed identity role assignment)
2. Connects to Key Vault using managed identity
3. Retrieves Anthropic API key
4. Injects secret into orchestrator's environment variables
5. Restarts orchestrator with updated configuration

**No manual steps required.** The GitHub Actions workflow handles all secret injection before marking deployment as complete.

```python
# Example: Secret injection happens in GitHub Actions workflow
# .github/scripts/inject_secrets.py

handler = SecretInjectionHandler(
    subscription_id=subscription_id,
    resource_group=resource_group
)
handler.wait_for_rbac_propagation(keyvault_name, principal_id)
handler.inject_secrets_to_container_app(container_app_name, keyvault_name, secrets)
```

### Integration Test Framework

After deployment completes, integration tests automatically verify all CLI commands against the deployed API:

```bash
# Tests run automatically in GitHub Actions
# Tests ALL CLI commands:
- haymaker deploy
- haymaker resources list
- haymaker resources show <id>
- haymaker status
- haymaker cleanup
```

Tests verify:
- API endpoints respond correctly
- CLI authentication works
- Resource operations succeed
- Error messages are clear

**If any test fails, deployment is marked as failed.**

### Deployment Verification

After integration tests pass, the verification module checks:

1. Container app is running
2. All endpoints respond (health check, /api/resources, etc.)
3. Key Vault access is working
4. Logging is operational
5. Metrics are being collected

**Deployment is only marked successful after all verification checks pass.**

## Architecture

### Components

```
GitOps Workflow (.github/workflows/deploy.yml)
    ↓
Bicep Infrastructure (infra/)
    ↓
Container App with Secret Injection (infra/orchestrator/)
    ↓
Integration Tests (tests/integration/)
    ↓
Deployment Verification (infra/verify/)
```

### Secret Injection Handler

**Location**: `infra/orchestrator/secret_injection_handler.py`

**Purpose**: Automatically inject secrets from Key Vault into orchestrator environment

**Features**:
- Detects environment from AZURE_ENV variable
- Uses managed identity (no passwords)
- Intelligent RBAC propagation wait (exponential backoff)
- Verifies secret access before proceeding
- Comprehensive error messages

**Usage**:
```python
from secret_injection_handler import SecretInjectionHandler

# Called automatically in orchestrator startup
handler = SecretInjectionHandler()
handler.inject_secrets()  # Blocks until ready
```

### Integration Test Framework

**Location**: `tests/integration/`

**Purpose**: Verify all CLI commands work against deployed API

**Test Coverage**:
- `test_cli_deploy.py` - Deploy command with scenarios
- `test_cli_resources.py` - Resource listing and details
- `test_cli_status.py` - Status checking
- `test_cli_cleanup.py` - Resource cleanup
- `test_api_endpoints.py` - Direct API testing

**Running Tests Manually**:
```bash
# Set environment variables
export HAYMAKER_API_URL="https://orch-dev-xyz.azurecontainerapps.io"
export AZURE_SUBSCRIPTION_ID="your-sub-id"
export ANTHROPIC_API_KEY="your-api-key"

# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/test_cli_resources.py -v
```

### Deployment Verification Module

**Location**: `infra/verify/deployment_verifier.py`

**Purpose**: Verify deployment health before marking successful

**Checks Performed**:
1. Container app status (running/healthy)
2. API endpoint availability (/health, /api/resources)
3. Key Vault secret access
4. Log Analytics connectivity
5. Metrics collection

**Usage**:
```python
from deployment_verifier import DeploymentVerifier

verifier = DeploymentVerifier(
    environment="dev",
    subscription_id="your-sub-id"
)

result = verifier.verify_deployment()
if result.success:
    print("Deployment verified successfully")
else:
    print(f"Verification failed: {result.failures}")
```

### GitHub Actions Integration

**Workflow**: `.github/workflows/deploy.yml`

The workflow automatically runs these stages:

```yaml
1. Build & Deploy Infrastructure (Bicep)
   - Creates resource group
   - Deploys Container Apps environment
   - Deploys Key Vault
   - Creates container app with managed identity
   - Assigns RBAC roles

2. Secret Injection (Automatic in GitHub Actions)
   - Infrastructure deployment completes
   - GitHub Actions workflow waits for RBAC propagation
   - Retrieves secrets from Key Vault using managed identity
   - Injects secrets into container app environment variables
   - Restarts container with updated configuration

3. Integration Tests
   - Runs all CLI command tests
   - Verifies API endpoints
   - Tests authentication
   - Validates error handling

4. Deployment Verification
   - Checks container health
   - Verifies endpoint availability
   - Tests Key Vault access
   - Confirms logging works

5. Mark Deployment Status
   - Success: All checks pass
   - Failure: Any check fails (with detailed logs)
```

## Usage Guide

### Triggering a Deployment

**Automatic**:
- Push to `develop` branch → deploys to dev
- Push to `main` branch → deploys to staging
- Manual workflow trigger → deploys to prod (requires approval)

**Manual Trigger**:
```bash
# Via GitHub CLI
gh workflow run "Deploy to Development"

# Via GitHub UI
# Go to Actions → Deploy to Development → Run workflow
```

### Monitoring Deployment Progress

**Via GitHub CLI**:
```bash
# Watch latest deployment
gh run watch

# List recent deployments
gh run list --workflow="Deploy to Development" --limit 5
```

**Via GitHub UI**:
1. Go to Actions tab
2. Click on latest workflow run
3. View real-time logs for each stage

### What to Expect During Deployment

**Typical Timeline** (dev environment):
- Infrastructure deployment: 3-5 minutes
- Secret injection with RBAC wait: 1-2 minutes
- Integration tests: 2-3 minutes
- Deployment verification: 1 minute
- **Total: 7-11 minutes**

**Log Output**:
```
✓ Infrastructure deployed successfully
✓ Container app created: orch-dev-abc123
✓ Secret injection handler started
⟳ Waiting for RBAC propagation... (attempt 1/10)
✓ Secrets injected successfully
✓ Integration tests passed (15/15)
✓ Deployment verification passed (5/5 checks)
✓ Deployment completed successfully
```

### What Happens if Something Fails

**Secret Injection Failure**:
- Handler retries with exponential backoff (up to 10 attempts)
- Logs detailed error message
- Container fails to start (visible in GitHub Actions)
- Deployment marked as failed

**Integration Test Failure**:
- Specific test failure is logged
- Remaining tests still run (to see full extent of issues)
- Deployment marked as failed
- Container app remains deployed (for debugging)

**Verification Failure**:
- Specific check failure is logged
- Deployment marked as failed
- Container app remains deployed (for debugging)

## Troubleshooting Guide

### RBAC Propagation Delays

**Symptom**: Secret injection handler reports "Access denied" errors

**Cause**: Azure RBAC role assignments can take up to 5 minutes to propagate

**Solution**: The handler automatically retries with exponential backoff. If it fails after 10 attempts:

```bash
# Check RBAC assignments manually
az role assignment list \
  --assignee $(az containerapp show -n orch-dev-abc123 -g haymaker-dev-rg --query identity.principalId -o tsv) \
  --scope /subscriptions/YOUR_SUB_ID/resourceGroups/haymaker-dev-rg/providers/Microsoft.KeyVault/vaults/haymaker-dev-kv

# If missing, the bicep template needs to assign the role:
# infra/orchestrator.bicep lines 45-52
```

### Integration Test Failures

**Symptom**: Integration tests fail with "Connection refused" or "404 Not Found"

**Possible Causes**:
1. Container app not fully started
2. Incorrect container app name in bicep
3. API endpoint not implemented
4. Authentication issues

**Diagnosis**:
```bash
# 1. Check container app status
az containerapp show -n orch-dev-abc123 -g haymaker-dev-rg --query properties.runningStatus

# 2. Check container logs
az containerapp logs show -n orch-dev-abc123 -g haymaker-dev-rg --tail 50

# 3. Test API endpoint manually
curl https://orch-dev-abc123.azurecontainerapps.io/health

# 4. Verify CLI can connect
haymaker --api-url https://orch-dev-abc123.azurecontainerapps.io resources list
```

**Common Fixes**:
- Ensure container app name matches CLI expectations (`haymaker-fastapi-orch` or environment-specific)
- Verify Dockerfile builds correctly
- Check that all API endpoints are implemented
- Verify Anthropic API key is valid

### Deployment Verification Failures

**Symptom**: Verification step fails even though container is running

**Possible Causes**:
1. API endpoints responding slowly
2. Key Vault access still propagating
3. Log Analytics not connected

**Diagnosis**:
```bash
# 1. Check API response time
time curl https://orch-dev-abc123.azurecontainerapps.io/health

# 2. Check Key Vault access from container
az containerapp exec -n orch-dev-abc123 -g haymaker-dev-rg \
  --command "python -c 'from azure.identity import ManagedIdentityCredential; from azure.keyvault.secrets import SecretClient; client = SecretClient(vault_url=\"https://haymaker-dev-kv.vault.azure.net\", credential=ManagedIdentityCredential()); print(client.get_secret(\"anthropic-api-key\").value)'"

# 3. Check Log Analytics connection
az monitor log-analytics workspace show -n haymaker-dev-logs -g haymaker-dev-rg
```

### Re-running Failed Steps

**To retry just the integration tests**:
```bash
# SSH into container app (if needed for debugging)
az containerapp exec -n orch-dev-abc123 -g haymaker-dev-rg

# Run tests manually
export HAYMAKER_API_URL="https://orch-dev-abc123.azurecontainerapps.io"
export AZURE_SUBSCRIPTION_ID="your-sub-id"
pytest tests/integration/ -v
```

**To retry entire deployment**:
```bash
# Re-run the GitHub Actions workflow
gh run rerun <run-id>

# Or trigger a new deployment
git commit --allow-empty -m "Trigger deployment"
git push origin develop
```

**To fix and redeploy**:
```bash
# Make fixes in your branch
git add .
git commit -m "fix: Address deployment issue"
git push origin your-branch

# Merge and deploy
gh pr merge your-branch
# Deployment triggers automatically on merge to develop/main
```

## Testing Strategy

### What Gets Tested

**Unit Tests** (in codebase):
- Secret injection handler logic
- Deployment verifier checks
- CLI command parsing
- API request handling

**Integration Tests** (in GitHub Actions):
- End-to-end CLI workflows
- API endpoint availability
- Authentication flows
- Resource operations

**Verification Checks** (in GitHub Actions):
- Container health
- Endpoint availability
- Key Vault access
- Logging functionality

### Running Tests Manually

**Local Development**:
```bash
# Unit tests for secret injection
pytest infra/orchestrator/tests/test_secret_injection.py -v

# Unit tests for deployment verifier
pytest infra/verify/tests/test_deployment_verifier.py -v
```

**Against Deployed Environment**:
```bash
# Set environment variables
export HAYMAKER_API_URL="https://orch-dev-abc123.azurecontainerapps.io"
export AZURE_SUBSCRIPTION_ID="your-sub-id"
export ANTHROPIC_API_KEY="your-api-key"

# Run all integration tests
pytest tests/integration/ -v

# Run specific test category
pytest tests/integration/test_cli_resources.py -v
pytest tests/integration/test_api_endpoints.py -v
```

**Deployment Verification**:
```bash
# Run verification manually
python infra/verify/deployment_verifier.py \
  --environment dev \
  --subscription-id your-sub-id

# Check specific components
python infra/verify/deployment_verifier.py \
  --check container-health \
  --check endpoint-availability
```

## Related Documentation

- [GitOps Setup Guide](./GITOPS_SETUP.md) - Initial configuration and setup
- [Deployment Guide](./DEPLOYMENT.md) - Manual deployment procedures
- [CLI Guide](./CLI_GUIDE.md) - Using the haymaker CLI
- [Architecture](./ARCHITECTURE.md) - Overall system architecture

## Support

### Getting Help

If deployments are failing:

1. Check GitHub Actions logs for detailed error messages
2. Review container logs: `az containerapp logs show -n orch-dev-abc123 -g haymaker-dev-rg`
3. Test endpoints manually: `curl https://orch-dev-abc123.azurecontainerapps.io/health`
4. Check RBAC assignments: `az role assignment list --assignee <principal-id>`
5. File GitHub issue with logs and error messages

### Common Pitfalls

**Container app naming mismatch**:
- Bicep creates: `orch-dev-{suffix}`
- CLI expects: `haymaker-fastapi-orch`
- Solution: Bicep templates now create fixed names matching CLI expectations

**RBAC propagation**:
- Azure can take up to 5 minutes for role assignments to propagate
- Secret injection handler automatically waits and retries
- If it fails after 10 attempts, there's a deeper RBAC configuration issue

**Outdated container images**:
- GitHub Actions always builds fresh images
- Container apps automatically pull latest images
- If you see old code, check that the Dockerfile is building correctly

**Missing API endpoints**:
- Integration tests will fail if endpoints are not implemented
- Check that FastAPI routes are defined in `src/orchestrator/app.py`
- Verify container is running the latest code

## What Changed (Issue #181)

This document describes the **fixed** GitOps deployment system. Previously:

**Problems**:
- Manual secret injection required
- No integration tests
- No deployment verification
- Inconsistent container app naming
- RBAC propagation not handled

**Solutions**:
- Automatic secret injection with RBAC wait
- Comprehensive integration test framework
- Deployment verification module
- Fixed container app naming in bicep
- Intelligent retry logic for RBAC propagation

All manual steps have been eliminated. GitOps now works fully automatically from git push to verified deployment.
