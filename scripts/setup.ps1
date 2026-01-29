<#
.SYNOPSIS
    Windows Setup Script for Aden Agent Framework
#>

$ErrorActionPreference = "Stop"

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "--------------------------------------------------" -ForegroundColor Cyan
    Write-Host "  $Message"
    Write-Host "--------------------------------------------------" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host "OK: $Message" -ForegroundColor Green
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Header "Aden Agent Framework - Python Setup (Windows)"

$PyCmd = "python"
try {
    $null = Get-Command "python" -ErrorAction Stop
}
catch {
    try {
        $null = Get-Command "py" -ErrorAction Stop
        $PyCmd = "py"
    }
    catch {
        Write-ErrorMsg "Python not found. Please install Python 3.11+."
        exit 1
    }
}

try {
    $PyVer = & $PyCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
}
catch {
    Write-ErrorMsg "Failed to check Python version."
    exit 1
}

Write-Host "Detected Python: $PyVer" -ForegroundColor Cyan

$VerParts = $PyVer.Split(".")
if ([int]$VerParts[0] -lt 3 -or ([int]$VerParts[0] -eq 3 -and [int]$VerParts[1] -lt 11)) {
    Write-ErrorMsg "Error: Python 3.11+ is required (found $PyVer)"
    exit 1
}
Write-Success "Python version check passed"

try {
    & $PyCmd -m pip --version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "pip exit code non-zero" }
}
catch {
    Write-ErrorMsg "pip is not installed"
    exit 1
}
Write-Success "pip detected"

Write-Host "Upgrading pip, setuptools, and wheel..." -ForegroundColor Gray
& $PyCmd -m pip install --upgrade pip setuptools wheel | Out-Null
Write-Success "Core packages upgraded"

Write-Header "Installing Core Framework"
Set-Location "$ProjectRoot\core"
if (Test-Path "pyproject.toml") {
    Write-Host "Installing framework from core/..."
    & $PyCmd -m pip install -e . 
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Framework installed"
    }
    else {
        Write-ErrorMsg "Framework installation failed"
    }
    
    if (Test-Path "requirements-dev.txt") {
        Write-Host "Installing dev dependencies..."
        & $PyCmd -m pip install -r requirements-dev.txt | Out-Null
    }
}
else {
    Write-ErrorMsg "No pyproject.toml found in core/"
}

Write-Header "Installing Tools"
Set-Location "$ProjectRoot\tools"
if (Test-Path "pyproject.toml") {
    Write-Host "Installing aden_tools from tools/..."
    & $PyCmd -m pip install -e .
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Tools installed"
    }
    else {
        Write-ErrorMsg "Tools installation failed"
        exit 1
    }
}
else {
    Write-ErrorMsg "No pyproject.toml found in tools/"
    exit 1
}

Write-Header "Fixing Compatibility"
& $PyCmd -m pip install "openai>=1.0.0" | Out-Null
Write-Success "Checked openai version"

Write-Header "Verifying Installation"
Set-Location "$ProjectRoot"

try {
    & $PyCmd -c "import framework; print('framework OK')" | Out-Null
    Write-Success "framework imports OK"
}
catch {
    Write-ErrorMsg "framework import failed"
}

try {
    & $PyCmd -c "import aden_tools; print('aden_tools OK')" | Out-Null
    Write-Success "aden_tools imports OK"
}
catch {
    Write-ErrorMsg "aden_tools import failed"
}

Write-Header "Setup Complete!"
Write-Host "To run agents:"
Write-Host "  `$env:PYTHONPATH='core;exports'"
Write-Host "  python -m agent_name validate"
Write-Host ""
Set-Location $ScriptDir
