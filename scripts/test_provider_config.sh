#!/bin/bash
#
# Test script for centralized provider configuration
# Tests both Bash 4+ (associative arrays) and simulates Bash 3.2 (indexed arrays)
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

test_case() {
    local description="$1"
    local expected="$2"
    local actual="$3"
    
    if [ "$expected" = "$actual" ]; then
        echo -e "${GREEN}✓${NC} $description"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} $description"
        echo "  Expected: '$expected'"
        echo "  Actual:   '$actual'"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

echo "=========================================="
echo "Testing Provider Configuration (Bash 4+)"
echo "=========================================="
echo ""

# Source the config section (Bash 4+ mode)
export USE_ASSOC_ARRAYS=true

# Provider config
PROVIDER_CONFIG=(
    "ANTHROPIC_API_KEY|anthropic|Anthropic (Claude)|https://console.anthropic.com/settings/keys"
    "OPENAI_API_KEY|openai|OpenAI (GPT)|https://platform.openai.com/api-keys"
    "GEMINI_API_KEY|gemini|Google Gemini|https://aistudio.google.com/apikey"
    "GOOGLE_API_KEY|google|Google AI|https://aistudio.google.com/apikey"
    "GROQ_API_KEY|groq|Groq|https://console.groq.com/keys"
    "CEREBRAS_API_KEY|cerebras|Cerebras|https://cloud.cerebras.ai/"
    "MISTRAL_API_KEY|mistral|Mistral|https://console.mistral.ai/"
    "TOGETHER_API_KEY|together|Together AI|https://docs.together.ai/"
    "DEEPSEEK_API_KEY|deepseek|DeepSeek|https://platform.deepseek.com/"
)

declare -A PROVIDER_DEFAULT_MODEL
PROVIDER_DEFAULT_MODEL=(
    ["anthropic"]="claude-haiku-4-5"
    ["openai"]="gpt-5-mini"
    ["gemini"]="gemini-3-flash-preview"
    ["groq"]="moonshotai/kimi-k2-instruct-0905"
    ["cerebras"]="zai-glm-4.7"
    ["mistral"]="mistral-large-latest"
    ["together"]="meta-llama/Llama-3.3-70B-Instruct-Turbo"
    ["deepseek"]="deepseek-chat"
)

MODEL_CHOICES_CONFIG=(
    "anthropic|claude-opus-4-6|Opus 4.6 - Most capable (recommended)|8192"
    "anthropic|claude-sonnet-4-5-20250929|Sonnet 4.5 - Best balance|8192"
    "anthropic|claude-sonnet-4-20250514|Sonnet 4 - Fast + capable|8192"
    "anthropic|claude-haiku-4-5-20251001|Haiku 4.5 - Fast + cheap|8192"
    "openai|gpt-5.2|GPT-5.2 - Most capable (recommended)|16384"
    "openai|gpt-5-mini|GPT-5 Mini - Fast + cheap|16384"
    "openai|gpt-5-nano|GPT-5 Nano - Fastest|16384"
    "gemini|gemini-3-flash-preview|Gemini 3 Flash - Fast (recommended)|8192"
    "gemini|gemini-3-pro-preview|Gemini 3 Pro - Best quality|8192"
    "groq|moonshotai/kimi-k2-instruct-0905|Kimi K2 - Best quality (recommended)|8192"
    "groq|openai/gpt-oss-120b|GPT-OSS 120B - Fast reasoning|8192"
    "cerebras|zai-glm-4.7|ZAI-GLM 4.7 - Best quality (recommended)|8192"
    "cerebras|qwen3-235b-a22b-instruct-2507|Qwen3 235B - Frontier reasoning|8192"
)

declare -A PROVIDER_NAMES
declare -A PROVIDER_IDS
declare -A PROVIDER_SIGNUP_URLS

for entry in "${PROVIDER_CONFIG[@]}"; do
    IFS='|' read -r env_var provider_id display_name signup_url <<< "$entry"
    PROVIDER_NAMES["$env_var"]="$display_name"
    PROVIDER_IDS["$env_var"]="$provider_id"
    PROVIDER_SIGNUP_URLS["$provider_id"]="$signup_url"
done

declare -A MODEL_CHOICES_ID
declare -A MODEL_CHOICES_LABEL
declare -A MODEL_CHOICES_MAXTOKENS
declare -A MODEL_CHOICES_COUNT

for entry in "${MODEL_CHOICES_CONFIG[@]}"; do
    IFS='|' read -r provider_id model_id model_label max_tokens <<< "$entry"
    count="${MODEL_CHOICES_COUNT[$provider_id]:-0}"
    MODEL_CHOICES_ID["${provider_id}:${count}"]="$model_id"
    MODEL_CHOICES_LABEL["${provider_id}:${count}"]="$model_label"
    MODEL_CHOICES_MAXTOKENS["${provider_id}:${count}"]="$max_tokens"
    MODEL_CHOICES_COUNT["$provider_id"]=$((count + 1))
done

get_provider_name() {
    echo "${PROVIDER_NAMES[$1]:-}"
}

get_provider_id() {
    echo "${PROVIDER_IDS[$1]:-}"
}

get_provider_signup_url() {
    echo "${PROVIDER_SIGNUP_URLS[$1]:-}"
}

get_default_model() {
    echo "${PROVIDER_DEFAULT_MODEL[$1]:-}"
}

get_model_choice_count() {
    echo "${MODEL_CHOICES_COUNT[$1]:-0}"
}

get_model_choice_id() {
    local provider_id="$1"
    local idx="$2"
    echo "${MODEL_CHOICES_ID[${provider_id}:${idx}]:-}"
}

get_model_choice_label() {
    local provider_id="$1"
    local idx="$2"
    echo "${MODEL_CHOICES_LABEL[${provider_id}:${idx}]:-}"
}

get_model_choice_maxtokens() {
    local provider_id="$1"
    local idx="$2"
    echo "${MODEL_CHOICES_MAXTOKENS[${provider_id}:${idx}]:-8192}"
}

# === Run Tests ===

echo "--- Provider Name Lookup ---"
test_case "ANTHROPIC_API_KEY" "Anthropic (Claude)" "$(get_provider_name "ANTHROPIC_API_KEY")"
test_case "OPENAI_API_KEY" "OpenAI (GPT)" "$(get_provider_name "OPENAI_API_KEY")"
test_case "MISTRAL_API_KEY" "Mistral" "$(get_provider_name "MISTRAL_API_KEY")"
test_case "DEEPSEEK_API_KEY" "DeepSeek" "$(get_provider_name "DEEPSEEK_API_KEY")"

echo ""
echo "--- Provider ID Lookup ---"
test_case "ANTHROPIC_API_KEY -> anthropic" "anthropic" "$(get_provider_id "ANTHROPIC_API_KEY")"
test_case "OPENAI_API_KEY -> openai" "openai" "$(get_provider_id "OPENAI_API_KEY")"
test_case "MISTRAL_API_KEY -> mistral" "mistral" "$(get_provider_id "MISTRAL_API_KEY")"
test_case "GROQ_API_KEY -> groq" "groq" "$(get_provider_id "GROQ_API_KEY")"

echo ""
echo "--- Signup URL Lookup ---"
test_case "anthropic URL" "https://console.anthropic.com/settings/keys" "$(get_provider_signup_url "anthropic")"
test_case "openai URL" "https://platform.openai.com/api-keys" "$(get_provider_signup_url "openai")"
test_case "gemini URL" "https://aistudio.google.com/apikey" "$(get_provider_signup_url "gemini")"

echo ""
echo "--- Default Model Lookup ---"
test_case "anthropic default" "claude-haiku-4-5" "$(get_default_model "anthropic")"
test_case "openai default" "gpt-5-mini" "$(get_default_model "openai")"
test_case "gemini default" "gemini-3-flash-preview" "$(get_default_model "gemini")"
test_case "mistral default" "mistral-large-latest" "$(get_default_model "mistral")"
test_case "deepseek default" "deepseek-chat" "$(get_default_model "deepseek")"

echo ""
echo "--- Model Choice Count ---"
test_case "anthropic count" "4" "$(get_model_choice_count "anthropic")"
test_case "openai count" "3" "$(get_model_choice_count "openai")"
test_case "gemini count" "2" "$(get_model_choice_count "gemini")"
test_case "groq count" "2" "$(get_model_choice_count "groq")"
test_case "cerebras count" "2" "$(get_model_choice_count "cerebras")"
test_case "mistral count (no curated)" "0" "$(get_model_choice_count "mistral")"

echo ""
echo "--- Model Choice ID ---"
test_case "anthropic:0" "claude-opus-4-6" "$(get_model_choice_id "anthropic" 0)"
test_case "anthropic:1" "claude-sonnet-4-5-20250929" "$(get_model_choice_id "anthropic" 1)"
test_case "anthropic:3" "claude-haiku-4-5-20251001" "$(get_model_choice_id "anthropic" 3)"
test_case "openai:0" "gpt-5.2" "$(get_model_choice_id "openai" 0)"
test_case "openai:2" "gpt-5-nano" "$(get_model_choice_id "openai" 2)"

echo ""
echo "--- Model Choice Label ---"
test_case "anthropic:0 label" "Opus 4.6 - Most capable (recommended)" "$(get_model_choice_label "anthropic" 0)"
test_case "openai:1 label" "GPT-5 Mini - Fast + cheap" "$(get_model_choice_label "openai" 1)"
test_case "gemini:0 label" "Gemini 3 Flash - Fast (recommended)" "$(get_model_choice_label "gemini" 0)"

echo ""
echo "--- Model Choice Max Tokens ---"
test_case "anthropic:0 max_tokens" "8192" "$(get_model_choice_maxtokens "anthropic" 0)"
test_case "openai:0 max_tokens" "16384" "$(get_model_choice_maxtokens "openai" 0)"
test_case "openai:2 max_tokens" "16384" "$(get_model_choice_maxtokens "openai" 2)"
test_case "gemini:1 max_tokens" "8192" "$(get_model_choice_maxtokens "gemini" 1)"
test_case "unknown provider fallback" "8192" "$(get_model_choice_maxtokens "unknown" 0)"

echo ""
echo "=========================================="
echo "Testing Provider Configuration (Bash 3.2)"
echo "=========================================="
echo ""

# Unset all previous arrays
unset PROVIDER_NAMES PROVIDER_IDS PROVIDER_SIGNUP_URLS
unset MODEL_CHOICES_ID MODEL_CHOICES_LABEL MODEL_CHOICES_MAXTOKENS MODEL_CHOICES_COUNT
unset PROVIDER_DEFAULT_MODEL

# Bash 3.2 mode
export USE_ASSOC_ARRAYS=false

# Provider config (same as above)
PROVIDER_CONFIG=(
    "ANTHROPIC_API_KEY|anthropic|Anthropic (Claude)|https://console.anthropic.com/settings/keys"
    "OPENAI_API_KEY|openai|OpenAI (GPT)|https://platform.openai.com/api-keys"
    "GEMINI_API_KEY|gemini|Google Gemini|https://aistudio.google.com/apikey"
    "GOOGLE_API_KEY|google|Google AI|https://aistudio.google.com/apikey"
    "GROQ_API_KEY|groq|Groq|https://console.groq.com/keys"
    "CEREBRAS_API_KEY|cerebras|Cerebras|https://cloud.cerebras.ai/"
    "MISTRAL_API_KEY|mistral|Mistral|https://console.mistral.ai/"
    "TOGETHER_API_KEY|together|Together AI|https://docs.together.ai/"
    "DEEPSEEK_API_KEY|deepseek|DeepSeek|https://platform.deepseek.com/"
)

PROVIDER_DEFAULT_MODEL_PROVIDER_IDS=(anthropic openai gemini groq cerebras mistral together deepseek)
PROVIDER_DEFAULT_MODEL_VALUES=("claude-haiku-4-5" "gpt-5-mini" "gemini-3-flash-preview" "moonshotai/kimi-k2-instruct-0905" "zai-glm-4.7" "mistral-large-latest" "meta-llama/Llama-3.3-70B-Instruct-Turbo" "deepseek-chat")

MODEL_CHOICES_CONFIG=(
    "anthropic|claude-opus-4-6|Opus 4.6 - Most capable (recommended)|8192"
    "anthropic|claude-sonnet-4-5-20250929|Sonnet 4.5 - Best balance|8192"
    "anthropic|claude-sonnet-4-20250514|Sonnet 4 - Fast + capable|8192"
    "anthropic|claude-haiku-4-5-20251001|Haiku 4.5 - Fast + cheap|8192"
    "openai|gpt-5.2|GPT-5.2 - Most capable (recommended)|16384"
    "openai|gpt-5-mini|GPT-5 Mini - Fast + cheap|16384"
    "openai|gpt-5-nano|GPT-5 Nano - Fastest|16384"
    "gemini|gemini-3-flash-preview|Gemini 3 Flash - Fast (recommended)|8192"
    "gemini|gemini-3-pro-preview|Gemini 3 Pro - Best quality|8192"
    "groq|moonshotai/kimi-k2-instruct-0905|Kimi K2 - Best quality (recommended)|8192"
    "groq|openai/gpt-oss-120b|GPT-OSS 120B - Fast reasoning|8192"
    "cerebras|zai-glm-4.7|ZAI-GLM 4.7 - Best quality (recommended)|8192"
    "cerebras|qwen3-235b-a22b-instruct-2507|Qwen3 235B - Frontier reasoning|8192"
)

PROVIDER_ENV_VARS=()
PROVIDER_DISPLAY_NAMES=()
PROVIDER_ID_LIST=()
PROVIDER_SIGNUP_URLS_LIST=()

for entry in "${PROVIDER_CONFIG[@]}"; do
    IFS='|' read -r env_var provider_id display_name signup_url <<< "$entry"
    PROVIDER_ENV_VARS+=("$env_var")
    PROVIDER_DISPLAY_NAMES+=("$display_name")
    PROVIDER_ID_LIST+=("$provider_id")
    PROVIDER_SIGNUP_URLS_LIST+=("$signup_url")
done

MODEL_CHOICES_PROVIDERS=()
MODEL_CHOICES_IDS=()
MODEL_CHOICES_LABELS=()
MODEL_CHOICES_MAXTOKENS_LIST=()

for entry in "${MODEL_CHOICES_CONFIG[@]}"; do
    IFS='|' read -r provider_id model_id model_label max_tokens <<< "$entry"
    MODEL_CHOICES_PROVIDERS+=("$provider_id")
    MODEL_CHOICES_IDS+=("$model_id")
    MODEL_CHOICES_LABELS+=("$model_label")
    MODEL_CHOICES_MAXTOKENS_LIST+=("$max_tokens")
done

MODEL_CHOICES_COUNT_ANTHROPIC=0
MODEL_CHOICES_COUNT_OPENAI=0
MODEL_CHOICES_COUNT_GEMINI=0
MODEL_CHOICES_COUNT_GROQ=0
MODEL_CHOICES_COUNT_CEREBRAS=0

for entry in "${MODEL_CHOICES_CONFIG[@]}"; do
    case "$entry" in
        anthropic*) MODEL_CHOICES_COUNT_ANTHROPIC=$((MODEL_CHOICES_COUNT_ANTHROPIC + 1)) ;;
        openai*)   MODEL_CHOICES_COUNT_OPENAI=$((MODEL_CHOICES_COUNT_OPENAI + 1)) ;;
        gemini*)   MODEL_CHOICES_COUNT_GEMINI=$((MODEL_CHOICES_COUNT_GEMINI + 1)) ;;
        groq*)     MODEL_CHOICES_COUNT_GROQ=$((MODEL_CHOICES_COUNT_GROQ + 1)) ;;
        cerebras*) MODEL_CHOICES_COUNT_CEREBRAS=$((MODEL_CHOICES_COUNT_CEREBRAS + 1)) ;;
    esac
done

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

get_provider_signup_url() {
    local provider_id="$1"
    local i=0
    while [ $i -lt ${#PROVIDER_ID_LIST[@]} ]; do
        if [ "${PROVIDER_ID_LIST[$i]}" = "$provider_id" ]; then
            echo "${PROVIDER_SIGNUP_URLS_LIST[$i]}"
            return
        fi
        i=$((i + 1))
    done
}

get_default_model() {
    local provider_id="$1"
    local i=0
    while [ $i -lt ${#PROVIDER_DEFAULT_MODEL_PROVIDER_IDS[@]} ]; do
        if [ "${PROVIDER_DEFAULT_MODEL_PROVIDER_IDS[$i]}" = "$provider_id" ]; then
            echo "${PROVIDER_DEFAULT_MODEL_VALUES[$i]}"
            return
        fi
        i=$((i + 1))
    done
}

get_model_choice_count() {
    local provider_id="$1"
    case "$provider_id" in
        anthropic) echo "$MODEL_CHOICES_COUNT_ANTHROPIC" ;;
        openai)    echo "$MODEL_CHOICES_COUNT_OPENAI" ;;
        gemini)    echo "$MODEL_CHOICES_COUNT_GEMINI" ;;
        groq)      echo "$MODEL_CHOICES_COUNT_GROQ" ;;
        cerebras)  echo "$MODEL_CHOICES_COUNT_CEREBRAS" ;;
        *)         echo "0" ;;
    esac
}

get_model_choice_id() {
    local provider_id="$1"
    local idx="$2"
    local count=0
    local i=0
    while [ $i -lt ${#MODEL_CHOICES_PROVIDERS[@]} ]; do
        if [ "${MODEL_CHOICES_PROVIDERS[$i]}" = "$provider_id" ]; then
            if [ $count -eq "$idx" ]; then
                echo "${MODEL_CHOICES_IDS[$i]}"
                return
            fi
            count=$((count + 1))
        fi
        i=$((i + 1))
    done
}

get_model_choice_label() {
    local provider_id="$1"
    local idx="$2"
    local count=0
    local i=0
    while [ $i -lt ${#MODEL_CHOICES_PROVIDERS[@]} ]; do
        if [ "${MODEL_CHOICES_PROVIDERS[$i]}" = "$provider_id" ]; then
            if [ $count -eq "$idx" ]; then
                echo "${MODEL_CHOICES_LABELS[$i]}"
                return
            fi
            count=$((count + 1))
        fi
        i=$((i + 1))
    done
}

get_model_choice_maxtokens() {
    local provider_id="$1"
    local idx="$2"
    local count=0
    local i=0
    while [ $i -lt ${#MODEL_CHOICES_PROVIDERS[@]} ]; do
        if [ "${MODEL_CHOICES_PROVIDERS[$i]}" = "$provider_id" ]; then
            if [ $count -eq "$idx" ]; then
                echo "${MODEL_CHOICES_MAXTOKENS_LIST[$i]}"
                return
            fi
            count=$((count + 1))
        fi
        i=$((i + 1))
    done
    echo "8192"
}

# === Run Tests ===

echo "--- Provider Name Lookup ---"
test_case "ANTHROPIC_API_KEY" "Anthropic (Claude)" "$(get_provider_name "ANTHROPIC_API_KEY")"
test_case "OPENAI_API_KEY" "OpenAI (GPT)" "$(get_provider_name "OPENAI_API_KEY")"
test_case "MISTRAL_API_KEY" "Mistral" "$(get_provider_name "MISTRAL_API_KEY")"
test_case "DEEPSEEK_API_KEY" "DeepSeek" "$(get_provider_name "DEEPSEEK_API_KEY")"

echo ""
echo "--- Provider ID Lookup ---"
test_case "ANTHROPIC_API_KEY -> anthropic" "anthropic" "$(get_provider_id "ANTHROPIC_API_KEY")"
test_case "OPENAI_API_KEY -> openai" "openai" "$(get_provider_id "OPENAI_API_KEY")"
test_case "MISTRAL_API_KEY -> mistral" "mistral" "$(get_provider_id "MISTRAL_API_KEY")"
test_case "GROQ_API_KEY -> groq" "groq" "$(get_provider_id "GROQ_API_KEY")"

echo ""
echo "--- Signup URL Lookup ---"
test_case "anthropic URL" "https://console.anthropic.com/settings/keys" "$(get_provider_signup_url "anthropic")"
test_case "openai URL" "https://platform.openai.com/api-keys" "$(get_provider_signup_url "openai")"
test_case "gemini URL" "https://aistudio.google.com/apikey" "$(get_provider_signup_url "gemini")"

echo ""
echo "--- Default Model Lookup ---"
test_case "anthropic default" "claude-haiku-4-5" "$(get_default_model "anthropic")"
test_case "openai default" "gpt-5-mini" "$(get_default_model "openai")"
test_case "gemini default" "gemini-3-flash-preview" "$(get_default_model "gemini")"
test_case "mistral default" "mistral-large-latest" "$(get_default_model "mistral")"
test_case "deepseek default" "deepseek-chat" "$(get_default_model "deepseek")"

echo ""
echo "--- Model Choice Count ---"
test_case "anthropic count" "4" "$(get_model_choice_count "anthropic")"
test_case "openai count" "3" "$(get_model_choice_count "openai")"
test_case "gemini count" "2" "$(get_model_choice_count "gemini")"
test_case "groq count" "2" "$(get_model_choice_count "groq")"
test_case "cerebras count" "2" "$(get_model_choice_count "cerebras")"
test_case "mistral count (no curated)" "0" "$(get_model_choice_count "mistral")"

echo ""
echo "--- Model Choice ID ---"
test_case "anthropic:0" "claude-opus-4-6" "$(get_model_choice_id "anthropic" 0)"
test_case "anthropic:1" "claude-sonnet-4-5-20250929" "$(get_model_choice_id "anthropic" 1)"
test_case "anthropic:3" "claude-haiku-4-5-20251001" "$(get_model_choice_id "anthropic" 3)"
test_case "openai:0" "gpt-5.2" "$(get_model_choice_id "openai" 0)"
test_case "openai:2" "gpt-5-nano" "$(get_model_choice_id "openai" 2)"

echo ""
echo "--- Model Choice Label ---"
test_case "anthropic:0 label" "Opus 4.6 - Most capable (recommended)" "$(get_model_choice_label "anthropic" 0)"
test_case "openai:1 label" "GPT-5 Mini - Fast + cheap" "$(get_model_choice_label "openai" 1)"
test_case "gemini:0 label" "Gemini 3 Flash - Fast (recommended)" "$(get_model_choice_label "gemini" 0)"

echo ""
echo "--- Model Choice Max Tokens ---"
test_case "anthropic:0 max_tokens" "8192" "$(get_model_choice_maxtokens "anthropic" 0)"
test_case "openai:0 max_tokens" "16384" "$(get_model_choice_maxtokens "openai" 0)"
test_case "openai:2 max_tokens" "16384" "$(get_model_choice_maxtokens "openai" 2)"
test_case "gemini:1 max_tokens" "8192" "$(get_model_choice_maxtokens "gemini" 1)"
test_case "unknown provider fallback" "8192" "$(get_model_choice_maxtokens "unknown" 0)"

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
