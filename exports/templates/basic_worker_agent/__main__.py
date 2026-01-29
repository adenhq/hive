"""
CLI entry point for Basic Worker Agent (Template).
"""
import asyncio
import json
import sys
import click

from .agent import default_agent

@click.group()
def cli():
    """Basic Worker Agent (Template)."""
    pass

@cli.command()
def info():
    """Show agent information."""
    info_data = default_agent.info()
    click.echo(json.dumps(info_data, indent=2))

@cli.command()
def validate():
    """Validate agent structure."""
    result = default_agent.validate()
    if result["valid"]:
        click.echo("Agent is valid")
        sys.exit(0)
    else:
        click.echo("Agent is invalid")
        for err in result["errors"]:
            click.echo(f"ERROR: {err}")
        sys.exit(1)

@cli.command()
@click.option("--mock", is_flag=True, help="Run in mock mode")
def run(mock):
    """Run the agent."""
    result = asyncio.run(default_agent.run({}, mock_mode=mock))

    if result is None:
        click.echo("{}")
        sys.exit(1)

    output = {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "steps_executed": result.steps_executed,
        "paused_at": result.paused_at,
    }

    click.echo(json.dumps(output, indent=2, default=str))
    sys.exit(0 if result.success else 1)

if __name__ == "__main__":
    cli()
