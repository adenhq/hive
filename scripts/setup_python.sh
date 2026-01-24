#!/bin/bash

# setup-python.sh - Python Environment Setup for Aden Agent Framework
#
# This script sets up the Python environment with all required packages
# for building and running goal-driven agents.

set -e

# Colors for output
NC='[0m' # No Color
BOLD='[1m'
RED='[91m'
GREEN='[92m'
YELLOW='[93m'

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

is_installed() { command -v "$1" &> /dev/null; }

is_file() { [ -f "$1" ]; }

echo
echo "$BOLD=================================================="
echo "  Aden Agent Framework - Python Setup"
echo "==================================================$NC"
echo

# Check for Python
if is_installed python3; then
  PYTHON_CMD="python3"
elif is_installed python; then
  PYTHON_CMD="python"
else
  echo "${RED}Error: Python is not installed.$NC"
  echo "Please install Python 3.11+ from https://python.org"
  exit 1
fi

# Check Python version
PYTHON_VERSION=$(
  "$PYTHON_CMD" \
  -c \
  'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
)
PYTHON_MAJOR=$("$PYTHON_CMD" -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$("$PYTHON_CMD" -c 'import sys; print(sys.version_info.minor)')
VENV_ACTIVATE=".venv/bin/activate"

echo "${BLUE}Detected Python:$NC $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] ||
  { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
  echo "${RED}Error: Python 3.11+ is required (found $PYTHON_VERSION)$NC"
  echo "Please upgrade your Python installation"
  exit 1
fi

if [ "$PYTHON_MINOR" -lt 11 ]; then
  echo "${YELLOW}Warning: Python 3.11+ is recommended for best compatibility$NC"
  echo "${YELLOW}You have Python $PYTHON_VERSION which may work but is not \
officially supported$NC"
  echo
fi

echo "$GREEN✓$NC Python version check passed"
echo

# Check for pip
# shellcheck source=/dev/null
if is_file "$VENV_ACTIVATE"; then
  source "$VENV_ACTIVATE"
elif is_file "../$VENV_ACTIVATE"; then
  source "../$VENV_ACTIVATE"
fi
if ! "$PYTHON_CMD" -m pip --version &> /dev/null; then
  echo "${RED}Error: pip is not installed$NC"
  echo "Please install pip for Python $PYTHON_VERSION"
  exit 1
fi

echo "$GREEN✓$NC pip detected"
echo

# Upgrade pip, setuptools, and wheel
echo "Upgrading pip, setuptools, and wheel..."
if ! "$PYTHON_CMD" -m pip install --upgrade pip setuptools wheel; then
  echo "Error: Failed to upgrade pip. \
Please check your python/venv configuration."
  exit 1
fi
echo "$GREEN✓$NC Core packages upgraded"
echo

# Install core framework package
echo "=================================================="
echo "Installing Core Framework Package"
echo "=================================================="
echo
cd "$PROJECT_ROOT/core"

if is_file "pyproject.toml"; then
  echo "Installing framework from core/ (editable mode)..."
  if "$PYTHON_CMD" -m pip install -e . > /dev/null 2>&1; then
    echo "$GREEN✓$NC Framework package installed"
  else
    echo "$YELLOW⚠$NC Framework installation encountered issues (may be OK if \
already installed)"
  fi
else
  echo "$YELLOW⚠$NC No pyproject.toml found in core/, skipping framework \
installation"
fi
echo

# Install tools package
echo "=================================================="
echo "Installing Tools Package (aden_tools)"
echo "=================================================="
echo
cd "$PROJECT_ROOT/tools"

if is_file "pyproject.toml"; then
  echo "Installing aden_tools from tools/ (editable mode)..."
  if "$PYTHON_CMD" -m pip install -e . > /dev/null 2>&1; then
    echo "$GREEN✓$NC Tools package installed"
  else
    echo "$RED✗$NC Tools installation failed"
    exit 1
  fi
else
  echo "${RED}Error: No pyproject.toml found in tools/$NC"
  exit 1
fi
echo

# Fix openai version compatibility with litellm
echo "=================================================="
echo "Fixing Package Compatibility"
echo "=================================================="
echo

# Check openai version
OPENAI_VERSION=$(
  "$PYTHON_CMD" -c "import openai; print(openai.__version__)" 2>/dev/null ||
    echo "not_installed"
)

if [ "$OPENAI_VERSION" = "not_installed" ]; then
  echo "Installing openai package..."
  "$PYTHON_CMD" -m pip install "openai>=1.0.0" > /dev/null 2>&1
  echo "$GREEN✓$NC openai package installed"
elif [[ "$OPENAI_VERSION" =~ ^0\. ]]; then
  echo "${YELLOW}Found old openai version: $OPENAI_VERSION$NC"
  echo "Upgrading to openai 1.x+ for litellm compatibility..."
  "$PYTHON_CMD" -m pip install --upgrade "openai>=1.0.0" > /dev/null 2>&1
  OPENAI_VERSION=$(
    "$PYTHON_CMD" -c "import openai; print(openai.__version__)" 2>/dev/null
  )
  echo "$GREEN✓$NC openai upgraded to $OPENAI_VERSION"
else
  echo "$GREEN✓$NC openai $OPENAI_VERSION is compatible"
fi
echo

# Verify installations
echo "=================================================="
echo "Verifying Installation"
echo "=================================================="
echo

cd "$PROJECT_ROOT"

# Test framework import
if "$PYTHON_CMD" -c "import framework; print('framework OK')" > \
  /dev/null 2>&1; then
  echo "$GREEN✓$NC framework package imports successfully"
else
  echo "$RED✗$NC framework package import failed"
  echo "$YELLOW  Note: This may be OK if you don't need the framework$NC"
fi

# Test aden_tools import
if "$PYTHON_CMD" -c "import aden_tools; print('aden_tools OK')" > \
  /dev/null 2>&1; then
  echo "$GREEN✓$NC aden_tools package imports successfully"
else
  echo "$RED✗$NC aden_tools package import failed"
  exit 1
fi

# Test litellm + openai compatibility
if "$PYTHON_CMD" -c "import litellm; print('litellm OK')" > \
  /dev/null 2>&1; then
  echo "$GREEN✓$NC litellm package imports successfully"
else
  echo "$YELLOW⚠$NC litellm import had issues (may be OK if not using LLM \
features)"
fi

echo

# Print agent commands
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo
echo "Python packages installed:"
echo "  • framework (core agent runtime)"
echo "  • aden_tools (tools and MCP servers)"
echo "  • All dependencies and compatibility fixes applied"
echo
echo "To run agents, use:"
echo
echo "  $BLUE# From project root:$NC"
echo "  PYTHONPATH=core:exports python -m agent_name validate"
echo "  PYTHONPATH=core:exports python -m agent_name info"
echo "  PYTHONPATH=core:exports python -m agent_name run --input '{...}'"
echo
echo "Available commands for your new agent:"
echo "  PYTHONPATH=core:exports python -m support_ticket_agent validate"
echo "  PYTHONPATH=core:exports python -m support_ticket_agent info"
echo "  PYTHONPATH=core:exports python -m support_ticket_agent run --input \
'{\"ticket_content\":\"...\",\"customer_id\":\"...\",\"ticket_id\":\"...\"}'"
echo
echo "To build new agents, use Claude Code skills:"
echo "  • /building-agents - Build a new agent"
echo "  • /testing-agent   - Test an existing agent"
echo
echo "Documentation: $PROJECT_ROOT/README.md"
echo "Agent Examples: $PROJECT_ROOT/exports/"
echo
