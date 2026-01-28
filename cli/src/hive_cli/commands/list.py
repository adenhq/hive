"""List agents command"""
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()


def list_agents(show_status: bool = False):
    """List all agents in workspace"""
    # Find workspace root
    current = Path.cwd()
    workspace_root = None
    
    while current != current.parent:
        if (current / "hive.yaml").exists():
            workspace_root = current
            break
        current = current.parent
    
    if not workspace_root:
        console.print("[red]Error: Not in a Hive workspace[/red]")
        return
    
    agents_dir = workspace_root / "agents"
    
    if not agents_dir.exists():
        console.print("[yellow]No agents directory found[/yellow]")
        return
    
    # Get all agents
    agents = [d for d in agents_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    
    if not agents:
        console.print("[yellow]No agents found[/yellow]")
        console.print("\nCreate one with: [bold]hive create my-agent[/bold]")
        return
    
    # Create table
    table = Table(title="Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    
    if show_status:
        table.add_column("Tests", style="yellow")
    
    for agent_dir in sorted(agents):
        agent_name = agent_dir.name
        agent_type = "function"  # Default, could detect based on files
        
        row = [agent_name, agent_type]
        
        if show_status:
            # Check if tests exist
            test_file = agent_dir / "test_agent.py"
            tests_status = "✓" if test_file.exists() else "✗"
            row.append(tests_status)
        
        table.add_row(*row)
    
    console.print(table)
    console.print(f"\nTotal: {len(agents)} agent(s)")
