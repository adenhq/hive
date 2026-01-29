"""Initialize Hive workspace command"""

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
import yaml

console = Console()


def init_workspace(name: str, parent_path: str = "."):
    """Initialize a new Hive workspace"""
    workspace_path = Path(parent_path) / name

    if workspace_path.exists():
        console.print(f"[red]Error: Directory '{name}' already exists[/red]")
        return

    # Create workspace structure
    workspace_path.mkdir(parents=True)
    (workspace_path / ".hive").mkdir()
    (workspace_path / "agents").mkdir()

    # Create hive.yaml config
    config = {
        "workspace": name,
        "version": "0.1.0",
        "agents_dir": "agents",
    }

    with open(workspace_path / "hive.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # Create README
    readme = f"""# {name}

Hive AI Agent Workspace

## Getting Started

```bash
# Create a new agent
hive create my-agent

# Test an agent
hive test my-agent

# Run an agent
hive run my-agent --input '{{"data": "..."}}'

# List all agents
hive list
```

## Directory Structure

- `agents/` - Your AI agents
- `.hive/` - Hive configuration and cache
- `hive.yaml` - Workspace configuration
"""

    with open(workspace_path / "README.md", "w") as f:
        f.write(readme)

    console.print(
        Panel.fit(
            f"[green]✓[/green] Initialized Hive workspace: [bold]{name}[/bold]\n\n"
            f"Next steps:\n"
            f"  cd {name}\n"
            f"  hive create my-agent",
            title="[bold green]Success![/bold green]",
            border_style="green",
        )
    )
