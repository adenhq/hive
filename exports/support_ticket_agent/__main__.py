"""Main entry point for support_ticket_agent module."""

import sys
import os
from pathlib import Path

# Add core to path so we can import framework
core_path = Path(__file__).parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

# Get the agent directory path
agent_path = str(Path(__file__).parent)

# Import and run framework CLI with this agent path
from framework.cli import main

if __name__ == "__main__":
    # When called as: python -m exports.support_ticket_agent validate
    # sys.argv is: ['exports.support_ticket_agent', 'validate']
    # We need to make it: ['framework', 'validate', 'exports/support_ticket_agent']
    
    # Replace the module name with 'framework'
    sys.argv[0] = 'framework'
    # Insert the agent path as the last argument
    sys.argv.append(agent_path)
    main()