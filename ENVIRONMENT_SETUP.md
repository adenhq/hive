# Agent Development Environment Setup

Complete setup guide for building and running goal-driven agents with the Aden Agent Framework.

## Quick Setup

```bash
# Run the automated setup script
./quickstart.sh
```

> **Note for Windows Users:**  
> Running the setup script on native Windows shells (PowerShell / Git Bash) may sometimes fail due to Python App Execution Aliases.  
> It is **strongly recommended to use WSL (Windows Subsystem for Linux)** for a smoother setup experience.

This will:

- Check Python version (requires 3.11+)
- Install the core framework package (`framework`)
- Install the tools package (`aden_tools`)
- Fix package compatibility issues (openai + litellm)
- Verify all installations

## Alpine Linux Setup

If you are using Alpine Linux (e.g., inside a Docker container), you must install system dependencies and use a virtual environment before running the setup script:

1. Install System Dependencies:
```bash
apk update
apk add bash git python3 py3-pip nodejs npm curl build-base python3-dev linux-headers libffi-dev
```
2. Set up Virtual Environment (Required for Python 3.12+):
```
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```
3. Run the Quickstart Script:
```
./quickstart.sh
```

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

> **Windows Tip:**  
> On Windows, if the verification commands fail, ensure you are running them in **WSL** or after **disabling Python App Execution Aliases** in Windows Settings → Apps → App Execution Aliases.

## Requirements

### Python Version

- **Minimum:** Python 3.11
- **Recommended:** Python 3.11 or 3.12
- **Tested on:** Python 3.11, 3.12, 3.13

### System Requirements

- pip (latest version)
- 2GB+ RAM
- Internet connection (for LLM API calls)
- For Windows users: WSL 2 is recommended for full compatibility.

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

### Example Commands

After building an agent via `/building-agents-construction`, use these commands:

```bash
# Validate agent structure
PYTHONPATH=core:exports python -m your_agent_name validate

# Show agent information
PYTHONPATH=core:exports python -m your_agent_name info

# Run agent with input
PYTHONPATH=core:exports python -m your_agent_name run --input '{
  "task": "Your input here"
}'

# Run in mock mode (no LLM calls)
PYTHONPATH=core:exports python -m your_agent_name run --mock --input '{...}'
```

## Building New Agents and Run Flow

Build and run an agent using Claude Code CLI with the agent building skills:

### 1. Install Claude Skills (One-time)

```bash
./quickstart.sh
```

This verifies agent-related Claude Code skills are available:

- `/building-agents-construction` - Step-by-step build guide
- `/building-agents-core` - Fundamental concepts
- `/building-agents-patterns` - Best practices
- `/testing-agent` - Test and validate agents
- `/agent-workflow` - Complete workflow

### 2. Build an Agent

```
claude> /building-agents-construction
```

Follow the prompts to:

1. Define your agent's goal
2. Design the workflow nodes
3. Connect nodes with edges
4. Generate the agent package under `exports/`

This step creates the initial agent structure required for further development.

### 3. Define Agent Logic

```
claude> /building-agents-core
```

Follow the prompts to:

1. Understand the agent architecture and file structure
2. Define the agent's goal, success criteria, and constraints
3. Learn node types (LLM, tool-use, router, function)
4. Discover and validate available tools before use

This step establishes the core concepts and rules needed before building an agent.

### 4. Apply Agent Patterns

```
claude> /building-agents-patterns
```

Follow the prompts to:

1. Apply best-practice agent design patterns
2. Add pause/resume flows for multi-turn interactions
3. Improve robustness with routing, fallbacks, and retries
4. Avoid common anti-patterns during agent construction

This step helps optimize agent design before final testing.

### 5. Test Your Agent

```
claude> /testing-agent
```
Follow the prompts to:

1. Generate test guidelines for constraints and success criteria
2. Write agent tests directly under `exports/{agent}/tests/`
3. Run goal-based evaluation tests
4. Debug failing tests and iterate on agent improvements

This step verifies that the agent meets its goals before production use.

### 6. Agent Development Workflow (End-to-End)

```
claude> /agent-workflow
```

Follow the guided flow to:

1. Understand core agent concepts (optional)
2. Build the agent structure step by step
3. Apply best-practice design patterns (optional)
4. Test and validate the agent against its goals

This workflow orchestrates all agent-building skills to take you from idea → production-ready agent.

## Common Setup Issues

This section covers frequent errors developers encounter during setup, with brief explanations and concrete fixes.

<details>
<summary><strong>🔍 Quick Diagnosis</strong></summary>

| Symptom | Likely Cause | Jump To |
|---------|--------------|---------|
| `command not found: python` | Python not in PATH | [Python PATH Issues](#python-path-issues) |
| `python: command not found` but `python3` works | Missing `python` alias | [Python vs Python3](#python-vs-python3) |
| `externally-managed-environment` error | System Python protection | [PEP 668 Error](#externally-managed-environment-error-pep-668) |
| `Permission denied` during install | Missing write permissions | [Permission Errors](#permission-errors) |
| `ModuleNotFoundError: framework` | Package not installed | [Missing Module Errors](#missing-module-errors) |
| `No module named 'your_agent_name'` | PYTHONPATH not set | [PYTHONPATH Issues](#pythonpath-issues) |
| Script hangs or no output | Virtual environment not activated | [Virtual Environment Issues](#virtual-environment-issues) |

</details>

---

### Python PATH Issues

**Symptom:** `command not found: python` or `python: command not found`

**Cause:** Python is installed but not in your shell's PATH.

**Solution:**

```bash
# Check if Python is installed somewhere
which python3
# If this returns a path, Python is installed but 'python' command isn't linked

# Option 1: Use python3 explicitly
python3 --version

# Option 2: Add alias to your shell profile (~/.bashrc, ~/.zshrc)
echo 'alias python=python3' >> ~/.zshrc
source ~/.zshrc
```

**macOS-specific:** If you installed Python via Homebrew:
```bash
# Add Homebrew Python to PATH
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

### Python vs Python3

**Symptom:** `python` doesn't work, but `python3` does.

**Cause:** Many systems install Python 3 as `python3` only, not `python`.

**Solution:**

```bash
# Option 1: Create a symlink (requires sudo on some systems)
sudo ln -s $(which python3) /usr/local/bin/python

# Option 2: Use an alias (add to ~/.bashrc or ~/.zshrc)
alias python=python3
alias pip=pip3

# Option 3: Use python3 in all commands
python3 -m venv .venv
python3 -c "import framework; print('OK')"
```

---

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
./quickstart.sh
```

Always activate the venv before running agents:

```bash
source .venv/bin/activate
PYTHONPATH=core:exports python -m your_agent_name demo
```

---

### Permission Errors

**Symptom:** `Permission denied` during pip install or script execution.

**Cause:** Trying to install packages system-wide without proper permissions.

**Solution:**

```bash
# NEVER use sudo pip install! Use a virtual environment instead:
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# If script isn't executable:
chmod +x ./quickstart.sh
./quickstart.sh
```

---

### Missing Module Errors

#### "ModuleNotFoundError: No module named 'framework'"

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
./quickstart.sh
```

### "ModuleNotFoundError: No module named 'openai.\_models'"

**Cause:** Outdated `openai` package (0.27.x) incompatible with `litellm`

**Solution:** Upgrade openai:

```bash
pip install --upgrade "openai>=1.0.0"
```

---

### PYTHONPATH Issues

#### "No module named 'your_agent_name'"

**Cause:** Not running from project root, missing PYTHONPATH, or agent not yet created.

**Solution:** 

```bash
# 1. Make sure you're in the project root
cd /path/to/hive

# 2. Check if agent exists
ls exports/

# 3. Run with PYTHONPATH set
PYTHONPATH=core:exports python -m your_agent_name validate
```

**Common mistakes:**
- Running from inside `core/` or `tools/` instead of project root
- Agent not yet created (run `/building-agents-construction` first)
- Typo in agent name

---

### Virtual Environment Issues

**Symptom:** Commands hang, wrong Python version used, or packages not found after install.

**Cause:** Virtual environment not activated or conflicting with system Python.

**Solution:**

```bash
# Check if venv is activated (should show .venv path)
which python

# If not activated, activate it:
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Verify correct Python is being used
python --version
which pip
```

**If you have multiple Python versions:**
```bash
# Create venv with specific Python version
python3.11 -m venv .venv
source .venv/bin/activate
```

---

### Agent imports fail with \"broken installation\"

**Symptom:** `pip list` shows packages pointing to non-existent directories

**Solution:** Reinstall packages properly:

```bash
# Remove broken installations
pip uninstall -y framework tools

# Reinstall correctly
./quickstart.sh
```

## Package Structure

The Hive framework consists of three Python packages:

```
hive/
├── core/                    # Core framework (runtime, graph executor, LLM providers)
│   ├── framework/
│   ├── .venv/              # Created by quickstart.sh
│   └── pyproject.toml
│
├── tools/                   # Tools and MCP servers
│   ├── src/
│   │   └── aden_tools/     # Actual package location
│   ├── .venv/              # Created by quickstart.sh
│   └── pyproject.toml
│
└── exports/                 # Agent packages (user-created, gitignored)
    └── your_agent_name/     # Created via /building-agents-construction
```

## Separate Virtual Environments

The project uses **separate virtual environments** for `core` and `tools` packages to:

- Isolate dependencies and avoid conflicts
- Allow independent development and testing of each package
- Enable MCP servers to run with their specific dependencies

### How It Works

When you run `./quickstart.sh` or `uv sync` in each directory:

1. **core/.venv/** - Contains the `framework` package and its dependencies (anthropic, litellm, mcp, etc.)
2. **tools/.venv/** - Contains the `aden_tools` package and its dependencies (beautifulsoup4, pandas, etc.)

### Cross-Package Imports

The `core` and `tools` packages are **intentionally independent**:

- **No cross-imports**: `framework` does not import `aden_tools` directly, and vice versa
- **Communication via MCP**: Tools are exposed to agents through MCP servers, not direct Python imports
- **Runtime integration**: The agent runner loads tools via the MCP protocol at runtime

If you need to use both packages in a single script (e.g., for testing), you have two options:

```bash
# Option 1: Install both in a shared environment
python -m venv .venv
source .venv/bin/activate
pip install -e core/ -e tools/

# Option 2: Use PYTHONPATH (for quick testing)
PYTHONPATH=core:tools/src python your_script.py
```

### MCP Server Configuration

The `.mcp.json` at project root configures MCP servers to use their respective virtual environments:

```json
{
  "mcpServers": {
    "agent-builder": {
      "command": "core/.venv/bin/python",
      "args": ["-m", "framework.mcp.agent_builder_server"]
    },
    "tools": {
      "command": "tools/.venv/bin/python",
      "args": ["-m", "aden_tools.mcp_server", "--stdio"]
    }
  }
}
```

This ensures each MCP server runs with its correct dependencies.

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
./quickstart.sh
```

### 2. Build Agent (Claude Code)

```
claude> /building-agents-construction
Enter goal: "Build an agent that processes customer support tickets"
```

### 3. Validate Agent

```bash
PYTHONPATH=core:exports python -m your_agent_name validate
```

### 4. Test Agent

```
claude> /testing-agent
```

### 5. Run Agent

```bash
PYTHONPATH=core:exports python -m your_agent_name run --input '{...}'
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
