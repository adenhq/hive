# Agent Development Environment Setup

Complete setup guide for building and running goal-driven agents with the Aden Agent Framework.

## Choose Your Operating System

Jump to setup instructions for your environment:

- **[macOS](#macos)** — Quick Setup, Manual Setup, and verification (use `python3` / `pip3`).
- **[Linux](#linux)** — Quick Setup, Manual Setup, and verification (use `python3` / `pip3`).
- **[Windows (PowerShell)](#windows-powershell)** — Quick Setup, Manual Setup, and verification (use `python`; PYTHONPATH uses `;`).

---

## macOS

**Python:** Use `python3` and `pip3` (or `pip`) so the correct 3.11+ interpreter is used. If `python` points to Python 2, avoid it.

### Quick Setup

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

### Manual Setup (Alternative)

If you prefer to set up manually or the script fails:

**1. Install Core Framework**

```bash
cd core
pip install -e .
# or: pip3 install -e .
```

**2. Install Tools Package**

```bash
cd tools
pip install -e .
# or: pip3 install -e .
```

**3. Upgrade OpenAI Package**

```bash
# litellm requires openai >= 1.0.0
pip install --upgrade "openai>=1.0.0"
```

**4. Verify Installation**

```bash
python3 -c "import framework; print('✓ framework OK')"
python3 -c "import aden_tools; print('✓ aden_tools OK')"
python3 -c "import litellm; print('✓ litellm OK')"
```

**Running agents (macOS):** Use colon-separated PYTHONPATH and `python3`:

```bash
PYTHONPATH=core:exports python3 -m agent_name COMMAND
```

---

## Linux

**Python:** Use `python3` and `pip3` (or `pip`) so the correct 3.11+ interpreter is used. If `python` points to Python 2, avoid it.

### Quick Setup

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

### Alpine Linux (Docker / Minimal Distros)

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

**1. Install Core Framework**

```bash
cd core
pip install -e .
# or: pip3 install -e .
```

**2. Install Tools Package**

```bash
cd tools
pip install -e .
# or: pip3 install -e .
```

**3. Upgrade OpenAI Package**

```bash
# litellm requires openai >= 1.0.0
pip install --upgrade "openai>=1.0.0"
```

**4. Verify Installation**

```bash
python3 -c "import framework; print('✓ framework OK')"
python3 -c "import aden_tools; print('✓ aden_tools OK')"
python3 -c "import litellm; print('✓ litellm OK')"
```

**Running agents (Linux):** Use colon-separated PYTHONPATH and `python3`:

```bash
PYTHONPATH=core:exports python3 -m agent_name COMMAND
```

---

## Windows (PowerShell)

**Python:** Use `python` and `pip` (Windows typically does not ship Python 2; `python3` may also be available). **PYTHONPATH:** In PowerShell use semicolons: `core;exports` (not colons).

> **Note for Windows Users:**  
> Running the setup script on native Windows shells (PowerShell / Git Bash) may sometimes fail due to Python App Execution Aliases.  
> It is **strongly recommended to use WSL (Windows Subsystem for Linux)** for a smoother setup experience.

### Quick Setup

From **WSL** or **Git Bash** (recommended):

```bash
# Run the automated setup script
./scripts/setup-python.sh
```

From **PowerShell** you can run the same script if Bash is available (e.g. Git Bash in PATH), or follow Manual Setup below.

This will:

- Check Python version (requires 3.11+)
- Install the core framework package (`framework`)
- Install the tools package (`aden_tools`)
- Fix package compatibility issues (openai + litellm)
- Verify all installations

### Manual Setup (Alternative)

If you prefer to set up manually or the script fails, run these in **PowerShell** (or your terminal):

**1. Install Core Framework**

```powershell
cd core
pip install -e .
```

**2. Install Tools Package**

```powershell
cd tools
pip install -e .
```

**3. Upgrade OpenAI Package**

```powershell
# litellm requires openai >= 1.0.0
pip install --upgrade "openai>=1.0.0"
```

**4. Verify Installation**

```powershell
python -c "import framework; print('✓ framework OK')"
python -c "import aden_tools; print('✓ aden_tools OK')"
python -c "import litellm; print('✓ litellm OK')"
```

> **Windows Tip:**  
> If verification fails, use **WSL** or **disable Python App Execution Aliases** in Windows Settings → Apps → App Execution Aliases.

**Running agents (PowerShell):** Set PYTHONPATH with semicolons, then run:

```powershell
$env:PYTHONPATH = "core;exports"
python -m agent_name COMMAND
```

Or one line (PowerShell):

```powershell
$env:PYTHONPATH="core;exports"; python -m agent_name COMMAND
```

---

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

**macOS / Linux:**

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

**Windows (PowerShell):**

```powershell
$env:ANTHROPIC_API_KEY = "your-key-here"
```

---

## Running Agents

All agent commands must be run from the project root with `PYTHONPATH` set.

- **macOS / Linux:** `PYTHONPATH=core:exports` (colon), and use `python3` if that’s your 3.11+ interpreter.
- **Windows (PowerShell):** `$env:PYTHONPATH="core;exports"` (semicolon), and use `python`.

```bash
# From project root (hive/)
# macOS/Linux:
PYTHONPATH=core:exports python3 -m agent_name COMMAND

# Windows PowerShell (set once per session or inline):
$env:PYTHONPATH="core;exports"; python -m agent_name COMMAND
```

### Example: Support Ticket Agent

**macOS / Linux:**

```bash
# Validate agent structure
PYTHONPATH=core:exports python3 -m support_ticket_agent validate

# Show agent information
PYTHONPATH=core:exports python3 -m support_ticket_agent info

# Run agent with input
PYTHONPATH=core:exports python3 -m support_ticket_agent run --input '{
  "ticket_content": "My login is broken. Error 401.",
  "customer_id": "CUST-123",
  "ticket_id": "TKT-456"
}'

# Run in mock mode (no LLM calls)
PYTHONPATH=core:exports python3 -m support_ticket_agent run --mock --input '{...}'
```

**Windows (PowerShell):** Set `$env:PYTHONPATH="core;exports"` once, then:

```powershell
python -m support_ticket_agent validate
python -m support_ticket_agent info
python -m support_ticket_agent run --input '{ "ticket_content": "My login is broken. Error 401.", "customer_id": "CUST-123", "ticket_id": "TKT-456" }'
python -m support_ticket_agent run --mock --input '{...}'
```

### Example: Other Agents

**macOS / Linux:**

```bash
# Market Research Agent
PYTHONPATH=core:exports python3 -m market_research_agent info

# Outbound Sales Agent
PYTHONPATH=core:exports python3 -m outbound_sales_agent validate

# Personal Assistant Agent
PYTHONPATH=core:exports python3 -m personal_assistant_agent run --input '{...}'
```

**Windows (PowerShell):** With `$env:PYTHONPATH="core;exports"` set:

```powershell
python -m market_research_agent info
python -m outbound_sales_agent validate
python -m personal_assistant_agent run --input '{...}'
```

## Building New Agents and Run Flow

Build and run an agent using Claude Code CLI with the agent building skills:

### 1. Install Claude Skills (One-time)

```bash
./quickstart.sh
```

This installs agent-related Claude Code skills:

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

---

## Troubleshooting

### "externally-managed-environment" error (PEP 668)

**Cause:** Python 3.12+ on macOS/Homebrew, WSL, or some Linux distros prevents system-wide pip installs.

**Solution:** Create and use a virtual environment:

**macOS / Linux:**

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Then run setup
./scripts/setup-python.sh
```

**Windows (PowerShell):**

```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\Activate.ps1

# Then run setup (from WSL/Git Bash if using the script, or do Manual Setup in PowerShell)
./scripts/setup-python.sh
```

Always activate the venv before running agents:

**macOS / Linux:**

```bash
source .venv/bin/activate
PYTHONPATH=core:exports python3 -m your_agent_name demo
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
$env:PYTHONPATH="core;exports"; python -m your_agent_name demo
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

**Solution:** Ensure you're in the project root directory and use:

**macOS / Linux:** `PYTHONPATH=core:exports python3 -m support_ticket_agent validate`

**Windows (PowerShell):** `$env:PYTHONPATH="core;exports"; python -m support_ticket_agent validate`

### Agent imports fail with "broken installation"

**Symptom:** `pip list` shows packages pointing to non-existent directories

**Solution:** Reinstall packages properly:

```bash
# Remove broken installations
pip uninstall -y framework tools

# Reinstall correctly
./scripts/setup-python.sh
```

---

## Package Structure

The Hive framework consists of three Python packages:

```
hive/
├── core/                    # Core framework (runtime, graph executor, LLM providers)
│   ├── framework/
│   ├── .venv/              # Isolated virtual environment for core
│   └── pyproject.toml
│
├── tools/                   # Tools and MCP servers
│   ├── src/
│   │   └── aden_tools/     # Actual package location
│   ├── .venv/              # Isolated virtual environment for tools
│   └── pyproject.toml
│
└── exports/                 # Agent packages (your agents go here)
    ├── support_ticket_agent/
    ├── market_research_agent/
    ├── outbound_sales_agent/
    └── personal_assistant_agent/
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

**Syntax by OS:** Use `core:exports` on macOS/Linux; use `core;exports` on Windows (PowerShell).

---

## Development Workflow

### 1. Setup (Once)

```bash
./scripts/setup-python.sh
```

### 2. Build Agent (Claude Code)

```
claude> /building-agents-construction
Enter goal: "Build an agent that processes customer support tickets"
```

### 3. Validate Agent

**macOS / Linux:** `PYTHONPATH=core:exports python3 -m support_ticket_agent validate`

**Windows (PowerShell):** `$env:PYTHONPATH="core;exports"; python -m support_ticket_agent validate`

### 4. Test Agent

```
claude> /testing-agent
```

### 5. Run Agent

**macOS / Linux:** `PYTHONPATH=core:exports python3 -m support_ticket_agent run --input '{...}'`

**Windows (PowerShell):** `$env:PYTHONPATH="core;exports"; python -m support_ticket_agent run --input '{...}'`

---

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

---

## Environment Variables

### Required for LLM Operations

**macOS / Linux:** `export ANTHROPIC_API_KEY="sk-ant-..."`

**Windows (PowerShell):** `$env:ANTHROPIC_API_KEY = "sk-ant-..."`

### Optional Configuration

**macOS / Linux:**

```bash
# Credentials storage location (default: ~/.aden/credentials)
export ADEN_CREDENTIALS_PATH="/custom/path"

# Agent storage location (default: /tmp)
export AGENT_STORAGE_PATH="/custom/storage"
```

**Windows (PowerShell):**

```powershell
$env:ADEN_CREDENTIALS_PATH = "/custom/path"
$env:AGENT_STORAGE_PATH = "/custom/storage"
```

---

## Additional Resources

- **Framework Documentation:** [core/README.md](core/README.md)
- **Tools Documentation:** [tools/README.md](tools/README.md)
- **Example Agents:** [exports/](exports/)
- **Agent Building Guide:** [.claude/skills/building-agents-construction/SKILL.md](.claude/skills/building-agents-construction/SKILL.md)
- **Testing Guide:** [.claude/skills/testing-agent/SKILL.md](.claude/skills/testing-agent/SKILL.md)

---

## Contributing

When contributing agent packages:

1. Place agents in `exports/agent_name/`
2. Follow the standard agent structure (see existing agents)
3. Include README.md with usage instructions
4. Add tests if using `/testing-agent`
5. Document required environment variables

---

## Support

- **Issues:** https://github.com/adenhq/hive/issues
- **Discord:** https://discord.com/invite/MXE49hrKDk
- **Documentation:** https://docs.adenhq.com/
