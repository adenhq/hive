"""Create agent from template command"""
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

FUNCTION_TEMPLATE = '''"""
{name} - Function-based agent
"""

def {func_name}(input_text: str) -> str:
    """
    TODO: Implement your agent logic here
    
    Args:
        input_text: Input data to process
        
    Returns:
        Processed result
    """
    # Example: simple classification
    if "urgent" in input_text.lower():
        return "HIGH_PRIORITY"
    return "NORMAL"


if __name__ == "__main__":
    # Test the agent
    result = {func_name}("This is urgent!")
    print(f"Result: {{result}}")
'''

TEST_TEMPLATE = '''"""
Tests for {name}
"""
import pytest
from agent import {func_name}


def test_{func_name}_urgent():
    """Test urgent classification"""
    result = {func_name}("This is urgent!")
    assert result == "HIGH_PRIORITY"


def test_{func_name}_normal():
    """Test normal classification"""
    result = {func_name}("Regular message")
    assert result == "NORMAL"
'''


def create_agent(name: str, agent_type: str):
    """Create a new agent from template"""
    # Find workspace root
    current = Path.cwd()
    workspace_root = None
    
    while current != current.parent:
        if (current / "hive.yaml").exists():
            workspace_root = current
            break
        current = current.parent
    
    if not workspace_root:
        console.print("[red]Error: Not in a Hive workspace. Run 'hive init' first.[/red]")
        return
    
    # Create agent directory
    agents_dir = workspace_root / "agents"
    agent_dir = agents_dir / name.replace("-", "_")
    
    if agent_dir.exists():
        console.print(f"[red]Error: Agent '{name}' already exists[/red]")
        return
    
    agent_dir.mkdir(parents=True)
    
    # Create agent files based on template
    func_name = name.replace("-", "_")
    
    if agent_type == "function":
        # Create agent.py
        with open(agent_dir / "agent.py", "w") as f:
            f.write(FUNCTION_TEMPLATE.format(name=name, func_name=func_name))
        
        # Create test_agent.py
        with open(agent_dir / "test_agent.py", "w") as f:
            f.write(TEST_TEMPLATE.format(name=name, func_name=func_name))
        
        # Create README
        with open(agent_dir / "README.md", "w") as f:
            f.write(f"# {name}\n\nFunction-based AI agent\n")
    
    console.print(Panel.fit(
        f"[green]✓[/green] Created agent: [bold]{name}[/bold]\n\n"
        f"Location: agents/{name.replace('-', '_')}/\n"
        f"Type: {agent_type}\n\n"
        f"Next steps:\n"
        f"  cd agents/{name.replace('-', '_')}\n"
        f"  # Edit agent.py\n"
        f"  hive test {name}",
        title="[bold green]Success![/bold green]",
        border_style="green"
    ))
