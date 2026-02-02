#!/bin/bash
#
# quickstart.sh - Interactive onboarding for Aden Agent Framework
#
# An interactive setup wizard that:
# 1. Installs Python dependencies
# 2. Installs Playwright browser for web scraping
# 3. Helps configure LLM API keys
# 4. Verifies everything works
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Helper function for prompts
prompt_yes_no() {
    local prompt="$1"
    local default="${2:-y}"
    local response

    if [ "$default" = "y" ]; then
        prompt="$prompt [Y/n] "
    else
        prompt="$prompt [y/N] "
    fi

    read -r -p "$prompt" response
    response="${response:-$default}"
    [[ "$response" =~ ^[Yy] ]]
}

# Helper function for choice prompts
prompt_choice() {
    local prompt="$1"
    shift
    local options=("$@")
    local i=1

    echo ""
    echo -e "${BOLD}$prompt${NC}"
    for opt in "${options[@]}"; do
        echo -e "  ${CYAN}$i)${NC} $opt"
        ((i++))
    done
    echo ""

    local choice
    while true; do
        read -r -p "Enter choice (1-${#options[@]}): " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
            return $((choice - 1))
        fi
        echo -e "${RED}Invalid choice. Please enter 1-${#options[@]}${NC}"
    done
}

clear
echo ""
echo -e "${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}"
echo ""
echo -e "${BOLD}          A D E N   H I V E${NC}"
echo ""
echo -e "${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}${DIM}⬡${NC}${YELLOW}⬢${NC}"
echo ""
echo -e "${DIM}     Goal-driven AI agent framework${NC}"
echo ""
echo "This wizard will help you set up everything you need"
echo "to build and run goal-driven AI agents."
echo ""

if ! prompt_yes_no "Ready to begin?"; then
    echo ""
    echo "No problem! Run this script again when you're ready."
    exit 0
fi

echo ""

# ============================================================
# Step 1: Check Python
# ============================================================

echo -e "${YELLOW}⬢${NC} ${BLUE}${BOLD}Step 1: Checking Python...${NC}"
echo ""

# Check for Python
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python is not installed.${NC}"
    echo ""
    echo "Please install Python 3.11+ from https://python.org"
    echo "Then run this script again."
    exit 1
fi

# Use project virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating project virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

PYTHON_CMD="$VENV_DIR/bin/python"
PIP_FLAGS="--break-system-packages"

if [ ! -f "$PYTHON_CMD" ]; then
    echo -e "${RED}Virtual environment Python not found at $PYTHON_CMD${NC}"
    exit 1
fi

# Check Python version (for logging/error messages)
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo -e "${RED}Python 3.11+ is required (found $PYTHON_VERSION)${NC}"
    echo ""
    echo "Please upgrade your Python installation and run this script again."
    exit 1
fi

echo -e "${GREEN}⬢${NC} Python $PYTHON_VERSION"
echo ""

# Check for uv (install automatically if missing)
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}  uv not found. Installing...${NC}"
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}Error: curl is not installed (needed to install uv)${NC}"
        echo "Please install curl or install uv manually from https://astral.sh/uv/"
        exit 1
    fi

    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"

    if ! command -v uv &> /dev/null; then
        echo -e "${RED}Error: uv installation failed${NC}"
        echo "Please install uv manually from https://astral.sh/uv/"
        exit 1
    fi
    echo -e "${GREEN}  ✓ uv installed successfully${NC}"
fi

UV_VERSION=$(uv --version)
echo -e "${GREEN}  ✓ uv detected: $UV_VERSION${NC}"
echo ""

# ============================================================
# Step 2: Install Python Packages
# ============================================================

echo -e "${YELLOW}⬢${NC} ${BLUE}${BOLD}Step 2: Installing packages...${NC}"
echo ""

echo -e "${DIM}This may take a minute...${NC}"
echo ""

# Upgrade pip, setuptools, and wheel
echo -n "  Upgrading pip... "
$PYTHON_CMD -m pip install $PIP_FLAGS --upgrade pip setuptools wheel 
echo -e "${GREEN}ok${NC}"

# Install framework package from core/
cd "$SCRIPT_DIR"

echo -n "  Installing framework... "
$PYTHON_CMD -m pip install $PIP_FLAGS -e core
echo -e "${GREEN}ok${NC}"

echo -n "  Installing aden_tools... "
$PYTHON_CMD -m pip install $PIP_FLAGS -e tools
echo -e "${GREEN}ok${NC}"

# Install MCP dependencies
echo -n "  Installing MCP... "
$PYTHON_CMD -m pip install $PIP_FLAGS mcp fastmcp
echo -e "${GREEN}ok${NC}"

# Fix openai version compatibility
echo -n "  Checking openai... "
$PYTHON_CMD -m pip install $PIP_FLAGS "openai>=1.0.0" 
echo -e "${GREEN}ok${NC}"

echo -n "  Fixing LiteLLM version... "
$PYTHON_CMD -m pip install $PIP_FLAGS "litellm>=1.81.0"
echo -e "${GREEN}ok${NC}"

# Install click for CLI
echo -n "  Installing CLI tools... "
$PYTHON_CMD -m pip install click
echo -e "${GREEN}ok${NC}"

# Install Playwright browser
echo -n "  Installing Playwright... "
$PYTHON_CMD -m pip install playwright
$PYTHON_CMD -m playwright install chromium || {
  echo -e "${YELLOW}Playwright browser install failed. You may need:${NC}"
  echo "sudo apt install -y libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgtk-3-0 libgbm1"
}
echo -e "${GREEN}ok${NC}"

cd "$SCRIPT_DIR"
echo ""
echo -e "${GREEN}⬢${NC} All packages installed"
echo ""

# ============================================================
# Step 3: Configure LLM API Key
# ============================================================

echo -e "${YELLOW}⬢${NC} ${BLUE}${BOLD}Step 3: Configuring LLM provider...${NC}"
echo ""

# ============================================================
# Step 3: Verify Python Imports
# ============================================================

echo -e "${BLUE}Step 3: Verifying Python imports...${NC}"
echo ""

IMPORT_ERRORS=0

for pkg in framework aden_tools litellm playwright; do
    echo -n "  Testing $pkg... "
    if $PYTHON_CMD -c "import $pkg" ; then
        echo -e "${GREEN}ok${NC}"
    else
        echo -e "${RED}failed${NC}"
        IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
    fi
done

if [ $IMPORT_ERRORS -gt 0 ]; then
    echo -e "${RED}Error: $IMPORT_ERRORS imports failed.${NC}"
    exit 1
fi
echo -e "${GREEN}⬢${NC} All imports successful"

# ============================================================
# Step 4: Verify Claude Code Skills
# ============================================================

echo -e "${BLUE}Step 4: Verifying Claude Code skills...${NC}"
echo ""

# Provider data as parallel indexed arrays (Bash 3.2 compatible — no declare -A)
PROVIDER_ENV_VARS=(ANTHROPIC_API_KEY OPENAI_API_KEY GEMINI_API_KEY GOOGLE_API_KEY GROQ_API_KEY CEREBRAS_API_KEY MISTRAL_API_KEY TOGETHER_API_KEY DEEPSEEK_API_KEY)
PROVIDER_DISPLAY_NAMES=("Anthropic (Claude)" "OpenAI (GPT)" "Google Gemini" "Google AI" "Groq" "Cerebras" "Mistral" "Together AI" "DeepSeek")
PROVIDER_ID_LIST=(anthropic openai gemini google groq cerebras mistral together deepseek)

# Default models by provider id (parallel arrays)
MODEL_PROVIDER_IDS=(anthropic openai gemini groq cerebras mistral together_ai deepseek)
MODEL_DEFAULTS=("claude-sonnet-4-5-20250929" "gpt-4o" "gemini-3.0-flash-preview" "moonshotai/kimi-k2-instruct-0905" "zai-glm-4.7" "mistral-large-latest" "meta-llama/Llama-3.3-70B-Instruct-Turbo" "deepseek-chat")

# Helper: get provider display name for an env var
get_provider_name() {
    local env_var="$1"
    local i=0
    while [ $i -lt ${#PROVIDER_ENV_VARS[@]} ]; do
        if [ "${PROVIDER_ENV_VARS[$i]}" = "$env_var" ]; then
            echo "${PROVIDER_DISPLAY_NAMES[$i]}"
            return
        fi
        i=$((i + 1))
    done
}

# Helper: get provider id for an env var
get_provider_id() {
    local env_var="$1"
    local i=0
    while [ $i -lt ${#PROVIDER_ENV_VARS[@]} ]; do
        if [ "${PROVIDER_ENV_VARS[$i]}" = "$env_var" ]; then
            echo "${PROVIDER_ID_LIST[$i]}"
            return
        fi
        i=$((i + 1))
    done
}

# Helper: get default model for a provider id
get_default_model() {
    local provider_id="$1"
    local i=0
    while [ $i -lt ${#MODEL_PROVIDER_IDS[@]} ]; do
        if [ "${MODEL_PROVIDER_IDS[$i]}" = "$provider_id" ]; then
            echo "${MODEL_DEFAULTS[$i]}"
            return
        fi
        i=$((i + 1))
    done
}

# Configuration directory
HIVE_CONFIG_DIR="$HOME/.hive"
HIVE_CONFIG_FILE="$HIVE_CONFIG_DIR/configuration.json"

# Function to save configuration
save_configuration() {
    local provider_id="$1"
    local env_var="$2"
    local model
    model="$(get_default_model "$provider_id")"

    mkdir -p "$HIVE_CONFIG_DIR"

    $PYTHON_CMD -c "
import json
config = {
    'llm': {
        'provider': '$provider_id',
        'model': '$model',
        'api_key_env_var': '$env_var'
    },
    'created_at': '$(date -Iseconds)'
}
with open('$HIVE_CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2)
print(json.dumps(config, indent=2))
" 2>/dev/null
}

# Check for .env files (temporarily disable set -e for robustness on Bash 3.2)
set +e
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env" 2>/dev/null
    set +a
fi

if [ -f "$HOME/.env" ]; then
    set -a
    source "$HOME/.env" 2>/dev/null
    set +a
fi
set -e

# Find all available API keys
FOUND_PROVIDERS=()      # Display names for UI
FOUND_ENV_VARS=()       # Corresponding env var names
SELECTED_PROVIDER_ID="" # Will hold the chosen provider ID
SELECTED_ENV_VAR=""     # Will hold the chosen env var

for env_var in "${PROVIDER_ENV_VARS[@]}"; do
    value="${!env_var}"
    if [ -n "$value" ]; then
        FOUND_PROVIDERS+=("$(get_provider_name "$env_var")")
        FOUND_ENV_VARS+=("$env_var")
    fi
done

if [ ${#FOUND_PROVIDERS[@]} -gt 0 ]; then
    echo "Found API keys:"
    echo ""
    for provider in "${FOUND_PROVIDERS[@]}"; do
        echo -e "  ${GREEN}⬢${NC} $provider"
    done
    echo ""

    if [ ${#FOUND_PROVIDERS[@]} -eq 1 ]; then
        # Only one provider found, use it automatically
        if prompt_yes_no "Use this key?"; then
            SELECTED_ENV_VAR="${FOUND_ENV_VARS[0]}"
            SELECTED_PROVIDER_ID="$(get_provider_id "$SELECTED_ENV_VAR")"

            echo ""
            echo -e "${GREEN}⬢${NC} Using ${FOUND_PROVIDERS[0]}"
        fi
    else
        # Multiple providers found, let user pick one
        echo -e "${BOLD}Select your default LLM provider:${NC}"
        echo ""

        # Build choice menu from found providers
        i=1
        for provider in "${FOUND_PROVIDERS[@]}"; do
            echo -e "  ${CYAN}$i)${NC} $provider"
            ((i++))
        done
        echo ""

        while true; do
            read -r -p "Enter choice (1-${#FOUND_PROVIDERS[@]}): " choice
            if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#FOUND_PROVIDERS[@]}" ]; then
                idx=$((choice - 1))
                SELECTED_ENV_VAR="${FOUND_ENV_VARS[$idx]}"
                SELECTED_PROVIDER_ID="$(get_provider_id "$SELECTED_ENV_VAR")"

                echo ""
                echo -e "${GREEN}⬢${NC} Selected: ${FOUND_PROVIDERS[$idx]}"
                break
            fi
            echo -e "${RED}Invalid choice. Please enter 1-${#FOUND_PROVIDERS[@]}${NC}"
        done
    fi
fi

if [ -z "$SELECTED_PROVIDER_ID" ]; then
    echo "No API keys found. Let's configure one."
    echo ""

    prompt_choice "Select your LLM provider:" \
        "Anthropic (Claude) - Recommended" \
        "OpenAI (GPT)" \
        "Google Gemini - Free tier available" \
        "Groq - Fast, free tier" \
        "Cerebras - Fast, free tier" \
        "Skip for now"
    choice=$?

    case $choice in
        0)
            SELECTED_ENV_VAR="ANTHROPIC_API_KEY"
            SELECTED_PROVIDER_ID="anthropic"
            PROVIDER_NAME="Anthropic"
            SIGNUP_URL="https://console.anthropic.com/settings/keys"
            ;;
        1)
            SELECTED_ENV_VAR="OPENAI_API_KEY"
            SELECTED_PROVIDER_ID="openai"
            PROVIDER_NAME="OpenAI"
            SIGNUP_URL="https://platform.openai.com/api-keys"
            ;;
        2)
            SELECTED_ENV_VAR="GEMINI_API_KEY"
            SELECTED_PROVIDER_ID="gemini"
            PROVIDER_NAME="Google Gemini"
            SIGNUP_URL="https://aistudio.google.com/apikey"
            ;;
        3)
            SELECTED_ENV_VAR="GROQ_API_KEY"
            SELECTED_PROVIDER_ID="groq"
            PROVIDER_NAME="Groq"
            SIGNUP_URL="https://console.groq.com/keys"
            ;;
        4)
            SELECTED_ENV_VAR="CEREBRAS_API_KEY"
            SELECTED_PROVIDER_ID="cerebras"
            PROVIDER_NAME="Cerebras"
            SIGNUP_URL="https://cloud.cerebras.ai/"
            ;;
        5)
            echo ""
            echo -e "${YELLOW}Skipped.${NC} Add your API key later:"
            echo ""
            echo -e "  ${CYAN}echo 'ANTHROPIC_API_KEY=your-key' >> .env${NC}"
            echo ""
            SELECTED_ENV_VAR=""
            SELECTED_PROVIDER_ID=""
            ;;
    esac

    if [ -n "$SELECTED_ENV_VAR" ] && [ -z "${!SELECTED_ENV_VAR}" ]; then
        echo ""
        echo -e "Get your API key from: ${CYAN}$SIGNUP_URL${NC}"
        echo ""
        read -r -p "Paste your $PROVIDER_NAME API key (or press Enter to skip): " API_KEY

        if [ -n "$API_KEY" ]; then
            # Save to .env
            echo "" >> "$SCRIPT_DIR/.env"
            echo "$SELECTED_ENV_VAR=$API_KEY" >> "$SCRIPT_DIR/.env"
            export "$SELECTED_ENV_VAR=$API_KEY"
            echo ""
            echo -e "${GREEN}⬢${NC} API key saved to .env"
        else
            echo ""
            echo -e "${YELLOW}Skipped.${NC} Add your API key to .env when ready."
            SELECTED_ENV_VAR=""
            SELECTED_PROVIDER_ID=""
        fi
    fi
fi

# Save configuration if a provider was selected
if [ -n "$SELECTED_PROVIDER_ID" ]; then
    echo ""
    echo -n "  Saving configuration... "
    save_configuration "$SELECTED_PROVIDER_ID" "$SELECTED_ENV_VAR"  
    echo -e "${GREEN}⬢${NC}"
    echo -e "  ${DIM}~/.hive/configuration.json${NC}"
fi

echo ""

# ============================================================
# Step 4: Verify Setup
# ============================================================

echo -e "${YELLOW}⬢${NC} ${BLUE}${BOLD}Step 4: Verifying installation...${NC}"
echo ""

ERRORS=0

# Test imports
echo -n "  ⬡ framework... "
echo "Using Python: $PYTHON_CMD"
$PYTHON_CMD -c "import sys; print(sys.executable)"

if $PYTHON_CMD -c "import framework" ; then
    echo -e "${GREEN}ok${NC}"
else
    echo -e "${RED}failed${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo -n "  ⬡ aden_tools... "
if $PYTHON_CMD -c "import aden_tools" ; then
    echo -e "${GREEN}ok${NC}"
else
    echo -e "${RED}failed${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo -n "  ⬡ litellm... "
if $PYTHON_CMD -c "import litellm" ; then
    echo -e "${GREEN}ok${NC}"
else
    echo -e "${YELLOW}--${NC}"
fi

echo -n "  ⬡ MCP config... "
if [ -f "$SCRIPT_DIR/.mcp.json" ]; then
    echo -e "${GREEN}ok${NC}"
else
    echo -e "${YELLOW}--${NC}"
fi

echo -n "  ⬡ skills... "
if [ -d "$SCRIPT_DIR/.claude/skills" ]; then
    SKILL_COUNT=$(ls -1d "$SCRIPT_DIR/.claude/skills"/*/ 2>/dev/null | wc -l)
    echo -e "${GREEN}${SKILL_COUNT} found${NC}"
else
    echo -e "${YELLOW}--${NC}"
fi

echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Setup failed with $ERRORS error(s).${NC}"
    echo "Please check the errors above and try again."
    exit 1
fi

# ============================================================
# Success!
# ============================================================

clear
echo ""
echo -e "${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}"
echo ""
echo -e "${GREEN}${BOLD}        ADEN HIVE — READY${NC}"
echo ""
echo -e "${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}${DIM}⬡${NC}${GREEN}⬢${NC}"
echo ""
echo -e "Your environment is configured for building AI agents."
echo ""

# Show configured provider
if [ -n "$SELECTED_PROVIDER_ID" ]; then
    SELECTED_MODEL="$(get_default_model "$SELECTED_PROVIDER_ID")"
    echo -e "${BOLD}Default LLM:${NC}"
    echo -e "  ${CYAN}$SELECTED_PROVIDER_ID${NC} → ${DIM}$SELECTED_MODEL${NC}"
    echo ""
fi

echo -e "${BOLD}Quick Start:${NC}"
echo ""
echo -e "  1. Open Claude Code in this directory:"
echo -e "     ${CYAN}claude${NC}"
echo ""
echo -e "  2. Build a new agent:"
echo -e "     ${CYAN}/agent-workflow${NC}"
echo ""
echo -e "  3. Test an existing agent:"
echo -e "     ${CYAN}/testing-agent${NC}"
echo ""
echo -e "${BOLD}Skills:${NC}"
if [ -d "$SCRIPT_DIR/.claude/skills" ]; then
    for skill_dir in "$SCRIPT_DIR/.claude/skills"/*/; do
        skill_name=$(basename "$skill_dir")
        echo -e "  ⬡ ${CYAN}/$skill_name${NC}"
    done
fi
echo ""
echo -e "${BOLD}Examples:${NC} ${CYAN}exports/${NC}"
echo ""
echo -e "${DIM}Run ./quickstart.sh again to reconfigure.${NC}"
echo ""
