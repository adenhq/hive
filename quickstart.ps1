<#
.SYNOPSIS
    Aden Agent Framework - Complete Setup (Windows)
.DESCRIPTION
    Installs Python dependencies and Claude Code skills.
    Replicates quickstart.sh logic for Windows/PowerShell.
#>

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host ""
Write-Host "=================================================="
Write-Host "  Aden Agent Framework - Complete Setup"
Write-Host "=================================================="
Write-Host ""

# Get script directories
$ScriptDir = $PSScriptRoot
# $ScriptDir in PS is usually defining where the script is, preventing issues if run from elsewhere
# quickstart.ps1 is in root, but user asked to mirror quickstart.sh which is in root too.
# However, if quickstart.ps1 is placed in root (e:\hive), then $PSScriptRoot is e:\hive.
# quickstart.sh logic uses SCRIPT_DIR as project root.
$ProjectRoot = $PSScriptRoot

$ClaudeSkillsDir = Join-Path $HOME ".claude\skills"

# ============================================================
# Step 1: Check Python Prerequisites
# ============================================================
Write-Host -ForegroundColor Cyan "Step 1: Checking Python prerequisites..."
Write-Host ""

try {
    $null = Get-Command "python" -ErrorAction Stop
} catch {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.11+."
    exit 1
}

$PyVerInfo = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$Major,$Minor = $PyVerInfo -split "\."
Write-Host "  Detected Python: $PyVerInfo"

if ([int]$Major -lt 3 -or ([int]$Major -eq 3 -and [int]$Minor -lt 11)) {
    Write-Error "Error: Python 3.11+ is required (found $PyVerInfo)"
    exit 1
}
Write-Host -ForegroundColor Green "  OK - Python version OK"
Write-Host ""

try {
    python -m pip --version | Out-Null
} catch {
    Write-Error "Error: pip is not installed"
    exit 1
}
Write-Host -ForegroundColor Green "  OK - pip detected"
Write-Host ""

# ============================================================
# Step 2: Install Python Packages
# ============================================================
Write-Host -ForegroundColor Cyan "Step 2: Installing Python packages..."
Write-Host ""

Write-Host "  Upgrading pip, setuptools, wheel..."
python -m pip install --upgrade pip setuptools wheel | Out-Null
Write-Host -ForegroundColor Green "  OK - Core tools upgraded"

Write-Host "  Installing framework package from core/..."
if (Test-Path "$ProjectRoot\core\pyproject.toml") {
    Push-Location "$ProjectRoot\core"
    python -m pip install -e . | Out-Null
    Pop-Location
    Write-Host -ForegroundColor Green "  OK - framework package installed"
} else {
    Write-Warning "  WARN - No pyproject.toml in core/"
}

Write-Host "  Installing aden_tools package from tools/..."
if (Test-Path "$ProjectRoot\tools\pyproject.toml") {
    Push-Location "$ProjectRoot\tools"
    python -m pip install -e . | Out-Null
    Pop-Location
    Write-Host -ForegroundColor Green "  OK - aden_tools package installed"
} else {
    Write-Error "No pyproject.toml in tools/"
    exit 1
}

Write-Host "  Installing MCP dependencies..."
python -m pip install mcp fastmcp | Out-Null
Write-Host -ForegroundColor Green "  OK - MCP dependencies installed"

# Install click separately to match bash script structure
python -m pip install click | Out-Null
Write-Host -ForegroundColor Green "  OK - click installed"

# Fix openai compatibility
$OpenAIInstalled = python -c "import openai; print('yes')" 2>$null
if ($OpenAIInstalled -ne 'yes') {
    Write-Host "  Installing openai..."
    python -m pip install "openai>=1.0.0" | Out-Null
    Write-Host -ForegroundColor Green "  OK - openai installed"
} else {
    $OpenAIVer = python -c "import openai; print(openai.__version__)"
    if ($OpenAIVer.StartsWith("0.")) {
        Write-Host "  Upgrading openai to 1.x+..."
        python -m pip install --upgrade "openai>=1.0.0" | Out-Null
        Write-Host -ForegroundColor Green "  OK - openai upgraded"
    } else {
        Write-Host -ForegroundColor Green "  OK - openai $OpenAIVer is compatible"
    }
}
Write-Host ""

# ============================================================
# Step 3: Verify Python Imports
# ============================================================
Write-Host -ForegroundColor Cyan "Step 3: Verifying Python imports..."
Write-Host ""
$ImportErrors = 0

# Temporarily set PYTHONPATH for verification
$OldPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = "$ProjectRoot\core;$ProjectRoot\exports;$env:PYTHONPATH"

try {
    # Using direct execution with redirection which is more reliable for python -c in PowerShell
    python -c "import framework" 2> "framework_err.txt"
    if ($LASTEXITCODE -eq 0) { Write-Host -ForegroundColor Green "  OK - framework imports OK" } 
    else { 
        Write-Host -ForegroundColor Red "  FAIL - framework import failed"
        if (Test-Path "framework_err.txt") { Get-Content "framework_err.txt" | ForEach-Object { Write-Host -ForegroundColor Red "    $_" } }
        $ImportErrors++ 
    }
    Remove-Item "framework_err.txt" -ErrorAction SilentlyContinue

    python -c "import aden_tools" 2> "tools_err.txt"
    if ($LASTEXITCODE -eq 0) { Write-Host -ForegroundColor Green "  OK - aden_tools imports OK" } 
    else { 
        Write-Host -ForegroundColor Red "  FAIL - aden_tools import failed"
        if (Test-Path "tools_err.txt") { Get-Content "tools_err.txt" | ForEach-Object { Write-Host -ForegroundColor Red "    $_" } }
        $ImportErrors++ 
    }
    Remove-Item "tools_err.txt" -ErrorAction SilentlyContinue

    if (python -c "import litellm" 2>$null) { Write-Host -ForegroundColor Green "  OK - litellm imports OK" } else { Write-Warning "  WARN - litellm import issues" }
    
    python -c "from framework.mcp import agent_builder_server" 2> "mcp_err.txt"
    if ($LASTEXITCODE -eq 0) { Write-Host -ForegroundColor Green "  OK - MCP server module OK" } 
    else { 
        Write-Host -ForegroundColor Red "  FAIL - MCP server module failed"
        if (Test-Path "mcp_err.txt") { Get-Content "mcp_err.txt" | ForEach-Object { Write-Host -ForegroundColor Red "    $_" } }
        $ImportErrors++ 
    }
    Remove-Item "mcp_err.txt" -ErrorAction SilentlyContinue

} finally {
    $env:PYTHONPATH = $OldPythonPath
}

if ($ImportErrors -gt 0) {
    Write-Error "Error: $ImportErrors import(s) failed."
    exit 1
}
Write-Host ""

# ============================================================
# Step 4: Install Claude Code Skills
# ============================================================
Write-Host -ForegroundColor Cyan "Step 4: Installing Claude Code skills..."
Write-Host ""

if (-not (Test-Path "$ProjectRoot\.claude\skills")) {
    Write-Error "Error: Skills directory not found at .claude\skills"
    exit 1
}

if (-not (Test-Path $ClaudeSkillsDir)) {
    New-Item -ItemType Directory -Force -Path $ClaudeSkillsDir | Out-Null
    Write-Host "  Creating Claude skills directory: $ClaudeSkillsDir"
}

function Install-Skill ($SkillName) {
    $SourceDir = Join-Path "$ProjectRoot\.claude\skills" $SkillName
    $TargetDir = Join-Path $ClaudeSkillsDir $SkillName

    if (-not (Test-Path $SourceDir)) {
        Write-Host -ForegroundColor Red "  FAIL - Skill not found: $SkillName"
        return
    }
    if (Test-Path $TargetDir) { Remove-Item -Recurse -Force $TargetDir }
    Copy-Item -Recurse -Force $SourceDir $TargetDir
    Write-Host -ForegroundColor Green "  OK - Installed: $SkillName"
}

$Skills = @("building-agents-core", "building-agents-construction", "building-agents-patterns", "testing-agent", "agent-workflow")
foreach ($Skill in $Skills) { Install-Skill $Skill }
Write-Host ""

# ============================================================
# Step 5: Verify MCP Configuration
# ============================================================
Write-Host -ForegroundColor Cyan "Step 5: Verifying MCP configuration..."
Write-Host ""

if (Test-Path "$ProjectRoot\.mcp.json") {
    Write-Host -ForegroundColor Green "  OK - .mcp.json found"
    Write-Host "  MCP servers configured:"
    python -c "import json; print('\n'.join([f'    - {name}' for name in json.load(open('.mcp.json')).get('mcpServers', {})]))"
} else {
    Write-Warning "  WARN - No .mcp.json found. Claude Code will not have access to MCP tools."
}
Write-Host ""

# ============================================================
# Step 6: Check API Key
# ============================================================
Write-Host -ForegroundColor Cyan "Step 6: Checking API key..."
Write-Host ""

$ApiKeyAvailable = python -c "from aden_tools.credentials import CredentialManager; print('yes' if CredentialManager().is_available('anthropic') else 'no')" 2>$null
if ($ApiKeyAvailable -eq 'yes') {
    Write-Host -ForegroundColor Green "  OK - ANTHROPIC_API_KEY is available (CredentialManager)"
} elseif ($env:ANTHROPIC_API_KEY) {
    Write-Host -ForegroundColor Green "  OK - ANTHROPIC_API_KEY is set in environment"
} else {
    Write-Warning "  WARN - ANTHROPIC_API_KEY not found"
    Write-Host "    Set it via: `$env:ANTHROPIC_API_KEY='your-key'"
}
Write-Host ""

# ============================================================
# Step 7: Success Summary
# ============================================================
Write-Host "=================================================="
Write-Host -ForegroundColor Green "  Setup Complete!"
Write-Host "=================================================="
Write-Host ""
Write-Host "Installed Python packages:"
Write-Host "  • framework (core agent runtime)"
Write-Host "  • aden_tools (tools and MCP servers)"
Write-Host "  • MCP dependencies"
Write-Host ""
Write-Host "Installed Claude Code skills:"
Write-Host "  • /building-agents-core"
Write-Host "  • /building-agents-construction"
Write-Host "  • /building-agents-patterns"
Write-Host "  • /testing-agent"
Write-Host "  • /agent-workflow"
Write-Host ""
Write-Host "Usage:"
Write-Host "  1. Open Claude Code in this directory:"
Write-Host -ForegroundColor Cyan "     cd ""$ProjectRoot""; claude"
Write-Host ""
Write-Host "  2. Build a new agent:"
Write-Host -ForegroundColor Cyan "     /building-agents-construction"
Write-Host ""
Write-Host "  3. Test an existing agent:"
Write-Host -ForegroundColor Cyan "     /testing-agent"
