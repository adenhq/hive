# LLM Provider Configuration

Hive's MCP server supports multiple LLM providers through a flexible provider system. This document explains how to configure and use different LLM providers.

## Available Providers

1. **LiteLLMProvider** (Default)
   - Supports multiple LLM backends through LiteLLM
   - Recommended for most use cases

2. **AnthropicProvider**
   - For Anthropic models (Claude)
   - Maintained for backward compatibility

## Configuration

### Setting Up the Default Provider

In your application startup code:

```python
from framework.llm.litellm import LiteLLMProvider
from framework.llm.anthropic import AnthropicProvider

# Set up LiteLLM (recommended)
set_llm_provider(LiteLLMProvider, model="gpt-4")

# Or with Anthropic
# set_llm_provider(AnthropicProvider, model="claude-3-haiku-20240307")
```

### Environment Variables

For LiteLLM:
```bash
# For OpenAI
LITELLM_MODEL=gpt-4
OPENAI_API_KEY=your-openai-key

# For Anthropic via LiteLLM
LITELLM_MODEL=claude-3-haiku-20240307
ANTHROPIC_API_KEY=your-anthropic-key
```

For direct Anthropic:
```bash
ANTHROPIC_API_KEY=your-anthropic-key
```

## Using the LLM Provider

### In Test Generation

```python
# Generate constraint tests
result = generate_constraint_tests(
    goal_id="goal123",
    goal_json=goal_json,
    agent_path="exports/my_agent",
    llm_provider=get_llm_provider()  # Uses default provider if not specified
)

# Generate success tests
result = generate_success_tests(
    goal_id="goal123",
    goal_json=goal_json,
    agent_path="exports/my_agent",
    llm_provider=get_llm_provider()  # Optional
)
```

## Error Handling

Common errors and solutions:

1. **No LLM Provider Configured**
   ```
   Error: No LLM provider configured. Call set_llm_provider() first.
   ```
   - **Solution**: Call `set_llm_provider()` at application startup

2. **Authentication Failed**
   ```
   Error: Failed to initialize LLM provider: Authentication failed
   ```
   - **Solution**: Verify your API keys and environment variables

3. **Model Not Available**
   ```
   Error: Model not found: gpt-5
   ```
   - **Solution**: Check the model name and your provider's documentation

## Best Practices

1. **Provider Selection**
   - Use `LiteLLMProvider` for most cases as it supports multiple backends
   - Only use `AnthropicProvider` if you specifically need direct Anthropic API access

2. **Error Handling**
   - Always wrap LLM calls in try/except blocks
   - Implement retries for transient failures

3. **Testing**
   - Mock LLM calls in unit tests
   - Test with different providers in different environments
