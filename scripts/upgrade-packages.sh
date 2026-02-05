#!/bin/bash
#
# upgrade-packages.sh - Automated package upgrade script for Aden Agent Framework
#
# This script automates the process of upgrading Python dependencies across
# the workspace (core and tools packages).
#
# Usage:
#   ./scripts/upgrade-packages.sh              # Upgrade all packages
#   ./scripts/upgrade-packages.sh --dry-run    # Show what would be upgraded
#   ./scripts/upgrade-packages.sh --check      # Check for outdated packages only
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get the repository root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse command line arguments
DRY_RUN=false
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --check)
            CHECK_ONLY=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be upgraded without making changes"
            echo "  --check      Check for outdated packages only"
            echo "  -h, --help   Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo ""
echo -e "${YELLOW}⬢${NC} ${BOLD}Aden Package Upgrade Script${NC}"
echo ""

# Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo ""
    echo "Please install uv from https://astral.sh/uv/"
    echo "Or run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

UV_VERSION=$(uv --version)
echo -e "${GREEN}✓${NC} uv detected: $UV_VERSION"
echo ""

# Function to check outdated packages
check_outdated() {
    echo -e "${BLUE}Checking for outdated packages...${NC}"
    echo ""

    cd "$REPO_ROOT"

    echo -e "${CYAN}Workspace packages:${NC}"
    if uv pip list --outdated 2>/dev/null | tail -n +3; then
        echo ""
        return 0
    else
        echo -e "${GREEN}All packages are up to date!${NC}"
        echo ""
        return 1
    fi
}

# Function to upgrade packages
upgrade_packages() {
    local dry_run_flag=""
    if [ "$DRY_RUN" = true ]; then
        dry_run_flag="--dry-run"
        echo -e "${YELLOW}Running in dry-run mode (no changes will be made)${NC}"
        echo ""
    fi

    echo -e "${BLUE}Upgrading workspace packages...${NC}"
    echo ""

    cd "$REPO_ROOT"

    # Upgrade all packages in the workspace
    echo -e "${CYAN}Running: uv sync --upgrade ${dry_run_flag}${NC}"
    if uv sync --upgrade $dry_run_flag; then
        echo ""
        echo -e "${GREEN}✓${NC} Workspace packages upgraded successfully"
    else
        echo ""
        echo -e "${RED}✗${NC} Failed to upgrade workspace packages"
        exit 1
    fi

    echo ""
}

# Function to verify installation
verify_installation() {
    echo -e "${BLUE}Verifying installation...${NC}"
    echo ""

    cd "$REPO_ROOT"

    # Test imports
    echo -n "  Testing framework import... "
    if uv run python -c "import framework" > /dev/null 2>&1; then
        echo -e "${GREEN}ok${NC}"
    else
        echo -e "${RED}failed${NC}"
        return 1
    fi

    echo -n "  Testing aden_tools import... "
    if uv run python -c "import aden_tools" > /dev/null 2>&1; then
        echo -e "${GREEN}ok${NC}"
    else
        echo -e "${RED}failed${NC}"
        return 1
    fi

    echo ""
    echo -e "${GREEN}✓${NC} All imports successful"
    echo ""
}

# Main execution
if [ "$CHECK_ONLY" = true ]; then
    check_outdated
    exit 0
fi

# Check for outdated packages first
if check_outdated; then
    if [ "$DRY_RUN" = false ]; then
        echo -e "${YELLOW}Outdated packages found.${NC}"
        echo ""
        read -p "Do you want to upgrade them? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Upgrade cancelled."
            exit 0
        fi
        echo ""
    fi

    # Perform upgrade
    upgrade_packages

    # Verify after upgrade (only if not dry-run)
    if [ "$DRY_RUN" = false ]; then
        verify_installation

        echo -e "${GREEN}⬢${NC} ${BOLD}Upgrade complete!${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Run tests: ${CYAN}make test${NC}"
        echo "  2. Run linting: ${CYAN}make check${NC}"
        echo "  3. Update uv.lock if needed: ${CYAN}git add uv.lock${NC}"
        echo ""
    fi
else
    echo -e "${GREEN}No upgrades needed.${NC}"
    echo ""
fi
