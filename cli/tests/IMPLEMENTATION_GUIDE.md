# Implementation Guide: CLI AI Email Generation Options

This guide provides step-by-step instructions for implementing the CLI options to make the tests pass.

**Test File**: `/home/azureuser/src/AzureHayMaker/cli/tests/test_kw_deploy_ai_options.py`
**Implementation File**: `/home/azureuser/src/AzureHayMaker/cli/src/haymaker_cli/kw/commands.py`

---

## Quick Start

### Current Test Status
```bash
cd /home/azureuser/src/AzureHayMaker/cli
source .venv/bin/activate
pytest tests/test_kw_deploy_ai_options.py -v
```

**Expected**: 33/34 tests failing (TDD - feature not implemented)

---

## Implementation Steps

### Step 1: Add Required Imports

Add to top of `commands.py`:

```python
import os
from azure_haymaker.knowledge_worker import (
    DeploymentConfig,
    KnowledgeWorkerOrchestrator,
)
from azure_haymaker.knowledge_worker.content import EmailGenerationConfig
```

**Tests this fixes**: Config construction tests will stop erroring on missing imports

---

### Step 2: Add CLI Options to `deploy` Command

Add these options to the `@kw.command()` decorator stack in `deploy()`:

```python
@kw.command()
@click.option(
    "--name",
    default="test-deployment",
    help="Deployment name",
)
@click.option(
    "--workers",
    default=5,
    type=int,
    help="Number of workers to deploy",
)
# ... existing options ...

# NEW: AI Email Generation Options
@click.option(
    "--enable-ai-generation / --no-enable-ai-generation",
    default=False,
    help="Enable AI-powered email content generation",
)
@click.option(
    "--email-directive",
    default=None,
    help="Custom directive for AI email generation (max 1000 chars)",
)
@click.option(
    "--ai-model",
    default=None,
    help="AI model to use (e.g., 'claude-3-5-sonnet-20241022', 'gpt-4-turbo')",
)

# NEW: Email Marker Options
@click.option(
    "--enable-markers / --no-enable-markers",
    default=True,
    help="Enable email markers for tracking",
)
@click.option(
    "--marker-format",
    default="MARKER",
    help="Marker format prefix (max 50 chars)",
)
@click.option(
    "--marker-style",
    type=click.Choice(["subject", "hidden", "both"], case_sensitive=False),
    default="subject",
    help="Marker placement style",
)

# Existing options continue...
@click.pass_context
def deploy(
    ctx: click.Context,
    name: str,
    workers: int,
    department: str,
    tenant_domain: str,
    duration: int,
    endpoint_type: str,
    dry_run: bool,
    # NEW parameters
    enable_ai_generation: bool,
    email_directive: str | None,
    ai_model: str | None,
    enable_markers: bool,
    marker_format: str,
    marker_style: str,
):
    """Deploy a knowledge worker simulation."""
    # Implementation continues below...
```

**Tests this fixes**: Basic option recognition tests (exit_code == 2 → 0)

---

### Step 3: Add Validation Logic

Add validation at the start of the `deploy()` function:

```python
def deploy(
    ctx: click.Context,
    # ... all parameters ...
):
    """Deploy a knowledge worker simulation."""

    # Validation: Email directive max length
    if email_directive and len(email_directive) > 1000:
        console.print("[red]Error: Email directive exceeds 1000 characters[/red]")
        console.print(f"Current length: {len(email_directive)}")
        sys.exit(1)

    # Validation: Marker format max length
    if marker_format and len(marker_format) > 50:
        console.print("[red]Error: Marker format exceeds 50 characters[/red]")
        console.print(f"Current length: {len(marker_format)}")
        sys.exit(1)

    # Validation: API key required when AI enabled
    if enable_ai_generation:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            console.print("[red]Error: ANTHROPIC_API_KEY environment variable not found[/red]")
            console.print("\n[cyan]To enable AI email generation:[/cyan]")
            console.print("  1. Get API key from: https://console.anthropic.com/settings/keys")
            console.print("  2. Set environment variable:")
            console.print("     export ANTHROPIC_API_KEY=sk-ant-...")
            sys.exit(1)

    # Handle empty/whitespace directive
    if email_directive and not email_directive.strip():
        console.print("[yellow]Warning: Empty email directive, using default persona-based prompts[/yellow]")
        email_directive = None

    # Warn if directive used without AI enabled
    if email_directive and not enable_ai_generation:
        console.print("[yellow]Warning: --email-directive specified but --enable-ai-generation not set[/yellow]")
        console.print("[yellow]The directive will be ignored[/yellow]")

    # Continue with existing code...
```

**Tests this fixes**: All validation tests in `TestAIGenerationValidation`

---

### Step 4: Create EmailGenerationConfig

Add after validation, before creating DeploymentConfig:

```python
    # Create AI email generation config
    email_gen_config = EmailGenerationConfig(
        enabled=enable_ai_generation,
        directive=email_directive,
        model=ai_model,
    )
```

**Tests this fixes**: Config construction tests

---

### Step 5: Update DeploymentConfig Creation

Replace the existing config creation with:

```python
    # Create deployment config
    config = DeploymentConfig(
        name=name,
        total_workers=workers,
        departments={
            department: {
                "count": workers,
                "endpoint_type": endpoint_type,
                "activity": {
                    "email_per_hour": 4,
                    "teams_messages_per_hour": 10,
                    "documents_per_day": 3,
                    "meetings_per_day": 4,
                },
            }
        },
        duration_hours=duration,
        tenant_domain=tenant_domain,
        # NEW: Email marker configuration
        email_markers_enabled=enable_markers,
        marker_format=marker_format,
        marker_style=marker_style,
        # NEW: AI email generation configuration
        email_generation=email_gen_config,
    )
```

**Tests this fixes**: Config mapping tests

---

### Step 6: Update Dry-Run Output

Update the dry-run section to display new configurations:

```python
    if dry_run:
        console.print("[yellow]Dry run - deployment not started[/yellow]")
        console.print("\n[cyan]Configuration:[/cyan]")
        console.print(f"  Name: {name}")
        console.print(f"  Workers: {workers}")
        console.print(f"  Department: {department}")
        console.print(f"  Tenant Domain: {tenant_domain}")
        console.print(f"  Duration: {duration}h")
        console.print(f"  Endpoint Type: {endpoint_type}")

        # NEW: AI Generation info
        if enable_ai_generation:
            console.print("\n[cyan]AI Email Generation:[/cyan]")
            console.print("  Status: [green]ENABLED[/green]")

            if email_directive:
                # Truncate long directives
                display_directive = email_directive
                if len(email_directive) > 80:
                    display_directive = email_directive[:77] + "..."
                console.print(f"  Directive: {display_directive}")
            else:
                console.print("  Directive: (default persona-based)")

            if ai_model:
                console.print(f"  Model: {ai_model}")

            # Cost estimate
            emails_per_worker_per_hour = 5  # Average
            estimated_emails = workers * duration * emails_per_worker_per_hour
            estimated_cost = estimated_emails * 0.01  # $0.01 per email estimate
            console.print(f"\n  [yellow]⚠️  Estimated Cost: ~${estimated_cost:.2f} for ~{estimated_emails} emails[/yellow]")
        else:
            console.print("\n[dim]AI Email Generation: Disabled (using template emails)[/dim]")

        # NEW: Marker info
        if enable_markers:
            console.print("\n[cyan]Email Markers:[/cyan]")
            console.print(f"  Status: [green]ENABLED[/green]")
            console.print(f"  Format: {marker_format}")
            console.print(f"  Style: {marker_style}")
            console.print(f"  Example: [MARKER:{department[:4]}-001-00001-abc123]")
        else:
            console.print("\n[dim]Email Markers: Disabled[/dim]")

        console.print("\n[cyan]Would create:[/cyan]")
        console.print(f"  - {workers} {department} workers")
        console.print(f"  - Endpoint type: {endpoint_type}")
        console.print("  - Security groups for workers")
        console.print("  - Transport rules (external email blocking)")

        endpoint_descriptions = {
            "cli_container": "CLI containers",
            "windows_vm": "Windows VMs",
            "cloud_pc": "Cloud PCs"
        }
        endpoint_desc = endpoint_descriptions.get(endpoint_type, "Endpoints")
        console.print(f"  - {endpoint_desc} for each worker")

        return
```

**Tests this fixes**: All dry-run output tests

---

### Step 7: Update Non-Dry-Run Path (Optional for Tests)

The tests focus on dry-run mode, but for completeness, ensure the config is passed correctly:

```python
    # Create orchestrator and start deployment
    orchestrator = KnowledgeWorkerOrchestrator(graph_client)
    run_id = orchestrator.create_deployment(config)  # Config includes email_generation

    # Rest of existing code...
```

---

## Testing Strategy

### Test After Each Step

Run tests after each implementation step:

```bash
# After Step 1 (imports)
pytest tests/test_kw_deploy_ai_options.py::TestConfigConstruction -v

# After Step 2 (options)
pytest tests/test_kw_deploy_ai_options.py::TestMarkerStyleValidation -v

# After Step 3 (validation)
pytest tests/test_kw_deploy_ai_options.py::TestAIGenerationValidation -v

# After Step 4-5 (config)
pytest tests/test_kw_deploy_ai_options.py::TestConfigConstruction -v

# After Step 6 (output)
pytest tests/test_kw_deploy_ai_options.py::TestDryRunOutput -v

# All tests
pytest tests/test_kw_deploy_ai_options.py -v
```

---

## Expected Test Progression

### Initial State
- ✓ 1 test passing (zero workers test)
- ✗ 33 tests failing

### After Step 1-2 (Options Added)
- ✓ ~15 tests passing (option recognition)
- ✗ ~19 tests failing (validation, output)

### After Step 3 (Validation)
- ✓ ~23 tests passing (+ validation tests)
- ✗ ~11 tests failing (config, output)

### After Step 4-5 (Config)
- ✓ ~29 tests passing (+ config tests)
- ✗ ~5 tests failing (output)

### After Step 6 (Output)
- ✓ 34 tests passing
- ✗ 0 tests failing ✨

---

## Common Implementation Issues

### Issue 1: Exit Code Confusion

**Problem**: Test expects `exit_code == 1` but getting `exit_code == 2`

**Cause**: Click returns 2 when option doesn't exist, 1 for validation errors

**Solution**: Add the option first, then add validation

---

### Issue 2: Mock Not Found

**Problem**: `AttributeError: module does not have attribute 'DeploymentConfig'`

**Cause**: Class not imported in commands.py

**Solution**: Add import at top of file

---

### Issue 3: Validation Not Triggering

**Problem**: Test expects validation error but command succeeds

**Cause**: Validation logic not added or condition wrong

**Solution**: Double-check validation conditions and `sys.exit(1)` calls

---

### Issue 4: Output Assertions Failing

**Problem**: Test expects "cost" in output but not found

**Cause**: Output not formatted correctly or missing

**Solution**: Check dry-run section has all required console.print statements

---

## Verification Checklist

After implementation, verify:

- [ ] All 34 tests pass
- [ ] `--help` shows new options
- [ ] Validation errors show helpful messages
- [ ] Dry-run shows all configuration details
- [ ] API key check only when AI enabled
- [ ] Empty directive handled gracefully
- [ ] Long directives truncated in output
- [ ] Cost warning shown when AI enabled
- [ ] Marker config shown when enabled
- [ ] All options work together

---

## Manual Testing

After tests pass, test manually:

### Test 1: Basic Help
```bash
haymaker kw deploy --help
```
**Verify**: New options listed

### Test 2: Validation
```bash
# Should fail - no API key
haymaker kw deploy --workers 5 --enable-ai-generation --dry-run

# Should fail - directive too long
haymaker kw deploy --workers 5 --email-directive "$(python -c 'print("x"*1001)')" --dry-run

# Should fail - marker format too long
haymaker kw deploy --workers 5 --marker-format "$(python -c 'print("x"*51)')" --dry-run
```

### Test 3: Success Cases
```bash
# Should succeed
export ANTHROPIC_API_KEY=sk-ant-test-key

haymaker kw deploy --workers 25 --enable-ai-generation --dry-run

haymaker kw deploy \
  --workers 25 \
  --enable-ai-generation \
  --email-directive "Write as limericks" \
  --marker-format "TEST" \
  --marker-style hidden \
  --dry-run
```

---

## File Structure Reference

```
cli/
├── src/
│   └── haymaker_cli/
│       ├── kw/
│       │   └── commands.py         ← MODIFY THIS FILE
│       └── ...
└── tests/
    ├── test_kw_deploy_ai_options.py   ← TESTS (already written)
    ├── TEST_SUMMARY_AI_OPTIONS.md     ← This summary
    ├── TEST_PATTERNS_REFERENCE.md     ← Test patterns
    └── IMPLEMENTATION_GUIDE.md        ← This guide
```

---

## Code Template

Here's a complete template for the modified deploy function:

```python
@kw.command()
# ... existing options ...
@click.option("--enable-ai-generation / --no-enable-ai-generation", default=False, help="...")
@click.option("--email-directive", default=None, help="...")
@click.option("--ai-model", default=None, help="...")
@click.option("--enable-markers / --no-enable-markers", default=True, help="...")
@click.option("--marker-format", default="MARKER", help="...")
@click.option("--marker-style", type=click.Choice(["subject", "hidden", "both"]), default="subject", help="...")
@click.option("--dry-run", is_flag=True, help="...")
@click.pass_context
def deploy(
    ctx: click.Context,
    name: str,
    workers: int,
    department: str,
    tenant_domain: str,
    duration: int,
    endpoint_type: str,
    dry_run: bool,
    enable_ai_generation: bool,
    email_directive: str | None,
    ai_model: str | None,
    enable_markers: bool,
    marker_format: str,
    marker_style: str,
):
    """Deploy a knowledge worker simulation."""

    # Step 3: Validation
    # ... validation code ...

    # Step 4: Create EmailGenerationConfig
    email_gen_config = EmailGenerationConfig(
        enabled=enable_ai_generation,
        directive=email_directive,
        model=ai_model,
    )

    # Step 5: Create DeploymentConfig
    config = DeploymentConfig(
        name=name,
        total_workers=workers,
        departments={...},
        duration_hours=duration,
        tenant_domain=tenant_domain,
        email_markers_enabled=enable_markers,
        marker_format=marker_format,
        marker_style=marker_style,
        email_generation=email_gen_config,
    )

    # Step 6: Dry-run output
    if dry_run:
        # ... output code ...
        return

    # Rest of function...
```

---

## Getting Help

If stuck:

1. Check test output for specific assertion failures
2. Review test patterns in TEST_PATTERNS_REFERENCE.md
3. Compare with existing CLI patterns in commands.py
4. Run individual test to isolate issue:
   ```bash
   pytest tests/test_kw_deploy_ai_options.py::TestAIGenerationValidation::test_specific_test -vv
   ```

---

## Success Criteria

**Done when**:
1. All 34 tests pass
2. Manual testing confirms expected behavior
3. Code follows existing patterns in commands.py
4. Error messages are clear and helpful
5. Output is well-formatted and informative

**Final verification**:
```bash
pytest tests/test_kw_deploy_ai_options.py -v
# Expected: 34 passed
```

Good luck! 🚀
