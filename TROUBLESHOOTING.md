# Troubleshooting Guide

Common issues and solutions for setting up and running Hive agents.

## Table of Contents
- [Setup Issues](#setup-issues)
- [Python Environment](#python-environment)
- [Running Agents](#running-agents)
- [Tool Issues](#tool-issues)
- [Windows-Specific Issues](#windows-specific-issues)

---

## Setup Issues

### ❌ `./scripts/setup-python.sh` fails or not executable

**Symptoms:**
- Permission denied error
- Command not found

**Solutions:**

**On Linux/macOS:**
```bash
chmod +x scripts/setup-python.sh
./scripts/setup-python.sh
```

**On Windows (Git Bash/WSL):**
```bash
bash scripts/setup-python.sh
```

**On Windows (PowerShell):**
```powershell
# Create Python virtual environment manually
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e core -e tools
```

---

### ❌ Wrong Python version detected (need 3.11, have 3.10 or 3.12)

**Symptoms:**
```
Error: Python 3.11 is required
```

**Solutions:**

**Check installed Python versions:**
```bash
python3.11 --version  # Linux/macOS
py -3.11 --version    # Windows
```

**If Python 3.11 not installed:**

**Ubuntu/Debian:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

**macOS (Homebrew):**
```bash
brew install python@3.11
```

**Windows:**
- Download from [python.org](https://www.python.org/downloads/)
- Or use `winget`: `winget install Python.Python.3.11`

**Use specific Python version:**
```bash
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
```

---

### ❌ `ModuleNotFoundError: No module named 'aden_tools'`

**Symptoms:**
- Setup script succeeded but import fails
- Verification step fails

**Solutions:**

1. **Ensure you're in the virtual environment:**
   ```bash
   source .venv/bin/activate  # Linux/macOS
   .\.venv\Scripts\Activate.ps1  # Windows
   ```

2. **Reinstall in editable mode:**
   ```bash
   pip install -e core -e tools
   ```

3. **Verify installation:**
   ```bash
   python -c "import aden_tools; print(aden_tools.__file__)"
   ```

---

## Python Environment

### ❌ `externally-managed-environment` error on Ubuntu/Debian

**Symptoms:**
```
error: externally-managed-environment
This environment is externally managed
```

**Solutions:**

**Option 1: Use virtual environment (RECOMMENDED):**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e core -e tools
```

**Option 2: Use system Python with --break-system-packages (NOT RECOMMENDED):**
```bash
pip install --break-system-packages -e core -e tools
```

---

### ❌ `pip` command not found

**Symptoms:**
```
bash: pip: command not found
```

**Solutions:**

**Use Python module instead:**
```bash
python -m pip install -e core -e tools
```

**Or install pip:**
```bash
# Ubuntu/Debian
sudo apt install python3-pip

# macOS
python3 -m ensurepip --upgrade

# Windows
py -m ensurepip --upgrade
```

---

## Running Agents

### ❌ `ModuleNotFoundError` when using `PYTHONPATH=core:exports`

**Symptoms:**
```
ModuleNotFoundError: No module named 'framework'
```

**Solutions:**

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH="core;exports"
python -m framework.cli run your_agent
```

**Windows (CMD):**
```cmd
set PYTHONPATH=core;exports
python -m framework.cli run your_agent
```

**Linux/macOS:**
```bash
PYTHONPATH=core:exports python -m framework.cli run your_agent
```

**Or use the CLI directly (if installed):**
```bash
hive run your_agent
```

---

### ❌ No agents found / `exports` directory missing

**Symptoms:**
```
Error: No agents found in exports directory
```

**Solutions:**

The `exports/` directory is for **exported production agents**, not development. For development:

1. **Use example agents from docs:**
   ```bash
   # Copy an example agent
   cp -r docs/examples/simple_agent exports/my_agent
   ```

2. **Or create a new agent:**
   ```bash
   python -m framework.cli create my_agent
   ```

3. **For development, run directly:**
   ```python
   # in your_script.py
   from framework.runner import AgentRunner
   runner = AgentRunner(agent_id="my_agent")
   result = runner.run(input_data={"query": "test"})
   ```

---

### ❌ API key errors (Anthropic, OpenAI, etc.)

**Symptoms:**
```
Error: ANTHROPIC_API_KEY not set
AuthenticationError: Invalid API key
```

**Solutions:**

**Set environment variables:**

**Linux/macOS:**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
export OPENAI_API_KEY="your-api-key-here"
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="your-api-key-here"
$env:OPENAI_API_KEY="your-api-key-here"
```

**Or create a `.env` file:**
```bash
# .env
ANTHROPIC_API_KEY=your-api-key-here
OPENAI_API_KEY=your-api-key-here
```

**Load .env in your script:**
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Tool Issues

### ❌ MCP server registration failed

**Symptoms:**
```
Error: Failed to register MCP servers
stdout corruption: non-JSON output
```

**Solutions:**

1. **Check MCP server logs:**
   ```bash
   python core/verify_mcp.py
   ```

2. **Ensure no print statements in STDIO mode:**
   - MCP servers must output ONLY valid JSON-RPC in STDIO mode
   - Check `tools/mcp_server.py` for any `print()` statements

3. **Restart MCP server:**
   ```bash
   pkill -f mcp_server
   python tools/mcp_server.py
   ```

---

### ❌ Tool imports failing

**Symptoms:**
```
ImportError: cannot import name 'web_search' from 'aden_tools'
```

**Solutions:**

1. **Reinstall tools package:**
   ```bash
   pip uninstall aden_tools -y
   pip install -e tools
   ```

2. **Check tool registration:**
   ```python
   from aden_tools import ToolRegistry
   registry = ToolRegistry()
   print(registry.list_tools())
   ```

---

## Windows-Specific Issues

### ❌ App Execution Aliases cause wrong Python

**Symptoms:**
- `python` command opens Microsoft Store
- Wrong Python version detected

**Solutions:**

**Disable App Execution Aliases:**
1. Open Settings → Apps → Apps & features
2. Click "App execution aliases"
3. Turn OFF both:
   - `python.exe`
   - `python3.exe`

**Then use full path or `py` launcher:**
```cmd
py -3.11 -m venv .venv
```

---

### ❌ `UnicodeEncodeError` when writing files

**Symptoms:**
```
UnicodeEncodeError: 'charmap' codec can't encode character
```

**Solutions:**

**Set UTF-8 encoding:**

**PowerShell:**
```powershell
$env:PYTHONIOENCODING="utf-8"
```

**Or in Python code:**
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

---

### ❌ Path separator issues (`:` vs `;`)

**Symptoms:**
- PYTHONPATH not working on Windows

**Solutions:**

**Windows uses `;` as path separator:**
```powershell
$env:PYTHONPATH="core;exports"  # PowerShell
set PYTHONPATH=core;exports     # CMD
```

**Linux/macOS uses `:`:**
```bash
export PYTHONPATH=core:exports
```

---

## Still Having Issues?

1. **Check the logs:**
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   python -m framework.cli run your_agent
   ```

2. **Search existing issues:**
   - [GitHub Issues](https://github.com/adenhq/hive/issues)

3. **Create a new issue:**
   - Include error messages, OS version, Python version
   - Minimal reproducible example

4. **Join the community:**
   - Discord: [link]
   - Discussions: [GitHub Discussions](https://github.com/adenhq/hive/discussions)

---

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Module not found | `pip install -e core -e tools` |
| Wrong Python | `python3.11 -m venv .venv` |
| Permission denied | `chmod +x scripts/setup-python.sh` |
| API key missing | `export ANTHROPIC_API_KEY="..."` |
| Windows PYTHONPATH | `$env:PYTHONPATH="core;exports"` |
| MCP registration | Check for print statements in tools |
