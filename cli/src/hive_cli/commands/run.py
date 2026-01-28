"""Run agent command"""
import json
import sys
from pathlib import Path
from rich.console import Console

console = Console()


def run_agent(name: str, input_data: str = None, interactive: bool = False):
    """Execute an agent"""
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
    
    # Find agent
    agents_dir = workspace_root / "agents"
    agent_dir = agents_dir / name.replace("-", "_")
    
    if not agent_dir.exists():
        console.print(f"[red]Error: Agent '{name}' not found[/red]")
        return
    
    # Import and run agent
    agent_file = agent_dir / "agent.py"
    if not agent_file.exists():
        console.print(f"[red]Error: agent.py not found in {name}[/red]")
        return
    
    # Add agent directory to path
    sys.path.insert(0, str(agent_dir))
    
    try:
        # Import the agent module
        import importlib.util
        spec = importlib.util.spec_from_file_location("agent", agent_file)
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)
        
        # Find the main function (assume it's the first function defined)
        func_name = name.replace("-", "_")
        if hasattr(agent_module, func_name):
            agent_func = getattr(agent_module, func_name)
            
            if interactive:
                console.print("[bold]Interactive mode[/bold] (Ctrl+C to exit)")
                while True:
                    try:
                        user_input = console.input("\n[cyan]Input:[/cyan] ")
                        result = agent_func(user_input)
                        console.print(f"[green]Output:[/green] {result}")
                    except KeyboardInterrupt:
                        console.print("\n[yellow]Exited[/yellow]")
                        break
            elif input_data:
                # Parse JSON input
                try:
                    data = json.loads(input_data)
                    result = agent_func(**data)
                except json.JSONDecodeError:
                    # Treat as plain string
                    result = agent_func(input_data)
                
                console.print(f"[green]Result:[/green] {result}")
            else:
                console.print("[red]Error: Provide --input or use --interactive[/red]")
        else:
            console.print(f"[red]Error: Function '{func_name}' not found in agent[/red]")
    
    except Exception as e:
        console.print(f"[red]Error running agent: {e}[/red]")
    finally:
        sys.path.pop(0)
