"""Test agent command"""
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()


def test_agent(name: str = None, mock: bool = False, test_all: bool = False):
    """Run agent tests"""
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
    
    if test_all:
        # Test all agents
        agents = [d for d in agents_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        if not agents:
            console.print("[yellow]No agents found[/yellow]")
            return
        
        for agent_dir in agents:
            console.print(f"\n[bold]Testing {agent_dir.name}...[/bold]")
            _run_tests(agent_dir)
    elif name:
        # Test specific agent
        agent_dir = agents_dir / name.replace("-", "_")
        if not agent_dir.exists():
            console.print(f"[red]Error: Agent '{name}' not found[/red]")
            return
        _run_tests(agent_dir)
    else:
        console.print("[red]Error: Specify agent name or use --all[/red]")


def _run_tests(agent_dir: Path):
    """Run tests for an agent directory"""
    test_file = agent_dir / "test_agent.py"
    
    if not test_file.exists():
        console.print(f"[yellow]No tests found in {agent_dir.name}[/yellow]")
        return
    
    try:
        result = subprocess.run(
            ["pytest", str(test_file), "-v"],
            cwd=agent_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print(f"[green]✓ Tests passed![/green]")
        else:
            console.print(f"[red]✗ Tests failed[/red]")
            console.print(result.stdout)
    except FileNotFoundError:
        console.print("[yellow]pytest not installed. Install with: pip install pytest[/yellow]")
