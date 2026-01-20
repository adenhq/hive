"""
Command-line interface for Goal Agent.

Usage:
    python -m core run exports/my-agent --input '{"key": "value"}'
    python -m core info exports/my-agent
    python -m core validate exports/my-agent
    python -m core list exports/
    python -m core dispatch exports/ --input '{"key": "value"}'
    python -m core shell exports/my-agent
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Goal Agent - Build and run goal-driven agents"
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Anthropic model to use",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Register runner commands (run, info, validate, list, dispatch, shell)
    from framework.runner.cli import register_commands
    register_commands(subparsers)

    args = parser.parse_args()

    if hasattr(args, "func"):
        sys.exit(args.func(args))


if __name__ == "__main__":
    main()
