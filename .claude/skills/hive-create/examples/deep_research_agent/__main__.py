"""
Improved CLI Entry Point for Deep Research Agent
"""

import asyncio
import json
import logging
import sys
import click
import os
from datetime import datetime

from .agent import default_agent, DeepResearchAgent


# --------------------------
# Global Settings
# --------------------------

DEFAULT_TIMEOUT = 300   # 5 minutes
MAX_RETRIES = 2
SAVE_DIR = "research_results"


# --------------------------
# Logging
# --------------------------

def setup_logging(level="warning"):

    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
    }

    logging.basicConfig(
        level=levels.get(level, logging.WARNING),
        format="%(asctime)s | %(levelname)s | %(message)s",
        stream=sys.stderr,
    )


# --------------------------
# Helpers
# --------------------------

def validate_topic(topic):

    if not topic:
        raise ValueError("Topic cannot be empty")

    if len(topic) < 3:
        raise ValueError("Topic is too short")

    return topic.strip()


def save_result(data):

    os.makedirs(SAVE_DIR, exist_ok=True)

    name = datetime.now().strftime("%Y%m%d_%H%M%S")

    file = f"{SAVE_DIR}/result_{name}.json"

    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return file


async def safe_run(agent, context, mock):

    for attempt in range(MAX_RETRIES + 1):

        try:
            return await asyncio.wait_for(
                agent.run(context, mock_mode=mock),
                timeout=DEFAULT_TIMEOUT
            )

        except asyncio.TimeoutError:
            print("⏳ Timeout... Retrying")

        except Exception as e:
            print(f"⚠️ Error: {e}")

    raise RuntimeError("Failed after retries")


# --------------------------
# CLI
# --------------------------

@click.group()
@click.version_option(version="2.0.0")
def cli():
    """Deep Research Agent CLI"""
    pass


# --------------------------
# RUN COMMAND
# --------------------------

@cli.command()
@click.option("--topic", "-t", required=True)
@click.option("--mock", is_flag=True)
@click.option("--log", default="warning")
def run(topic, mock, log):

    """Run research"""

    setup_logging(log)

    try:
        topic = validate_topic(topic)

    except ValueError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)

    click.echo("🔍 Starting research...")

    context = {"topic": topic}

    agent = default_agent

    try:
        result = asyncio.run(safe_run(agent, context, mock))

        output = {
            "success": result.success,
            "steps": result.steps_executed,
            "output": result.output,
            "error": result.error,
        }

        file = save_result(output)

        click.echo("✅ Research complete")
        click.echo(f"📁 Saved: {file}")

        click.echo(json.dumps(output, indent=2))

    except Exception as e:
        click.echo(f"❌ Failed: {e}")
        sys.exit(1)


# --------------------------
# INTERACTIVE MODE
# --------------------------

@cli.command()
def shell():

    """Interactive mode"""

    asyncio.run(run_shell())


async def run_shell():

    setup_logging("info")

    agent = DeepResearchAgent()
    await agent.start()

    print("=== Research Shell ===")
    print("Type 'quit' to exit\n")

    try:

        while True:

            topic = input("Topic> ").strip()

            if topic.lower() in ["quit", "exit"]:
                break

            try:
                topic = validate_topic(topic)

            except ValueError as e:
                print(f"❌ {e}")
                continue

            print("🔄 Working...\n")

            try:

                result = await safe_run(
                    agent,
                    {"topic": topic},
                    False
                )

                if result.success:
                    print("✅ Done\n")
                    print(json.dumps(result.output, indent=2))

                else:
                    print(f"❌ Failed: {result.error}")

            except Exception as e:
                print(f"⚠️ Error: {e}")

    finally:
        await agent.stop()
        print("👋 Goodbye")


# --------------------------
# INFO
# --------------------------

@cli.command()
def info():

    """Show agent info"""

    data = default_agent.info()

    print("\nAgent Info\n----------")

    for k, v in data.items():
        print(f"{k}: {v}")


# --------------------------
# VALIDATE
# --------------------------

@cli.command()
def validate():

    """Validate agent"""

    result = default_agent.validate()

    if result["valid"]:
        print("✅ Agent is valid")

    else:
        print("❌ Errors found:")

        for e in result["errors"]:
            print("-", e)

    sys.exit(0 if result["valid"] else 1)


# --------------------------
# MAIN
# --------------------------

if __name__ == "__main__":
    cli()
