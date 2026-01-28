"""
Command-line interface for Goal Agent.

Usage:
    python -m core run exports/my-agent --input '{"key": "value"}'
    python -m core info exports/my-agent
    python -m core validate exports/my-agent
    python -m core list exports/
    python -m core dispatch exports/ --input '{"key": "value"}'
    python -m core shell exports/my-agent

Testing commands:
    python -m core test-run <agent_path> --goal <goal_id>
    python -m core test-debug <goal_id> <test_id>
    python -m core test-list <goal_id>
    python -m core test-stats <goal_id>
"""

import argparse
import sys
import traceback


def main():
    parser = argparse.ArgumentParser(description="Goal Agent - Build and run goal-driven agents")
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="Anthropic model to use",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show full tracebacks on error",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Register runner commands (run, info, validate, list, dispatch, shell)
    from framework.runner.cli import register_commands

    register_commands(subparsers)

    # Register testing commands (test-run, test-debug, test-list, test-stats)
    from framework.testing.cli import register_testing_commands

    register_testing_commands(subparsers)

    args = parser.parse_args()

    if hasattr(args, "func"):
        try:
            sys.exit(args.func(args))
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            sys.exit(130)
        except Exception as exc:
            # Last-resort handler for anything that escapes command-level handling
            from framework.errors import _resolve_error, format_error

            verbose = getattr(args, "verbose", False)
            cli_err = _resolve_error(exc)
            cli_err.__cause__ = exc
            print(format_error(cli_err, verbose=verbose), file=sys.stderr)
            if verbose:
                traceback.print_exc(file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
