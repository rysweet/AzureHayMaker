# Anthropic Model Configuration Tests

## Overview

This document describes the comprehensive test suite for Anthropic model configuration in the Knowledge Worker email generation system.

**Test File:** `/home/azureuser/src/AzureHayMaker/worktrees/fix-anthropic-model/tests/unit/test_anthropic_model_config.py`

## Purpose

These tests were written FIRST (Test-Driven Development) to validate the fix for Anthropic model configuration. They ensure:
1. Email generation works with valid model names
2. Invalid models raise appropriate errors
3. Environment variable configuration works correctly
4. Default model is used when not configured
5. Configuration priority is respected (explicit config > env var > default)

## Test Structure

### 1. TestAnthropicModelConfiguration (6 tests)

**Critical path tests for model configuration:**

- `test_email_generation_with_valid_model_succeeds`
  - Validates that explicitly configured models work
  - Verifies model is passed correctly to Anthropic API
  - Checks metadata contains correct model name

- `test_email_generation_with_opus_model`
  - Tests Claude Opus 4.5 model variant
  - Ensures system supports multiple model types

- `test_invalid_model_name_raises_appropriate_error`
  - Tests error handling for invalid model names
  - Verifies graceful failure with RuntimeError
  - Ensures API errors are properly caught

- `test_env_var_model_configuration_works`
  - Tests `ANTHROPIC_MODEL` environment variable
  - Verifies env var is used when config.model is None
  - Critical for deployment configuration

- `test_default_model_used_when_not_configured`
  - Tests fallback to default "claude-sonnet-4-5-20250929"
  - Ensures system works without explicit configuration
  - Validates backwards compatibility

- `test_config_model_overrides_env_var`
  - Tests configuration precedence hierarchy
  - Validates: explicit config > env var > default
  - Important for multi-environment deployments

### 2. TestModelConfigurationEdgeCases (5 tests)

**Boundary conditions and edge cases:**

- `test_empty_model_string_uses_default`
  - Empty string "" should fall back to default
  - Prevents errors from misconfiguration

- `test_whitespace_model_string_uses_default`
  - Whitespace-only strings treated as empty
  - Validates input sanitization

- `test_model_metadata_correctly_stored`
  - Ensures model name is stored in email metadata
  - Important for debugging and tracking

- `test_config_model_field_is_optional` ✓ PASSING
  - Confirms model field can be None
  - Validates Pydantic model definition
  - Non-async test

- `test_authentication_error_with_custom_model`
  - Tests auth error handling with custom models
  - Ensures errors are properly sanitized

### 3. TestModelConfigurationIntegration (2 tests)

**End-to-end integration tests:**

- `test_model_config_flows_through_full_generation`
  - Full generation flow with all parameters
  - Verifies model configuration is preserved throughout
  - Tests with run_id, directive, and all metadata

- `test_different_models_for_different_departments`
  - Simulates multi-department scenario
  - Tests engineering, executive, and support departments
  - Validates model flexibility across use cases

## Test Results

**Current Status:**
- **Total:** 13 tests
- **Passing:** 1 (synchronous test)
- **Pending:** 12 (async tests - require pytest-asyncio)

**Why Async Tests Don't Run:**
The async tests require `pytest-asyncio` to be installed. The test structure is correct and follows the same patterns as existing async tests in the codebase (e.g., `tests/security/test_email_content_security.py`).

## Running the Tests

### Prerequisites
```bash
# Install pytest-asyncio (if not already installed)
pip install pytest-asyncio

# Or using uv
uv pip install pytest-asyncio
```

### Run All Tests
```bash
python -m pytest tests/unit/test_anthropic_model_config.py -v
```

### Run Specific Test Class
```bash
python -m pytest tests/unit/test_anthropic_model_config.py::TestAnthropicModelConfiguration -v
```

### Run Single Test
```bash
python -m pytest tests/unit/test_anthropic_model_config.py::TestAnthropicModelConfiguration::test_email_generation_with_valid_model_succeeds -v
```

### Run with Coverage
```bash
python -m pytest tests/unit/test_anthropic_model_config.py --cov=azure_haymaker.knowledge_worker.content.email_generator --cov-report=html
```

## Test Coverage Matrix

| Test Category | Happy Path | Error Cases | Edge Cases | Integration |
|--------------|------------|-------------|------------|-------------|
| Valid Models | ✓ | ✓ | - | ✓ |
| Invalid Models | - | ✓ | - | - |
| Env Var Config | ✓ | - | - | ✓ |
| Default Model | ✓ | - | ✓ | - |
| Config Priority | ✓ | - | - | - |
| Empty/Whitespace | - | - | ✓ | - |
| Metadata Storage | ✓ | - | - | ✓ |
| Auth Errors | - | ✓ | - | - |

## Implementation Checklist

When implementing the fix, ensure all these tests pass:

- [ ] Valid model names are accepted and used
- [ ] Invalid model names raise RuntimeError
- [ ] ANTHROPIC_MODEL env var is respected
- [ ] Default model is "claude-sonnet-4-5-20250929"
- [ ] Empty/whitespace model strings fall back to default
- [ ] Model is stored in email metadata
- [ ] Configuration priority: explicit config > env var > default
- [ ] Multiple model types work (Sonnet, Opus)
- [ ] Auth errors are properly handled
- [ ] Model config flows through full generation pipeline

## Critical Paths

### 1. Email Generation with Valid Model
```python
config = EmailGenerationConfig(
    enabled=True,
    api_key="sk-ant-...",
    model="claude-sonnet-4-5-20250929"
)
generator = EmailContentGenerator(config)
result = await generator.generate_email(...)
# Should succeed and use specified model
```

### 2. Environment Variable Configuration
```python
os.environ["ANTHROPIC_MODEL"] = "claude-opus-4-5-20251101"
config = EmailGenerationConfig(enabled=True, model=None)
# Should use env var model
```

### 3. Default Model Fallback
```python
config = EmailGenerationConfig(enabled=True, model=None)
# Should default to "claude-sonnet-4-5-20250929"
```

### 4. Configuration Priority
```python
os.environ["ANTHROPIC_MODEL"] = "claude-sonnet-4-5-20250929"
config = EmailGenerationConfig(
    enabled=True,
    model="claude-opus-4-5-20251101"  # This should win
)
# Should use explicit config model, not env var
```

## Related Files

- **Implementation:** `src/azure_haymaker/knowledge_worker/content/email_generator.py`
- **Security Tests:** `tests/security/test_email_content_security.py`
- **Config Model:** `azure_haymaker.knowledge_worker.content.email_generator.EmailGenerationConfig`

## Notes

1. **Test-First Approach:** These tests were written before the implementation, following TDD principles.

2. **Mocking Strategy:** Tests use `unittest.mock` to mock the Anthropic client, avoiding real API calls.

3. **Error Handling:** Tests verify that API errors are properly caught and sanitized (preventing API key leakage).

4. **Backwards Compatibility:** Tests ensure existing code without explicit model configuration continues to work.

5. **Model Variants:** Tests cover both Sonnet and Opus model families to ensure broad compatibility.

## Success Criteria

All 13 tests should pass once:
1. pytest-asyncio is properly installed
2. The implementation correctly handles:
   - Explicit model configuration
   - Environment variable fallback
   - Default model fallback
   - Empty/whitespace handling
   - Metadata storage
   - Error handling

---

**Status:** Tests are ready. Implementation pending.
**Last Updated:** 2025-12-11
