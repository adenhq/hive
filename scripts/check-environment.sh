#!/bin/bash
#
# check-environment.sh - Environment Validation Tool
#
# This script validates the development environment before running setup.
# Shows a checklist of requirements with pass/fail status to catch issues early.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Track validation results
PASSED=0
FAILED=0
WARNINGS=0

# Function to print check result
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# Function to print section header
section_header() {
    echo ""
    echo -e "${CYAN}$1${NC}"
    echo "----------------------------------------"
}

# Function to print fix suggestion
print_fix() {
    echo -e "  ${BLUE}→${NC} $1"
}

echo ""
echo "=================================================="
echo "  Environment Validation Checklist"
echo "=================================================="
echo ""
echo "Checking requirements before setup..."
echo ""

# ============================================================
# 1. Python Installation Check
# ============================================================
section_header "1. Python Installation"

if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    check_fail "Python not found"
    echo ""
    echo -e "${YELLOW}Quick fix:${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_fix "macOS (Homebrew): brew install python@3.11"
        print_fix "macOS (Official): https://www.python.org/downloads/"
    elif [[ "$OSTYPE" == "linux"* ]]; then
        print_fix "Ubuntu/Debian: sudo apt update && sudo apt install python3.11"
        print_fix "Fedora/RHEL: sudo dnf install python3.11"
    else
        print_fix "Download from: https://www.python.org/downloads/"
    fi
else
    # Use python3 if available, otherwise python
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
    PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)' 2>/dev/null)
    PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)' 2>/dev/null)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        check_fail "Python version too old (found $PYTHON_VERSION, requires 3.11+)"
        echo ""
        echo -e "${YELLOW}Quick fix:${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            print_fix "macOS (Homebrew): brew install python@3.11"
            print_fix "macOS (pyenv): brew install pyenv && pyenv install 3.11.0 && pyenv global 3.11.0"
        elif [[ "$OSTYPE" == "linux"* ]]; then
            print_fix "Ubuntu/Debian: sudo apt update && sudo apt install python3.11"
            print_fix "Using pyenv: curl https://pyenv.run | bash && pyenv install 3.11.0 && pyenv global 3.11.0"
        else
            print_fix "Download from: https://www.python.org/downloads/"
        fi
    else
        check_pass "Python $PYTHON_VERSION detected (requires 3.11+)"
    fi
fi

# ============================================================
# 2. pip Installation Check
# ============================================================
section_header "2. pip Package Manager"

if [ -z "$PYTHON_CMD" ]; then
    check_fail "Cannot check pip (Python not found)"
else
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        check_fail "pip not available"
        echo ""
        echo -e "${YELLOW}Quick fix:${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            print_fix "python3 -m ensurepip --upgrade"
            print_fix "Or reinstall Python: brew reinstall python@3.11"
        elif [[ "$OSTYPE" == "linux"* ]]; then
            print_fix "Ubuntu/Debian: sudo apt install python3-pip"
            print_fix "Fedora/RHEL: sudo dnf install python3-pip"
        else
            print_fix "python3 -m ensurepip --upgrade"
        fi
    else
        PIP_VERSION=$($PYTHON_CMD -m pip --version | cut -d' ' -f2)
        check_pass "pip $PIP_VERSION detected"
    fi
fi

# ============================================================
# 3. Virtual Environment Check
# ============================================================
section_header "3. Virtual Environment"

if [ -z "$VIRTUAL_ENV" ]; then
    check_warn "Not running in a virtual environment"
    echo ""
    echo -e "${YELLOW}Recommendation:${NC}"
    print_fix "Create virtual environment: python3 -m venv .venv"
    print_fix "Activate it: source .venv/bin/activate"
    print_fix "Then run: ./scripts/setup-python.sh"
else
    check_pass "Running in virtual environment: $(basename "$VIRTUAL_ENV")"
fi

# ============================================================
# 4. Project Structure Check
# ============================================================
section_header "4. Project Structure"

if [ ! -d "$PROJECT_ROOT/core" ]; then
    check_fail "core/ directory not found"
    echo ""
    echo -e "${YELLOW}Quick fix:${NC}"
    print_fix "Ensure you're in the project root directory"
    print_fix "Re-clone repository if needed: git clone <repository-url>"
else
    check_pass "core/ directory exists"
fi

if [ ! -d "$PROJECT_ROOT/tools" ]; then
    check_fail "tools/ directory not found"
    echo ""
    echo -e "${YELLOW}Quick fix:${NC}"
    print_fix "Ensure you're in the project root directory"
    print_fix "Re-clone repository if needed: git clone <repository-url>"
else
    check_pass "tools/ directory exists"
fi

if [ ! -f "$PROJECT_ROOT/core/pyproject.toml" ]; then
    check_fail "core/pyproject.toml not found"
    echo ""
    echo -e "${YELLOW}Quick fix:${NC}"
    print_fix "Repository may be incomplete. Try: git pull origin main"
else
    check_pass "core/pyproject.toml exists"
fi

if [ ! -f "$PROJECT_ROOT/tools/pyproject.toml" ]; then
    check_fail "tools/pyproject.toml not found"
    echo ""
    echo -e "${YELLOW}Quick fix:${NC}"
    print_fix "Repository may be incomplete. Try: git pull origin main"
else
    check_pass "tools/pyproject.toml exists"
fi

if [ ! -d "$PROJECT_ROOT/exports" ]; then
    check_warn "exports/ directory not found (will be created during setup)"
else
    check_pass "exports/ directory exists"
fi

# ============================================================
# 5. Package Installation Status Check
# ============================================================
section_header "5. Package Installation Status"

if [ -n "$PYTHON_CMD" ] && $PYTHON_CMD -m pip --version &> /dev/null; then
    # Check framework package
    if $PYTHON_CMD -c "import framework" &> /dev/null 2>&1; then
        FRAMEWORK_VERSION=$($PYTHON_CMD -c "import framework; print(getattr(framework, '__version__', 'installed'))" 2>/dev/null || echo "installed")
        check_pass "framework package installed"
    else
        check_warn "framework package not installed (will be installed during setup)"
    fi
    
    # Check aden_tools package
    if $PYTHON_CMD -c "import aden_tools" &> /dev/null 2>&1; then
        check_pass "aden_tools package installed"
    else
        check_warn "aden_tools package not installed (will be installed during setup)"
    fi
    
    # Check openai version compatibility
    if $PYTHON_CMD -c "import openai" &> /dev/null 2>&1; then
        OPENAI_VERSION=$($PYTHON_CMD -c "import openai; print(openai.__version__)" 2>/dev/null)
        if [[ "$OPENAI_VERSION" =~ ^0\. ]]; then
            check_fail "openai version $OPENAI_VERSION is incompatible (requires >=1.0.0)"
            echo ""
            echo -e "${YELLOW}Quick fix:${NC}"
            print_fix "pip install --upgrade \"openai>=1.0.0\""
            echo ""
            echo -e "${YELLOW}Why this happened:${NC}"
            echo "  Old openai versions (0.x) are incompatible with litellm (Issue #450)"
        else
            check_pass "openai $OPENAI_VERSION is compatible"
        fi
    else
        check_warn "openai package not installed (will be installed during setup)"
    fi
else
    check_warn "Cannot check package status (pip not available)"
fi

# ============================================================
# 6. Common Issue Detection
# ============================================================
section_header "6. Common Issue Detection"

if [ -n "$PYTHON_CMD" ] && $PYTHON_CMD -m pip --version &> /dev/null; then
    # Check for PEP 668 externally-managed-environment
    PIP_CHECK_OUTPUT=$(mktemp)
    if $PYTHON_CMD -m pip install --dry-run pip &> "$PIP_CHECK_OUTPUT" 2>&1; then
        rm -f "$PIP_CHECK_OUTPUT"
        check_pass "No PEP 668 restrictions detected"
    else
        PIP_CHECK_ERROR=$(cat "$PIP_CHECK_OUTPUT")
        rm -f "$PIP_CHECK_OUTPUT"
        
        if echo "$PIP_CHECK_ERROR" | grep -q "externally-managed-environment\|This environment is externally managed"; then
            check_fail "PEP 668 externally-managed-environment detected"
            echo ""
            echo -e "${YELLOW}What happened:${NC}"
            echo "  Your system Python is protected from modifications"
            echo ""
            echo -e "${YELLOW}Quick fix (Recommended):${NC}"
            print_fix "Create virtual environment: python3 -m venv .venv"
            print_fix "Activate it: source .venv/bin/activate"
            print_fix "Then run: ./scripts/setup-python.sh"
            echo ""
            echo -e "${YELLOW}Alternative (Not recommended):${NC}"
            print_fix "Use --break-system-packages flag (may cause conflicts)"
        else
            check_pass "No PEP 668 restrictions detected"
        fi
    fi
    
    # Check write permissions
    TEMP_TEST_DIR=$(mktemp -d 2>/dev/null || echo "/tmp")
    if [ -w "$TEMP_TEST_DIR" ]; then
        check_pass "Write permissions OK"
    else
        check_fail "Write permissions issue detected"
        echo ""
        echo -e "${YELLOW}Quick fix:${NC}"
        print_fix "Use a virtual environment to avoid permission issues"
        print_fix "python3 -m venv .venv && source .venv/bin/activate"
    fi
else
    check_warn "Cannot check common issues (pip not available)"
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "=================================================="
echo "  Validation Summary"
echo "=================================================="
echo ""
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "You're ready to run setup:"
    echo -e "  ${BLUE}./scripts/setup-python.sh${NC}"
    echo ""
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠ Some warnings detected, but setup should proceed${NC}"
    echo ""
    echo "You can run setup, but consider addressing warnings:"
    echo -e "  ${BLUE}./scripts/setup-python.sh${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please fix the issues above before running setup.${NC}"
    echo ""
    echo "After fixing issues, run:"
    echo -e "  ${BLUE}./scripts/setup-python.sh${NC}"
    echo ""
    echo "For help, see:"
    echo "  • ENVIRONMENT_SETUP.md"
    echo "  • DEVELOPER.md"
    echo ""
    exit 1
fi
