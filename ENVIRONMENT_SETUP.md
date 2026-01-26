# Agent Development Environment Setup

Complete setup guide for building and running goal-driven agents with the Aden Agent Framework.

## Quick Setup

### Recommended: With uv (Fast & Reliable)

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run the automated setup script (auto-detects uv)
./scripts/setup-python.sh
```

This will:

- Install Python 3.11 automatically via uv
- Sync all workspace packages (framework + aden_tools)
- Use uv.lock for reproducible installations
- Verify all packages import correctly

**Benefits of uv:**
- 10-100x faster than pip
- Reproducible builds with lock file
- Automatic Python version management
- Better dependency resolution

### Alternative: With pip (Legacy)

```bash
# Run the automated setup script
./scripts/setup-python.sh
```

The script automatically falls back to pip if uv is not installed.

This will:

- Check Python version (requires 3.11+)
- Install the core framework package (`framework`)
- Install the tools package (`aden_tools`)
- Fix package compatibility issues (openai + litellm)
- Verify all installations

> See [UV Migration Guide](docs/UV_MIGRATION.md) for detailed information about using uv.

## Manual Setup (Alternative)

If you prefer to set up manually or the script fails:

### With uv (Recommended)

```bash
# From project root
uv sync --all-packages
```

That's it! This single command:
- Installs Python 3.11 if needed
- Syncs both framework and aden_tools packages
- Uses the lock file for reproducible builds

### With pip (Legacy)

```bash
# 1. Install Core Framework
cd core
pip install -e .

# 2. Install Tools Package
cd ../tools
pip install -e .

# 3. Upgrade OpenAI Package (litellm compatibility)
pip install --upgrade "openai>=1.0.0"
```

### Verify Installation

```bash
# With uv
uv run python -c "import framework; print('✓ framework OK')"
uv run python -c "import aden_tools; print('✓ aden_tools OK')"
uv run python -c "import litellm; print('✓ litellm OK')"

# With pip
python -c "import framework; print('✓ framework OK')"
python -c "import aden_tools; print('✓ aden_tools OK')"
python -c "import litellm; print('✓ litellm OK')"
```

## Requirements

### Python Version

- **Minimum:** Python 3.11
- **Recommended:** Python 3.11 or 3.12
- **Tested on:** Python 3.11, 3.12, 3.13

### Package Manager

**Recommended:**
- [uv](https://docs.astral.sh/uv/) 0.5+ - Fast Python package manager
  - Installs Python automatically
  - 10-100x faster than pip
  - Reproducible builds

**Alternative:**
- pip (latest version)

### System Requirements

- 2GB+ RAM
- Internet connection (for LLM API calls and package downloads)

### API Keys (Optional)

For running agents with real LLMs:

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

## Running Agents

All agent commands must be run from the project root with `PYTHONPATH` set:

### With uv (Recommended)

```bash
# From /hive/ directory
PYTHONPATH=core:exports uv run python -m agent_name COMMAND
```

### With pip (Legacy)

```bash
# From /hive/ directory
PYTHONPATH=core:exports python -m agent_name COMMAND
```

### Example: Support Ticket Agent

#### With uv

```bash
# Validate agent structure
PYTHONPATH=core:exports uv run python -m support_ticket_agent validate

# Show agent information
PYTHONPATH=core:exports uv run python -m support_ticket_agent info

# Run agent with input
PYTHONPATH=core:exports uv run python -m support_ticket_agent run --input '{
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

Use Claude Code CLI with the agent building skills:

### 1. Install Skills (One-time)

```bash
./quickstart.sh
```

This installs:

- `/building-agents` - Build new agents
- `/testing-agent` - Test agents

### 2. Build an Agent

```
claude> /building-agents
```

Follow the prompts to:

1. Define your agent's goal
2. Design the workflow nodes
3. Connect edges
4. Generate the agent package

### 3. Test Your Agent

```
claude> /testing-agent
```

Creates comprehensive test suites for your agent.

## Troubleshooting

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

**Solution:** Ensure you're in `/home/timothy/oss/hive/` and use:

```bash
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

## UV Development Workflow

If you're using uv (recommended), here are common commands for development:

### Managing Dependencies

```bash
# Add a new dependency to core package
cd core
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Remove a dependency
uv remove <package-name>

# Update a specific package
uv lock --upgrade-package <package-name>
uv sync

# Update all packages
uv lock --upgrade
uv sync
```

### Working with the Workspace

```bash
# Sync all workspace packages (from project root)
uv sync --all-packages

# Sync only production dependencies
uv sync --no-dev

# Sync with all optional dependencies
uv sync --all-extras

# View dependency tree
uv tree

# List installed packages
uv pip list
```

### Python Version Management

```bash
# Install Python 3.11
uv python install 3.11

# Install Python 3.12
uv python install 3.12

# List available Python versions
uv python list

# Pin Python version (creates .python-version)
echo "3.11" > .python-version
```

### Running Commands

```bash
# Run Python script
uv run python script.py

# Run tests
uv run pytest tests/

# Run with environment variables
ANTHROPIC_API_KEY=... uv run python -m agent_name run
```

### Troubleshooting

```bash
# Clear cache and reinstall
uv cache clean
uv sync --refresh

# Check lock file is up to date
uv lock --check

# Regenerate lock file
uv lock
```

For detailed information, see the [UV Migration Guide](docs/UV_MIGRATION.md).

## Additional Resources

- **UV Migration Guide:** [docs/UV_MIGRATION.md](docs/UV_MIGRATION.md)
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
