---
name: hive-contribute
description: Guide through finding issues, analyzing the codebase, and creating PRs for the Hive repository. Use when you want to contribute to Hive.
---

# Hive Contribution Workflow

This skill helps you contribute to the Hive (Aden Agent Framework) repository by guiding you through finding issues, understanding the codebase, and creating proper PRs.

## Quick Reference

**Repository**: github.com/adenhq/hive
**Main Rules**:
1. Issues must be assigned before PRs (except docs/micro-fixes)
2. 5-day rule: No activity = unassigned
3. PRs must reference issues (`Fixes #123`)
4. Follow conventional commits (`type(scope): description`)

---

## Workflow Steps

### Step 1: Find an Issue to Work On

First, check for good issues to contribute to:

```bash
# View open issues with helpful labels
gh issue list --repo adenhq/hive --label "good first issue" --state open
gh issue list --repo adenhq/hive --label "help wanted" --state open
gh issue list --repo adenhq/hive --label "bug" --state open

# Search for specific topics
gh issue list --repo adenhq/hive --search "Integration" --state open
gh issue list --repo adenhq/hive --search "tool" --state open
```

**Priority Labels:**
- `good first issue` - Best for new contributors
- `help wanted` - Maintainers actively need help
- `bug` - Fix something broken
- `Integration` - High demand, many examples to follow

### Step 2: Check Issue Status

Before claiming, verify the issue is available:

```bash
# View issue details
gh issue view <number> --repo adenhq/hive

# Check if assigned
gh issue view <number> --repo adenhq/hive --json assignees
```

**If unassigned**: Comment to claim it
**If assigned but stale (>7 days)**: You may comment expressing interest

### Step 3: Claim the Issue

Comment on the issue to request assignment:

```bash
gh issue comment <number> --repo adenhq/hive --body "I'd like to work on this! I have experience with [relevant skill] and plan to [brief approach]."
```

**Wait for assignment** - Maintainers typically respond within 24 hours.

### Step 4: Understand the Codebase

While waiting for assignment, understand the relevant code:

**Key Directories:**
```
core/framework/graph/     # Execution engine (executor.py, node.py, edge.py)
core/framework/llm/       # LLM providers
core/framework/runtime/   # Decision tracking, observability
tools/src/aden_tools/     # MCP tools
```

**For bug fixes:**
1. Read the issue carefully
2. Find the relevant code using Grep/Glob
3. Understand the intended behavior
4. Identify the fix approach

**For tool integrations:**
1. Study existing tools in `tools/src/aden_tools/tools/`
2. Follow the pattern from similar tools
3. Check `tools/BUILDING_TOOLS.md`

### Step 5: Set Up Development Environment

```bash
# Fork on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/hive.git
cd hive
git remote add upstream https://github.com/adenhq/hive.git
./quickstart.sh

# Verify setup
python -c "import framework; import aden_tools; print('Setup OK')"
```

### Step 6: Create Your Branch

```bash
# Update from upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### Step 7: Implement Your Changes

**Code Style:**
- Python 3.11+
- PEP 8 style
- Type hints on functions
- Docstrings for classes/public functions

**Add Tests:**
```bash
# Tests go in the relevant tests/ directory
# core/tests/ for framework changes
# tools/tests/ for tool changes
```

**Run Checks:**
```bash
make check                              # Lint and format
cd core && python -m pytest tests/ -v   # Core tests
cd tools && python -m pytest tests/ -v  # Tools tests
```

### Step 8: Commit with Conventional Format

```bash
git add .
git commit -m "type(scope): description

- Detail 1
- Detail 2

Fixes #<issue-number>"
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `test` - Tests
- `refactor` - Code restructuring
- `chore` - Maintenance

### Step 9: Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create PR on GitHub with this structure:

```markdown
## Summary

- What you changed
- Why you changed it

## Test Plan

- [ ] Added unit tests
- [ ] Ran existing tests (`pytest tests/ -v`)
- [ ] Ran linting (`make check`)
- [ ] Tested manually

Fixes #<issue-number>
```

### Step 10: Respond to Review

- Address feedback promptly
- Push additional commits for changes
- Be respectful and collaborative

---

## Exception Cases

### Documentation (No Assignment Needed)

For docs fixes, include `doc` or `docs` in PR title:

```
docs: fix typo in README
docs(setup): clarify Python version requirement
```

### Micro-fixes (No Assignment Needed)

For tiny fixes (<20 lines), include `micro-fix` in PR title:

```
chore(micro-fix): remove unused import
style(micro-fix): fix formatting in executor.py
```

**Micro-fix criteria:**
- < 20 lines changed
- Typos, docs, linting only
- No logic/API/DB changes
- Not a bug fix or feature

---

## Analyzing the Codebase

### Finding Relevant Code

```bash
# Find files by pattern
ls core/framework/graph/

# Search for specific code
grep -r "GraphExecutor" core/

# Read key files
cat core/framework/graph/executor.py
```

### Key Files to Understand

| File | Purpose |
|------|---------|
| `core/framework/graph/executor.py` | Main execution engine |
| `core/framework/graph/node.py` | Node types and SharedMemory |
| `core/framework/graph/edge.py` | Edge conditions and routing |
| `core/framework/graph/goal.py` | Goal definitions |
| `core/framework/graph/judge.py` | HybridJudge verification |
| `tools/src/aden_tools/mcp_server.py` | MCP tool server |

### Understanding Patterns

**For tool integrations**, study:
- `tools/src/aden_tools/tools/web_search_tool/` - Web search pattern
- `tools/src/aden_tools/tools/web_scrape_tool/` - Web scraping pattern
- `tools/src/aden_tools/tools/file_system_toolkits/` - File operation patterns

**For bug fixes**, understand:
- The execution flow in `executor.py`
- Error handling patterns
- Test patterns in `core/tests/`

---

## Generating PR Descriptions

When ready to create a PR, use this template:

```markdown
## Summary

[1-2 sentences describing the change]

### Changes Made

- [Change 1]
- [Change 2]
- [Change 3]

### Why This Change

[Explanation of the problem being solved]

## Test Plan

- [ ] Added unit tests for [functionality]
- [ ] All existing tests pass (`cd core && pytest tests/ -v`)
- [ ] Linting passes (`make check`)
- [ ] Manual testing: [describe what you tested]

## Screenshots (if applicable)

[Add screenshots for UI changes]

---

Fixes #[issue-number]
```

---

## Validation Checklist

Before submitting your PR, verify:

- [ ] **Issue assigned to you** (except docs/micro-fixes)
- [ ] **Branch is up-to-date** with upstream/main
- [ ] **Code follows style guide** (PEP 8, type hints, docstrings)
- [ ] **Tests added/updated** for your changes
- [ ] **All tests pass** locally
- [ ] **Commit messages** follow conventional format
- [ ] **PR description** references the issue (`Fixes #123`)
- [ ] **Documentation updated** if adding new features

---

## Common Commands

```bash
# Stay updated
git fetch upstream && git merge upstream/main

# Run tests
cd core && python -m pytest tests/ -v

# Run linting
make check

# View issue
gh issue view <number> --repo adenhq/hive

# Create PR
gh pr create --title "type(scope): description" --body "..."

# Check PR status
gh pr status --repo adenhq/hive
```

---

## Getting Help

- **Discord**: https://discord.com/invite/MXE49hrKDk
- **Issues**: Ask questions in the issue thread
- **Docs**: Read CONTRIBUTING.md, DEVELOPER.md

---

## Anti-Patterns to Avoid

| Don't | Do Instead |
|-------|------------|
| Submit PR without issue assignment | Comment and wait for assignment |
| Create huge PRs with multiple features | One focused change per PR |
| Skip tests | Add tests for your changes |
| Ignore review feedback | Respond promptly and collaboratively |
| Push to main directly | Always use feature branches |
| Copy-paste without understanding | Study existing patterns first |
