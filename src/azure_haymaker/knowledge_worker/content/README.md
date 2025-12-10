# Email Content Generation Module

AI-powered email content generation for Knowledge Worker deployments with email markers for tracking and analytics.

## Overview

This module provides three key capabilities:

1. **Email Markers**: Add tracking markers to emails for analytics
2. **AI-Generated Content**: Use Claude (Anthropic) to generate realistic email content
3. **Custom Directives**: Apply per-deployment directives (e.g., include limericks in signatures)

## Architecture

The module implements a three-level fallback strategy:

```
1. AI Generation (if enabled)
   ↓ (on failure)
2. Simple Fallback Generator
   ↓ (on error)
3. Hardcoded Content
```

## Components

### EmailContent

Dataclass representing email content with metadata:

```python
from azure_haymaker.knowledge_worker.content import EmailContent

email = EmailContent(
    subject="Project Update",
    body="<p>The project is on track...</p>",
    metadata={
        "source": "anthropic_claude",
        "worker_id": "kw-eng-1",
        "tokens_used": 150,
    }
)
```

### EmailGenerationConfig

Configuration for AI email generation:

```python
from azure_haymaker.knowledge_worker.content import EmailGenerationConfig

config = EmailGenerationConfig(
    enabled=True,
    api_key="sk-ant-...",  # Optional, uses ANTHROPIC_API_KEY env var
    model="claude-3-5-sonnet-20241022",
    directive="Include a humorous limerick in your signature",
    max_tokens=1024,
    temperature=0.7,
    timeout_seconds=30,
)
```

### EmailContentGenerator

AI-powered email generator using Anthropic Claude:

```python
from azure_haymaker.knowledge_worker.content import (
    EmailContentGenerator,
    EmailGenerationConfig,
)

config = EmailGenerationConfig(enabled=True)
generator = EmailContentGenerator(config)

email = await generator.generate_email(
    worker_id="kw-eng-1",
    department="engineering",
    recipient="kw-eng-2@test.com",
    activity_count=42,
    run_id="deployment-123",
)
```

### FallbackEmailGenerator

Simple fallback generator with hardcoded content:

```python
from azure_haymaker.knowledge_worker.content import FallbackEmailGenerator

fallback = FallbackEmailGenerator()

email = fallback.generate_email(
    worker_id="kw-eng-1",
    activity_count=42,
    department="engineering",
)
```

## Email Markers

Email markers enable tracking and analytics for Knowledge Worker emails.

### Configuration

```python
from azure_haymaker.knowledge_worker.orchestrator import DeploymentConfig

config = DeploymentConfig(
    email_markers_enabled=True,
    marker_format="MARKER",  # Custom format string
    marker_style="subject",  # "subject", "hidden", "both"
)
```

### Marker Styles

1. **Subject**: Add marker to subject line
   ```
   [MARKER:run-123:kw-eng-1:42] Project Update
   ```

2. **Hidden**: Add marker as HTML comment in body
   ```html
   <!-- [MARKER:run-123:kw-eng-1:42] -->
   <p>Email body content...</p>
   ```

3. **Both**: Add markers to both subject and body

## Usage with Orchestrator

### Basic Setup (Markers Only)

```python
from azure_haymaker.knowledge_worker.orchestrator import (
    DeploymentConfig,
    KnowledgeWorkerOrchestrator,
)

config = DeploymentConfig(
    name="markers-demo",
    email_markers_enabled=True,
    marker_style="subject",
)

orchestrator = KnowledgeWorkerOrchestrator(graph_client, config)
```

### AI-Generated Emails with Custom Directive

```python
from azure_haymaker.knowledge_worker.content import EmailGenerationConfig
from azure_haymaker.knowledge_worker.orchestrator import DeploymentConfig

config = DeploymentConfig(
    name="ai-email-demo",
    email_markers_enabled=True,
    email_generation=EmailGenerationConfig(
        enabled=True,
        directive="Include a limerick about working in the age of AI in your signature",
        temperature=0.7,
    ),
)

orchestrator = KnowledgeWorkerOrchestrator(graph_client, config)
```

### Complete Example

See `/home/azureuser/src/AzureHayMaker/examples/ai_email_deployment.py` for a complete working example.

## Environment Variables

Required when AI generation is enabled:

- `ANTHROPIC_API_KEY`: Anthropic API key for Claude
- `KW_TENANT_ID`: Azure AD tenant ID
- `KW_APP_ID`: Application client ID
- `KW_CLIENT_SECRET`: Client secret
- `KW_TENANT_DOMAIN`: M365 tenant domain

## Prompt Templates

The module uses carefully designed prompts to generate realistic work emails:

### System Prompt

- Establishes worker persona (department-based)
- Defines output format requirements
- Includes custom directive if provided

### User Prompt

- Provides activity context (worker ID, recipient, count)
- Guides content generation

## Custom Directives

Directives allow per-deployment customization of email content:

### Example Directives

```python
# Limericks in signatures
directive = "Include a humorous limerick about working in the age of AI in your email signature"

# Technical focus
directive = "Use technical jargon and include code snippet references when appropriate"

# Marketing style
directive = "Use enthusiastic language and marketing buzzwords"

# Financial focus
directive = "Include financial metrics and ROI discussions"
```

## Fallback Strategy

The orchestrator implements a three-level fallback:

```python
async def _generate_email_content(self, ...) -> EmailContent:
    # Level 1: Try AI generation
    if self.email_generator:
        try:
            return await self.email_generator.generate_email(...)
        except Exception as e:
            logger.warning(f"AI failed: {e}")

    # Level 2 & 3: Use fallback generator
    return self.fallback_generator.generate_email(...)
```

This ensures emails are always generated even if:
- AI generation is disabled
- API key is invalid
- API service is unavailable
- Rate limits are exceeded

## Performance Considerations

- **Caching**: Not implemented (each email is unique)
- **Rate Limiting**: Handled by Anthropic SDK
- **Timeouts**: Configurable via `timeout_seconds`
- **Async Operations**: All generation is async to avoid blocking

## Testing

### Manual Testing

```bash
python examples/ai_email_deployment.py
```

### Unit Testing

```python
# Test fallback generator
fallback = FallbackEmailGenerator()
email = fallback.generate_email("worker-1", 0)
assert "Activity 1" in email.subject

# Test config
config = EmailGenerationConfig(enabled=False)
assert config.model == "claude-3-5-sonnet-20241022"
```

## Future Enhancements

1. **Per-Department Directives**: Different directives per department
2. **Email Threading**: Generate reply chains
3. **Attachment References**: Mention attached files
4. **Meeting Context**: Reference calendar events
5. **Caching**: Cache similar requests
6. **Analytics**: Track generation success rates

## Files

```
content/
├── __init__.py           # Public API exports
├── README.md             # This file
├── email_generator.py    # AI email generation
├── prompts.py            # Prompt templates
└── fallback.py           # Fallback generator
```

## Integration Points

### Orchestrator

The orchestrator integrates email generation in `_run_activity_loop()`:

1. Generate email content (AI or fallback)
2. Add markers if enabled
3. Send via M365 Graph API

### Agent

Knowledge Worker agents receive the generated content and send it via the M365 client.

## Error Handling

- **Invalid API Key**: Falls back to simple generator
- **API Timeout**: Logs warning and uses fallback
- **Parsing Errors**: Returns default content
- **Network Errors**: Graceful degradation

## Logging

The module uses Python's logging framework:

```python
logger.info("Generated email content for worker-1")
logger.warning("AI generation failed, using fallback")
logger.debug("Fallback email generated")
```

## Security Considerations

- **API Keys**: Never logged or exposed in errors
- **Content Filtering**: No PII in generated emails
- **Markers**: Safe for internal tracking only

## License

Part of Azure HayMaker project.
