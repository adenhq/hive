**Problem**
The project deals with executing code, shell commands, and handling API keys, but lacks automated security linting in `requirements-dev.txt` or `pyproject.toml`. There are no visible scripts to check for common vulnerabilities (like the `shell=True` issue found manually).

**Evidence**
File: `core/pyproject.toml` and `tools/pyproject.toml` include `ruff` and `mypy` but no security scanners like `bandit` or `safety`.

**Impact**
**Security Risk**. Vulnerabilities like Issue #1 can easily regress or be introduced by new contributors without automated checks.

**Proposed Solution**
1.  Add `bandit` to `dev` dependencies.
2.  Add a `scripts/security-check.sh` or update `CONTRIBUTING.md` to include running `bandit -r core tools`.

**Priority**
Medium
