# LLM Provider API Reference

API reference for the multi-provider LLM abstraction layer in Azure HayMaker.

## Module: `azure_haymaker.llm`

### Public API

```python
from azure_haymaker.llm import (
    create_llm_client,  # Factory function
    LLMConfig,          # Configuration model
    LLMResponse,        # Response type
    LLMMessage,         # Message type
    BaseLLMProvider,    # Base class (for custom providers)
)
```

## `create_llm_client(config: LLMConfig) -> BaseLLMProvider`

Factory function that creates the appropriate LLM provider based on configuration.

**Parameters:**
- `config` (LLMConfig): Provider configuration

**Returns:**
- `BaseLLMProvider`: Configured provider instance

**Example:**
```python
from azure_haymaker.llm import create_llm_client, LLMConfig

config = LLMConfig(provider="anthropic", api_key="sk-...")
client = create_llm_client(config)
```

---

## `LLMConfig`

Configuration model for LLM providers.

**Fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `provider` | str | Yes | - | Provider name: "anthropic", "azure_openai", "azure_ai_foundry" |
| `model` | str | No | Provider default | Model name or deployment |
| `api_key` | SecretStr | No | None | API key (uses managed identity if not provided) |
| `endpoint` | str | No | None | Azure endpoint URL (required for Azure providers) |
| `deployment` | str | No | None | Azure OpenAI deployment name |
| `api_version` | str | No | "2024-02-15-preview" | Azure OpenAI API version |
| `timeout_seconds` | int | No | 120 | Request timeout |
| `max_retries` | int | No | 3 | Maximum retry attempts |

**Example:**
```python
from azure_haymaker.llm import LLMConfig

# Anthropic
config = LLMConfig(
    provider="anthropic",
    model="claude-3-sonnet-20241022",
    api_key="sk-..."
)

# Azure OpenAI with managed identity
config = LLMConfig(
    provider="azure_openai",
    endpoint="https://myresource.openai.azure.com",
    deployment="gpt-4",
    api_version="2024-02-15-preview"
)

# Azure AI Foundry
config = LLMConfig(
    provider="azure_ai_foundry",
    endpoint="https://myendpoint.inference.ml.azure.com",
    model="Meta-Llama-3-70B-Instruct"
)
```

---

## `LLMMessage`

Represents a single message in a conversation.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `role` | str | Message role: "user", "assistant", "system" |
| `content` | str | Message content |

**Example:**
```python
from azure_haymaker.llm import LLMMessage

messages = [
    LLMMessage(role="user", content="Write a professional email about project update")
]
```

---

## `LLMResponse`

Response from an LLM provider.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | str | Generated text content |
| `model` | str | Model that generated the response |
| `usage` | dict | Token usage statistics |
| `stop_reason` | str | Why generation stopped |

**Example:**
```python
response = await client.create_message_async(messages)
print(response.content)  # Generated text
print(response.usage)    # {"input_tokens": 10, "output_tokens": 50}
```

---

## `BaseLLMProvider`

Abstract base class for LLM providers.

### Methods

#### `create_message(messages, system, max_tokens, temperature) -> LLMResponse`

Synchronous message creation.

**Parameters:**
- `messages` (list[LLMMessage]): Conversation messages
- `system` (str, optional): System prompt
- `max_tokens` (int): Maximum tokens to generate (default: 1024)
- `temperature` (float): Sampling temperature (default: 0.7)

**Returns:**
- `LLMResponse`: Generated response

#### `create_message_async(messages, system, max_tokens, temperature) -> LLMResponse`

Asynchronous message creation.

**Parameters:** Same as `create_message`

**Returns:**
- `LLMResponse`: Generated response

**Example:**
```python
from azure_haymaker.llm import create_llm_client, LLMConfig, LLMMessage

config = LLMConfig(provider="anthropic", api_key="sk-...")
client = create_llm_client(config)

messages = [LLMMessage(role="user", content="Hello!")]

# Sync
response = client.create_message(messages, max_tokens=100)

# Async
response = await client.create_message_async(messages, max_tokens=100)
```

---

## Provider-Specific Details

### Anthropic Provider

- **Models**: claude-3-opus-20240229, claude-3-sonnet-20241022, claude-3-haiku-20240307
- **Default Model**: claude-3-sonnet-20241022
- **Authentication**: API key required

### Azure OpenAI Provider

- **Models**: Depends on deployment (gpt-4, gpt-4o, gpt-35-turbo)
- **Authentication**: DefaultAzureCredential or API key
- **Required Fields**: `endpoint`, `deployment`

### Azure AI Foundry Provider

- **Models**: Meta-Llama-3-70B-Instruct, Mistral-large, Phi-3-medium, etc.
- **Authentication**: DefaultAzureCredential or API key
- **Required Fields**: `endpoint`, `model`

---

## Error Handling

All providers raise standard exceptions:

```python
from azure_haymaker.llm.exceptions import (
    LLMAuthenticationError,  # Invalid credentials
    LLMRateLimitError,       # Rate limit exceeded (retryable)
    LLMInvalidRequestError,  # Invalid request parameters
    LLMProviderError,        # Provider-specific error
)
```

**Example:**
```python
from azure_haymaker.llm import create_llm_client, LLMConfig
from azure_haymaker.llm.exceptions import LLMRateLimitError

try:
    response = await client.create_message_async(messages)
except LLMRateLimitError:
    # Automatic retry with backoff
    pass
except LLMAuthenticationError:
    # Check credentials
    pass
```

---

## See Also

- [How to Configure LLM Providers](../howto/configure-llm-providers.md)
- [Architecture Overview](../ARCHITECTURE.md)
