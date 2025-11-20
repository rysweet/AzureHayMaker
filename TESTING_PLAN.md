# Mandatory Local Testing Plan for haymaker orch Commands

## Testing Requirements (Step 8 of DEFAULT_WORKFLOW.md)

Per USER_PREFERENCES.md learned patterns (2025-11-10):
> I always want you to test each PR like a user would, from the outside in, not just unit testing.

## Test Environment Setup

**Prerequisites**:
- Azure subscription with Container Apps orchestrator deployed
- Azure CLI authenticated (`az login`)
- Environment variables or config file with orchestrator settings

**Configuration**:
```bash
# Option 1: Environment variables
export AZURE_SUBSCRIPTION_ID="c190c55a-9ab2-4b1e-92c4-cc8b1a032285"
export AZURE_RESOURCE_GROUP="haymaker-dev-rg"
export HAYMAKER_ORCHESTRATOR_CONTAINER_APP_NAME="orch-dev-yc4hkcb2vv"

# Option 2: Config file (~/.haymaker/config.yaml)
orchestrator:
  subscription_id: c190c55a-9ab2-4b1e-92c4-cc8b1a032285
  resource_group: haymaker-dev-rg
  container_app_name: orch-dev-yc4hkcb2vv
```

## Test Cases

### Test 1: Installation and Import
```bash
# Install from branch (uvx --from git+...)
cd /home/azureuser/src/AzureHayMaker/worktrees/feat-issue-26-cli-commands
pip install -e cli/

# Verify import works
python -c "from haymaker_cli.orch import ContainerAppsClient, load_orchestrator_config; print('✓ Imports successful')"

# Verify command is registered
haymaker orch --help
```

**Expected**: Help text shows 4 commands (status, replicas, logs, health)

### Test 2: Configuration Loading
```bash
# Test with environment variables
export AZURE_SUBSCRIPTION_ID="test-sub"
export AZURE_RESOURCE_GROUP="test-rg"
haymaker orch status --app-name test-app

# Test with config file
haymaker orch status
```

**Expected**: Commands load config from ENV or file, show clear error if missing

### Test 3: haymaker orch status
```bash
# Basic status
haymaker orch status

# With specific app
haymaker orch status --app-name orch-dev-yc4hkcb2vv

# JSON output
haymaker orch status --format json

# YAML output
haymaker orch status --format yaml
```

**Expected**:
- Shows orchestrator endpoint
- Lists active revisions with traffic weights
- Displays health status for each revision
- JSON/YAML output is valid and parseable

### Test 4: haymaker orch replicas
```bash
# List replicas for latest revision
haymaker orch replicas --revision orch-dev-yc4hkcb2vv--0008

# Follow mode (Ctrl+C to exit)
haymaker orch replicas --revision orch-dev-yc4hkcb2vv--0008 --follow --interval 5

# JSON output
haymaker orch replicas --revision orch-dev-yc4hkcb2vv--0008 --format json
```

**Expected**:
- Shows replica STATUS, CPU, MEMORY, RESTARTS
- Follow mode polls every N seconds
- Ctrl+C exits gracefully
- JSON output valid

### Test 5: haymaker orch logs
```bash
# Show logs guidance
haymaker orch logs
haymaker orch logs --revision orch-dev-yc4hkcb2vv--0008
```

**Expected**:
- Shows helpful message with Azure Portal link
- Provides Azure CLI command for actual log fetching
- Explains why direct log fetching isn't implemented yet

### Test 6: haymaker orch health
```bash
# Basic health checks
haymaker orch health

# Deep health checks
haymaker orch health --deep --timeout 60

# Verbose output
haymaker orch health --verbose

# JSON output
haymaker orch health --format json
```

**Expected**:
- Runs container app status check
- Checks endpoint connectivity (DNS, TCP)
- Validates replica health
- Deep mode adds HTTP endpoint checks
- Shows suggestions for failures
- JSON output valid

### Test 7: Error Handling
```bash
# Missing configuration
unset AZURE_SUBSCRIPTION_ID
haymaker orch status

# Invalid app name
haymaker orch status --app-name nonexistent-app

# Network error (disconnect network)
haymaker orch status
```

**Expected**:
- Exit code 1 for config errors with setup instructions
- Exit code 3 for API errors (404) with helpful message
- Exit code 2 for network errors with connectivity suggestions

### Test 8: Follow Mode Interruption
```bash
# Start follow mode
haymaker orch replicas --revision orch-dev-yc4hkcb2vv--0008 --follow

# Press Ctrl+C after 10 seconds
```

**Expected**:
- Polls continuously until interrupted
- Ctrl+C shows "Interrupted by user" message
- Exit code 0 (clean exit)

## Success Criteria

✅ All commands execute without Python errors
✅ Configuration loading works from ENV and file
✅ Output formats (table, JSON, YAML) are valid
✅ Error messages are clear and actionable
✅ Exit codes match specification (0-4)
✅ Follow modes work and handle Ctrl+C gracefully
✅ Health checks provide useful diagnostics
✅ Azure SDK integration works correctly

## Test Results

**Tested By**: _____________________
**Date**: _____________________
**Environment**: Azure subscription c190c55a-9ab2-4b1e-92c4-cc8b1a032285

| Test Case | Status | Notes |
|-----------|--------|-------|
| Test 1: Installation | ⏳ | |
| Test 2: Configuration | ⏳ | |
| Test 3: status command | ⏳ | |
| Test 4: replicas command | ⏳ | |
| Test 5: logs command | ⏳ | |
| Test 6: health command | ⏳ | |
| Test 7: Error handling | ⏳ | |
| Test 8: Follow mode | ⏳ | |

## Notes

- Testing requires actual Azure Container Apps environment
- Can be tested against orch-dev-yc4hkcb2vv in subscription c190c55a-9ab2-4b1e-92c4-cc8b1a032285
- Container startup issue (Issue #26 Part 1) must be resolved first
- Once container is running, test all commands end-to-end

## Next Steps After Testing

1. Document test results in this file
2. Fix any bugs discovered during testing
3. Update PR description with test results
4. Mark Step 8 as complete in workflow
