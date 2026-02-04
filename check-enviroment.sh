#!/bin/bash
#
# check-environment.sh - Setup validation for Aden Agent Framework
#
# Run this before setup to see a checklist of requirements with pass/fail status.
# Catches common issues (PEP 668, missing dirs, wrong Python, etc.) before they cause failures.
#
# Usage: ./check-enviroment.sh   (from repo root)
#    or: ./scripts/check-environment.sh  (if moved to scripts/)
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Resolve project root: script may live in repo root or in scripts/
SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
if [[ "$(basename "$SCRIPT_DIR")" == "scripts" ]]; then
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
    PROJECT_ROOT="$SCRIPT_DIR"
fi

PASS=0
FAIL=0
WARN=0

check_pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    ((PASS++)) || true
}

check_fail() {
    echo -e "  ${RED}✗${NC} $1"
    ((FAIL++)) || true
}

check_warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    ((WARN++)) || true
}

echo ""
echo "=================================================="
echo "  Aden Agent Framework - Environment Check"
echo "=================================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# --- Python ---
echo -e "${BLUE}Python${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    check_fail "Python not found. Install Python 3.11+ (see ENVIRONMENT_SETUP.md)"
    echo ""
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "")
if [[ -z "$PYTHON_VERSION" ]]; then
    check_fail "Could not get Python version (broken install?)"
else
    PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')
    if [[ "$PYTHON_MAJOR" -lt 3 ]] || { [[ "$PYTHON_MAJOR" -eq 3 ]] && [[ "$PYTHON_MINOR" -lt 11 ]]; }; then
        check_fail "Python 3.11+ required; found $PYTHON_VERSION"
    else
        check_pass "Python $PYTHON_VERSION (3.11+ required)"
    fi
fi
echo ""

# --- pip ---
echo -e "${BLUE}pip${NC}"
if $PYTHON_CMD -m pip --version &> /dev/null; then
    check_pass "pip available"
else
    check_fail "pip not found. Run: $PYTHON_CMD -m ensurepip --upgrade"
fi
echo ""

# --- Virtual environment ---
echo -e "${BLUE}Virtual environment${NC}"
if [[ -n "$VIRTUAL_ENV" ]]; then
    check_pass "Active venv: $(basename "$VIRTUAL_ENV")"
else
    check_warn "No virtual environment. Recommended: python3 -m venv .venv && source .venv/bin/activate"
fi
echo ""

# --- PEP 668 (externally managed) ---
echo -e "${BLUE}PEP 668 / system Python${NC}"
PIP_CHECK=$(mktemp)
# Try dry-run to detect PEP 668 (externally-managed-environment) errors
$PYTHON_CMD -m pip install --dry-run pip &> "$PIP_CHECK" 2>&1 || true
if grep -q "externally-managed-environment\|externally managed" "$PIP_CHECK" 2>/dev/null; then
    check_fail "System Python is externally managed (PEP 668). Use a venv: python3 -m venv .venv && source .venv/bin/activate"
elif grep -q "unknown option.*dry-run\|unrecognized.*dry-run" "$PIP_CHECK" 2>/dev/null; then
    # Older pip version without --dry-run support
    check_warn "Cannot pre-check PEP 668 (pip version may not support --dry-run). Setup will detect it."
elif grep -q "error\|Error\|ERROR" "$PIP_CHECK" 2>/dev/null; then
    # Other error - might be OK, setup will handle it
    check_warn "pip dry-run had issues (may be OK). Run setup: ./scripts/setup-python.sh"
else
    check_pass "pip can install packages (no PEP 668 block detected)"
fi
rm -f "$PIP_CHECK"
echo ""

# --- Project layout ---
echo -e "${BLUE}Project layout${NC}"
[[ -d "$PROJECT_ROOT/core" ]] && check_pass "core/ exists" || check_fail "core/ missing (wrong directory or incomplete clone)"
[[ -f "$PROJECT_ROOT/core/pyproject.toml" ]] && check_pass "core/pyproject.toml exists" || check_fail "core/pyproject.toml missing"
[[ -d "$PROJECT_ROOT/tools" ]] && check_pass "tools/ exists" || check_fail "tools/ missing"
[[ -f "$PROJECT_ROOT/tools/pyproject.toml" ]] && check_pass "tools/pyproject.toml exists" || check_fail "tools/pyproject.toml missing"
if [[ -d "$PROJECT_ROOT/exports" ]]; then
    check_pass "exports/ exists"
else
    check_warn "exports/ missing (will be created by setup-python.sh)"
fi
echo ""

# --- Installed packages (optional) ---
echo -e "${BLUE}Installed packages (optional before setup)${NC}"
if $PYTHON_CMD -c "import framework" 2>/dev/null; then
    check_pass "framework importable"
else
    check_warn "framework not installed yet. Run: ./scripts/setup-python.sh"
fi
if $PYTHON_CMD -c "import aden_tools" 2>/dev/null; then
    check_pass "aden_tools importable"
else
    check_warn "aden_tools not installed yet. Run: ./scripts/setup-python.sh"
fi
OPENAI_VER=$($PYTHON_CMD -c "import openai; print(openai.__version__)" 2>/dev/null || echo "")
if [[ -n "$OPENAI_VER" ]]; then
    if [[ "$OPENAI_VER" =~ ^0\. ]]; then
        check_fail "openai $OPENAI_VER is too old (need >=1.0.0 for litellm). Run: pip install --upgrade \"openai>=1.0.0\""
    else
        check_pass "openai $OPENAI_VER (compatible with litellm)"
    fi
else
    check_warn "openai not installed (setup-python.sh will install/upgrade)"
fi
if $PYTHON_CMD -c "import litellm" 2>/dev/null; then
    check_pass "litellm importable"
else
    check_warn "litellm not installed yet (installed with framework)"
fi
echo ""

# --- Summary ---
echo "=================================================="
echo -e "  Summary: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, ${YELLOW}$WARN warnings${NC}"
echo "=================================================="
echo ""
if [[ "$FAIL" -gt 0 ]]; then
    echo "Fix the failed checks above, then run:"
    echo -e "  ${BLUE}./scripts/setup-python.sh${NC}"
    echo ""
    echo "See ENVIRONMENT_SETUP.md for detailed help."
    echo ""
    exit 1
fi
if [[ "$WARN" -gt 0 ]]; then
    echo "All required checks passed. Warnings are optional improvements."
    echo "To install packages and finish setup:"
    echo -e "  ${BLUE}./scripts/setup-python.sh${NC}"
    echo ""
    exit 0
fi
echo "Environment looks good. To install/update packages:"
echo -e "  ${BLUE}./scripts/setup-python.sh${NC}"
echo ""
exit 0
