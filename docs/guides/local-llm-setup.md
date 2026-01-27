# Running Agents with Local LLMs (Ollama)

This guide shows how to run Hive agents without paid API keys using Ollama, a free local LLM runtime.

## Why Use Local LLMs?

- No API costs
- No rate limits
- Data stays on your machine
- Works offline

Trade-off: Slower than cloud APIs (30-120 seconds per request vs 1-3 seconds).

## Prerequisites

- macOS, Linux, or Windows
- 8GB RAM minimum (16GB recommended)
- 5GB disk space for models

## Installation

### Step 1: Install Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from https://ollama.com/download

### Step 2: Start Ollama

```bash
ollama serve
```

This starts the Ollama server on `http://localhost:11434`.

### Step 3: Download a Model

```bash
# Recommended for most agents (3B parameters, fast)
ollama pull llama3.2

# For better quality (8B parameters, slower)
ollama pull llama3.1:8b

# For complex reasoning (requires 32GB+ RAM)
ollama pull llama3.1:70b
```

### Step 4: Verify Installation

```bash
ollama list
```

You should see your downloaded models.

## Configuring Agents for Ollama

Edit your agent's `config.py`:

```python
@dataclass
class RuntimeConfig:
    model: str = "ollama/llama3.2"  # Format: ollama/<model-name>
    temperature: float = 0.3
    max_tokens: int = 4096
```

The `ollama/` prefix tells LiteLLM to use the local Ollama server.

## Available Ollama Models

| Model | Size | RAM Needed | Best For |
|-------|------|------------|----------|
| `ollama/llama3.2` | 3B | 8GB | Fast prototyping, simple tasks |
| `ollama/llama3.1:8b` | 8B | 16GB | Balanced speed/quality |
| `ollama/mistral` | 7B | 16GB | Good for structured output |
| `ollama/codellama` | 7B | 16GB | Code generation |
| `ollama/llama3.1:70b` | 70B | 64GB | Complex reasoning |

## Troubleshooting

### Problem: JSON Output Has Markdown Formatting

Local models often wrap JSON in markdown code blocks:

```
```json
{"key": "value"}
```
```

**Solution:** Add explicit instructions to your node prompts:

```python
system_prompt="""
...your instructions...

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks.
Just the JSON object starting with { and ending with }
"""
```

### Problem: Responses Are Very Slow

Local inference depends on your hardware. Typical times:

- Apple M1/M2: 30-60 seconds
- Intel/AMD CPU: 60-120 seconds
- With GPU: 5-15 seconds

**Solutions:**
1. Use smaller models (`llama3.2` instead of `llama3.1:8b`)
2. Reduce `max_tokens` in config
3. Simplify prompts to require shorter responses

### Problem: Model Not Found

```
Error: model 'llama3.2' not found
```

**Solution:** Pull the model first:
```bash
ollama pull llama3.2
```

### Problem: Connection Refused

```
Error: Connection refused localhost:11434
```

**Solution:** Start the Ollama server:
```bash
ollama serve
```

### Problem: Out of Memory

```
Error: out of memory
```

**Solution:** Use a smaller model or close other applications.

## Switching Between Local and Cloud

You can easily switch between Ollama and cloud providers by changing the model in `config.py`:

```python
# Local (free, slow)
model: str = "ollama/llama3.2"

# Gemini (free tier available, fast)
model: str = "gemini/gemini-2.0-flash"

# OpenAI (paid, fast)
model: str = "gpt-4o-mini"

# Anthropic (paid, fast)
model: str = "claude-haiku-4-5-20251001"

# Cerebras (free, very fast)
model: str = "cerebras/llama-3.3-70b"
```

For cloud providers, set the corresponding API key:
```bash
export GOOGLE_API_KEY="..."      # Gemini
export OPENAI_API_KEY="..."      # OpenAI
export ANTHROPIC_API_KEY="..."   # Anthropic
export CEREBRAS_API_KEY="..."    # Cerebras
```

## Performance Comparison

| Provider | Speed | Cost | Quality |
|----------|-------|------|---------|
| Ollama (local) | 30-120s | Free | Good |
| Cerebras | 1-3s | Free | Very Good |
| Gemini Flash | 1-3s | Free tier | Very Good |
| GPT-4o-mini | 1-3s | ~$0.001/request | Excellent |
| Claude Haiku | 1-3s | ~$0.001/request | Excellent |

## Recommended Setup for Development

1. Use Ollama for initial development and testing
2. Switch to Cerebras or Gemini (free) for faster iteration
3. Use GPT-4o or Claude for production if quality matters

## Example: Testing Your Setup

```bash
# Start Ollama
ollama serve

# In another terminal, test a simple prompt
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Say hello in JSON format: {\"greeting\": \"...\"}",
  "stream": false
}'
```

You should get a JSON response within 30-60 seconds.

## Next Steps

- See example agents in `.claude/skills/building-agents-construction/examples/`
- Read the agent building guide: `docs/guides/building-your-first-agent.md`
- Use `/agent-workflow` in Claude Code to build your own agent
- Join the Discord for help: https://discord.com/invite/MXE49hrKDk
