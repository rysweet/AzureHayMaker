# TDD Test Summary: CLI AI Email Generation Options

**Test File**: `/home/azureuser/src/AzureHayMaker/cli/tests/test_kw_deploy_ai_options.py`

**Status**: ✅ Tests written FIRST (TDD approach)

**Current State**: All tests failing as expected (feature not yet implemented)

---

## Test Coverage Overview

### 1. Validation Tests (8 tests)
Tests input validation and error handling for CLI options:

- ✗ `test_email_directive_max_length_1000_chars_fails` - Directive >1000 chars should error
- ✗ `test_email_directive_exactly_1000_chars_succeeds` - Exactly 1000 chars should pass
- ✗ `test_marker_format_max_length_50_chars_fails` - Marker format >50 chars should error
- ✗ `test_marker_format_exactly_50_chars_succeeds` - Exactly 50 chars should pass
- ✗ `test_ai_enabled_without_api_key_fails` - No ANTHROPIC_API_KEY should error
- ✗ `test_ai_enabled_with_api_key_succeeds` - Valid API key should succeed
- ✗ `test_empty_directive_warns_and_sets_none` - Empty string should warn and use default
- ✗ `test_whitespace_only_directive_warns_and_sets_none` - Whitespace should warn

**Critical Validations**:
- Email directive: max 1000 characters
- Marker format: max 50 characters
- ANTHROPIC_API_KEY required when AI enabled
- Empty/whitespace directives handled gracefully

---

### 2. Config Construction Tests (6 tests)
Tests that CLI options correctly map to configuration objects:

- ✗ `test_enable_ai_generation_maps_to_config` - Maps to EmailGenerationConfig.enabled
- ✗ `test_email_directive_maps_to_config` - Maps to EmailGenerationConfig.directive
- ✗ `test_marker_config_maps_to_deployment_config` - Maps to DeploymentConfig marker fields
- ✗ `test_no_enable_markers_disables_markers` - Disables markers correctly
- ✗ `test_defaults_applied_when_options_not_provided` - Default values set properly
- ✗ `test_all_options_combined_work_correctly` - All options work together

**Expected Mappings**:
```python
CLI Option                    → Config Field
--enable-ai-generation        → email_generation.enabled = True
--email-directive "text"      → email_generation.directive = "text"
--marker-format "TEXT"        → marker_format = "TEXT"
--marker-style "hidden"       → marker_style = "hidden"
--enable-markers              → email_markers_enabled = True
--no-enable-markers           → email_markers_enabled = False
```

---

### 3. Dry-Run Output Tests (5 tests)
Tests output formatting and information display:

- ✗ `test_dry_run_shows_all_configurations` - All config details visible
- ✗ `test_dry_run_truncates_long_directives` - Directives >80 chars truncated with "..."
- ✗ `test_dry_run_shows_cost_warning_when_ai_enabled` - Cost warning displayed
- ✗ `test_dry_run_shows_marker_config_when_enabled` - Marker details shown
- ✗ `test_dry_run_does_not_show_marker_config_when_disabled` - Marker details hidden

**Expected Dry-Run Output**:
```
Preparing KW deployment...
  Name: test-deployment
  Workers: 25
  Department: operations
  Duration: 4h
  Endpoint Type: cli_container

  AI Email Generation: ENABLED
    Directive: Write emails about IT operations... (truncated)
    Estimated Cost: ~$2.50 for ~400 emails

  Email Markers: ENABLED
    Format: OPS-TEST
    Style: subject

Dry run - deployment not started
```

---

### 4. Environment Variable Tests (3 tests)
Tests API key handling from environment:

- ✗ `test_anthropic_api_key_from_env` - Reads from ANTHROPIC_API_KEY
- ✗ `test_missing_api_key_shows_helpful_error` - Clear error message when missing
- ✗ `test_api_key_not_checked_when_ai_disabled` - No check when AI disabled

**Expected Behavior**:
- AI enabled + no key = Error with helpful message
- AI enabled + valid key = Success
- AI disabled + no key = Success (key not needed)

---

### 5. Marker Style Validation Tests (2 tests)
Tests marker style option validation:

- ✗ `test_valid_marker_styles_accepted` - "subject", "hidden", "both" accepted
- ✗ `test_invalid_marker_style_fails` - Invalid styles rejected

**Valid Options**: `subject`, `hidden`, `both`

---

### 6. Boundary Condition Tests (4 tests)
Tests edge cases:

- ✓ `test_zero_workers_handled` - Zero workers handled gracefully (PASSING)
- ✗ `test_large_worker_count_with_ai_shows_cost_warning` - Prominent cost warning
- ✗ `test_directive_with_special_characters` - Special chars handled
- ✗ `test_marker_format_with_special_characters` - Special chars in markers

---

### 7. Option Interaction Tests (3 tests)
Tests interactions between options:

- ✗ `test_directive_without_enable_ai_shows_warning` - Warn if directive without AI
- ✗ `test_markers_work_without_ai_generation` - Markers independent of AI
- ✗ `test_ai_generation_works_without_custom_markers` - AI works with default markers

---

### 8. Integration Scenario Tests (3 tests)
Tests realistic end-to-end scenarios:

- ✗ `test_typical_ai_deployment_scenario` - Standard AI deployment
- ✗ `test_red_team_stealth_scenario` - Hidden markers for red team
- ✗ `test_cost_optimized_scenario` - No AI, markers only

---

## CLI Options to Implement

### AI Generation Options

```bash
--enable-ai-generation / --no-enable-ai-generation
    Enable AI-powered email content generation
    Default: False (disabled)
    Requires: ANTHROPIC_API_KEY environment variable

--email-directive TEXT
    Custom instructions for AI email generation
    Max length: 1000 characters
    Default: None (persona-based defaults)
    Example: "Write all emails as limericks"

--ai-model MODEL_NAME
    AI model to use for generation
    Default: SDK default (claude-3-5-sonnet or gpt-4-turbo)
    Examples: "claude-3-5-sonnet-20241022", "gpt-4-turbo"
```

### Email Marker Options

```bash
--enable-markers / --no-enable-markers
    Enable/disable email markers for tracking
    Default: True (enabled)

--marker-format TEXT
    Marker format prefix
    Max length: 50 characters
    Default: "MARKER"
    Example: "TEST-ID" → [TEST-ID:worker-00001]

--marker-style [subject|hidden|both]
    Marker placement style
    Default: "subject"
    Options:
        subject - Visible in email subject
        hidden  - Hidden HTML metadata in body
        both    - Both visible and hidden
```

---

## Implementation Checklist

When implementing the feature, ensure these tests pass:

### Phase 1: Add CLI Options
- [ ] Add `--enable-ai-generation` flag
- [ ] Add `--email-directive` option with validation
- [ ] Add `--ai-model` option
- [ ] Add `--enable-markers/--no-enable-markers` flag
- [ ] Add `--marker-format` option with validation
- [ ] Add `--marker-style` choice option

### Phase 2: Validation
- [ ] Validate directive max length (1000 chars)
- [ ] Validate marker format max length (50 chars)
- [ ] Check ANTHROPIC_API_KEY when AI enabled
- [ ] Handle empty/whitespace directives
- [ ] Validate marker style choices

### Phase 3: Config Construction
- [ ] Create EmailGenerationConfig from options
- [ ] Map to DeploymentConfig.email_generation
- [ ] Map marker options to DeploymentConfig fields
- [ ] Apply defaults when options not provided

### Phase 4: Dry-Run Output
- [ ] Display AI generation status
- [ ] Show directive (truncated if >80 chars)
- [ ] Show cost estimate when AI enabled
- [ ] Show marker configuration
- [ ] Format output clearly

### Phase 5: Error Handling
- [ ] Clear error messages for validation failures
- [ ] Helpful guidance for missing API key
- [ ] Warnings for option mismatches

---

## Test Execution

### Run all tests:
```bash
cd /home/azureuser/src/AzureHayMaker/cli
source .venv/bin/activate
pytest tests/test_kw_deploy_ai_options.py -v
```

### Run specific test class:
```bash
pytest tests/test_kw_deploy_ai_options.py::TestAIGenerationValidation -v
```

### Run with coverage:
```bash
pytest tests/test_kw_deploy_ai_options.py --cov=haymaker_cli.kw.commands --cov-report=term-missing
```

---

## Current Test Results

**Total Tests**: 34
**Passing**: 1 (3%)
**Failing**: 33 (97%)

**Status**: ✅ Expected (TDD - tests written first)

### Failure Reasons:
1. CLI options don't exist yet (`exit_code == 2` from Click)
2. `KnowledgeWorkerOrchestrator` not imported in commands module
3. `DeploymentConfig` not used in deploy command
4. Validation logic not implemented
5. Dry-run output not updated

---

## Example Usage (After Implementation)

### Basic AI Generation
```bash
haymaker kw deploy \
  --workers 25 \
  --enable-ai-generation \
  --dry-run
```

### Custom Directive
```bash
haymaker kw deploy \
  --workers 25 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work" \
  --dry-run
```

### Custom Markers
```bash
haymaker kw deploy \
  --workers 10 \
  --marker-format "TEST-2025" \
  --marker-style hidden \
  --dry-run
```

### Complete Configuration
```bash
haymaker kw deploy \
  --name ai-test \
  --workers 50 \
  --department operations \
  --duration 4 \
  --enable-ai-generation \
  --email-directive "Focus on IT operations and infrastructure" \
  --marker-format "OPS-TEST" \
  --marker-style both \
  --dry-run
```

---

## Related Files

**Test File**:
- `/home/azureuser/src/AzureHayMaker/cli/tests/test_kw_deploy_ai_options.py`

**Implementation File** (to be modified):
- `/home/azureuser/src/AzureHayMaker/cli/src/haymaker_cli/kw/commands.py`

**Config Models**:
- `/home/azureuser/src/AzureHayMaker/src/azure_haymaker/knowledge_worker/orchestrator.py` (DeploymentConfig)
- `/home/azureuser/src/AzureHayMaker/src/azure_haymaker/knowledge_worker/content/email_generator.py` (EmailGenerationConfig)

**Documentation**:
- `/home/azureuser/src/AzureHayMaker/docs/knowledge-worker-framework/AI_EMAIL_GENERATION.md`
- `/home/azureuser/src/AzureHayMaker/docs/knowledge-worker-framework/EMAIL_MARKERS_GUIDE.md`

---

## Next Steps

1. Review test coverage and add any missing scenarios
2. Implement CLI options in `haymaker_cli/kw/commands.py`
3. Add validation logic for inputs
4. Wire up config construction
5. Update dry-run output formatting
6. Run tests and fix failures iteratively
7. Verify all 34 tests pass

**TDD Cycle**: Red → Green → Refactor

Tests are currently **RED** ✓ (expected in TDD)
Next: Make them **GREEN** by implementing the feature
