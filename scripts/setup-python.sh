#!/bin/bash
#
# setup-python.sh - Python Environment Setup for Aden Agent Framework
#
# This script sets up the Python environment with all required packages
# for building and running goal-driven agents.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "=================================================="
echo "  Aden Agent Framework - Python Setup"
echo "=================================================="
echo ""

# Check for Python
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python is not installed.${NC}"
    echo "Please install Python 3.11+ from https://python.org"
    exit 1
fi

# Use python if available, otherwise python3
# (On Windows, 'python' is more reliable and properly associated with pip)
# Test which one actually has pip available
PYTHON_CMD=""

# Try to find venv in common locations (even if VIRTUAL_ENV is not set in bash)
# Look for venv folder next to this script or in parent directories
for venv_dir in "$PROJECT_ROOT/venv" "$(cd "$PROJECT_ROOT/.." 2>/dev/null && pwd)/venv" "./venv" "../venv"; do
    if [ -f "$venv_dir/Scripts/python.exe" ]; then
        echo "DEBUG: Found venv python.exe at: $venv_dir/Scripts/python.exe"
        PYTHON_CMD="$venv_dir/Scripts/python.exe"
        break
    fi
done

# If not found in venv, try direct commands with full path
if [ -z "$PYTHON_CMD" ]; then
    echo "DEBUG: Trying to find python in PATH"
    # On Windows bash, try to find python.exe directly
    if python.exe -m pip --version > /dev/null 2>&1; then
        PYTHON_CMD="python.exe"
    elif python -m pip --version > /dev/null 2>&1; then
        PYTHON_CMD="python"
    elif python3 -m pip --version > /dev/null 2>&1; then
        PYTHON_CMD="python3"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Error: Python/pip is not installed or not accessible.${NC}"
    echo "Please install Python 3.11+ from https://python.org"
    echo "DEBUG: Tried paths: $PROJECT_ROOT/venv, ./venv, ../venv"
    exit 1
fi

echo "DEBUG: Using PYTHON_CMD: $PYTHON_CMD"

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

echo -e "${BLUE}Detected Python:${NC} $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo -e "${RED}Error: Python 3.11+ is required (found $PYTHON_VERSION)${NC}"
    echo "Please upgrade your Python installation"
    exit 1
fi

if [ "$PYTHON_MINOR" -lt 11 ]; then
    echo -e "${YELLOW}Warning: Python 3.11+ is recommended for best compatibility${NC}"
    echo -e "${YELLOW}You have Python $PYTHON_VERSION which may work but is not officially supported${NC}"
    echo ""
fi

echo -e "${GREEN}✓${NC} Python version check passed"
echo ""

# Set up pip command
PIP_CMD="$PYTHON_CMD -m pip"

echo -e "${GREEN}✓${NC} pip detected"
echo ""

# Upgrade pip, setuptools, and wheel
echo "Upgrading pip, setuptools, and wheel..."
if ! $PIP_CMD install --upgrade pip setuptools wheel; then
  echo "Error: Failed to upgrade pip. Please check your python/venv configuration."
  exit 1
fi
echo -e "${GREEN}✓${NC} Core packages upgraded"
echo ""

# Install core framework package
echo "=================================================="
echo "Installing Core Framework Package"
echo "=================================================="
echo ""
cd "$PROJECT_ROOT/core"

if [ -f "pyproject.toml" ]; then
    echo "Installing framework from core/ (editable mode)..."
    $PIP_CMD install -e . > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Framework package installed"
    else
        echo -e "${YELLOW}⚠${NC} Framework installation encountered issues (may be OK if already installed)"
    fi
else
    echo -e "${YELLOW}⚠${NC} No pyproject.toml found in core/, skipping framework installation"
fi
echo ""

# Install tools package
echo "=================================================="
echo "Installing Tools Package (aden_tools)"
echo "=================================================="
echo ""
cd "$PROJECT_ROOT/tools"

if [ -f "pyproject.toml" ]; then
    echo "Installing aden_tools from tools/ (editable mode)..."
    $PIP_CMD install -e . > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Tools package installed"
    else
        echo -e "${RED}✗${NC} Tools installation failed"
        exit 1
    fi
else
    echo -e "${RED}Error: No pyproject.toml found in tools/${NC}"
    exit 1
fi
echo ""

# Fix openai version compatibility with litellm
echo "=================================================="
echo "Fixing Package Compatibility"
echo "=================================================="
echo ""

# Check openai version
OPENAI_VERSION=$($PYTHON_CMD -c "import openai; print(openai.__version__)" 2>/dev/null || echo "not_installed")

if [ "$OPENAI_VERSION" = "not_installed" ]; then
    echo "Installing openai package..."
    $PIP_CMD install "openai>=1.0.0" > /dev/null 2>&1
    echo -e "${GREEN}✓${NC} openai package installed"
elif [[ "$OPENAI_VERSION" =~ ^0\. ]]; then
    echo -e "${YELLOW}Found old openai version: $OPENAI_VERSION${NC}"
    echo "Upgrading to openai 1.x+ for litellm compatibility..."
    $PIP_CMD install --upgrade "openai>=1.0.0" > /dev/null 2>&1
    OPENAI_VERSION=$($PYTHON_CMD -c "import openai; print(openai.__version__)" 2>/dev/null)
    echo -e "${GREEN}✓${NC} openai upgraded to $OPENAI_VERSION"
else
    echo -e "${GREEN}✓${NC} openai $OPENAI_VERSION is compatible"
fi
echo ""

# Verify installations
echo "=================================================="
echo "Verifying Installation"
echo "=================================================="
echo ""

cd "$PROJECT_ROOT"

# Test framework import
if $PYTHON_CMD -c "import framework; print('framework OK')" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} framework package imports successfully"
else
    echo -e "${RED}✗${NC} framework package import failed"
    echo -e "${YELLOW}  Note: This may be OK if you don't need the framework${NC}"
fi

# Test aden_tools import
if $PYTHON_CMD -c "import aden_tools; print('aden_tools OK')" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} aden_tools package imports successfully"
else
    echo -e "${RED}✗${NC} aden_tools package import failed"
    exit 1
fi

# Test litellm + openai compatibility
if $PYTHON_CMD -c "import litellm; print('litellm OK')" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} litellm package imports successfully"
else
    echo -e "${YELLOW}⚠${NC} litellm import had issues (may be OK if not using LLM features)"
fi

echo ""

# Print agent commands
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "Python packages installed:"
echo "  • framework (core agent runtime)"
echo "  • aden_tools (tools and MCP servers)"
echo "  • All dependencies and compatibility fixes applied"
echo ""
echo "To run agents, use:"
echo ""
echo "  ${BLUE}# From project root:${NC}"
echo "  PYTHONPATH=core:exports python -m agent_name validate"
echo "  PYTHONPATH=core:exports python -m agent_name info"
echo "  PYTHONPATH=core:exports python -m agent_name run --input '{...}'"
echo ""
echo "Available commands for your new agent:"
echo "  PYTHONPATH=core:exports python -m support_ticket_agent validate"
echo "  PYTHONPATH=core:exports python -m support_ticket_agent info"
echo "  PYTHONPATH=core:exports python -m support_ticket_agent run --input '{\"ticket_content\":\"...\",\"customer_id\":\"...\",\"ticket_id\":\"...\"}'"
echo ""
echo "To build new agents, use Claude Code skills:"
echo "  • /building-agents - Build a new agent"
echo "  • /testing-agent   - Test an existing agent"
echo ""
echo "Documentation: ${PROJECT_ROOT}/README.md"
echo "Agent Examples: ${PROJECT_ROOT}/exports/"
echo ""
