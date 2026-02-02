# Using Local LLMs with Hive on Windows

Guide for running Hive with local language models (Ollama) on Windows. No API keys or cloud services required.

## Prerequisites

- Python 3.11+ installed
- Hive set up and running (see [Environment Setup](../ENVIRONMENT_SETUP.md))
- One of: WSL, PowerShell, or Git Bash

## Installing Ollama

1. Download Ollama from [ollama.com/download](https://ollama.com/download/windows)
2. Run the installer
3. Verify installation:

```powershell
ollama --version
```

Ollama runs as a background service on `http://localhost:11434` after installation.

## Pulling a Model

Download a model before using it with Hive:

```powershell
# Pull a model (runs once, downloads to local storage)
ollama pull llama3
ollama pull mistral

# List downloaded models
ollama list

# Verify a model works
ollama run llama3 "Hello, world"
```

### Recommended Models for Getting Started

| Model | Size | Notes |
|-------|------|-------|
| `llama3` | ~4.7 GB | Good general-purpose model |
| `mistral` | ~4.1 GB | Fast, good for code tasks |
| `phi3` | ~2.3 GB | Smaller, runs on less RAM |
| `codellama` | ~3.8 GB | Optimized for code generation |

> **Note:** Larger models need more RAM. 8 GB RAM minimum for 7B parameter models, 16 GB+ recommended for 13B+.

## Configuring Hive to Use Ollama

### Option 1: Set Model in Agent Config

In your agent's `config.py` (`exports/your_agent/config.py`):

```python
CONFIG = {
    "model": "ollama/llama3",  # Use ollama/ prefix + model name
    "max_tokens": 4096,
    "temperature": 0.7,
}
```

### Option 2: Override via Environment Variable

If the agent supports model override via environment:

PowerShell:
```powershell
$env:AGENT_MODEL="ollama/llama3"
```

WSL / Git Bash:
```bash
export AGENT_MODEL="ollama/llama3"
```

### Running an Agent with Ollama

Make sure Ollama is running, then:

PowerShell:
```powershell
$env:PYTHONPATH="core;exports"
python -m your_agent_name run --input '{"task": "Your input here"}'
```

WSL / Git Bash:
```bash
PYTHONPATH=core:exports python -m your_agent_name run --input '{"task": "Your input here"}'
```

No API key is needed — Hive's LiteLLM integration detects the `ollama/` prefix and connects to your local Ollama server automatically.

## Using a Custom Ollama Host

If Ollama runs on a different machine or port, set the base URL:

PowerShell:
```powershell
$env:OLLAMA_API_BASE="http://192.168.1.100:11434"
```

WSL / Git Bash:
```bash
export OLLAMA_API_BASE="http://192.168.1.100:11434"
```

## Optional: Hugging Face Models via LiteLLM

LiteLLM also supports Hugging Face Inference API:

1. Get an API token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Set the environment variable:

PowerShell:
```powershell
$env:HUGGINGFACE_API_KEY="hf_..."
```

WSL / Git Bash:
```bash
export HUGGINGFACE_API_KEY="hf_..."
```

3. Use the model in your agent config:
```python
CONFIG = {
    "model": "huggingface/meta-llama/Llama-3-8B-Instruct",
}
```

See [LiteLLM Hugging Face docs](https://docs.litellm.ai/docs/providers/huggingface) for supported models.

## Troubleshooting

### Ollama not responding

```powershell
# Check if Ollama is running
ollama list

# If not running, start it
ollama serve
```

On Windows, Ollama usually starts automatically as a system service. If it doesn't, launch it from the Start menu or run `ollama serve` in a terminal.

### Connection refused errors

Verify Ollama is listening:

```powershell
curl http://localhost:11434/api/tags
```

If using WSL, note that `localhost` inside WSL may not reach the Windows host. Use the Windows host IP instead:

```bash
# Find your Windows host IP from WSL
cat /etc/resolv.conf | grep nameserver
# Use that IP:
export OLLAMA_API_BASE="http://<windows-ip>:11434"
```

### Model not found

```powershell
# List available models
ollama list

# Pull the model if missing
ollama pull llama3
```

### Out of memory

- Close other applications to free RAM
- Use a smaller model (e.g., `phi3` instead of `llama3`)
- Check model requirements with `ollama show llama3`

### Slow responses

- Local inference speed depends on your hardware (CPU/GPU)
- GPU acceleration requires compatible NVIDIA GPU with CUDA
- For CPU-only systems, smaller models (phi3, tinyllama) respond faster

## Further Reading

- [Ollama documentation](https://ollama.com/)
- [LiteLLM providers](https://docs.litellm.ai/docs/providers)
- [Hive Configuration Guide](configuration.md)
- [Hive Environment Setup](../ENVIRONMENT_SETUP.md)
