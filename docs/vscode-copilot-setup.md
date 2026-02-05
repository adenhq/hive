# VS Code + GitHub Copilot Setup Guide

This guide helps you set up VS Code with GitHub Copilot to use Hive's MCP servers and custom agents for building and testing AI agents.

## Prerequisites

- **VS Code** version 1.102 or later (for MCP support)
- **GitHub Copilot** extension installed and activated
- **Python 3.11+** installed
- **uv** package manager ([installation guide](https://docs.astral.sh/uv/))

## Quick Start

The Hive repository comes pre-configured with VS Code support! If you cloned the repository, MCP servers and custom agents are already set up.

### 1. Verify Installation

Open VS Code in the Hive repository:

```bash
cd hive
code .
```

### 2. Check MCP Configuration

The `.vscode/mcp.json` file should contain two MCP servers:

- **agent-builder** - Tools for creating and testing agents
- **tools** - 19 tools for agent capabilities (web search, file operations, etc.)

You can view the configuration:

```bash
cat .vscode/mcp.json
```

### 3. Verify Custom Agents

Custom agents are available in `.github/agents/`:

```bash
ls .github/agents/
```

You should see 6 `.agent.md` files:
- `agent-workflow.agent.md` - Complete agent development workflow
- `building-agents-core.agent.md` - Core concepts and fundamentals
- `building-agents-construction.agent.md` - Step-by-step agent building
- `building-agents-patterns.agent.md` - Best practices and patterns
- `testing-agent.agent.md` - Testing and validation
- `setup-credentials.agent.md` - Credential management

### 4. Enable MCP in VS Code Settings

The `.vscode/settings.json` is pre-configured with:

```jsonc
{
  // Enable Agent Skills (experimental)
  "chat.useAgentSkills": true,

  // Enable MCP servers
  "chat.mcp.access": true,

  // Auto-start MCP servers
  "chat.mcp.autostart": true
}
```

### 5. Test the Setup

Open GitHub Copilot Chat (Cmd/Ctrl + Shift + I):

1. Click the mode dropdown at the top of the chat panel
2. You'll see standard modes (Ask, Plan, Agent) plus your custom agents:
   - `agent-workflow`
   - `building-agents-construction`
   - `building-agents-core`
   - `building-agents-patterns`
   - `testing-agent`
   - `setup-credentials`

3. Select a custom agent (e.g., `agent-workflow`)
4. Ask the agent to help you:
   ```
   Build a simple file monitor agent
   ```

The custom agent will guide you through the process with access to MCP tools.

## Understanding the Setup

### MCP Configuration (`.vscode/mcp.json`)

MCP servers provide tools that GitHub Copilot can use. The Hive repository includes two servers:

#### agent-builder Server

Provides tools for building and testing agents:
- `create_session` - Start a new agent build session
- `add_node` - Add nodes to agent workflow
- `add_edge` - Connect nodes with edges
- `set_goal` - Define agent goals and success criteria
- `test_node` - Validate node configuration
- `validate_graph` - Check agent structure
- `generate_constraint_tests` - Create constraint tests
- `generate_success_tests` - Create success criteria tests
- `run_tests` - Execute agent tests
- `debug_test` - Debug test failures

#### tools Server

Provides 19 operational tools:
- **Web**: `web_search`, `web_scrape`, `fetch_webpage`
- **Files**: `read_file`, `write_file`, `list_directory`, `file_search`
- **Shell**: `run_command`
- **Git**: `git_status`, `git_diff`, `git_commit`
- **AI**: `llm_generate`, `llm_extract_json`
- And more...

### Custom Agents (`.github/agents/*.agent.md`)

Custom agents are specialized assistants that guide specific tasks. They have access to MCP tools and workspace context.

#### Available Agents

1. **agent-workflow** - Orchestrates the complete agent development process from concept to production
2. **building-agents-core** - Teaches agent architecture, node types, and core concepts
3. **building-agents-construction** - Guides step-by-step agent building with interactive approval
4. **building-agents-patterns** - Provides best practices, design patterns, and anti-patterns
5. **testing-agent** - Creates and runs comprehensive test suites for agents
6. **setup-credentials** - Manages API keys and credentials securely

#### Using Custom Agents

To use a custom agent:

1. Open Copilot Chat (Cmd/Ctrl + Shift + I)
2. Click the **mode dropdown** at the top of the chat panel
3. Select the specific custom agent you want to use (they appear alongside Ask, Plan, and Agent modes):
   - **agent-workflow** - "I want to build a sales prospecting agent"
   - **building-agents-core** - "Explain node types and agent architecture"
   - **building-agents-construction** - "Create a new agent step by step"
   - **building-agents-patterns** - "Show me best practices for error handling"
   - **testing-agent** - "Test the agent in exports/my_agent"
   - **setup-credentials** - "Configure credentials for hubspot-agent"
4. Type your request in the chat

The selected custom agent will guide you through the task with specialized knowledge and access to MCP tools.

## Troubleshooting

### MCP Servers Not Starting

**Symptoms**: Copilot doesn't have access to MCP tools

**Solutions**:

1. Check VS Code version (must be 1.102+)
2. Verify `uv` is installed: `uv --version`
3. Check VS Code Output panel → "MCP" for error messages
4. Manually restart MCP servers:
   - Open Command Palette (Cmd/Ctrl + Shift + P)
   - Run: "GitHub Copilot: Restart MCP Servers"

### Custom Agents Not Available

**Symptoms**: Custom agents don't appear in the mode dropdown

**Solutions**:

1. Verify `chat.useAgentSkills` is `true` in `.vscode/settings.json`
2. Check `.github/agents/` directory exists with 6 `.agent.md` files
3. Reload VS Code window: "Developer: Reload Window" (Cmd/Ctrl + Shift + P)
4. Check VS Code version (1.108+ required for custom agents)
5. Ensure GitHub Copilot extension is up to date

### Permission Errors

**Symptoms**: "Permission denied" when MCP tries to run Python

**Solutions**:

1. Ensure Python 3.11+ is in PATH: `python --version`
2. Verify `uv` can run Python: `uv run python --version`
3. Check file permissions on `core/` and `tools/` directories

### Tool Import Errors

**Symptoms**: MCP server fails with "ModuleNotFoundError"

**Solutions**:

1. Install dependencies:
   ```bash
   cd core && uv sync
   cd ../tools && uv sync
   ```

2. Verify PYTHONPATH in `.vscode/mcp.json`:
   ```json
   "env": {
     "PYTHONPATH": "${workspaceFolder}/tools/src:${workspaceFolder}/core"
   }
   ```

## Advanced Configuration

### Adding Custom MCP Servers

To add your own MCP servers, edit `.vscode/mcp.json`:

```json
{
  "servers": {
    "my-server": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "${workspaceFolder}/my-server",
        "python",
        "server.py"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/my-server"
      }
    }
  }
}
```

### Creating Custom Agents

Create a new `.agent.md` file in `.github/agents/`:

```markdown
---
description: Your agent description
name: My Custom Agent
tools: ['agent-builder/*', 'tools/*']
target: vscode
---

# Your Agent Content

Instructions and guidance for your custom agent...
```

### Environment Variables

MCP servers can access environment variables. Common ones:

- `ANTHROPIC_API_KEY` - For LLM calls in agents
- `HUBSPOT_ACCESS_TOKEN` - For HubSpot integration tools
- `BRAVE_SEARCH_API_KEY` - For web search tools

Set these in your shell profile (`~/.bashrc`, `~/.zshrc`) or use the `setup-credentials` agent.

## Differences from Other IDEs

| Feature | VS Code | Cursor | Claude Code |
|---------|---------|--------|-------------|
| **MCP Config** | `.vscode/mcp.json` | `.cursor/mcp.json` | Built-in |
| **Agents/Skills** | `.github/agents/*.agent.md` | Symlinks in `.cursor/skills/` | `.claude/skills/` |
| **Path Variables** | `${workspaceFolder}` | Relative paths | Relative paths |
| **Discovery** | Workspace settings | IDE-specific | Built-in |
| **Setup** | Pre-configured | Pre-configured | Pre-configured |

All IDEs in this repository have equivalent functionality - choose based on your preference!

## Next Steps

- **Build your first agent**: Open Copilot Chat, select `agent-workflow` from the mode dropdown, and describe what you want to build
- **Read the docs**: Check `docs/getting-started.md` for tutorials
- **Explore examples**: See `exports/` for example agents
- **Join the community**: [Discord](https://discord.com/invite/MXE49hrKDk)

## Resources

- [VS Code MCP Documentation](https://code.visualstudio.com/docs/copilot/customization/mcp-servers)
- [VS Code Custom Agents Documentation](https://code.visualstudio.com/docs/copilot/customization/custom-agents)
- [Hive Documentation](https://docs.adenhq.com/)
- [GitHub Copilot Extension](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot)

## Support

Having issues? 

1. Check the [troubleshooting section](#troubleshooting) above
2. Search [GitHub Issues](https://github.com/adenhq/hive/issues)
3. Ask on [Discord](https://discord.com/invite/MXE49hrKDk)
4. [Open a new issue](https://github.com/adenhq/hive/issues/new)
