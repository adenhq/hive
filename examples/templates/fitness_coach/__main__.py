"""
CLI entry point for Fitness Coach Agent.

Uses AgentRuntime for multi-entrypoint support with timer-driven check-ins.
"""

import asyncio
import json
import logging
import sys
import click

from .agent import default_agent, FitnessCoachAgent


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
    """Fitness Coach Agent - Track calories, generate workouts, stay on schedule."""
    pass


@cli.command()
@click.option("--mock", is_flag=True, help="Run in mock mode")
@click.option("--verbose", "-v", is_flag=True, help="Show execution details")
@click.option("--debug", is_flag=True, help="Show debug logging")
def tui(mock, verbose, debug):
    """Launch the TUI dashboard for interactive fitness coaching."""
    setup_logging(verbose=verbose, debug=debug)

    try:
        from framework.tui.app import AdenTUI
    except ImportError:
        click.echo(
            "TUI requires the 'textual' package. Install with: pip install textual"
        )
        sys.exit(1)

    from pathlib import Path

    from framework.llm import LiteLLMProvider
    from framework.runner.tool_registry import ToolRegistry
    from framework.runtime.agent_runtime import create_agent_runtime
    from framework.runtime.execution_stream import EntryPointSpec

    async def run_with_tui():
        agent = FitnessCoachAgent()

        agent._tool_registry = ToolRegistry()

        storage_path = Path.home() / ".hive" / "agents" / "fitness_coach"
        storage_path.mkdir(parents=True, exist_ok=True)

        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            agent._tool_registry.load_mcp_config(mcp_config_path)

        llm = None
        if not mock:
            llm = LiteLLMProvider(
                model=agent.config.model,
                api_key=agent.config.api_key,
                api_base=agent.config.api_base,
            )

        tools = list(agent._tool_registry.get_tools().values())
        tool_executor = agent._tool_registry.get_executor()
        graph = agent._build_graph()

        runtime = create_agent_runtime(
            graph=graph,
            goal=agent.goal,
            storage_path=storage_path,
            entry_points=[
                EntryPointSpec(
                    id="start",
                    name="Start Fitness Coach",
                    entry_node="intake",
                    trigger_type="manual",
                    isolation_level="shared",
                ),
                EntryPointSpec(
                    id="meal-timer",
                    name="Meal Check-in",
                    entry_node="meal-checkin",
                    trigger_type="timer",
                    trigger_config={"schedule": ["08:00", "12:00", "19:00"]},
                    isolation_level="shared",
                    max_concurrent=1,
                ),
                EntryPointSpec(
                    id="exercise-timer",
                    name="Exercise Reminder",
                    entry_node="exercise-reminder",
                    trigger_type="timer",
                    trigger_config={"interval_minutes": 240},
                    isolation_level="shared",
                    max_concurrent=1,
                ),
            ],
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
        )

        await runtime.start()

        try:
            app = AdenTUI(runtime)
            await app.run_async()
        finally:
            await runtime.stop()

    asyncio.run(run_with_tui())


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
        click.echo("\nAsync entry points:")
        for ep in info_data["async_entry_points"]:
            click.echo(f"  - {ep['name']} → {ep['entry_node']}")


@cli.command()
def validate():
    """Validate agent structure."""
    validation = default_agent.validate()
    if validation["valid"]:
        click.echo("Agent is valid")
        if validation["warnings"]:
            for warning in validation["warnings"]:
                click.echo(f"  WARNING: {warning}")
    else:
        click.echo("Agent has errors:")
        for error in validation["errors"]:
            click.echo(f"  ERROR: {error}")
    sys.exit(0 if validation["valid"] else 1)


if __name__ == "__main__":
    cli()
