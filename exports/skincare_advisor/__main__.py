"""
CLI entry point for Skincare Product Advisor.

Uses AgentRuntime for multi-entrypoint support with HITL pause/resume.
"""

import asyncio
import json
import logging
import sys
import click

from .agent import default_agent, SkincareAdvisorAgent


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
    """Skincare Product Advisor - Evaluate beauty products for your skin."""
    pass


@cli.command()
@click.option("--user-id", "-u", type=str, required=True, help="User identifier for profile storage")
@click.option("--product", "-p", type=str, required=True, help="Product name to evaluate (e.g. 'CeraVe Moisturizing Cream')")
@click.option("--routine", "-r", type=str, default="", help="JSON string describing current skincare routine")
@click.option("--skin-type", "-s", type=str, default="", help="Skin type (oily, dry, combination, sensitive, normal)")
@click.option("--update", type=str, default="", help="Routine update / reaction feedback for a previously added product")
@click.option("--mock", is_flag=True, help="Run in mock mode")
@click.option("--quiet", "-q", is_flag=True, help="Only output result JSON")
@click.option("--verbose", "-v", is_flag=True, help="Show execution details")
@click.option("--debug", is_flag=True, help="Show debug logging")
def run(user_id, product, routine, skin_type, update, mock, quiet, verbose, debug):
    """Evaluate a skincare/beauty product."""
    if not quiet:
        setup_logging(verbose=verbose, debug=debug)

    # Build product query with all provided context
    product_query_parts = [f"Evaluate: {product}"]
    if skin_type:
        product_query_parts.append(f"Skin type: {skin_type}")
    if routine:
        product_query_parts.append(f"Current routine: {routine}")

    context = {
        "user_id": user_id,
        "product_query": ". ".join(product_query_parts),
        "routine_update": update,
    }

    result = asyncio.run(default_agent.run(context, mock_mode=mock))

    output_data = {
        "success": result.success,
        "steps_executed": result.steps_executed,
        "output": result.output,
    }
    if result.error:
        output_data["error"] = result.error

    click.echo(json.dumps(output_data, indent=2, default=str))
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
        click.echo(f"\nGoal: {info_data['goal']['name']}")
        click.echo(f"  {info_data['goal']['description']}")
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
    """Interactive skincare advisor session."""
    asyncio.run(_interactive_shell(verbose))


async def _interactive_shell(verbose=False):
    """Async interactive shell."""
    setup_logging(verbose=verbose)

    click.echo("=== Skincare Product Advisor ===")
    click.echo("Evaluate any skincare or beauty product for your skin.\n")
    click.echo("First, tell me about yourself:")

    user_id = await asyncio.get_event_loop().run_in_executor(
        None, input, "Your name/ID> "
    )
    skin_type = await asyncio.get_event_loop().run_in_executor(
        None, input, "Skin type (oily/dry/combination/sensitive/normal)> "
    )
    routine_input = await asyncio.get_event_loop().run_in_executor(
        None, input, "Current routine (comma-separated products, or 'none')> "
    )

    click.echo(f"\nProfile set: {user_id} ({skin_type} skin)")
    click.echo("Enter a product to evaluate (or 'quit' to exit):\n")

    agent = SkincareAdvisorAgent()
    await agent.start()

    try:
        while True:
            try:
                product = await asyncio.get_event_loop().run_in_executor(
                    None, input, "Product> "
                )
                if product.lower() in ["quit", "exit", "q"]:
                    click.echo("Goodbye!")
                    break

                if not product.strip():
                    continue

                product_query = f"Evaluate: {product}. Skin type: {skin_type}."
                if routine_input and routine_input.lower() != "none":
                    product_query += f" Current routine: {routine_input}"

                click.echo("\nAnalyzing product...\n")

                result = await agent.trigger_and_wait(
                    "start",
                    {
                        "user_id": user_id,
                        "product_query": product_query,
                        "routine_update": "",
                    },
                )

                if result is None:
                    click.echo("\n[Execution timed out]\n")
                    continue

                if result.success:
                    output = result.output
                    if "detailed_report" in output:
                        click.echo("\n--- Product Rating Report ---\n")
                        click.echo(output["detailed_report"])
                        click.echo()
                    if "overall_rating" in output:
                        click.echo(f"Overall Rating: {output['overall_rating']}/10")
                    if "recommendation" in output:
                        click.echo(f"Recommendation: {output['recommendation']}")
                    click.echo()

                    # Ask if they want to add to routine
                    add = await asyncio.get_event_loop().run_in_executor(
                        None, input, "Add this product to your routine? (y/n)> "
                    )
                    if add.lower() in ["y", "yes"]:
                        reaction = await asyncio.get_event_loop().run_in_executor(
                            None,
                            input,
                            "How has your skin reacted? (or 'skip' to log later)> ",
                        )
                        if reaction.lower() != "skip":
                            await agent.trigger_and_wait(
                                "start",
                                {
                                    "user_id": user_id,
                                    "product_query": product_query,
                                    "routine_update": f"Added {product} to routine. Reaction: {reaction}",
                                },
                            )
                            click.echo("Routine updated!\n")
                else:
                    click.echo(f"\nAnalysis failed: {result.error}\n")

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
