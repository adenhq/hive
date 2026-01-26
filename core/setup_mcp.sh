#!/bin/bash

# Setup script for Aden Hive Framework MCP Server
# This script installs the framework and configures the MCP server

set -e  # Exit on error

echo "=== Aden Hive Framework MCP Server Setup ==="
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}Step 1: Installing framework package...${NC}"

# Check if uv is available
if command -v uv &> /dev/null; then
    echo "Using uv package manager..."
    # Navigate to project root and sync all packages
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    cd "$PROJECT_ROOT"
    uv sync --frozen --all-packages || {
        echo -e "${RED}Failed to install packages via uv${NC}"
        exit 1
    }
    cd "$SCRIPT_DIR"
    echo -e "${GREEN}✓ Framework and dependencies installed via uv${NC}"
else
    echo "Using pip package manager..."
    pip install -e . || {
        echo -e "${RED}Failed to install framework package${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Framework package installed${NC}"
    echo ""

    echo -e "${YELLOW}Step 2: Installing MCP dependencies...${NC}"
    pip install mcp fastmcp || {
        echo -e "${RED}Failed to install MCP dependencies${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ MCP dependencies installed${NC}"
fi
echo ""

echo -e "${YELLOW}Step 2: Verifying MCP server configuration...${NC}"
if [ -f ".mcp.json" ]; then
    echo -e "${GREEN}✓ MCP configuration found at .mcp.json${NC}"
    echo "Configuration:"
    cat .mcp.json
else
    echo -e "${RED}✗ No .mcp.json found${NC}"
    echo "Creating default MCP configuration..."

    cat > .mcp.json <<EOF
{
  "mcpServers": {
    "agent-builder": {
      "command": "python",
      "args": ["-m", "framework.mcp.agent_builder_server"],
      "cwd": "$SCRIPT_DIR"
    }
  }
}
EOF
    echo -e "${GREEN}✓ Created .mcp.json${NC}"
fi
echo ""

echo -e "${YELLOW}Step 3: Testing MCP server...${NC}"

# Use appropriate Python command based on package manager
if command -v uv &> /dev/null; then
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    cd "$PROJECT_ROOT"
    uv run python -c "from framework.mcp import agent_builder_server; print('✓ MCP server module loads successfully')" || {
        echo -e "${RED}Failed to import MCP server module${NC}"
        exit 1
    }
    cd "$SCRIPT_DIR"
else
    python -c "from framework.mcp import agent_builder_server; print('✓ MCP server module loads successfully')" || {
        echo -e "${RED}Failed to import MCP server module${NC}"
        exit 1
    }
fi
echo -e "${GREEN}✓ MCP server module verified${NC}"
echo ""

echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "The MCP server is now ready to use!"
echo ""
echo "To start the MCP server manually:"
if command -v uv &> /dev/null; then
    echo "  uv run python -m framework.mcp.agent_builder_server"
else
    echo "  python -m framework.mcp.agent_builder_server"
fi
echo ""
echo "MCP Configuration location:"
echo "  $SCRIPT_DIR/.mcp.json"
echo ""
echo "To use with Claude Desktop or other MCP clients,"
echo "add the following to your MCP client configuration:"
echo ""
echo "{
  \"mcpServers\": {
    \"agent-builder\": {
      \"command\": \"python\",
      \"args\": [\"-m\", \"framework.mcp.agent_builder_server\"],
      \"cwd\": \"$SCRIPT_DIR\"
    }
  }
}"
echo ""
