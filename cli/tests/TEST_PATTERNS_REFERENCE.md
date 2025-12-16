# Test Patterns Reference for AI Options Tests

This document explains the testing patterns used in `test_kw_deploy_ai_options.py`.

---

## Testing Framework

**Framework**: pytest with Click's CliRunner
**Style**: TDD (Test-Driven Development)
**Coverage**: 34 tests across 8 test classes

---

## Pattern 1: Basic CLI Option Testing

### Testing that options are recognized

```python
def test_option_accepted(self):
    """Test that CLI option is recognized."""
    runner = CliRunner()

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--enable-ai-generation",  # New option
            "--dry-run",
        ],
    )

    # exit_code == 0 means option was recognized
    # exit_code == 2 means Click doesn't recognize the option
    assert result.exit_code == 0
```

---

## Pattern 2: Validation Testing

### Testing input validation with boundary values

```python
def test_max_length_validation(self):
    """Test maximum length validation."""
    runner = CliRunner()

    # Test value that should fail
    too_long = "x" * 1001  # Over 1000 char limit

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--email-directive", too_long,
            "--dry-run",
        ],
    )

    # Should exit with error
    assert result.exit_code == 1

    # Should show helpful error message
    assert "directive" in result.output.lower()
    assert "1000" in result.output or "too long" in result.output.lower()
```

### Boundary testing pattern

```python
# Test boundary cases
too_large = limit + 1   # Should fail
exactly_at_limit = limit  # Should succeed
under_limit = limit - 1   # Should succeed
```

---

## Pattern 3: Environment Variable Testing

### Testing environment variable handling

```python
def test_with_env_var(self):
    """Test reading from environment variables."""
    runner = CliRunner()

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--enable-ai-generation",
        ],
        env={"ANTHROPIC_API_KEY": "sk-ant-test-key"},  # Set env var
    )

    assert result.exit_code == 0


def test_missing_env_var(self):
    """Test missing environment variable handling."""
    runner = CliRunner()

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--enable-ai-generation",
        ],
        env={},  # Empty env (no API key)
    )

    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY" in result.output
```

---

## Pattern 4: Mock Testing for Config Construction

### Testing that CLI maps to config objects

```python
from unittest.mock import MagicMock, patch

@patch("haymaker_cli.kw.commands.DeploymentConfig")
@patch("haymaker_cli.kw.commands.KnowledgeWorkerOrchestrator")
def test_config_mapping(self, mock_orch, mock_config):
    """Test CLI options map to config correctly."""
    runner = CliRunner()
    mock_config.return_value = MagicMock()
    mock_orch.return_value = MagicMock()

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--enable-ai-generation",
            "--email-directive", "Test directive",
            "--dry-run",
        ],
        env={"ANTHROPIC_API_KEY": "sk-ant-test"},
    )

    assert result.exit_code == 0

    # Verify DeploymentConfig was called with correct args
    call_kwargs = mock_config.call_args.kwargs
    assert call_kwargs["email_generation"].enabled is True
    assert call_kwargs["email_generation"].directive == "Test directive"
```

**Why Mock?**
- Tests config construction without executing full deployment
- Verifies argument passing without side effects
- Fast test execution

---

## Pattern 5: Output Verification Testing

### Testing dry-run output formatting

```python
def test_output_contains_expected_info(self):
    """Test that output displays expected information."""
    runner = CliRunner()

    result = runner.invoke(
        deploy,
        [
            "--workers", "25",
            "--enable-ai-generation",
            "--marker-format", "TEST-ID",
            "--dry-run",
        ],
        env={"ANTHROPIC_API_KEY": "sk-ant-test"},
    )

    assert result.exit_code == 0

    output = result.output
    # Verify key information is displayed
    assert "25" in output  # Worker count
    assert "AI" in output or "generation" in output.lower()
    assert "TEST-ID" in output  # Marker format
    assert "cost" in output.lower()  # Cost warning
```

### Pattern: Check for keywords in output

```python
output_lower = result.output.lower()
assert any(
    keyword in output_lower
    for keyword in ["cost", "billing", "estimate", "charges"]
)
```

---

## Pattern 6: Boolean Flag Testing

### Testing flags with enable/disable variants

```python
def test_enable_flag(self):
    """Test enabling a feature."""
    runner = CliRunner()

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--enable-markers",  # Enable
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    # Verify markers enabled


def test_disable_flag(self):
    """Test disabling a feature."""
    runner = CliRunner()

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--no-enable-markers",  # Disable
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    # Verify markers disabled
```

**Click Pattern**: `--enable-markers / --no-enable-markers`

---

## Pattern 7: Choice Option Testing

### Testing options with limited valid choices

```python
def test_valid_choices_accepted(self):
    """Test that all valid choices are accepted."""
    runner = CliRunner()

    valid_choices = ["subject", "hidden", "both"]

    for choice in valid_choices:
        result = runner.invoke(
            deploy,
            [
                "--workers", "5",
                "--marker-style", choice,
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, f"Choice '{choice}' should be valid"


def test_invalid_choice_rejected(self):
    """Test that invalid choice is rejected."""
    runner = CliRunner()

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--marker-style", "invalid-choice",
            "--dry-run",
        ],
    )

    # Click returns exit_code != 0 for invalid choice
    assert result.exit_code != 0
    assert "invalid" in result.output.lower() or "choice" in result.output.lower()
```

---

## Pattern 8: Edge Case Testing

### Testing special characters and edge values

```python
def test_special_characters_handled(self):
    """Test that special characters are handled correctly."""
    runner = CliRunner()

    # Value with special characters
    special_text = 'Text with "quotes", $symbols, and \n newlines'

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--email-directive", special_text,
            "--dry-run",
        ],
    )

    # Should handle gracefully
    assert result.exit_code == 0
```

### Testing whitespace edge cases

```python
def test_whitespace_only_value(self):
    """Test whitespace-only input."""
    runner = CliRunner()

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--email-directive", "   \t\n  ",  # Whitespace only
            "--dry-run",
        ],
    )

    # Should warn and use default
    assert result.exit_code == 0
    assert "empty" in result.output.lower() or "default" in result.output.lower()
```

---

## Pattern 9: Option Interaction Testing

### Testing how options interact with each other

```python
def test_dependent_option_warning(self):
    """Test warning when using option without its dependency."""
    runner = CliRunner()

    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--email-directive", "Some text",  # Used without --enable-ai-generation
            "--dry-run",
        ],
    )

    # Should succeed but warn
    assert result.exit_code == 0
    assert "warn" in result.output.lower() or "ignored" in result.output.lower()


def test_independent_options_work_separately(self):
    """Test that independent options work separately."""
    runner = CliRunner()

    # Markers work without AI generation
    result = runner.invoke(
        deploy,
        [
            "--workers", "5",
            "--marker-format", "TEST",  # Markers independent
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
```

---

## Pattern 10: Integration Scenario Testing

### Testing realistic end-to-end scenarios

```python
def test_realistic_deployment_scenario(self):
    """Test a realistic deployment scenario."""
    runner = CliRunner()

    # Realistic combination of options
    result = runner.invoke(
        deploy,
        [
            "--name", "test-deployment",
            "--workers", "25",
            "--department", "operations",
            "--duration", "4",
            "--enable-ai-generation",
            "--email-directive", "Focus on IT operations",
            "--marker-format", "OPS-TEST",
            "--marker-style", "both",
            "--dry-run",
        ],
        env={"ANTHROPIC_API_KEY": "sk-ant-test"},
    )

    assert result.exit_code == 0

    # Verify all key info in output
    output = result.output
    assert "25" in output
    assert "operations" in output.lower()
    assert "OPS-TEST" in output
```

---

## Test Organization

### Class-based organization

```python
class TestAIGenerationValidation:
    """Test validation of AI generation options."""

    def test_validation_rule_1(self):
        """Test specific validation rule."""
        pass

    def test_validation_rule_2(self):
        """Test another validation rule."""
        pass


class TestConfigConstruction:
    """Test that CLI options map to config objects."""

    def test_mapping_1(self):
        """Test specific mapping."""
        pass
```

**Benefits**:
- Related tests grouped together
- Easy to run specific test suites
- Clear test organization

---

## Assertion Patterns

### Exit Code Assertions

```python
# Success
assert result.exit_code == 0

# Validation error (user error)
assert result.exit_code == 1

# Click option not recognized
assert result.exit_code == 2

# Flexible (any non-zero)
assert result.exit_code != 0
```

### Output Assertions

```python
# Check for exact string
assert "MARKER" in result.output

# Check for case-insensitive
assert "error" in result.output.lower()

# Check for multiple possible strings
assert any(word in result.output for word in ["cost", "price", "billing"])

# Check string NOT present
assert "secret" not in result.output
```

### Config Assertions (with mocks)

```python
# Verify function called
mock_config.assert_called_once()

# Verify specific kwargs
call_kwargs = mock_config.call_args.kwargs
assert call_kwargs["enabled"] is True
assert call_kwargs["directive"] == "Expected value"
```

---

## Test Naming Convention

### Pattern: `test_<what>_<condition>_<expected>`

```python
# Good names
def test_email_directive_max_length_1000_chars_fails(self):
def test_ai_enabled_without_api_key_fails(self):
def test_marker_format_exactly_50_chars_succeeds(self):

# What it tests is immediately clear from the name
```

---

## Running Tests

### Run all tests
```bash
pytest tests/test_kw_deploy_ai_options.py -v
```

### Run specific class
```bash
pytest tests/test_kw_deploy_ai_options.py::TestAIGenerationValidation -v
```

### Run specific test
```bash
pytest tests/test_kw_deploy_ai_options.py::TestAIGenerationValidation::test_ai_enabled_without_api_key_fails -v
```

### Run with output capture disabled (see print statements)
```bash
pytest tests/test_kw_deploy_ai_options.py -v -s
```

### Run with coverage
```bash
pytest tests/test_kw_deploy_ai_options.py --cov=haymaker_cli.kw.commands
```

---

## Common Testing Mistakes to Avoid

### ❌ Don't: Test implementation details
```python
# Bad - testing internal variable names
assert result._internal_var == "value"
```

### ✅ Do: Test observable behavior
```python
# Good - testing exit code and output
assert result.exit_code == 0
assert "expected output" in result.output
```

---

### ❌ Don't: Create test dependencies
```python
# Bad - test depends on another test running first
def test_b(self):
    # Assumes test_a already ran
```

### ✅ Do: Make tests independent
```python
# Good - each test stands alone
def test_b(self):
    # Setup needed state
    # Run test
    # Assert results
```

---

### ❌ Don't: Test multiple things in one test
```python
# Bad - testing too much
def test_everything(self):
    # Tests validation
    # Tests config
    # Tests output
    # Tests errors
```

### ✅ Do: One assertion per test (or closely related)
```python
# Good - focused test
def test_validation_max_length_fails(self):
    # Only tests max length validation
```

---

## TDD Workflow

### Red-Green-Refactor Cycle

1. **Red**: Write failing test first
   ```python
   def test_new_feature(self):
       result = runner.invoke(deploy, ["--new-option", "value"])
       assert result.exit_code == 0
   ```

2. **Green**: Implement minimum code to pass
   ```python
   @click.option("--new-option", help="New option")
   def deploy(new_option):
       # Minimal implementation
       pass
   ```

3. **Refactor**: Clean up code while keeping tests green
   - Improve structure
   - Remove duplication
   - Enhance readability

---

## Summary

**Key Testing Principles**:
1. Write tests FIRST (TDD)
2. Test behavior, not implementation
3. Each test should be independent
4. Use descriptive test names
5. Test happy path AND error cases
6. Test boundary conditions
7. Use mocks for isolation
8. Keep tests fast and focused

**Coverage Goal**: Test all paths through the code
- Happy path (normal usage)
- Error conditions (validation failures)
- Edge cases (boundaries, special chars)
- Option interactions
- Integration scenarios
