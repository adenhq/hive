#!/usr/bin/env python3
"""
Hive CLI - Main entry point
"""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Hive - AI Agent Development Framework CLI"""
    pass


@cli.command()
@click.argument("name")
@click.option("--path", default=".", help="Parent directory for workspace")
def init(name, path):
    """Initialize a new Hive workspace"""
    from hive_cli.commands.init import init_workspace

    init_workspace(name, path)


@cli.command()
@click.argument("name")
@click.option(
    "--type",
    "agent_type",
    type=click.Choice(["function", "llm", "multi-node"]),
    default="function",
    help="Type of agent to create",
)
def create(name, agent_type):
    """Create a new agent from template"""
    from hive_cli.commands.create import create_agent

    create_agent(name, agent_type)


@cli.command()
@click.argument("name", required=False)
@click.option("--mock", is_flag=True, help="Run in mock mode (no API calls)")
@click.option("--all", "test_all", is_flag=True, help="Test all agents")
def test(name, mock, test_all):
    """Run agent tests"""
    from hive_cli.commands.test import test_agent

    test_agent(name, mock, test_all)


@cli.command()
@click.argument("name")
@click.option("--input", "input_data", help="JSON input data")
@click.option("--interactive", is_flag=True, help="Run in interactive mode")
def run(name, input_data, interactive):
    """Execute an agent"""
    from hive_cli.commands.run import run_agent

    run_agent(name, input_data, interactive)


@cli.command()
@click.option("--status", is_flag=True, help="Show agent status")
def list(status):
    """List all agents in workspace"""
    from hive_cli.commands.list import list_agents

    list_agents(status)


if __name__ == "__main__":
    cli()
