#!/usr/bin/env python3
"""
Verification script for Aden Hive Framework MCP Server

This script checks if the MCP server is properly installed and configured.
"""

import json
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
    # Disable colors on Windows if colorama is not available
    _use_colors = COLORAMA_AVAILABLE or platform.system() != 'Windows'
    GREEN = '\033[0;32m' if _use_colors else ''
    YELLOW = '\033[1;33m' if _use_colors else ''
    RED = '\033[0;31m' if _use_colors else ''
    BLUE = '\033[0;34m' if _use_colors else ''
    NC = '\033[0m' if _use_colors else ''


def check(description: str) -> bool:
    """Print check description and return a context manager for result."""
    print(f"Checking {description}...", end=" ")
    return True


def success(msg: str = "OK"):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")


def warning(msg: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.NC}")


def error(msg: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")


def main():
    """Run verification checks."""
    print("=== MCP Server Verification ===")
    print()

    script_dir = Path(__file__).parent.absolute()
    all_checks_passed = True

    # Check 0: Python version
    check("Python version")
    py_version = sys.version.split()[0]
    py_major_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info >= (3, 11):
        success(f"{py_version} (>= 3.11)")
    else:
        warning(f"{py_version} (3.11+ recommended)")
    print()

    # Check 1: Framework package installed
    check("framework package installation")
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import framework; print(framework.__file__); print(getattr(framework, '__version__', 'unknown'))"],
            capture_output=True,
            text=True,
            check=True
        )
        lines = result.stdout.strip().split('\n')
        framework_path = lines[0] if lines else 'unknown'
        framework_version = lines[1] if len(lines) > 1 else 'unknown'
        success(f"v{framework_version} at {framework_path}")
    except subprocess.CalledProcessError as e:
        error("framework package not found")
        is_windows = platform.system() == 'Windows'
        if is_windows:
            print(f"  Run (PowerShell): python -m pip install -e {script_dir}")
        else:
            print(f"  Run: pip install -e {script_dir}")
        if e.stderr:
            print(f"  Error: {e.stderr}")
        all_checks_passed = False

    # Check 2: MCP dependencies
    check("MCP dependencies")
    missing_deps = []
    installed_versions = {}
    for dep in ["mcp", "fastmcp"]:
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {dep}; print(getattr({dep}, '__version__', 'unknown'))"],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()
            installed_versions[dep] = version
        except subprocess.CalledProcessError:
            missing_deps.append(dep)

    if missing_deps:
        error(f"missing: {', '.join(missing_deps)}")
        is_windows = platform.system() == 'Windows'
        if is_windows:
            print(f"  Run (PowerShell): python -m pip install {' '.join(missing_deps)}")
        else:
            print(f"  Run: pip install {' '.join(missing_deps)}")
        all_checks_passed = False
    else:
        versions_str = ', '.join([f"{k} v{v}" for k, v in installed_versions.items()])
        success(f"installed ({versions_str})")

    # Check 3: MCP server module
    check("MCP server module")
    try:
        result = subprocess.run(
            [sys.executable, "-c", "from framework.mcp import agent_builder_server"],
            capture_output=True,
            text=True,
            check=True
        )
        success("loads successfully")
    except subprocess.CalledProcessError as e:
        error("failed to import")
        if e.stderr:
            print(f"  Error: {e.stderr}")
        if e.stdout:
            print(f"  Output: {e.stdout}")
        print(f"  Hint: Ensure framework package is installed with MCP dependencies")
        all_checks_passed = False

    # Check 4: MCP configuration file
    check("MCP configuration file")
    mcp_config = script_dir / ".mcp.json"
    if mcp_config.exists():
        try:
            with open(mcp_config) as f:
                config = json.load(f)

            if "mcpServers" in config and "agent-builder" in config["mcpServers"]:
                server_config = config["mcpServers"]["agent-builder"]
                success("found and valid")
                print(f"  Command: {server_config.get('command')}")
                print(f"  Args: {' '.join(server_config.get('args', []))}")
                print(f"  CWD: {server_config.get('cwd')}")
            else:
                warning("exists but missing agent-builder config")
                all_checks_passed = False
        except json.JSONDecodeError:
            error("invalid JSON format")
            all_checks_passed = False
    else:
        warning("not found (optional)")
        print(f"  Location would be: {mcp_config}")
        print(f"  Run setup_mcp.py to create it")

    # Check 5: Framework modules
    check("core framework modules")
    modules_to_check = [
        "framework.runtime.core",
        "framework.graph.executor",
        "framework.graph.node",
        "framework.builder.query",
        "framework.llm",
    ]

    failed_modules = []
    for module in modules_to_check:
        try:
            subprocess.run(
                [sys.executable, "-c", f"import {module}"],
                capture_output=True,
                check=True
            )
        except subprocess.CalledProcessError:
            failed_modules.append(module)

    if failed_modules:
        error(f"failed to import: {', '.join(failed_modules)}")
        all_checks_passed = False
    else:
        success(f"all {len(modules_to_check)} modules OK")

    # Check 6: Test MCP server startup (quick test)
    check("MCP server startup")
    try:
        # Try to import and instantiate the MCP server
        result = subprocess.run(
            [sys.executable, "-c",
             "from framework.mcp.agent_builder_server import mcp; print('OK')"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        if "OK" in result.stdout:
            success("server can start")
        else:
            warning("unexpected output")
    except subprocess.TimeoutExpired:
        warning("server startup slow (might be OK)")
    except subprocess.CalledProcessError as e:
        error("server failed to start")
        print(f"  Error: {e.stderr}")
        all_checks_passed = False

    print()
    print("=" * 40)
    is_windows = platform.system() == 'Windows'
    shell_name = "PowerShell" if is_windows else "shell"
    
    if all_checks_passed:
        print(f"{Colors.GREEN}✓ All checks passed!{Colors.NC}")
        print()
        print("Your MCP server is ready to use.")
        print()
        print(f"{Colors.BLUE}To start the server ({shell_name}):{Colors.NC}")
        print(f"  python -m framework.mcp.agent_builder_server")
        print()
        print(f"{Colors.BLUE}To use with Claude Desktop:{Colors.NC}")
        print(f"  Add the configuration from .mcp.json to your")
        print(f"  Claude Desktop MCP settings")
    else:
        print(f"{Colors.RED}✗ Some checks failed{Colors.NC}")
        print()
        print(f"To fix issues, run ({shell_name}):")
        print(f"  python {script_dir / 'setup_mcp.py'}")
    print()


if __name__ == "__main__":
    main()
