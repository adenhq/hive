# setup-python.ps1
# Windows Python Environment Setup for Aden Agent Framework
# Cross-platform parity script for setup-python.sh

Write-Host ""
Write-Host "=================================================="
Write-Host "  Aden Agent Framework - Python Setup (Windows)"
Write-Host "=================================================="
Write-Host ""

$REQUIRED_PYTHON_MAJOR = 3
$REQUIRED_PYTHON_MINOR = 11

function Fail($msg) {
    Write-Host ""
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

function Info($msg) {
    Write-Host $msg -ForegroundColor Cyan
}

function Success($msg) {
    Write-Host $msg -ForegroundColor Green
}

# ------------------ Paths ------------------

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Info "Project root: $PROJECT_ROOT"
Write-Host ""

# ------------------ Python Detection ------------------

$pythonCmd = $null
$pythonExec = $null

$possiblePythons = @("py", "python", "python3")

foreach ($cmd in $possiblePythons) {
    try {
        if ($cmd -eq "py") {
            py -3 -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $pythonCmd = "py"
                $pythonExec = "py -3"
                break
            }
        } else {
            & $cmd -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $pythonCmd = $cmd
                $pythonExec = $cmd
                break
            }
        }
    } catch {}
}

if (-not $pythonExec) {
    Fail "No Python found. Install Python 3.11+ from https://www.python.org/downloads/"
}

Success "Python detected: $pythonExec"

# ------------------ Version Check ------------------

$version = & $pythonExec -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$parts = $version.Split(".")

if ([int]$parts[0] -lt $REQUIRED_PYTHON_MAJOR -or ([int]$parts[0] -eq $REQUIRED_PYTHON_MAJOR -and [int]$parts[1] -lt $REQUIRED_PYTHON_MINOR)) {
    Fail "Python 3.11+ required. Found $version"
}

Success "Python version OK: $version"

# ------------------ pip Check ------------------

try {
    & $pythonExec -m pip --version | Out-Null
} catch {
    Fail "pip not found"
}

Success "pip detected"

# ------------------ uv Check ------------------

try {
    uv --version | Out-Null
} catch {
    Fail "uv not installed. Install from https://github.com/astral-sh/uv"
}

Success "uv detected"

Write-Host ""

# ------------------ Core Setup ------------------

Write-Host "==================================================" -ForegroundColor Yellow
Write-Host " Installing Core Framework" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Yellow
Write-Host ""

Set-Location "$PROJECT_ROOT\core"

if (!(Test-Path ".venv")) {
    Info "Creating core/.venv ..."
    uv venv
    Success "core/.venv created"
} else {
    Success "core/.venv already exists"
}

$CORE_PYTHON = ".venv\Scripts\python.exe"

if (Test-Path "pyproject.toml") {
    Info "Installing core package (editable)..."
    uv pip install --python $CORE_PYTHON -e .
    Success "Core framework installed"
} else {
    Info "No pyproject.toml in core/, skipping install"
}

Write-Host ""

# ------------------ Tools Setup ------------------

Write-Host "==================================================" -ForegroundColor Yellow
Write-Host " Installing Tools Package (aden_tools)" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Yellow
Write-Host ""

Set-Location "$PROJECT_ROOT\tools"

if (!(Test-Path ".venv")) {
    Info "Creating tools/.venv ..."
    uv venv
    Success "tools/.venv created"
} else {
    Success "tools/.venv already exists"
}

$TOOLS_PYTHON = ".venv\Scripts\python.exe"

if (Test-Path "pyproject.toml") {
    Info "Installing tools package (editable)..."
    uv pip install --python $TOOLS_PYTHON -e .
    Success "aden_tools installed"
} else {
    Fail "tools/pyproject.toml missing"
}

Write-Host ""

# ------------------ Directory Structure ------------------

Write-Host "==================================================" -ForegroundColor Yellow
Write-Host " Verifying Directory Structure" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Yellow
Write-Host ""

Set-Location "$PROJECT_ROOT"

if (!(Test-Path "exports")) {
    New-Item -ItemType Directory -Path "exports" | Out-Null
    "# Agent Exports" | Out-File "exports\README.md"
    "Auto-generated agent packages will appear here." | Out-File "exports\README.md" -Append
    Success "exports directory created"
} else {
    Success "exports directory exists"
}

Write-Host ""

# ------------------ Verification ------------------

Write-Host "==================================================" -ForegroundColor Yellow
Write-Host " Verifying Installation" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Yellow
Write-Host ""

try {
    & "$PROJECT_ROOT\core\.venv\Scripts\python.exe" -c "import framework" | Out-Null
    Success "framework import OK"
} catch {
    Info "framework import failed (may be optional)"
}

try {
    & "$PROJECT_ROOT\tools\.venv\Scripts\python.exe" -c "import aden_tools" | Out-Null
    Success "aden_tools import OK"
} catch {
    Fail "aden_tools import failed"
}

Write-Host ""

# ------------------ Done ------------------

Write-Host "==================================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Core venv:  core\.venv"
Write-Host "Tools venv: tools\.venv"
Write-Host ""
Write-Host "You can now run agents and MCP services."
Write-Host ""
Write-Host "Docs: README.md"
Write-Host "Exports: exports\"
Write-Host ""
