# Pre-commit Hooks Setup

This project uses [pre-commit](https://pre-commit.com/) hooks to enforce code quality and consistency across the codebase.

## Installation

1. **Install pre-commit** (if not already installed):
   ```bash
   pip install pre-commit
   ```

2. **Install the git hook scripts**:
   ```bash
   pre-commit install
   ```

3. **Run against all files** (optional, to fix existing issues):
   ```bash
   pre-commit run --all-files
   ```

## What Gets Checked

The pre-commit hooks will automatically run on staged files before each commit:

### General File Checks
- ✅ Remove trailing whitespace
- ✅ Ensure files end with a newline
- ✅ Validate YAML syntax
- ✅ Validate JSON syntax
- ✅ Validate TOML syntax
- ✅ Check for large files (>1MB)
- ✅ Check for merge conflict markers
- ✅ Fix mixed line endings (use LF)

### Python Checks (Ruff)
- ✅ **Linting**: Checks for code style issues, bugs, and anti-patterns
- ✅ **Formatting**: Auto-formats Python code for consistency
- ✅ **Import Sorting**: Organizes imports according to project standards

## Configuration

Pre-commit hooks are configured in [`.pre-commit-config.yaml`](.pre-commit-config.yaml).

Python linting and formatting rules are defined in [`core/pyproject.toml`](core/pyproject.toml) under the `[tool.ruff]` section.

### Temporarily Ignored Rules

To allow smooth adoption without blocking development, the following rules are temporarily ignored:

- `E501`: Line too long (>100 characters)
- `E402`: Module level import not at top of file
- `F841`: Unused local variables
- `UP038`: Use `X | Y` instead of `(X, Y)` in isinstance
- `B904`: Exception handling without `from err`/`from None`
- `C401`: Generator to set comprehension
- `B007`: Unused loop variable
- `E712`: Comparison to True/False

These issues exist in the current codebase and will be fixed progressively in future PRs.

## Running Manually

You can run the hooks manually at any time:

```bash
# Run on all files
pre-commit run --all-files

# Run on specific files
pre-commit run --files core/framework/graph/node.py

# Run a specific hook
pre-commit run ruff --all-files
pre-commit run trailing-whitespace --all-files
```

## Skipping Hooks (Not Recommended)

If you absolutely need to skip pre-commit hooks for a commit:

```bash
git commit --no-verify -m "your message"
```

**Note**: This is not recommended as it bypasses quality checks.

## Updating Hooks

To update hooks to the latest versions:

```bash
pre-commit autoupdate
```

## Troubleshooting

### Hooks are not running
- Ensure you've run `pre-commit install`
- Check that `.git/hooks/pre-commit` exists and is executable

### Pre-commit is too slow
- Hooks cache their environments, so they're faster after the first run
- Use `pre-commit run --files <specific-files>` for faster partial checks

### Formatting conflicts
- Run `pre-commit run --all-files` to let ruff auto-fix formatting issues
- If ruff and manual formatting conflict, trust ruff's formatting

### Linting errors blocking commits
- Check [`core/pyproject.toml`](core/pyproject.toml) for ignored rules
- Consider whether the error should be fixed or added to the ignore list
- Use `--no-verify` only as a last resort

## Benefits

✨ **Consistency**: All code follows the same style guidelines
✨ **Quality**: Catches bugs and anti-patterns early
✨ **Time Saving**: Auto-fixes common issues automatically
✨ **Less Review Friction**: PRs are cleaner and easier to review
✨ **CI/CD Alignment**: Local checks match CI pipeline requirements

## Contributing

When contributing to this project:

1. Always run `pre-commit install` after cloning the repository
2. Let the hooks auto-fix issues where possible
3. For persistent linting errors, consider whether they should be:
   - Fixed in your code
   - Added to the ignore list (if valid pattern)
   - Raised as a discussion in the PR

## Progressive Cleanup

As the codebase is cleaned up, ignored rules can be gradually removed from [`core/pyproject.toml`](core/pyproject.toml). This allows the project to improve code quality incrementally without blocking current development.
