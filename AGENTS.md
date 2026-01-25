# Hive Agent Builder

This project uses MCP tools for building goal-driven AI agents.

## Setup

```bash
# Run setup to install skills and configure MCP
./scripts/setup-codex.sh
```

## Skills Available

After setup, these skills are installed to `~/.codex/skills/`:

| Skill | Purpose |
|-------|---------|
| `building-agents-core` | Core concepts - goals, nodes, edges |
| `building-agents-construction` | Step-by-step build guide |
| `building-agents-patterns` | Best practices & patterns |
| `testing-agent` | Testing and validation |
| `agent-workflow` | Complete workflow reference |

Mention the skill name in your prompt to use it.

## MCP Tools

Two MCP servers are available:

### agent-builder (build agents)
- `mcp.agent-builder.create_session` — Start a build session
- `mcp.agent-builder.add_mcp_server` — Register tool servers
- `mcp.agent-builder.list_mcp_tools` — Discover available tools
- `mcp.agent-builder.set_goal` — Define agent goal
- `mcp.agent-builder.add_node` — Add processing nodes
- `mcp.agent-builder.add_edge` — Connect nodes
- `mcp.agent-builder.validate_graph` — Validate before export
- `mcp.agent-builder.export_graph` — Export to Python package

### hive-tools (runtime tools)
- `web_search` — Search the web
- `web_scrape` — Scrape webpages
- `pdf_read` — Read PDFs
- `view_file`, `write_to_file`, `list_dir` — File operations
- `grep_search`, `execute_command_tool` — Dev tools

## Quick Start

```python
# 1. Create session
mcp.agent-builder.create_session(name="my-agent")

# 2. Register tools (MANDATORY before adding tool nodes)
mcp.agent-builder.add_mcp_server(
    name="hive-tools",
    transport="stdio",
    command="python",
    args='["mcp_server.py", "--stdio"]',
    cwd="tools"
)

# 3. Verify tools exist
mcp.agent-builder.list_mcp_tools()

# 4. Set goal
mcp.agent-builder.set_goal(
    goal_id="my-goal",
    name="My Agent Goal",
    description="What the agent should accomplish",
    success_criteria='[{"id": "sc1", "description": "...", "metric": "...", "target": "..."}]'
)

# 5. Add nodes
mcp.agent-builder.add_node(
    node_id="first-node",
    name="First Node",
    node_type="llm_tool_use",  # or llm_generate, router, function
    input_keys='["input"]',
    output_keys='["output"]',
    system_prompt="...",
    tools='["web_search"]'
)

# 6. Add edges
mcp.agent-builder.add_edge(
    edge_id="e1",
    source="first-node",
    target="second-node",
    condition="on_success"
)

# 7. Validate and export
mcp.agent-builder.validate_graph()
mcp.agent-builder.export_graph(output_dir="exports/my_agent")
```

## Critical Rules

1. **Register hive-tools FIRST** — Before adding nodes that use tools
2. **Only use existing tools** — Call `list_mcp_tools()` to verify
3. **entry_points format** — Always `{"start": "first-node-id"}`
4. **Validate before export** — Catches errors early

## Documentation

- Skills: `.claude/skills/` (source of truth for both Claude Code and Codex)
- MCP Guide: `core/MCP_SERVER_GUIDE.md`
- Example Agent: `.claude/skills/building-agents-construction/examples/online_research_agent/`
