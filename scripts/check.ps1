param(
    [switch]$Fix,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$script = Join-Path $repoRoot "scripts\check.py"

$argsList = @()
if ($Fix) { $argsList += "--fix" }
if ($SkipTests) { $argsList += "--skip-tests" }

python $script @argsList


