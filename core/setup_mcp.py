#!/usr/bin/env python3
"""
Setup script for Aden Hive Framework MCP Server

This script installs the framework and configures the MCP server.
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

try:
    import colorama
    colorama.init()
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class Colors:
    """ANSI color codes for terminal output."""
    # Disable colors on Windows if colorama is not available
    _use_colors = COLORAMA_AVAILABLE or platform.system() != 'Windows'
    GREEN = '\033[0;32m' if _use_colors else ''
    YELLOW = '\033[1;33m' if _use_colors else ''
    RED = '\033[0;31m' if _use_colors else ''
    BLUE = '\033[0;34m' if _use_colors else ''
    NC = '\033[0m' if _use_colors else ''


def print_step(message: str, color: str = Colors.YELLOW):
    """Print a colored step message."""
    print(f"{color}{message}{Colors.NC}")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.NC}", file=sys.stderr)


def run_command(cmd: list, error_msg: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print_error(error_msg)
        if e.stderr:
            print(f"Error output: {e.stderr}", file=sys.stderr)
        if e.stdout:
            print(f"Command output: {e.stdout}", file=sys.stderr)
        return False, e.stderr


def main():
    """Main setup function."""
    print("=== Aden Hive Framework MCP Server Setup ===")
    print()

    # Get script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    # Step 1: Check Python version
    print_step("Step 1: Checking Python version...")
    py_version = sys.version.split()[0]
    print(f"Python version: {py_version}")
    if sys.version_info < (3, 11):
        print_error(f"Python 3.11+ required, found {py_version}")
        sys.exit(1)
    print_success(f"Python {py_version} OK")
    print()

    # Step 2: Install framework package
    print_step("Step 2: Installing framework package...")
    success, output = run_command(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        "Failed to install framework package"
    )
    if not success:
        sys.exit(1)
    print_success("Framework package installed")
    print()

    # Step 3: Install MCP dependencies
    print_step("Step 3: Installing MCP dependencies...")
    success, output = run_command(
        [sys.executable, "-m", "pip", "install", "mcp", "fastmcp"],
        "Failed to install MCP dependencies"
    )
    if not success:
        sys.exit(1)
    print_success("MCP dependencies installed")
    
    # Report installed versions
    try:
        import mcp
        import fastmcp
        print(f"  mcp version: {getattr(mcp, '__version__', 'unknown')}")
        print(f"  fastmcp version: {getattr(fastmcp, '__version__', 'unknown')}")
    except ImportError:
        pass
    print()

    # Step 4: Verify/create MCP configuration
    print_step("Step 4: Verifying MCP server configuration...")
    mcp_config_path = script_dir / ".mcp.json"

    if mcp_config_path.exists():
        print_success("MCP configuration found at .mcp.json")
        print("Configuration:")
        with open(mcp_config_path) as f:
            config = json.load(f)
            print(json.dumps(config, indent=2))
    else:
        print_error("No .mcp.json found")
        print("Creating default MCP configuration...")

        config = {
            "mcpServers": {
                "agent-builder": {
                    "command": "python",
                    "args": ["-m", "framework.mcp.agent_builder_server"],
                    "cwd": str(script_dir)
                }
            }
        }

        with open(mcp_config_path, 'w') as f:
            json.dump(config, f, indent=2)

        print_success("Created .mcp.json")
    print()

    # Step 5: Test MCP server
    print_step("Step 5: Testing MCP server...")
    try:
        # Try importing the MCP server module
        result = subprocess.run(
            [sys.executable, "-c", "from framework.mcp import agent_builder_server"],
            check=True,
            capture_output=True,
            text=True
        )
        print_success("MCP server module verified")
    except subprocess.CalledProcessError as e:
        print_error("Failed to import MCP server module")
        print(f"Error: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    print()

    # Success summary
    print(f"{Colors.GREEN}=== Setup Complete ==={Colors.NC}")
    print()
    print("The MCP server is now ready to use!")
    print()
    is_windows = platform.system() == 'Windows'
    shell_name = "PowerShell" if is_windows else "shell"
    
    print(f"{Colors.BLUE}To start the MCP server manually ({shell_name}):{Colors.NC}")
    print(f"  python -m framework.mcp.agent_builder_server")
    print()
    print(f"{Colors.BLUE}MCP Configuration location:{Colors.NC}")
    print(f"  {mcp_config_path}")
    print()
    print(f"{Colors.BLUE}To use with Claude Desktop or other MCP clients,{Colors.NC}")
    print(f"{Colors.BLUE}add the following to your MCP client configuration:{Colors.NC}")
    print()

    example_config = {
        "mcpServers": {
            "agent-builder": {
                "command": "python",
                "args": ["-m", "framework.mcp.agent_builder_server"],
                "cwd": str(script_dir)
            }
        }
    }
    print(json.dumps(example_config, indent=2))
    print()


if __name__ == "__main__":
    main()
