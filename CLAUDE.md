# CLAUDE.md - AI Assistant Guide for Aden Agent Framework

This file provides guidance for AI assistants working with the Aden Agent Framework (Hive) codebase.

## Project Overview

Aden is an open-source Python framework for building goal-driven, self-improving AI agents. Key characteristics:

- **Goal-Driven Development**: Define objectives in natural language; a coding agent generates agent graphs and connection code
- **Self-Adapting**: Framework captures failures, evolves agent graphs, and redeploys automatically
- **SDK-Wrapped Nodes**: Every node gets shared memory, monitoring, tools, and LLM access out of the box
- **Human-in-the-Loop**: Intervention nodes that pause execution for human input
- **100+ LLM Providers**: Via LiteLLM (OpenAI, Anthropic, Google, DeepSeek, Mistral, Groq, Ollama, etc.)

**License**: Apache 2.0

## Directory Structure

```
hive/
├── core/                   # Core framework package
│   ├── framework/
│   │   ├── runner/         # AgentRunner - loads & executes agents
│   │   ├── graph/          # GraphExecutor - DAG execution with branching
│   │   ├── llm/            # LLM provider integrations (Anthropic, LiteLLM)
│   │   ├── runtime/        # Agent runtime, event bus, streaming
│   │   ├── schemas/        # Pydantic models (Run, Decision)
│   │   ├── storage/        # Run/decision persistence
│   │   ├── testing/        # Goal-based testing framework
│   │   ├── builder/        # BuilderQuery for run analysis
│   │   ├── credentials/    # Credential management
│   │   └── mcp/            # MCP server integration
│   ├── tests/              # Framework test suite
│   ├── pyproject.toml      # Package metadata & Ruff config
│   └── requirements*.txt   # Dependencies
│
├── tools/                  # Aden Tools MCP server (19 tools)
│   ├── src/aden_tools/
│   │   ├── tools/
│   │   │   ├── file_system_toolkits/  # view_file, write_to_file, list_dir, etc.
│   │   │   ├── web_search_tool/
│   │   │   ├── web_scrape_tool/
│   │   │   ├── pdf_read_tool/
│   │   │   └── ...
│   │   └── mcp_server.py   # FastMCP server entry point
│   ├── pyproject.toml
│   └── requirements.txt
│
├── exports/                # User-created agent packages (gitignored)
│   └── [agent_name]/
│       ├── __init__.py
│       ├── __main__.py     # CLI entry point
│       ├── agent.json      # Agent graph definition
│       ├── tools.py        # Custom tools
│       ├── mcp_servers.json
│       └── tests/          # Agent tests
│
├── .claude/                # Claude Code skills
│   └── skills/
│       ├── building-agents-core/
│       ├── building-agents-construction/
│       ├── building-agents-patterns/
│       ├── testing-agent/
│       └── agent-workflow/
│
├── docs/                   # Documentation
├── scripts/                # Setup scripts
└── .github/                # CI/CD workflows
```

## Quick Reference Commands

### Setup
```bash
./scripts/setup-python.sh    # Install framework + aden_tools
./quickstart.sh              # Install Claude Code skills
```

### Development
```bash
make lint                    # Ruff check with auto-fix
make format                  # Ruff format
make check                   # CI-safe checks (no modifications)
make test                    # Run pytest
make install-hooks           # Install pre-commit hooks
```

### Running Agents
```bash
PYTHONPATH=core:exports python -m agent_name run --input '{...}'
PYTHONPATH=core:exports python -m agent_name test
```

### Direct Commands
```bash
# Linting
cd core && ruff check --fix .
cd tools && ruff check --fix .

# Formatting
cd core && ruff format .
cd tools && ruff format .

# Testing
cd core && pytest tests/ -v
cd tools && pytest tests/ -v
```

## Code Style & Conventions

### Python Standards
- **Version**: Python 3.11+ required
- **Line Length**: 100 characters
- **Type Hints**: Required for all function signatures
- **Docstrings**: Google style

### Ruff Configuration
```toml
target-version = "py311"
line-length = 100
lint.select = ["B", "C4", "E", "F", "I", "Q", "UP", "W"]
```

Enabled rules:
- `B` - bugbear errors
- `C4` - flake8-comprehensions
- `E` - pycodestyle errors
- `F` - pyflakes errors
- `I` - import sorting (isort)
- `Q` - flake8-quotes
- `UP` - pyupgrade
- `W` - pycodestyle warnings

### Import Order
```python
# 1. Standard library
import json
from typing import Any, Dict, Optional

# 2. Third-party
import litellm
from pydantic import BaseModel

# 3. Framework (first-party)
from framework.runner import AgentRunner

# 4. Local
from .tools import custom_tool
```

### Naming Conventions
- **Modules**: `snake_case` (e.g., `ticket_handler.py`)
- **Classes**: `PascalCase` (e.g., `TicketHandler`)
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Test files**: `test_*.py` prefix
- **Agent packages**: `snake_case` (e.g., `support_agent/`)

### Editor Settings (.editorconfig)
- Charset: UTF-8
- EOL: LF (Unix)
- Indentation: 4 spaces (Python), 2 spaces (YAML, JSON)
- Final newline: Yes
- Trim trailing whitespace: Yes (except Markdown)

## Testing

### Framework Tests
```bash
cd core && pytest tests/ -v              # Run all tests
cd core && pytest tests/ -v -x           # Stop on first failure
cd core && pytest tests/ -v -n auto      # Parallel execution
```

### Agent Tests
Agents use a goal-based testing framework:
- **Constraint Tests**: Verify agents respect constraints
- **Success Tests**: Verify agents meet success criteria
- Tests live in `exports/{agent}/tests/test_*.py`

```bash
PYTHONPATH=core:exports python -m agent_name test
```

### CI Pipeline
1. **Lint**: `ruff check` and `ruff format --check` on core/ and tools/
2. **Test**: `pytest tests/ -v` in core/
3. **Validate**: Check agent.json files in exports/

## Git Workflow

### Commit Convention (Conventional Commits)
```
type(scope): description

[optional body]
[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:
```
feat(runtime): add decision recording
fix(executor): handle null responses
docs(readme): update installation
```

### Issue Assignment Policy
- **Required**: Claim issue before submitting PR
- **Process**: Comment on issue → Wait for assignment (24h) → Submit PR
- **5-Day Rule**: Issues unassigned if no activity for 5 days
- **Exceptions**: Documentation, micro-fixes, small refactors

### PR Process
1. Get assigned to issue first
2. Create feature branch: `git checkout -b feature/your-feature`
3. Make changes and add tests
4. Run `make check` and `make test`
5. Submit PR with conventional commit title
6. Request review from maintainers

## Key Architecture Concepts

### Agent Structure
Agents are Python packages with:
- `agent.json` - Graph definition (nodes, edges, goal, success criteria)
- `tools.py` - Custom tool functions
- `mcp_servers.json` - MCP server integrations
- `__main__.py` - CLI entry point

### Runtime Components
- **AgentRunner**: Loads agents from agent.json, sets up context
- **GraphExecutor**: Executes node graphs (DAG with branching)
- **Runtime**: Interface for recording decisions and outcomes
- **NodeContext**: Provides memory, LLM, tools to each node

### Decision Recording
Agents capture decisions (not just actions) for analysis:
```python
runtime.decide(intent, options, choice)
runtime.record_outcome(success, result, metrics)
```

## Dependencies

### Core Framework
- pydantic>=2.0
- anthropic>=0.40.0
- httpx>=0.27.0
- litellm>=1.81.0
- mcp>=1.0.0
- fastmcp>=2.0.0
- pytest>=8.0
- pytest-asyncio>=0.23
- pytest-xdist>=3.0

### Development
- ruff>=0.1.0
- mypy>=1.0

## Environment Variables

```bash
ANTHROPIC_API_KEY     # For Claude models
OPENAI_API_KEY        # For OpenAI models
BRAVE_SEARCH_API_KEY  # For web search tool
PYTHONPATH=core:exports  # Required when running agents
```

## Claude Code Skills

Available slash commands for building agents:
- `/building-agents` - Build goal-driven agents
- `/building-agents-construction` - Step-by-step agent construction
- `/testing-agent` - Write and run agent tests
- `/agent-workflow` - Complete workflow orchestration

## Common Tasks

### Creating a New Agent
1. Use `/building-agents-construction` in Claude Code
2. Define goal and success criteria
3. Add nodes (LLM, Router, Function)
4. Connect edges (on_success, on_failure, conditional)
5. Test with `/testing-agent`
6. Export to `exports/agent_name/`

### Adding a New Tool
1. Create directory in `tools/src/aden_tools/tools/`
2. Implement tool function with type hints
3. Register in `mcp_server.py`
4. Add README.md documentation
5. Test the tool

### Debugging Agent Failures
1. Check run storage for decision history
2. Use BuilderQuery to analyze patterns
3. Examine node outputs and edge conditions
4. Run specific test cases

## Important Notes

- Always set `PYTHONPATH=core:exports` when running agents
- Pre-commit hooks run Ruff lint and format automatically
- Agent packages in `exports/` are gitignored (user-created)
- Use Pydantic models for all data structures
- Decisions are recorded for Builder LLM analysis
