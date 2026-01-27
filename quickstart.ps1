<# 
  quickstart.ps1 - Complete setup for Aden Agent Framework skills on Windows

  This script:
  1. Checks Python (3.11+) and pip
  2. Installs Python dependencies (framework, aden_tools, MCP)
  3. Verifies Python imports
  4. Installs Claude Code skills
  5. Verifies MCP configuration
  6. Checks ANTHROPIC_API_KEY availability
  7. Prints a success summary
#>

$ErrorActionPreference = "Stop"

# Colors (ANSI escape codes – supported on modern Windows terminals)
$Red    = "`e[0;31m"
$Green  = "`e[0;32m"
$Yellow = "`e[1;33m"
$Blue   = "`e[0;34m"
$NC     = "`e[0m"   # No Color

# Script directory (equivalent to SCRIPT_DIR in bash)
$ScriptDir = $PSScriptRoot

# Claude skills directory
$ClaudeSkillsDir = Join-Path $env:USERPROFILE ".claude\skills"

Write-Host ""
Write-Host "=================================================="
Write-Host "  Aden Agent Framework - Complete Setup (Windows)"
Write-Host "=================================================="
Write-Host ""

### ============================================================
### Step 1: Check Python Prerequisites
### ============================================================

Write-Host "$Blue Step 1: Checking Python prerequisites...$NC"
Write-Host ""

# Determine Python command (prefer python; rely on PATH/venv)
$PythonCmd = "python"

try {
    $pythonVersion = & $PythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $pythonMajor   = & $PythonCmd -c "import sys; print(sys.version_info.major)"
    $pythonMinor   = & $PythonCmd -c "import sys; print(sys.version_info.minor)"
} catch {
    Write-Host "$Red Error: Python is not installed or not on PATH.$NC"
    Write-Host "Please install Python 3.11+ from `https://python.org` and ensure 'python' is on PATH."
    exit 1
}

Write-Host ("  Detected Python: {0}{1}{2}" -f $Green, $pythonVersion, $NC)

if ([int]$pythonMajor -lt 3 -or (([int]$pythonMajor -eq 3) -and ([int]$pythonMinor -lt 11))) {
    Write-Host ("{0}Error: Python 3.11+ is required (found {1}){2}" -f $Red, $pythonVersion, $NC)
    Write-Host "Please upgrade your Python installation."
    exit 1
}

if ([int]$pythonMinor -lt 11) {
    Write-Host ("{0}  Warning: Python 3.11+ is recommended for best compatibility{1}" -f $Yellow, $NC)
}

Write-Host ("{0}  Python version OK{1}" -f $Green, $NC)
Write-Host ""

# Check for pip
try {
    & $PythonCmd -m pip --version *> $null
} catch {
    Write-Host ("{0}Error: pip is not installed for this Python interpreter.{1}" -f $Red, $NC)
    Write-Host "Please install pip for Python $pythonVersion."
    exit 1
}

Write-Host ("{0}  pip detected{1}" -f $Green, $NC)
Write-Host ""

### ============================================================
### Step 2: Install Python Packages
### ============================================================

Write-Host "$Blue Step 2: Installing Python packages...$NC"
Write-Host ""

Write-Host "  Upgrading pip, setuptools, wheel..."
& $PythonCmd -m pip install --upgrade pip setuptools wheel *> $null
Write-Host ("{0}  Core tools upgraded{1}" -f $Green, $NC)

# Install framework package from core/
Write-Host "  Installing framework package from core/..."
$coreDir = Join-Path $ScriptDir "core"
if (Test-Path (Join-Path $coreDir "pyproject.toml")) {
    Push-Location $coreDir
    & $PythonCmd -m pip install -e . *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host ("{0}  framework package installed{1}" -f $Green, $NC)
    } else {
        Write-Host ("{0}  ⚠ framework installation had issues (may be OK){1}" -f $Yellow, $NC)
    }
    Pop-Location
} else {
    Write-Host ("{0}  ✗ No pyproject.toml in core\{1}" -f $Red, $NC)
    exit 1
}

# Install aden_tools package from tools/
Write-Host "  Installing aden_tools package from tools/..."
$toolsDir = Join-Path $ScriptDir "tools"
if (Test-Path (Join-Path $toolsDir "pyproject.toml")) {
    Push-Location $toolsDir
    & $PythonCmd -m pip install -e . *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host ("{0}  aden_tools package installed{1}" -f $Green, $NC)
    } else {
        Write-Host ("{0}  ✗ aden_tools installation failed{1}" -f $Red, $NC)
        Pop-Location
        exit 1
    }
    Pop-Location
} else {
    Write-Host ("{0}  ✗ No pyproject.toml in tools\{1}" -f $Red, $NC)
    exit 1
}

# Install MCP dependencies
Write-Host "  Installing MCP dependencies..."
& $PythonCmd -m pip install mcp fastmcp *> $null
Write-Host ("{0}  MCP dependencies installed{1}" -f $Green, $NC)

# Fix openai version compatibility
$openaiVersion = & $PythonCmd -c "import importlib.util; spec = importlib.util.find_spec('openai'); print('not_installed' if spec is None else __import__('openai').__version__)" 2>$null
if ($LASTEXITCODE -ne 0 -or -not $openaiVersion) {
    $openaiVersion = "not_installed"
}

if ($openaiVersion -eq "not_installed") {
    Write-Host "  Installing openai package..."
    & $PythonCmd -m pip install "openai>=1.0.0" *> $null
    Write-Host ("{0}  openai installed{1}" -f $Green, $NC)
} elseif ($openaiVersion.StartsWith("0.")) {
    Write-Host "  Upgrading openai to 1.x+ for litellm compatibility..."
    & $PythonCmd -m pip install --upgrade "openai>=1.0.0" *> $null
    Write-Host ("{0}  openai upgraded{1}" -f $Green, $NC)
} else {
    Write-Host ("{0}  openai {1} is compatible{2}" -f $Green, $openaiVersion, $NC)
}

# Install click for CLI
& $PythonCmd -m pip install click *> $null
Write-Host ("{0}  click installed{1}" -f $Green, $NC)

Write-Host ""

### ============================================================
### Step 3: Verify Python Imports
### ============================================================

Write-Host "$Blue Step 3: Verifying Python imports...$NC"
Write-Host ""

$importErrors = 0

& $PythonCmd -c "import framework" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host ("{0}  framework imports OK{1}" -f $Green, $NC)
} else {
    Write-Host ("{0}  ✗ framework import failed{1}" -f $Red, $NC)
    $importErrors++
}

& $PythonCmd -c "import aden_tools" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host ("{0}  aden_tools imports OK{1}" -f $Green, $NC)
} else {
    Write-Host ("{0}  ✗ aden_tools import failed{1}" -f $Red, $NC)
    $importErrors++
}

& $PythonCmd -c "import litellm" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host ("{0}  litellm imports OK{1}" -f $Green, $NC)
} else {
    Write-Host ("{0}  ⚠ litellm import issues (may be OK){1}" -f $Yellow, $NC)
}

& $PythonCmd -c "from framework.mcp import agent_builder_server" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host ("{0}  MCP server module OK{1}" -f $Green, $NC)
} else {
    Write-Host ("{0}  ✗ MCP server module failed{1}" -f $Red, $NC)
    $importErrors++
}

if ($importErrors -gt 0) {
    Write-Host ""
    Write-Host ("{0}Error: {1} import(s) failed. Please check the errors above.{2}" -f $Red, $importErrors, $NC)
    exit 1
}

Write-Host ""

### ============================================================
### Step 4: Install Claude Code Skills
### ============================================================

Write-Host "$Blue Step 4: Installing Claude Code skills...$NC"
Write-Host ""

$sourceSkillsDir = Join-Path $ScriptDir ".claude\skills"
if (-not (Test-Path $sourceSkillsDir)) {
    Write-Host ("{0}Error: Skills directory not found at {1}{2}" -f $Red, $sourceSkillsDir, $NC)
    exit 1
}

if (-not (Test-Path $ClaudeSkillsDir)) {
    Write-Host "  Creating Claude skills directory: $ClaudeSkillsDir"
    New-Item -ItemType Directory -Force -Path $ClaudeSkillsDir | Out-Null
}

function Install-Skill {
    param(
        [string]$SkillName
    )

    $sourceDir = Join-Path $sourceSkillsDir $SkillName
    $targetDir = Join-Path $ClaudeSkillsDir $SkillName

    if (-not (Test-Path $sourceDir)) {
        Write-Host ("{0}  ✗ Skill not found: {1}{2}" -f $Red, $SkillName, $NC)
        return
    }

    if (Test-Path $targetDir) {
        Remove-Item -Recurse -Force $targetDir
    }

    Copy-Item -Recurse -Force -Path $sourceDir -Destination $targetDir
    Write-Host ("{0}  Installed: {1}{2}" -f $Green, $SkillName, $NC)
}

Install-Skill "building-agents-core"
Install-Skill "building-agents-construction"
Install-Skill "building-agents-patterns"
Install-Skill "testing-agent"
Install-Skill "agent-workflow"

Write-Host ""

### ============================================================
### Step 5: Verify MCP Configuration
### ============================================================

Write-Host "$Blue Step 5: Verifying MCP configuration...$NC"
Write-Host ""

$mcpConfigPath = Join-Path $ScriptDir ".mcp.json"
if (Test-Path $mcpConfigPath) {
    Write-Host ("{0}  .mcp.json found at project root{1}" -f $Green, $NC)
    Write-Host ""
    Write-Host "  MCP servers configured:"
    try {
        $configJson = Get-Content $mcpConfigPath -Raw | ConvertFrom-Json
        $servers = $configJson.mcpServers
        if ($servers) {
            foreach ($prop in $servers.PSObject.Properties) {
                Write-Host ("    - {0}" -f $prop.Name)
            }
        } else {
            Write-Host "    (no servers configured)"
        }
    } catch {
        Write-Host "    (could not parse config)"
    }
} else {
    Write-Host ("{0}  ⚠ No .mcp.json found at project root{1}" -f $Yellow, $NC)
    Write-Host "    Claude Code will not have access to MCP tools"
}

Write-Host ""

### ============================================================
### Step 6: Check API Key
### ============================================================

Write-Host "$Blue Step 6: Checking API key...$NC"
Write-Host ""

$apiKeyAvailable = & $PythonCmd -c "from aden_tools.credentials import CredentialManager; c = CredentialManager(); print('yes' if c.is_available('anthropic') else 'no')" 2>$null
if ($LASTEXITCODE -ne 0 -or -not $apiKeyAvailable) {
    $apiKeyAvailable = "no"
}

if ($apiKeyAvailable -eq "yes") {
    Write-Host ("{0}  ANTHROPIC_API_KEY is available via CredentialManager{1}" -f $Green, $NC)
} elseif ($env:ANTHROPIC_API_KEY) {
    Write-Host ("{0}  ANTHROPIC_API_KEY is set in environment{1}" -f $Green, $NC)
} else {
    Write-Host ("{0}  ⚠ ANTHROPIC_API_KEY not found{1}" -f $Yellow, $NC)
    Write-Host ""
    Write-Host "    For real agent testing, you'll need to set your API key:"
    Write-Host "    $Blue`$env:ANTHROPIC_API_KEY = 'your-key-here'$NC"
    Write-Host ""
    Write-Host "    Or add it to your .env file or credential manager."
}

Write-Host ""

### ============================================================
### Step 7: Success Summary
### ============================================================

Write-Host "=================================================="
Write-Host ("{0}  Setup Complete!{1}" -f $Green, $NC)
Write-Host "=================================================="
Write-Host ""
Write-Host "Installed Python packages:"
Write-Host "  • framework (core agent runtime)"
Write-Host "  • aden_tools (tools and MCP servers)"
Write-Host "  • MCP dependencies (mcp, fastmcp)"
Write-Host ""
Write-Host "Installed Claude Code skills:"
Write-Host "  • /building-agents-core         - Fundamental concepts"
Write-Host "  • /building-agents-construction - Step-by-step build guide"
Write-Host "  • /building-agents-patterns     - Best practices"
Write-Host "  • /testing-agent                - Test and validate agents"
Write-Host "  • /agent-workflow               - Complete workflow"
Write-Host ""
Write-Host "Usage:"
Write-Host ("  1. Open Claude Code in this directory:")
Write-Host ("     {0}cd {1}{2}" -f $Blue, $ScriptDir, $NC)
Write-Host ""
Write-Host "  2. Build a new agent:"
Write-Host ("     {0}/building-agents-construction{1}" -f $Blue, $NC)
Write-Host ""
Write-Host "  3. Test an existing agent:"
Write-Host ("     {0}/testing-agent{1}" -f $Blue, $NC)
Write-Host ""
Write-Host "  4. Or use the complete workflow:"
Write-Host ("     {0}/agent-workflow{1}" -f $Blue, $NC)
Write-Host ""
Write-Host "MCP Tools available (when running from this directory):"
Write-Host "  • mcp__agent-builder__create_session"
Write-Host "  • mcp__agent-builder__set_goal"
Write-Host "  • mcp__agent-builder__add_node"
Write-Host "  • mcp__agent-builder__run_tests"
Write-Host "  • ... and more"
Write-Host ""
Write-Host "Documentation:"
Write-Host "  • Skills: $ClaudeSkillsDir\"
Write-Host "  • Examples: $ScriptDir\exports\"
Write-Host ""