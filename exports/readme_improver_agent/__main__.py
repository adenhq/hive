"""
CLI entry point for README Improver Agent.

Uses AgentRuntime for multi-entrypoint support with HITL pause/resume.
"""

import asyncio
import json
import logging
import sys
import click

from .agent import default_agent, ReadmeImproverAgent


def setup_logging(verbose=False, debug=False):
    """Configure logging for execution visibility."""
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
    """README Improver Agent - Polish draft READMEs with proper formatting."""
    pass


@cli.command()
@click.option("--file", "-f", "file_path", type=str, required=True, help="Path to the file to improve")
@click.option("--output", "-o", type=str, help="Output file path (optional, prints to stdout if not specified)")
@click.option("--mock", is_flag=True, help="Run in mock mode")
@click.option("--quiet", "-q", is_flag=True, help="Only output the polished content")
@click.option("--verbose", "-v", is_flag=True, help="Show execution details")
@click.option("--debug", is_flag=True, help="Show debug logging")
def run(file_path, output, mock, quiet, verbose, debug):
    """Improve a README or text file."""
    if not quiet:
        setup_logging(verbose=verbose, debug=debug)

    context = {"file_path": file_path}

    result = asyncio.run(default_agent.run(context, mock_mode=mock))

    if quiet:
        # Only output the polished content
        if result.success and result.output.get("polished_content"):
            click.echo(result.output["polished_content"])
        sys.exit(0 if result.success else 1)
    else:
        # Full output
        if result.success:
            polished = result.output.get("polished_content", "")
            improvements = result.output.get("improvements_made", [])

            click.echo("\n--- Improvements Made ---")
            for imp in improvements:
                click.echo(f"  - {imp}")

            click.echo("\n--- Polished Content ---\n")
            click.echo(polished)

            if output:
                with open(output, "w") as f:
                    f.write(polished)
                click.echo(f"\n[Saved to: {output}]")
        else:
            click.echo(f"Error: {result.error}", err=True)

        sys.exit(0 if result.success else 1)


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
        click.echo(f"Entry: {info_data['entry_node']}")
        click.echo(f"Terminal: {', '.join(info_data['terminal_nodes'])}")


@cli.command()
def validate():
    """Validate agent structure."""
    validation = default_agent.validate()
    if validation["valid"]:
        click.echo("Agent is valid")
    else:
        click.echo("Agent has errors:")
        for error in validation["errors"]:
            click.echo(f"  ERROR: {error}")
    sys.exit(0 if validation["valid"] else 1)


@cli.command()
@click.option("--verbose", "-v", is_flag=True)
def shell(verbose):
    """Interactive session - enter file paths to improve."""
    asyncio.run(_interactive_shell(verbose))


async def _interactive_shell(verbose=False):
    """Async interactive shell."""
    setup_logging(verbose=verbose)

    click.echo("=== README Improver Agent ===")
    click.echo("Enter a file path to improve (or 'quit' to exit):\n")

    agent = ReadmeImproverAgent()
    await agent.start()

    try:
        while True:
            try:
                file_path = await asyncio.get_event_loop().run_in_executor(
                    None, input, "File> "
                )
                if file_path.lower() in ["quit", "exit", "q"]:
                    click.echo("Goodbye!")
                    break

                if not file_path.strip():
                    continue

                click.echo("\nImproving...\n")

                result = await agent.trigger_and_wait("start", {"file_path": file_path})

                if result is None:
                    click.echo("\n[Execution timed out]\n")
                    continue

                if result.success:
                    output = result.output
                    improvements = output.get("improvements_made", [])
                    polished = output.get("polished_content", "")

                    click.echo("--- Improvements Made ---")
                    for imp in improvements:
                        click.echo(f"  - {imp}")

                    click.echo("\n--- Polished Content ---\n")
                    click.echo(polished[:1000])
                    if len(polished) > 1000:
                        click.echo(f"\n... [{len(polished) - 1000} more characters]")
                    click.echo("\n")
                else:
                    click.echo(f"\nError: {result.error}\n")

            except KeyboardInterrupt:
                click.echo("\nGoodbye!")
                break
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                import traceback
                traceback.print_exc()
    finally:
        await agent.stop()


if __name__ == "__main__":
    cli()
