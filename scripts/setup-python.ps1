<#
.SYNOPSIS
    Python Environment Setup for Aden Agent Framework (Windows)
.DESCRIPTION
    Replicates scripts/setup-python.sh logic for Windows/PowerShell.
#>

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host ""
Write-Host "=================================================="
Write-Host "  Aden Agent Framework - Python Setup (Windows)"
Write-Host "=================================================="
Write-Host ""

# Get script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Check Python presence
try {
    $null = Get-Command "python" -ErrorAction Stop
} catch {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.11+."
    exit 1
}

# Check Python Version
$PyVerInfo = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$Major,$Minor = $PyVerInfo -split "\."

Write-Host -ForegroundColor Cyan "Detected Python: $PyVerInfo"

if ([int]$Major -lt 3 -or ([int]$Major -eq 3 -and [int]$Minor -lt 11)) {
    Write-Error "Error: Python 3.11+ is required (found $PyVerInfo)"
    exit 1
}

if ([int]$Minor -lt 11) {
    Write-Warning "Warning: Python 3.11+ is recommended. Found $PyVerInfo."
} else {
    Write-Host -ForegroundColor Green "OK - Python version check passed"
}
Write-Host ""

# Check Pip
try {
    $null = python -m pip --version -ErrorAction Stop
    Write-Host -ForegroundColor Green "OK - Pip detected"
} catch {
    Write-Error "Error: pip is not installed."
    exit 1
}
Write-Host ""

# Upgrade Pip
Write-Host "Upgrading pip, setuptools, and wheel..."
python -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip" }
Write-Host -ForegroundColor Green "OK - Core packages upgraded"
Write-Host ""

# Install Core Framework
Write-Host "=================================================="
Write-Host "Installing Core Framework Package"
Write-Host "=================================================="
Push-Location "$ProjectRoot\core"
if (Test-Path "pyproject.toml") {
    Write-Host "Installing framework from core/ (editable mode)..."
    python -m pip install -e .
    if ($LASTEXITCODE -eq 0) {
        Write-Host -ForegroundColor Green "OK - Framework package installed"
    } else {
        Write-Warning "Framework installation encountered issues."
    }
} else {
    Write-Warning "No pyproject.toml in core/, skipping."
}
Pop-Location
Write-Host ""

# Install Tools Package
Write-Host "=================================================="
Write-Host "Installing Tools Package (aden_tools)"
Write-Host "=================================================="
Push-Location "$ProjectRoot\tools"
if (Test-Path "pyproject.toml") {
    Write-Host "Installing aden_tools from tools/ (editable mode)..."
    python -m pip install -e .
    if ($LASTEXITCODE -eq 0) {
        Write-Host -ForegroundColor Green "OK - Tools package installed"
    } else {
        Write-Error "Tools installation failed."
        exit 1
    }
} else {
    Write-Error "No pyproject.toml found in tools/"
    exit 1
}
Pop-Location
Write-Host ""

# Fix openai version compatibility
Write-Host "=================================================="
Write-Host "Fixing Package Compatibility"
Write-Host "=================================================="
$OpenAIInstalled = python -c "import openai; print('yes')" 2>$null
if ($OpenAIInstalled -ne 'yes') {
    Write-Host "Installing openai..."
    python -m pip install "openai>=1.0.0"
    Write-Host -ForegroundColor Green "OK - openai installed"
} else {
    $OpenAIVer = python -c "import openai; print(openai.__version__)"
    if ($OpenAIVer.StartsWith("0.")) {
        Write-Warning "Found old openai version: $OpenAIVer. Upgrading..."
        python -m pip install --upgrade "openai>=1.0.0"
        Write-Host -ForegroundColor Green "OK - openai upgraded"
    } else {
        Write-Host -ForegroundColor Green "OK - openai $OpenAIVer is compatible"
    }
}
Write-Host ""

# Verification
Write-Host "=================================================="
Write-Host "Verifying Installation"
Write-Host "=================================================="
Push-Location "$ProjectRoot"

# Test Framework
python -c "import framework; print('framework OK')"
if ($LASTEXITCODE -eq 0) {
    Write-Host -ForegroundColor Green "OK - framework imports successfully"
} else {
    Write-Error "Failed to import framework"
}

# Test Tools
python -c "import aden_tools; print('aden_tools OK')"
if ($LASTEXITCODE -eq 0) {
    Write-Host -ForegroundColor Green "OK - aden_tools imports successfully"
} else {
    Write-Error "Failed to import aden_tools"
    exit 1
}

# Test litellm
python -c "import litellm; print('litellm OK')"
if ($LASTEXITCODE -eq 0) {
    Write-Host -ForegroundColor Green "OK - litellm imports successfully"
} else {
    Write-Warning "litellm import had issues"
}

Pop-Location

Write-Host ""
Write-Host "=================================================="
Write-Host "  Setup Complete!"
Write-Host "=================================================="
Write-Host ""
Write-Host -ForegroundColor Cyan "To run agents on Windows (PowerShell):"
Write-Host "  `$env:PYTHONPATH='core;exports'"
Write-Host "  python -m agent_name run --input '{...}'"
