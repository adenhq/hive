# UV Package Manager Migration Guide

## Overview

The Hive project has migrated from pip to [uv](https://docs.astral.sh/uv/), a blazingly fast Python package installer and resolver written in Rust. This guide will help you transition to using uv for development.

## Why UV?

### Performance
- **10-100x faster** than pip for dependency installation
- Parallel downloads and installations
- Efficient caching mechanism

### Reliability
- **Reproducible builds** with uv.lock file
- Consistent dependency resolution across all environments
- Prevents "works on my machine" issues

### Developer Experience
- Single tool for Python version management, virtual environments, and packages
- Better error messages and conflict resolution
- Workspace support for monorepos

### Comparison

| Metric | pip | uv | Improvement |
|--------|-----|-----|------------|
| Fresh install | ~45s | ~4s | **11x faster** |
| Cached install | ~15s | ~0.5s | **30x faster** |
| Lock file | ❌ | ✅ | Reproducible builds |
| Workspace support | ❌ | ✅ | Monorepo-friendly |

## Installing UV

### macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Via Homebrew (macOS)

```bash
brew install uv
```

### Via Cargo (if you have Rust installed)

```bash
cargo install uv
```

### Verify Installation

```bash
uv --version
```

## Quick Start

Once uv is installed, setting up the Hive project is simple:

```bash
# Clone the repository
git clone https://github.com/adenhq/hive.git
cd hive

# Run the setup script (auto-detects uv)
./scripts/setup-python.sh

# That's it! The script will:
# 1. Install Python 3.11 if needed
# 2. Sync all workspace packages (framework + aden_tools)
# 3. Verify installations
```

## Command Comparison: pip vs uv

### Installation

| Task | pip | uv |
|------|-----|-----|
| Install dependencies | `pip install -r requirements.txt` | `uv sync` |
| Install package | `pip install -e .` | `uv sync` |
| Install all workspace packages | Multiple `pip install -e` commands | `uv sync --all-packages` |
| Add a new dependency | Edit `pyproject.toml` + `pip install` | `uv add <package>` |
| Remove a dependency | Edit `pyproject.toml` + `pip uninstall` | `uv remove <package>` |

### Running Commands

| Task | pip | uv |
|------|-----|-----|
| Run Python script | `python script.py` | `uv run python script.py` |
| Run tests | `pytest tests/` | `uv run pytest tests/` |
| Run agent | `python -m agent_name` | `uv run python -m agent_name` |

### Virtual Environments

| Task | pip | uv |
|------|-----|-----|
| Create venv | `python -m venv .venv` | `uv venv` (automatic) |
| Activate venv | `source .venv/bin/activate` | Not needed with `uv run` |
| Python version | Install separately | `uv python install 3.11` |

### Information

| Task | pip | uv |
|------|-----|-----|
| List packages | `pip list` | `uv pip list` |
| Show package info | `pip show <package>` | `uv pip show <package>` |
| Dependency tree | `pip install pipdeptree && pipdeptree` | `uv tree` |
| Check for updates | `pip list --outdated` | `uv pip list --outdated` |

## Common Workflows

### 1. Setting Up Development Environment

```bash
# With pip (old way)
python -m venv .venv
source .venv/bin/activate
cd core && pip install -e .
cd ../tools && pip install -e .

# With uv (new way)
uv sync --all-packages
```

### 2. Adding a New Dependency

```bash
# With pip (old way)
# 1. Edit pyproject.toml manually
# 2. pip install <package>
# 3. Remember to update requirements.txt

# With uv (new way)
cd core  # or tools, depending on which package needs it
uv add <package>  # Automatically updates pyproject.toml and uv.lock
```

### 3. Running Tests

```bash
# With pip (old way)
cd core
pytest tests/ -v

# With uv (new way)
cd core
uv run pytest tests/ -v

# Or from project root
uv run --directory core pytest tests/ -v
```

### 4. Running Agents

```bash
# With pip (old way)
export PYTHONPATH=core:exports
python -m support_ticket_agent run --input '{"ticket_content":"..."}'

# With uv (new way)
PYTHONPATH=core:exports uv run python -m support_ticket_agent run --input '{"ticket_content":"..."}'
```

### 5. Updating Dependencies

```bash
# With pip (old way)
pip install --upgrade <package>

# With uv (new way)
uv lock --upgrade-package <package>
uv sync
```

### 6. Checking Dependency Tree

```bash
# With pip (old way)
pip install pipdeptree
pipdeptree

# With uv (new way)
uv tree
```

## Workspace Structure

The Hive project uses uv's workspace feature for managing multiple packages:

```
hive/
├── pyproject.toml        # Root workspace configuration
├── uv.lock              # Shared lock file (commit this!)
├── .python-version      # Python version pinning
├── core/                # Framework package
│   └── pyproject.toml
└── tools/               # Tools package
    └── pyproject.toml
```

### Key Points

- **Single lock file** (`uv.lock`) ensures all packages use compatible versions
- **Root workspace** defined in `pyproject.toml` at repository root
- **Synchronized releases** - both packages share the same dependency versions
- **One command** to install everything: `uv sync --all-packages`

## Backward Compatibility

During the transition period, both uv and pip are supported:

### Setup Script Auto-Detection

The `setup-python.sh` script automatically detects which package manager to use:

```bash
./scripts/setup-python.sh

# If uv is installed:
# ✓ Uses uv for fast installation

# If uv is not installed:
# ✓ Falls back to pip
# ✓ Shows instructions for installing uv
```

### CI/CD

- **GitHub Actions** use uv for all workflows
- **Docker builds** use uv for optimal performance
- **Local development** supports both uv and pip

### Requirements.txt Files

For backward compatibility, `requirements.txt` files are temporarily maintained:

- Keep in sync with `pyproject.toml` for now
- Will be deprecated in future releases
- Use `pyproject.toml` + `uv.lock` for new development

## Troubleshooting

### Issue: uv not found

**Symptoms:**
```bash
./scripts/setup-python.sh
uv not found. Install: https://docs.astral.sh/uv/
Falling back to pip installation...
```

**Solution:**
Install uv using one of the methods above, then run the setup script again.

### Issue: Lock file conflicts

**Symptoms:**
```bash
uv sync
error: The lockfile is out of date
```

**Solution:**
Regenerate the lock file:
```bash
uv lock
uv sync --all-packages
```

### Issue: Dependency resolution fails

**Symptoms:**
```bash
uv lock
error: No solution found when resolving dependencies
```

**Solution:**
1. Check for conflicting version requirements in `pyproject.toml` files
2. Use `uv tree` to inspect dependency tree
3. Try upgrading specific packages: `uv lock --upgrade-package <package>`

### Issue: Python version mismatch

**Symptoms:**
```bash
uv sync
error: No interpreter found for Python 3.11
```

**Solution:**
Install Python 3.11 with uv:
```bash
uv python install 3.11
```

### Issue: Import errors after installation

**Symptoms:**
```bash
uv run python -c "import framework"
ModuleNotFoundError: No module named 'framework'
```

**Solution:**
1. Ensure you're in the project root directory
2. Resync packages: `uv sync --all-packages`
3. Check that both packages installed: `uv pip list | grep -E 'framework|tools'`

### Issue: Cache issues

**Symptoms:**
Unexpected behavior, stale dependencies

**Solution:**
Clear uv cache and reinstall:
```bash
uv cache clean
uv sync --all-packages --refresh
```

## FAQ

### Do I need to activate a virtual environment?

**No!** With uv, you don't need to manually activate virtual environments. Just use `uv run` prefix:

```bash
# Instead of:
source .venv/bin/activate
python script.py

# Just do:
uv run python script.py
```

### Can I still use pip?

**Yes**, during the transition period. The setup script supports both uv and pip. However, we recommend switching to uv for the performance and reliability benefits.

### What happens to my existing .venv?

You can safely delete your old `.venv` directory. uv manages its own virtual environments automatically.

### How do I update uv?

```bash
# macOS / Linux
uv self update

# Or reinstall
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Should I commit uv.lock to git?

**Yes!** The `uv.lock` file should be committed to ensure reproducible builds across all environments.

### How do I see what changed in uv.lock?

The lock file is human-readable. You can:
- View diffs in git: `git diff uv.lock`
- Use `uv tree` to see the dependency tree
- Check specific package versions: `uv pip show <package>`

### Can I use uv in Docker?

**Yes!** The project's Dockerfile has been optimized for uv. See `tools/Dockerfile` for the multi-stage build implementation.

### What if I'm on an air-gapped network?

uv supports offline installation using cached wheels. After the first install:
```bash
uv sync --offline
```

### How do I install optional dependencies?

```bash
# Install all optional dependencies
uv sync --all-extras

# Install specific optional groups
uv sync --extra ocr --extra sandbox
```

For the tools package, this includes:
- `ocr`: pytesseract, pillow
- `sandbox`: RestrictedPython
- `dev`: pytest, pytest-asyncio

## Additional Resources

- **uv Documentation**: https://docs.astral.sh/uv/
- **uv GitHub**: https://github.com/astral-sh/uv
- **Hive Project README**: ../README.md
- **Developer Guide**: ../DEVELOPER.md
- **Environment Setup**: ../ENVIRONMENT_SETUP.md

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [uv documentation](https://docs.astral.sh/uv/)
2. Search [Hive GitHub issues](https://github.com/adenhq/hive/issues)
3. Ask in the project's discussion forum
4. File a new issue with:
   - Your OS and Python version
   - The command you ran
   - The full error message
   - Output of `uv --version`
