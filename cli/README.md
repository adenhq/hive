# Hive CLI

Command-line interface for the Hive AI agent framework - making agent development simple and intuitive.

## Installation

```bash
cd cli
pip install -e .
```

## Quick Start

```bash
# Initialize a workspace
hive init my-agents
cd my-agents

# Create an agent
hive create ticket-classifier

# Test it
hive test ticket-classifier

# Run it
hive run ticket-classifier --input '{"text": "Urgent bug in production"}'

# List all agents
hive list
```

## Commands

### `hive init <name>`

Initialize a new Hive workspace with proper structure.

```bash
hive init my-project
cd my-project
```

Creates:
```
my-project/
├── .hive/           # Configuration and cache
├── agents/          # Your AI agents
├── hive.yaml        # Workspace config
└── README.md
```

### `hive create <name>`

Create a new agent from template.

```bash
hive create email-classifier
hive create ticket-router --type multi-node
```

Options:
- `--type` - Agent type: `function` (default), `llm`, `multi-node`

Creates:
```
agents/email_classifier/
├── agent.py         # Agent implementation
├── test_agent.py    # Tests
└── README.md
```

### `hive test <name>`

Run agent tests.

```bash
hive test email-classifier
hive test email-classifier --mock  # No API calls
hive test --all                     # Test all agents
```

### `hive run <name>`

Execute an agent.

```bash
# With JSON input
hive run classifier --input '{"subject": "...", "body": "..."}'

# Interactive mode
hive run classifier --interactive
```

### `hive list`

List all agents in workspace.

```bash
hive list
hive list --status  # Show test status
```

## Why CLI?

Before:
```bash
mkdir my-agent && cd my-agent
# Manually create agent.py...
PYTHONPATH=../../core:../../exports python -m my_agent test
```

After:
```bash
hive create my-agent
hive test my-agent
```

## Features

- ✅ **No PYTHONPATH juggling** - Workspace auto-configured
- ✅ **Agent templates** - Start with working examples
- ✅ **Simple testing** - `hive test` just works
- ✅ **Beautiful output** - Rich terminal UI
- ✅ **Discoverable** - `hive --help` shows all commands

## Development

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT
