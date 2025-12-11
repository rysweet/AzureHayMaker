# [PLANNED - Implementation Pending]

# CLI Reference: AI Email Generation Options

**Purpose**: Complete reference for `haymaker kw deploy` AI email generation options.

**Last Updated**: 2025-12-10
**Status**: Planned Feature

---

## Command Synopsis

```bash
haymaker kw deploy [OPTIONS]
```

## AI Email Generation Options

### `--enable-ai-generation`

**Type**: Flag (boolean)
**Default**: Disabled
**Required**: ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable

Enable AI-powered email content generation using LLMs.

```bash
haymaker kw deploy --workers 10 --enable-ai-generation
```

**Behavior**:
- Without flag: Uses template emails (`Automated activity generated at {timestamp}`)
- With flag: Generates contextual email bodies using AI model
- Automatically selects model based on available API keys (Claude > GPT-4)

**Environment Variables**:
- `ANTHROPIC_API_KEY`: For Claude models (preferred)
- `OPENAI_API_KEY`: For GPT models

**Example Output**:
```
[INFO] AI email generation enabled (model: gpt-4-turbo)
[INFO] Estimated cost: ~$2.00 for 200 emails over 8 hours
```

---

### `--email-directive "TEXT"`

**Type**: String
**Default**: Persona-specific prompt
**Maximum Length**: 500 characters
**Requires**: `--enable-ai-generation`

Custom instructions for AI email content generation.

```bash
haymaker kw deploy \
  --workers 25 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about office work"
```

**Default Directives by Department**:
- `executive`: "Write as senior executive discussing strategy and leadership"
- `legal`: "Write as legal professional discussing compliance and policies"
- `engineering`: "Write as software engineer discussing technical topics"
- `hr`: "Write as HR professional about employee matters and policies"
- `finance`: "Write as finance professional about budgets and reporting"
- `sales`: "Write as sales representative about deals and customers"
- `operations`: "Write as operations team member about systems and processes"
- `marketing`: "Write as marketing professional about campaigns and content"

**Directive Examples**:

```bash
# Limericks
--email-directive "Write all emails as limericks"

# Security focus
--email-directive "Focus on cybersecurity and data protection topics"

# Urgent tone
--email-directive "Write urgent emails about critical production issues"

# Casual style
--email-directive "Write casual, friendly emails with emojis"

# Formal style
--email-directive "Write very formal business correspondence"

# Technical depth
--email-directive "Include technical jargon and system architecture discussions"

# Short emails
--email-directive "Keep all emails under 50 words, very concise"

# Long emails
--email-directive "Write detailed emails with multiple paragraphs"
```

**Constraints**:
- Maximum 500 characters
- Must be appropriate content (AI safety filters apply)
- Cannot override persona entirely (engineering workers won't write legal emails)

**Validation**:
```bash
# This works
--email-directive "Write about project deadlines and team coordination"

# This fails (too long)
--email-directive "Write extremely detailed emails that cover multiple topics including technical implementations, business strategy, team dynamics, project timelines, budget considerations, and stakeholder communications with extensive background context and forward-looking analysis spanning multiple business quarters and strategic initiatives across the entire organization with detailed breakdowns of each component and exhaustive explanations of every decision point and rationale behind all recommendations..."  # 501+ chars
```

---

### `--ai-model MODEL_NAME`

**Type**: String (choice)
**Default**: SDK default (gpt-4-turbo or claude-3-5-sonnet)
**Requires**: `--enable-ai-generation`

Override AI model for email generation.

```bash
haymaker kw deploy \
  --workers 10 \
  --enable-ai-generation \
  --ai-model claude-sonnet-4-5-20250929
```

**Supported Models**:

**Anthropic (Claude)**:
- `claude-sonnet-4-5-20250929` - Latest Sonnet, best quality
- `claude-sonnet-4-5-20250929` - Previous Sonnet version
- `claude-3-opus-20240229` - Older opus version
- `claude-3-haiku-20240307` - Fastest, cheapest (not recommended for emails)

**OpenAI (GPT)**:
- `gpt-4o` - GPT-4 Omni, excellent quality
- `gpt-4-turbo` - Fast GPT-4, good quality
- `gpt-4` - Original GPT-4 (slower)
- `gpt-3.5-turbo` - Cheapest, decent quality

**Model Selection Logic**:
1. If `--ai-model` specified: Use that model
2. Else if `ANTHROPIC_API_KEY` set: Use `claude-sonnet-4-5-20250929`
3. Else if `OPENAI_API_KEY` set: Use `gpt-4-turbo`
4. Else: Error (no API key found)

**Cost Comparison** (per 1000 emails):

| Model | Input | Output | Total | Quality |
|-------|-------|--------|-------|---------|
| gpt-3.5-turbo | $0.50 | $1.50 | ~$2.00 | Good |
| gpt-4-turbo | $5.00 | $7.50 | ~$12.50 | Excellent |
| gpt-4o | $7.50 | $10.00 | ~$17.50 | Excellent |
| claude-3-5-sonnet | $7.50 | $10.00 | ~$17.50 | Excellent |

**Recommendation**:
- **Testing**: `gpt-3.5-turbo` (cheap, fast)
- **Production**: `gpt-4-turbo` or `claude-3-5-sonnet` (best quality)
- **High-volume**: `gpt-3.5-turbo` (cost-effective)

---

### `--enable-markers`

**Type**: Flag (boolean)
**Default**: Enabled
**Opposite**: `--no-enable-markers`

Enable email marker injection for tracking and analysis.

```bash
# Enable markers (default)
haymaker kw deploy --workers 10 --enable-markers

# Disable markers
haymaker kw deploy --workers 10 --no-enable-markers
```

**Marker Purpose**:
- Track emails in testing scenarios
- Correlate emails with deployment runs
- Filter haymaker emails from production traffic
- Enable post-deployment analysis

**Marker Example**:
```
Subject: Activity 5 from kw-engi-001 [MARKER:engi-001-00005-a3f2c1]
```

**Related Options**:
- `--marker-style`: Control marker visibility
- `--marker-format`: Customize marker prefix

---

### `--marker-style STYLE`

**Type**: Choice [subject|hidden|both]
**Default**: subject
**Requires**: `--enable-markers` (default enabled)

Control email marker placement and visibility.

```bash
# Visible markers in subject (default)
haymaker kw deploy --workers 10 --marker-style subject

# Hidden markers in HTML body
haymaker kw deploy --workers 10 --marker-style hidden

# Both visible and hidden markers
haymaker kw deploy --workers 10 --marker-style both
```

**Styles Explained**:

#### `subject` (default)
Marker in email subject line (visible to users).

```
Subject: Activity 5 from kw-engi-001 [MARKER:engi-001-00005-a3f2c1]
Body: Email content here...
```

**Pros**:
- Easy to identify in inbox
- Quick filtering with email client rules
- Visible in logs and monitoring

**Cons**:
- Not realistic (real users don't send marked emails)
- May affect user experience in testing

**Use When**:
- Testing/debugging
- Demo scenarios
- Lab environments

---

#### `hidden`
Marker embedded in HTML body with zero-size styling (invisible to users).

```
Subject: Activity 5 from kw-engi-001
Body: Email content here...
      <div style="font-size:0;color:white;display:none;">
      [METADATA:MARKER:engi-001-00005-a3f2c1|run_id=kw-abc123|seq=5]
      </div>
```

**Pros**:
- Realistic appearance (no visible markers)
- Parseable by email systems
- Useful for SIEM ingestion

**Cons**:
- Harder to spot visually
- Requires HTML parsing to extract

**Use When**:
- Production-like testing
- Red team operations
- SIEM/DLP validation

---

#### `both`
Markers in both subject and hidden body.

**Pros**:
- Maximum tracking capability
- Visual identification + programmatic parsing
- Redundancy if one marker stripped

**Cons**:
- Subject marker reduces realism

**Use When**:
- Critical testing scenarios
- Maximum traceability required
- Post-deployment analysis essential

---

### `--marker-format TEXT`

**Type**: String
**Default**: MARKER
**Requires**: `--enable-markers` (default enabled)
**Maximum Length**: 50 characters

Customize the marker prefix format.

```bash
# Use TEST-ID prefix
haymaker kw deploy --workers 10 --marker-format TEST-ID

# Use run-specific prefix
haymaker kw deploy --workers 25 --marker-format "Q1-2025-SIEM"

# Use simple format
haymaker kw deploy --workers 5 --marker-format RUN
```

**Marker Pattern**:
```
[{FORMAT}:{worker-id}-{sequence}-{uuid}]
```

**Examples**:

| Format | Full Marker Example |
|--------|-------------------|
| MARKER (default) | `[MARKER:engi-001-00005-a3f2c1]` |
| TEST-ID | `[TEST-ID:engi-001-00005-a3f2c1]` |
| RUN | `[RUN:engi-001-00005-a3f2c1]` |
| Q1-SIEM | `[Q1-SIEM:engi-001-00005-a3f2c1]` |
| BENIGN | `[BENIGN:engi-001-00005-a3f2c1]` |

**Format Constraints**:
- Maximum 50 characters
- Alphanumeric, hyphens, underscores only
- No spaces or special characters

**Validation**:
```bash
# Valid
--marker-format "TEST-2025-Q1"
--marker-format "SIMULATION_RUN"
--marker-format "RT-OPS"

# Invalid
--marker-format "Test Run"  # Space not allowed
--marker-format "Test@Run"  # @ not allowed
--marker-format "VERY_LONG_MARKER_FORMAT_NAME_THAT_EXCEEDS_50_CHARS"  # Too long
```

**Use Cases**:

```bash
# Testing campaigns
--marker-format "TEST-2025-12-10"

# Red team operations
--marker-format "BENIGN-RT-Q1"

# SIEM validation
--marker-format "SIEM-VAL-RUN"

# Departmental tracking
--marker-format "DEPT-ENG"
```

---

## Complete Examples

### Minimal AI Email Deployment

```bash
haymaker kw deploy \
  --workers 5 \
  --enable-ai-generation

# Uses: Default model, default directives, markers enabled (subject style)
# Cost: ~$0.50 for 1 hour
```

---

### Custom Directive with Cost Optimization

```bash
haymaker kw deploy \
  --workers 50 \
  --department operations \
  --duration 8 \
  --enable-ai-generation \
  --email-directive "Write about IT operations and system maintenance" \
  --ai-model gpt-3.5-turbo

# Uses: GPT-3.5 (cheaper), custom directive, 50 workers
# Cost: ~$4.00 for 8 hours
```

---

### Stealth Deployment with Hidden Markers

```bash
haymaker kw deploy \
  --workers 25 \
  --department sales \
  --enable-ai-generation \
  --marker-style hidden \
  --marker-format BENIGN-2025

# Uses: Hidden markers only, realistic appearance
# Cost: ~$2.40 for 8 hours (sales: 12 emails/hr)
```

---

### High-Quality Red Team Simulation

```bash
haymaker kw deploy \
  --workers 10 \
  --department executive \
  --duration 4 \
  --enable-ai-generation \
  --ai-model claude-sonnet-4-5-20250929 \
  --email-directive "Write strategic emails about business initiatives" \
  --marker-style both \
  --marker-format RT-EXEC-Q1

# Uses: Claude Sonnet (best quality), executive persona, both marker styles
# Cost: ~$4.80 for 4 hours
```

---

### Limerick Testing Scenario

```bash
haymaker kw deploy \
  --workers 25 \
  --department engineering \
  --duration 2 \
  --enable-ai-generation \
  --email-directive "Write all emails as limericks about software development" \
  --marker-format LIMERICK

# Uses: Default model, limerick directive, 25 engineering workers
# Cost: ~$1.00 for 2 hours
# Result: 200 limerick emails with [LIMERICK:...] markers
```

---

## Option Dependencies

### Required Combinations

| Option | Requires |
|--------|----------|
| `--email-directive` | `--enable-ai-generation` |
| `--ai-model` | `--enable-ai-generation` |
| `--marker-style` | `--enable-markers` (default: enabled) |
| `--marker-format` | `--enable-markers` (default: enabled) |

### Validation Errors

```bash
# ERROR: Directive without AI generation
haymaker kw deploy --workers 10 --email-directive "Write limericks"
# Error: --email-directive requires --enable-ai-generation

# ERROR: Model without AI generation
haymaker kw deploy --workers 10 --ai-model gpt-4o
# Error: --ai-model requires --enable-ai-generation

# ERROR: Marker style without markers enabled
haymaker kw deploy --workers 10 --no-enable-markers --marker-style hidden
# Error: --marker-style requires --enable-markers

# VALID: AI generation without explicit model (uses default)
haymaker kw deploy --workers 10 --enable-ai-generation
# OK: Uses default model based on available API keys
```

---

## Environment Variables

### Required for AI Generation

```bash
# For Anthropic (Claude) models
export ANTHROPIC_API_KEY=sk-ant-api03-...

# For OpenAI (GPT) models
export OPENAI_API_KEY=sk-...

# Knowledge Worker credentials (always required)
export KW_TENANT_ID=...
export KW_APP_ID=...
export KW_CLIENT_SECRET=...
```

### Optional

```bash
# Override default model selection
export HAYMAKER_AI_MODEL=gpt-4-turbo

# Set default email directive
export HAYMAKER_EMAIL_DIRECTIVE="Write concise professional emails"

# Set default marker format
export HAYMAKER_MARKER_FORMAT=TEST-ID
```

**Priority**: CLI options override environment variables

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Missing API key (when `--enable-ai-generation` used) |
| 2 | Invalid option combination |
| 3 | AI model not available |
| 4 | Rate limit exceeded |
| 5 | Deployment failed |

---

## Related Commands

```bash
# Check deployment status
haymaker kw status

# View generated email logs
haymaker logs --agent-id kw-engi-001 --tail 100

# Generate telemetry report
haymaker kw telemetry-report --run-id kw-20251210-abc123

# List available personas
haymaker kw list-personas
```

---

## See Also

- [AI_EMAIL_GENERATION.md](./AI_EMAIL_GENERATION.md) - Complete guide and examples
- [EMAIL_MARKERS_GUIDE.md](./EMAIL_MARKERS_GUIDE.md) - Marker documentation
- [../CLI_GUIDE.md](../CLI_GUIDE.md) - Full CLI reference
