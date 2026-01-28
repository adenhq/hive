# Agent Development Environment Setup

Complete step-by-step setup guide for building and running goal-driven agents with the Aden Agent Framework.

## 📋 Setup Checklist

Use this checklist to track your progress through the setup process:

- [ ] **Clone Repository** - Get the source code
- [ ] **Check Python Version** - Ensure Python 3.11+
- [ ] **Run Setup Script** - Automated installation
- [ ] **Verify Installation** - Test all packages
- [ ] **Configure API Keys** - Set up LLM access
- [ ] **Test LLM Connection** - Verify your keys work
- [ ] **Optional: Install Claude Code** - For interactive agent building

## Prerequisites

### System Requirements

- **OS**: Linux, macOS, or Windows (with PowerShell or WSL)
- **Python**: 3.11+ (3.12 or 3.13 recommended)
- **RAM**: 2GB minimum (4GB+ recommended)
- **Disk**: 500MB for packages and dependencies
- **Internet**: Required for LLM API calls

### API Keys Required (Choose at least one)

1. **[Anthropic Claude](https://console.anthropic.com/settings/keys)** ⭐ Recommended
   - Go to: https://console.anthropic.com/settings/keys
   - Click "Create Key"
   - Copy and save securely

2. **[OpenAI](https://platform.openai.com/api-keys)** - Alternative
   - Go to: https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Copy and save securely

### API Keys Optional (For Enhanced Features)

3. **[Brave Search](https://api.search.brave.com/)** - For web search tool
4. **[Cerebras](https://cerebras.ai/)** - For faster inference

## Quick Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/adenhq/hive.git
cd hive
```

### Step 2: Run Automated Setup Script

```bash
# Run the setup script
./scripts/setup-python.sh
```

This will automatically:

✓ Check Python version (requires 3.11+)  
✓ Install the core framework package (`framework`)  
✓ Install the tools package (`aden_tools`)  
✓ Fix package compatibility issues (openai + litellm)  
✓ Verify all installations  

**Output should show:**
```
✓ Python version OK (3.11+)
✓ framework installed
✓ aden_tools installed
✓ All dependencies verified
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# .env file (at project root: /hive/.env)

# ===== REQUIRED =====
# Choose at least ONE LLM provider

# Anthropic Claude (Recommended)
ANTHROPIC_API_KEY=sk-ant-...

# OR OpenAI
# OPENAI_API_KEY=sk-...

# ===== OPTIONAL =====
# Brave Search (for web_search_tool)
BRAVE_SEARCH_API_KEY=...

# Cerebras (for faster inference)
CEREBRAS_API_KEY=...

# Google Gemini (alternative LLM)
GOOGLE_API_KEY=...
```

**On Linux/macOS**, add to your shell profile instead:

```bash
# ~/.bashrc, ~/.zshrc, or ~/.fish/config.fish
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."  # Optional
export BRAVE_SEARCH_API_KEY="..."  # Optional
```

Load it immediately:
```bash
source ~/.bashrc  # or ~/.zshrc
```

**On Windows (PowerShell)**, set environment variables:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:OPENAI_API_KEY = "sk-..."  # Optional
$env:BRAVE_SEARCH_API_KEY = "..."  # Optional
```

To make permanent, use `[Environment]::SetEnvironmentVariable()` or edit System Variables in Control Panel.

### Step 4: Verify Installation

```bash
# Test Python packages
python -c "import framework; print('✓ framework OK')"
python -c "import aden_tools; print('✓ aden_tools OK')"
python -c "import litellm; print('✓ litellm OK')"

# Test LLM access
python << 'EOF'
from framework.llm.litellm import LiteLLMProvider

try:
    llm = LiteLLMProvider(model='claude-3-5-sonnet-20241022')
    print('✓ LLM provider initialized')
except Exception as e:
    print(f'✗ LLM Error: {e}')
    print('  Check your ANTHROPIC_API_KEY is set correctly')
EOF
```

Expected output:
```
✓ framework OK
✓ aden_tools OK
✓ litellm OK
✓ LLM provider initialized
```

## Manual Setup (Alternative)

If the automated script fails or you prefer manual setup:

### 1. Install Core Framework

```bash
cd core
pip install -e .
cd ..
```

### 2. Install Tools Package

```bash
cd tools
pip install -e .
cd ..
```

### 3. Upgrade OpenAI Package (Required for LiteLLM)

```bash
pip install --upgrade "openai>=1.0.0"
```

### 4. Verify Installation

```bash
python -c "import framework; print('✓ framework OK')"
python -c "import aden_tools; print('✓ aden_tools OK')"
python -c "import litellm; print('✓ litellm OK')"
```

If any step fails, see the **Troubleshooting** section below.

## Requirements

### Python Version

- **Minimum:** Python 3.11
- **Recommended:** Python 3.11 or 3.12
- **Tested on:** Python 3.11, 3.12, 3.13

### System Requirements

- pip (latest version)
- 2GB+ RAM
- Internet connection (for LLM API calls)

### API Keys (Optional)

For running agents with real LLMs:

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

## Running Agents

### Command Structure

All agent commands must be run from the project root with `PYTHONPATH` set:

```bash
# General format
PYTHONPATH=core:exports python -m AGENT_NAME COMMAND

# Example
PYTHONPATH=core:exports python -m support_ticket_agent validate
```

### Common Commands

```bash
# Validate agent structure
PYTHONPATH=core:exports python -m your_agent_name validate

# Show agent info (goals, nodes, tools)
PYTHONPATH=core:exports python -m your_agent_name info

# Run agent with JSON input
PYTHONPATH=core:exports python -m your_agent_name run --input '{...}'

# Run in mock mode (no API calls, no cost)
PYTHONPATH=core:exports python -m your_agent_name run --mock --input '{...}'

# Run with custom configuration
PYTHONPATH=core:exports python -m your_agent_name run --config config.json --input '{...}'
```

### Example: Support Ticket Agent

```bash
# Validate structure
PYTHONPATH=core:exports python -m support_ticket_agent validate

# View agent configuration
PYTHONPATH=core:exports python -m support_ticket_agent info

# Run agent
PYTHONPATH=core:exports python -m support_ticket_agent run --input '{
  "ticket_content": "My login is broken. Error 401.",
  "customer_id": "CUST-123",
  "ticket_id": "TKT-456"
}'

# Test without LLM calls
PYTHONPATH=core:exports python -m support_ticket_agent run --mock --input '{
  "ticket_content": "Sample ticket",
  "customer_id": "CUST-001"
}'
```

### Example: Multiple Agents

```bash
# Market Research Agent
PYTHONPATH=core:exports python -m market_research_agent info

# Outbound Sales Agent  
PYTHONPATH=core:exports python -m outbound_sales_agent validate

# Personal Assistant Agent
PYTHONPATH=core:exports python -m personal_assistant_agent run --input '{
  "task": "Schedule a meeting"
}'
```

## Building New Agents

### With Claude Code (Recommended)

```bash
# Install skills (one-time)
./quickstart.sh

# Start building
claude> /building-agents
```

Follow the interactive prompts to:
1. Name your agent
2. Define its goal/purpose
3. Design workflow nodes
4. Connect edges (on_success, on_failure, etc.)
5. Configure tools
6. Generate the agent package

### Pure Python (Code-First)

```bash
# View example
cat core/examples/manual_agent.py

# Run example (no API keys needed)
PYTHONPATH=core python core/examples/manual_agent.py
```

This shows how to use the framework directly with pure Python functions.

### Testing Your Agent

```bash
# Using Claude Code
claude> /testing-agent

# Or manually
PYTHONPATH=core:exports python -m your_agent_name run --mock --input '{
  "test_input": "test_value"
}'
```

## Environment Configuration Examples

### Minimal Configuration (Single LLM)

```bash
# .env file - Minimal setup
ANTHROPIC_API_KEY=sk-ant-...
```

```bash
# Or in shell profile
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Complete Configuration (All Features)

```bash
# .env file - Complete setup
# ===== LLM PROVIDERS =====
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
CEREBRAS_API_KEY=...
GOOGLE_API_KEY=...

# ===== SEARCH & TOOLS =====
BRAVE_SEARCH_API_KEY=...

# ===== OPTIONAL RUNTIME =====
LOG_LEVEL=DEBUG
AGENT_TIMEOUT=300
MAX_RETRIES=3
```

### Development Configuration

For local testing without API costs:

```bash
# .env.dev
# Use mock LLM (for testing)
MOCK_LLM=true

# Or use cheaper models
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Disable expensive tools
DISABLE_WEB_SEARCH=true

# Short timeouts for testing
AGENT_TIMEOUT=30
```

### Production Configuration

For production deployment:

```bash
# .env.prod
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...

# Use best models for accuracy
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Production settings
LOG_LEVEL=WARNING
AGENT_TIMEOUT=600
MAX_RETRIES=5

# Resource limits
MAX_MEMORY_MB=2048
MAX_TOKENS_PER_MINUTE=10000
```

### Multi-Environment Setup

```bash
# Load appropriate .env file
source .env.dev   # For development
source .env.prod  # For production

# Or selectively override
export ANTHROPIC_API_KEY="prod-key"
```

## Troubleshooting

### Installation Issues

#### "externally-managed-environment" error (PEP 668)

**Cause:** Python 3.12+ on macOS/Homebrew, WSL, or some Linux distros

**Solution:** Use a virtual environment:

```bash
# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Run setup
./scripts/setup-python.sh
```

Always activate before running agents:

```bash
source .venv/bin/activate
PYTHONPATH=core:exports python -m your_agent_name validate
```

#### "ModuleNotFoundError: No module named 'framework'"

**Solution:**

```bash
cd core && pip install -e .
```

#### "ModuleNotFoundError: No module named 'aden_tools'"

**Solution:**

```bash
cd tools && pip install -e .
```

Or run the full setup:

```bash
./scripts/setup-python.sh
```

#### "ModuleNotFoundError: No module named 'openai.\_models'"

**Cause:** Outdated openai package incompatible with litellm

**Solution:**

```bash
pip install --upgrade "openai>=1.0.0"
```

### Runtime Issues

#### "APIError: Incorrect API Key"

**Cause:** ANTHROPIC_API_KEY not set or incorrect

**Solution:**

```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

# Or test directly
python << 'EOF'
import os
key = os.getenv('ANTHROPIC_API_KEY')
if not key:
    print("ERROR: ANTHROPIC_API_KEY not set")
elif key.startswith('sk-ant-'):
    print("✓ Key format looks correct")
else:
    print("ERROR: Key format invalid (should start with sk-ant-)")
EOF
```

#### "No module named 'support_ticket_agent'"

**Cause:** Not running from project root or missing PYTHONPATH

**Solution:**

```bash
# Verify you're in /hive directory
pwd  # Should show .../hive

# Use correct PYTHONPATH
PYTHONPATH=core:exports python -m your_agent_name validate
```

#### Agent imports fail with "broken installation"

**Symptom:** `pip list` shows packages pointing to non-existent directories

**Solution:**

```bash
# Clean reinstall
pip uninstall -y framework aden_tools
./scripts/setup-python.sh
```

### API Key Issues

#### "Brave Search API key not valid"

**Solution:**

1. Get key from https://api.search.brave.com/
2. Set correctly:
   ```bash
   export BRAVE_SEARCH_API_KEY="your-key-here"
   ```
3. Test:
   ```bash
   python -c "import os; print('Key:', os.getenv('BRAVE_SEARCH_API_KEY')[:10])"
   ```

#### "Multiple API keys set but agent not using mine"

**Solution:** Check provider precedence in your agent config. By default, LiteLLM tries providers in order:
1. Anthropic (if ANTHROPIC_API_KEY set)
2. OpenAI (if OPENAI_API_KEY set)
3. Others (Gemini, Cerebras, etc.)

To force a specific provider:

```bash
PYTHONPATH=core:exports python -m your_agent_name run --model openai/gpt-4o --input '{...}'
```

### Debugging

#### Enable debug logging

```bash
# Run with debug output
LOG_LEVEL=DEBUG PYTHONPATH=core:exports python -m your_agent_name run --input '{...}'
```

#### Test individual components

```bash
# Test LLM provider
python << 'EOF'
from framework.llm.litellm import LiteLLMProvider
llm = LiteLLMProvider(model='claude-3-5-sonnet-20241022')
response = llm.complete("Say hello")
print("✓ LLM works:", response)
EOF

# Test tools
python << 'EOF'
from aden_tools import WebSearchTool
tool = WebSearchTool()
result = tool.search("Python tutorial")
print("✓ Web Search works:", result)
EOF
```

#### Run agent in mock mode

```bash
# No API calls, no cost - good for testing
PYTHONPATH=core:exports python -m your_agent_name run --mock --input '{
  "test": "input"
}'
```

## Next Steps

✅ Setup complete! Now you can:

1. **Build your first agent** - `./quickstart.sh` then `claude> /building-agents`
2. **Run an example agent** - `PYTHONPATH=core:exports python -m support_ticket_agent info`
3. **Learn the framework** - Read [DEVELOPER.md](../DEVELOPER.md)
4. **Explore documentation** - Visit [docs/](../docs/)
5. **Check examples** - Look in [core/examples/](../core/examples/)

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/adenhq/hive/issues)
- **Discussions**: [GitHub Discussions](https://github.com/adenhq/hive/discussions)
- **Discord**: [Join community](https://discord.com/invite/MXE49hrKDk)
- **Docs**: [Complete documentation](https://docs.adenhq.com/)

## Package Structure

The Hive framework consists of three Python packages:

```
hive/
├── core/                    # Core framework (runtime, graph executor, LLM providers)
│   ├── framework/
│   ├── pyproject.toml
│   └── requirements.txt
│
├── tools/                   # Tools and MCP servers
│   ├── src/
│   │   └── aden_tools/     # Actual package location
│   ├── pyproject.toml
│   └── README.md
│
└── exports/                 # Agent packages (your agents go here)
    ├── support_ticket_agent/
    ├── market_research_agent/
    ├── outbound_sales_agent/
    └── personal_assistant_agent/
```

### Why PYTHONPATH is Required

The packages are installed in **editable mode** (`pip install -e`), which means:

- `framework` and `aden_tools` are globally importable (no PYTHONPATH needed)
- `exports` is NOT installed as a package (PYTHONPATH required)

This design allows agents in `exports/` to be:

- Developed independently
- Version controlled separately
- Deployed as standalone packages

## Development Workflow

### 1. Setup (Once)

```bash
./scripts/setup-python.sh
```

### 2. Build Agent (Claude Code)

```
claude> /building-agents
Enter goal: "Build an agent that processes customer support tickets"
```

### 3. Validate Agent

```bash
PYTHONPATH=core:exports python -m support_ticket_agent validate
```

### 4. Test Agent

```
claude> /testing-agent
```

### 5. Run Agent

```bash
PYTHONPATH=core:exports python -m support_ticket_agent run --input '{...}'
```

## IDE Setup

### VSCode

Add to `.vscode/settings.json`:

```json
{
  "python.analysis.extraPaths": [
    "${workspaceFolder}/core",
    "${workspaceFolder}/exports"
  ],
  "python.autoComplete.extraPaths": [
    "${workspaceFolder}/core",
    "${workspaceFolder}/exports"
  ]
}
```

### PyCharm

1. Open Project Settings → Project Structure
2. Mark `core` as Sources Root
3. Mark `exports` as Sources Root

## Environment Variables

### Required for LLM Operations

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Optional Configuration

```bash
# Credentials storage location (default: ~/.aden/credentials)
export ADEN_CREDENTIALS_PATH="/custom/path"

# Agent storage location (default: /tmp)
export AGENT_STORAGE_PATH="/custom/storage"
```

## Additional Resources

- **Framework Documentation:** [core/README.md](core/README.md)
- **Tools Documentation:** [tools/README.md](tools/README.md)
- **Example Agents:** [exports/](exports/)
- **Agent Building Guide:** [.claude/skills/building-agents-construction/SKILL.md](.claude/skills/building-agents-construction/SKILL.md)
- **Testing Guide:** [.claude/skills/testing-agent/SKILL.md](.claude/skills/testing-agent/SKILL.md)

## Contributing

When contributing agent packages:

1. Place agents in `exports/agent_name/`
2. Follow the standard agent structure (see existing agents)
3. Include README.md with usage instructions
4. Add tests if using `/testing-agent`
5. Document required environment variables

## Support

- **Issues:** https://github.com/adenhq/hive/issues
- **Discord:** https://discord.com/invite/MXE49hrKDk
- **Documentation:** https://docs.adenhq.com/
