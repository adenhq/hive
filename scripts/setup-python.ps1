$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "`n=== Aden Agent Framework Setup ===`n"

# 1. Python Environment
Write-Host "Checking Python..."
$ver = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Detected: $ver"

# 2. Install Packages
Write-Host "`nInstalling Core..."
cd "$ProjectRoot\core"
pip install -e .

Write-Host "Installing Tools..."
cd "$ProjectRoot\tools"
pip install -e .

Write-Host "Installing Dependencies..."
pip install mcp fastmcp click openai keyboard

# 3. Install Skills
Write-Host "`nInstalling Claude Skills..."
$SourceDir = "$ProjectRoot\.claude\skills"
$DestDir = "$env:USERPROFILE\.claude\skills"

if (Test-Path $SourceDir) {
    if (-not (Test-Path $DestDir)) {
        New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    }
    
    $skills = Get-ChildItem -Path $SourceDir -Directory
    foreach ($skill in $skills) {
        $target = "$DestDir\$($skill.Name)"
        if (Test-Path $target) { Remove-Item -Recurse -Force $target }
        Copy-Item -Recurse -Force $skill.FullName $target
        Write-Host "Installed: $($skill.Name)"
    }
} else {
    Write-Host "Warning: Skills directory not found (skipping)"
}

# 4. Verify
Write-Host "`nVerifying..."
cd "$ProjectRoot"
python -c "import framework; print('framework OK')"
python -c "import aden_tools; print('aden_tools OK')"

Write-Host "`nSetup Complete."
