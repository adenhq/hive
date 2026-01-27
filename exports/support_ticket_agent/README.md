# Support Ticket Agent

A minimal example agent that demonstrates the Goal-Agent framework's capabilities.

## Structure
- `agent.json`: Declarative graph and goal definition.
- `tools.py`: Custom Python logic auto-discovered by the agent.
- `__main__.py`: Makes the agent runnable as a Python module.

## Usage

### 1. Validate the Agent
Check if the agent structure and tools are valid:
```bash
PYTHONPATH=core:exports python -m support_ticket_agent validate
```

### 2. Run with Mock LLM
Test the execution flow without making real API calls:
```bash
PYTHONPATH=core:exports python -m support_ticket_agent run --mock --input '{
  "ticket_content": "My login is broken. Error 401.",
  "customer_id": "CUST-123"
}'
```

### 3. Start Interactive Shell
Chat with the agent (requires `ANTHROPIC_API_KEY` or `--model` flag):
```bash
PYTHONPATH=core:exports python -m support_ticket_agent shell
```

## Features
- **Categorization**: Automatically classifies tickets (Technical, Billing, etc.).
- **Prioritization**: Assigns urgency based on content.
- **Routing**: Recommends the best department for resolution.
