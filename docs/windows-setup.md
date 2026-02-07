# Windows Setup Guide

This guide provides Windows-specific instructions for setting up the Aden Agent Framework using PowerShell.

## Prerequisites

Before you begin, ensure you have:

- **Windows 10/11** with PowerShell 5.1 or later
- **Python 3.11+** - [Download from python.org](https://www.python.org/downloads/)
  - ⚠️ During installation, check "Add Python to PATH"
- **Git for Windows** - [Download](https://git-scm.com/download/win)
- **pip** - Comes with Python (verify with `pip --version`)

## Verify Prerequisites

Open PowerShell and verify your installations:

```powershell
# Check Python version (should be 3.11+)
python --version

# Check pip
pip --version

# Check git
git --version
```

## Installation Steps

### 1. Clone the Repository

```powershell
# Clone the repo
git clone https://github.com/adenhq/hive.git
cd hive
```

### 2. Install Framework Package

```powershell
# Navigate to core directory and install
cd core
pip install -e .
cd ..
```

Expected output:
```
Obtaining file:///E:/GitHub/hive/core
Installing build dependencies ... done
...
Successfully installed framework
```

### 3. Install Tools Package

```powershell
# Navigate to tools directory and install
cd tools
pip install -e .
cd ..
```

Expected output:
```
Obtaining file:///E:/GitHub/hive/tools
Installing build dependencies ... done
...
Successfully installed aden-tools
```

### 4. Verify Installation

```powershell
# Test that packages are installed correctly
python -c "import framework; import aden_tools; print('✓ Setup complete')"
```

If successful, you should see:
```
✓ Setup complete
```

## Configuration

### Setting Up API Keys

For running agents with real LLMs, you'll need API keys. Set them as environment variables:

#### Temporary (Current PowerShell Session Only)

```powershell
$env:ANTHROPIC_API_KEY = "your-key-here"
$env:OPENAI_API_KEY = "your-key-here"
$env:BRAVE_SEARCH_API_KEY = "your-key-here"
```

#### Permanent (System Environment Variables)

1. Open **System Properties**:
   - Press `Win + R`, type `sysdm.cpl`, press Enter
   
2. Go to **Advanced** tab → **Environment Variables**

3. Under **User variables**, click **New** and add:
   - Variable name: `ANTHROPIC_API_KEY`
   - Variable value: `your-key-here`

4. Repeat for other API keys

5. **Restart PowerShell** for changes to take effect

#### Using PowerShell Profile (Recommended for Developers)

```powershell
# Open your PowerShell profile
notepad $PROFILE

# Add these lines:
$env:ANTHROPIC_API_KEY = "your-key-here"
$env:OPENAI_API_KEY = "your-key-here"
$env:BRAVE_SEARCH_API_KEY = "your-key-here"

# Save and reload
. $PROFILE
```

Get API keys from:
- **Anthropic**: [console.anthropic.com](https://console.anthropic.com/)
- **OpenAI**: [platform.openai.com](https://platform.openai.com/)
- **Brave Search**: [brave.com/search/api](https://brave.com/search/api/)

## Running Tests

```powershell
# Run framework tests
cd core
python -m pytest tests/ -v

# Run tools tests
cd ..\tools
python -m pytest tests/ -v

# Return to root
cd ..
```

## Common Issues

### Issue: "Python was not found"

**Problem:** When running `python`, you get:
```
Python was not found; run without arguments to install from the Microsoft Store...
```

**Solution:**
1. Reinstall Python from [python.org](https://www.python.org/downloads/)
2. **Check "Add Python to PATH"** during installation
3. Restart PowerShell
4. Verify with `python --version`

### Issue: "pip is not recognized"

**Problem:** `pip` command not found

**Solution:**
```powershell
# Ensure pip is installed
python -m ensurepip --upgrade

# Use python -m pip instead
python -m pip install -e .
```

### Issue: "Access Denied" or Permission Errors

**Problem:** Installation fails due to permissions

**Solution:**
1. Run PowerShell as Administrator (Right-click → "Run as Administrator")
2. Or use virtual environment (see below)

### Issue: Bash Scripts Don't Work

**Problem:** The `setup-python.sh` and `quickstart.sh` scripts are for bash

**Solution:**
- Use the PowerShell commands from this guide instead
- Or install [Git Bash](https://git-scm.com/download/win) to run bash scripts

### Issue: Import Errors After Installation

**Problem:** Python can't find the installed packages

**Solution:**
```powershell
# Set PYTHONPATH to your hive directory
$env:PYTHONPATH = "C:\path\to\hive\core;C:\path\to\hive\tools"

# Or reinstall in editable mode
cd core
pip install -e .
cd ..\tools
pip install -e .
```

## Using Virtual Environments (Recommended)

Virtual environments isolate project dependencies:

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install packages
cd core
pip install -e .
cd ..\tools
pip install -e .
cd ..

# Deactivate when done
deactivate
```

## Next Steps

After installation:

1. **Read the docs:**
   - [Getting Started Guide](getting-started.md)
   - [Architecture Overview](architecture.md)
   - [Developer Guide](../DEVELOPER.md)

2. **Run example tests:**
   ```powershell
   cd core
   python -m pytest tests/test_builder.py -v
   ```

3. **Explore the codebase:**
   ```powershell
   # View project structure
   tree /F /A
   ```

## Additional Resources

- **Main README:** [README.md](../README.md)
- **Contributing Guide:** [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Environment Setup:** [ENVIRONMENT_SETUP.md](../ENVIRONMENT_SETUP.md)
- **Discord Community:** [Join Discord](https://discord.com/invite/MXE49hrKDk)

## Need Help?

- **GitHub Issues:** [Report a problem](https://github.com/adenhq/hive/issues)
- **Discord:** [Join the community](https://discord.com/invite/MXE49hrKDk)
- **Documentation:** [docs.adenhq.com](https://docs.adenhq.com/)

---

**Tested on:**
- Windows 11
- PowerShell 5.1
- Python 3.12.2
- Git 2.43.0
