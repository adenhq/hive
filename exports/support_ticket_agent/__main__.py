import argparse
import sys
from pathlib import Path
import logging

from framework.runner.cli import cmd_run, cmd_validate, cmd_info, cmd_shell

def main():
    agent_path = Path(__file__).parent.absolute()
    
    parser = argparse.ArgumentParser(description="Support Ticket Agent CLI")
    parser.add_argument(
        "--model",
        help="LLM model to use (any LiteLLM model name)",
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the agent")
    run_parser.add_argument("--input", "-i", type=str, help="Input context as JSON string")
    run_parser.add_argument("--mock", action="store_true", help="Run in mock mode")
    run_parser.add_argument("--quiet", "-q", action="store_true", help="Only output JSON")
    run_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed logs")
    run_parser.set_defaults(func=cmd_run)
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate the agent structure")
    validate_parser.set_defaults(func=cmd_validate)
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show agent information")
    info_parser.set_defaults(func=cmd_info)
    
    # Shell command
    shell_parser = subparsers.add_parser("shell", help="Start interactive shell")
    shell_parser.set_defaults(func=cmd_shell)
    
    args = parser.parse_args()
    
    # Inject agent_path and missing expected attributes
    args.agent_path = str(agent_path)
    if not hasattr(args, "input_file"): args.input_file = None
    if not hasattr(args, "output"): args.output = None
    if not hasattr(args, "no_approve"): args.no_approve = False
    if not hasattr(args, "multi"): args.multi = False
    if not hasattr(args, "agents_dir"): args.agents_dir = "exports"
    if not hasattr(args, "json"): args.json = False # for cmd_info
    
    if hasattr(args, "func"):
        sys.exit(args.func(args))

if __name__ == "__main__":
    main()
