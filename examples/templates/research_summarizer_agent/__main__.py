"""
CLI entry point for Research & Summarization Agent.
"""

import asyncio
import json
import logging
import sys
import click

from .agent import default_agent, ResearchSummarizerAgent


def setup_logging(verbose=False, debug=False):
    if debug:
        level, fmt = logging.DEBUG, "%(asctime)s %(name)s: %(message)s"
    elif verbose:
        level, fmt = logging.INFO, "%(message)s"
    else:
        level, fmt = logging.WARNING, "%(levelname)s: %(message)s"

    logging.basicConfig(level=level, format=fmt, stream=sys.stderr)
    logging.getLogger("framework").setLevel(level)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Research & Summarization Agent."""
    pass


# RUN
@cli.command()
@click.option("--quiet", "-q", is_flag=True, help="Only output result JSON")
@click.option("--verbose", "-v", is_flag=True, help="Show execution details")
@click.option("--debug", is_flag=True, help="Show debug logging")
def run(quiet, verbose, debug):
    """Execute the research summarizer agent."""
    if not quiet:
        setup_logging(verbose=verbose, debug=debug)

    context = {}

    result = asyncio.run(default_agent.run(context))

    output_data = {
        "success": result.success,
        "steps_executed": result.steps_executed,
        "output": result.output,
    }
    if result.error:
        output_data["error"] = result.error

    click.echo(json.dumps(output_data, indent=2, default=str))
    sys.exit(0 if result.success else 1)


# INFO
@cli.command()
@click.option("--json", "output_json", is_flag=True)
def info(output_json):
    """Show agent information."""
    info_data = default_agent.info()
    if output_json:
        click.echo(json.dumps(info_data, indent=2))
    else:
        click.echo(f"Agent: {info_data['name']}")
        click.echo(f"Version: {info_data['version']}")
        click.echo(f"Description: {info_data['description']}")
        click.echo(f"\nNodes: {', '.join(info_data['nodes'])}")
        click.echo(f"Client-facing: {', '.join(info_data['client_facing_nodes'])}")
        click.echo(f"Entry: {info_data['entry_node']}")
        click.echo(f"Terminal: {', '.join(info_data['terminal_nodes'])}")


# VALIDATE
@cli.command()
def validate():
    """Validate agent structure."""
    validation = default_agent.validate()
    if validation["valid"]:
        click.echo("Agent is valid")
        if validation["warnings"]:
            for warning in validation["warnings"]:
                click.echo(f"WARNING: {warning}")
    else:
        click.echo("Agent has errors:")
        for error in validation["errors"]:
            click.echo(f"ERROR: {error}")
    sys.exit(0 if validation["valid"] else 1)


# SIMPLE SHELL
@cli.command()
@click.option("--verbose", "-v", is_flag=True)
def shell(verbose):
    """Interactive research session."""
    asyncio.run(_interactive_shell(verbose))


async def _interactive_shell(verbose=False):
    setup_logging(verbose=verbose)

    click.echo("=== Research & Summarization Agent ===")
    click.echo("Enter a topic to research (or 'quit'):\n")

    agent = ResearchSummarizerAgent()
    await agent.start()

    try:
        while True:
            user_input = input("Topic> ")

            if user_input.lower() in ["quit", "exit", "q"]:
                click.echo("Goodbye!")
                break

            context = {"topic": user_input}

            result = await agent.run(context)

            if result.success:
                click.echo("\n--- SUMMARY ---\n")
                click.echo(str(result.output))
                click.echo("\n--------------\n")
            else:
                click.echo(f"\nError: {result.error}\n")

    finally:
        await agent.stop()


if __name__ == "__main__":
    cli()
