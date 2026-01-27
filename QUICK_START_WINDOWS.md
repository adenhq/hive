# Quick Start Guide - Windows

## One-Time Setup

### Step 1: Open PowerShell in Project Directory

```powershell
cd d:\hive
```

### Step 2: Check Python Version

```powershell
python --version
# Must be 3.11 or higher
```

### Step 3: Run Setup (PowerShell)

```powershell
#If you want to in powershell
./quickstart.ps1

# If you have Git Bash or WSL:
bash ./quickstart.sh

# OR manually install:
cd core
pip install -e .
cd ..\tools
pip install -e .
pip install mcp fastmcp
pip install --upgrade "openai>=1.0.0"
```

### Step 4: Set API Key

```powershell
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Or add to system environment variables permanently
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-ant-your-key-here', 'User')
```

### Step 5: Verify

```powershell
python -c "import framework; print('OK')"
python -c "import aden_tools; print('OK')"
```

---

## Running Agents (Windows)

### Validate Agent

```powershell
$env:PYTHONPATH="core;exports"
python -m your_agent_name validate
```

### View Agent Info

```powershell
$env:PYTHONPATH="core;exports"
python -m your_agent_name info
```

### Run Agent

```powershell
$env:PYTHONPATH="core;exports"
python -m your_agent_name run --input '{\"ticket_id\":\"123\"}'
```

### Run in Mock Mode

```powershell
$env:PYTHONPATH="core;exports"
python -m your_agent_name run --mock --input '{}'
```

---

## PowerShell Script Helper

Create `run-agent.ps1`:

```powershell
param(
    [string]$AgentName,
    [string]$Command = "run",
    [string]$Input = "{}",
    [switch]$Mock
)

$env:PYTHONPATH = "core;exports"

if ($Mock) {
    python -m $AgentName $Command --mock --input $Input
} else {
    python -m $AgentName $Command --input $Input
}
```

Usage:

```powershell
.\run-agent.ps1 -AgentName "support_ticket_agent" -Input '{\"ticket_id\":\"123\"}'
.\run-agent.ps1 -AgentName "support_ticket_agent" -Command "validate"
.\run-agent.ps1 -AgentName "support_ticket_agent" -Mock
```

---

## Building Agents

1. Open Claude Code in `d:\hive`
2. Use skill: `/building-agents`
3. Follow the prompts

---

## Common Windows Issues

**Issue: Scripts won't run**

```powershell
# Solution: Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Issue: PYTHONPATH not working**

```powershell
# Use semicolon separator for Windows
$env:PYTHONPATH="core;exports"
```

**Issue: Path with spaces**

```powershell
# Use quotes
cd "d:\my projects\hive"
```
