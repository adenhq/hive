# Agent Development Environment Setup

Complete setup guide for building and running goal-driven agents with the Aden Agent Framework.

## Prerequisites

Before you start, make sure you have:

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.11+ (3.12 recommended) | `python --version` |
| pip | Latest | `pip --version` |
| git | Any recent version | `git --version` |

### Operating System Support

| OS | Status | Notes |
|----|--------|-------|
| **macOS** | Fully supported | Works out of the box |
| **Linux** | Fully supported | Ubuntu, Debian, Fedora tested |
| **Windows** | Supported | Use PowerShell or WSL; see [Windows notes](#windows-setup-notes) below |

### Optional Tools

- **Claude Code CLI** - Only needed if you want to use the `/building-agents` and `/testing-agent` skills. You can build agents manually without it.
- **Docker** - Only needed for containerized deployment, not required for local development.

## Quick Setup

```bash
# Run the automated setup script
./scripts/setup-python.sh
```

This will:

- Check Python version (requires 3.11+)
- Install the core framework package (`framework`)
- Install the tools package (`aden_tools`)
- Fix package compatibility issues (openai + litellm)
- Verify all installations

## Using a Virtual Environment (Recommended)

We recommend using a virtual environment to avoid conflicts with system packages:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate        # macOS/Linux
# OR
.venv\Scripts\activate           # Windows PowerShell

# Then run setup
./scripts/setup-python.sh
```

> **Note:** On some Linux systems (Ubuntu 24.04+), installing packages system-wide is blocked. A virtual environment is required.

## Manual Setup (Alternative)

If you prefer to set up manually or the script fails:

### 1. Install Core Framework

```bash
cd core
pip install -e .
```

### 2. Install Tools Package

```bash
cd tools
pip install -e .
```

### 3. Upgrade OpenAI Package

```bash
# litellm requires openai >= 1.0.0
pip install --upgrade "openai>=1.0.0"
```

### 4. Verify Installation

```bash
python -c "import framework; print('✓ framework OK')"
python -c "import aden_tools; print('✓ aden_tools OK')"
python -c "import litellm; print('✓ litellm OK')"
```

## Important: PYTHONPATH for Running Agents

When running agents, you need to set `PYTHONPATH` so Python can find both the framework and your agent packages:

```bash
# Always run from the project root (hive/) directory
PYTHONPATH=core:exports python -m agent_name COMMAND
```

**Why?** The `exports/` directory contains agent packages that aren't installed via pip. Setting PYTHONPATH tells Python where to find them.

**Quick test after setup:**
```bash
PYTHONPATH=core:exports python -m support_ticket_agent validate
```

If this works, you're all set!

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

All agent commands must be run from the project root with `PYTHONPATH` set:

```bash
# From /hive/ directory
PYTHONPATH=core:exports python -m agent_name COMMAND
```

### Example: Support Ticket Agent

```bash
# Validate agent structure
PYTHONPATH=core:exports python -m support_ticket_agent validate

# Show agent information
PYTHONPATH=core:exports python -m support_ticket_agent info

# Run agent with input
PYTHONPATH=core:exports python -m support_ticket_agent run --input '{
  "ticket_content": "My login is broken. Error 401.",
  "customer_id": "CUST-123",
  "ticket_id": "TKT-456"
}'

# Run in mock mode (no LLM calls)
PYTHONPATH=core:exports python -m support_ticket_agent run --mock --input '{...}'
```

### Example: Other Agents

```bash
# Market Research Agent
PYTHONPATH=core:exports python -m market_research_agent info

# Outbound Sales Agent
PYTHONPATH=core:exports python -m outbound_sales_agent validate

# Personal Assistant Agent
PYTHONPATH=core:exports python -m personal_assistant_agent run --input '{...}'
```

## Building New Agents

You have two options for building agents:

### Option A: Using Claude Code Skills (Recommended)

If you have [Claude Code CLI](https://docs.anthropic.com/claude/docs/claude-code) installed:

```bash
# Install the skills (one-time)
./quickstart.sh
```

Then use the skills:
```
claude> /building-agents   # Guided agent creation
claude> /testing-agent     # Generate test suites
```

### Option B: Manual Agent Creation

You can also create agents manually without Claude Code:

1. Copy an existing agent as a template:
   ```bash
   cp -r exports/support_ticket_agent exports/my_agent
   ```

2. Edit `agent.json` to define your nodes and edges
3. Add custom tools in `tools.py` if needed
4. Update `README.md` with your agent's documentation

See [exports/support_ticket_agent/](exports/support_ticket_agent/) for a complete example.

## Windows Setup Notes

### Running the Setup Script

On Windows, use Git Bash or WSL to run the setup script:

```bash
# Git Bash
./scripts/setup-python.sh

# Or use WSL
wsl ./scripts/setup-python.sh
```

### Setting PYTHONPATH on Windows

```powershell
# PowerShell (temporary, current session only)
$env:PYTHONPATH = "core;exports"
python -m support_ticket_agent validate

# Or use the SET command in CMD
set PYTHONPATH=core;exports
python -m support_ticket_agent validate
```

> **Note:** Windows uses `;` as the path separator, not `:` like macOS/Linux.

### Common Windows Issues

- **"execution of scripts is disabled"** - Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell as admin
- **Unicode errors** - Set `$env:PYTHONIOENCODING = "utf-8"` before running agents

## Troubleshooting

### "externally-managed-environment" error (PEP 668)

**Cause:** Python 3.12+ on macOS/Homebrew, WSL, or some Linux distros prevents system-wide pip installs.

**Solution:** Create and use a virtual environment:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Then run setup
./scripts/setup-python.sh
```

Always activate the venv before running agents:

```bash
source .venv/bin/activate
PYTHONPATH=core:exports python -m your_agent_name demo
```

### "ModuleNotFoundError: No module named 'framework'"

**Solution:** Install the core package:

```bash
cd core && pip install -e .
```

### "ModuleNotFoundError: No module named 'aden_tools'"

**Solution:** Install the tools package:

```bash
cd tools && pip install -e .
```

Or run the setup script:

```bash
./scripts/setup-python.sh
```

### "ModuleNotFoundError: No module named 'openai.\_models'"

**Cause:** Outdated `openai` package (0.27.x) incompatible with `litellm`

**Solution:** Upgrade openai:

```bash
pip install --upgrade "openai>=1.0.0"
```

### "No module named 'support_ticket_agent'"

**Cause:** Not running from project root or missing PYTHONPATH

**Solution:** Make sure you're in the `hive/` project root directory and use:

```bash
# Check you're in the right directory
ls core/  # Should show framework/, pyproject.toml, etc.

# Run with PYTHONPATH
PYTHONPATH=core:exports python -m support_ticket_agent validate
```

### Agent imports fail with "broken installation"

**Symptom:** `pip list` shows packages pointing to non-existent directories

**Solution:** Reinstall packages properly:

```bash
# Remove broken installations
pip uninstall -y framework tools

# Reinstall correctly
./scripts/setup-python.sh
```

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
