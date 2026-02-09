# 🎯 Your Hive Contribution Roadmap

## ✅ COMPLETED: Issue #4135 - Graph-level max_retries

**Status:** Ready to submit PR
**Branch:** `fix/graph-level-max-retries`
**Commit:** a30ae9a

### What You Fixed
- Graph-level `max_retries_per_node` now properly applies when node doesn't set `max_retries`
- Updated executor logic in 2 places (sequential + parallel execution)
- Added comprehensive test coverage
- All 682 tests pass ✅

### Next Actions (DO THIS NOW)

1. **Comment on Issue #4135 to claim it:**
   ```
   I'd like to work on this issue. I've investigated the executor retry logic
   and have a fix ready with tests. Will submit PR shortly.
   ```
   Link: https://github.com/adenhq/hive/issues/4135

2. **Push your branch:**
   ```bash
   cd /home/ahsan2411/projects/hive-hello/hive
   git push origin fix/graph-level-max-retries
   ```

3. **Create PR on GitHub:**
   - Go to: https://github.com/adenhq/hive/compare
   - Click "compare across forks"
   - Base: `adenhq/hive` `main`
   - Head: `ahn009/hive` `fix/graph-level-max-retries`
   - Use PR template from `PR_SUMMARY.md`

4. **After PR is created, comment on issue:**
   ```
   Submitted PR #XXXX to fix this issue.
   ```

---

## 📋 PHASE 2: Test Coverage (Week 2)

### Option A: HubSpot Tool Tests (RECOMMENDED)
**Why:** No tests exist, high-value integration, clear scope

**Files to create:**
- `tools/tests/tools/test_hubspot_tool.py`

**Pattern to follow:**
- Look at `tools/tests/tools/test_slack_tool.py` (38KB, comprehensive)
- Look at `tools/tests/tools/test_github_tool.py` (22KB, good structure)

**Test cases needed:**
1. Authentication/credential handling
2. Contact CRUD operations
3. Deal/pipeline operations
4. Error handling (rate limits, invalid data)
5. Pagination
6. Webhook handling (if applicable)

**Steps:**
```bash
# 1. Find/create issue for HubSpot tests
# Search: https://github.com/adenhq/hive/issues?q=hubspot+test

# 2. If no issue exists, create one:
# Title: [Test Coverage] Add comprehensive tests for HubSpot tool
# Body: Currently the HubSpot integration lacks test coverage. 
#       This PR adds comprehensive tests following patterns from 
#       existing tool tests (Slack, GitHub).

# 3. Create branch
git checkout main
git pull upstream main
git checkout -b test/hubspot-tool-coverage

# 4. Create test file
# Copy structure from test_slack_tool.py
# Adapt for HubSpot API patterns

# 5. Run tests
cd tools && uv run pytest tests/tools/test_hubspot_tool.py -v

# 6. Commit and push
git add tools/tests/tools/test_hubspot_tool.py
git commit -m "test(tools): add comprehensive HubSpot tool tests

- Add authentication tests
- Add CRUD operation tests  
- Add error handling tests
- Add pagination tests
- Follow patterns from existing tool tests"
git push origin test/hubspot-tool-coverage
```

### Option B: Runtime Logs Tool Enhancement
**Why:** Has basic tests, needs edge cases

**File to enhance:**
- `tools/tests/tools/test_runtime_logs_tool.py` (currently 11KB)

**Additional tests needed:**
1. Concurrent access scenarios
2. Large log file handling
3. Log rotation edge cases
4. Memory efficiency tests
5. Error recovery tests

---

## 📋 PHASE 3: Documentation (Week 3)

### Issue #4166: Beginner Onboarding Documentation

**Files to improve:**
- `docs/getting-started.md`
- `docs/environment-setup.md`
- Possibly create `docs/troubleshooting.md`

**Improvements needed:**
1. **Common Pitfalls section:**
   - Windows WSL requirements
   - Python version issues
   - API key configuration
   - Virtual environment problems

2. **Visual diagrams:**
   - Agent execution flow
   - Node → Edge → Node visualization
   - Memory flow diagram

3. **Quick troubleshooting:**
   - "Command not found" → use `uv run`
   - "Import errors" → check PYTHONPATH
   - "Tests failing" → check virtual env

4. **First agent walkthrough:**
   - Step-by-step with screenshots
   - Expected output at each step
   - How to debug when things go wrong

**Steps:**
```bash
# 1. Comment on issue #4166
# 2. Create branch
git checkout -b docs/improve-beginner-onboarding

# 3. Make improvements
# 4. Test locally (render markdown)
# 5. Submit PR
```

---

## 📋 PHASE 4: Integration (Week 4+)

### Build Notion Integration Tool

**Why:**
- Mentioned in issue #4148
- High demand (productivity tool)
- Clear API documentation
- Shows full-stack capability

**Files to create:**
- `tools/src/aden_tools/tools/notion_tool/`
  - `__init__.py`
  - `notion_tool.py`
  - `README.md`
- `tools/tests/tools/test_notion_tool.py`

**Features to implement:**
1. Database operations (query, create, update)
2. Page operations (read, create, update)
3. Block operations (read, append)
4. Search functionality
5. Webhook support

**Pattern to follow:**
- Look at `tools/src/aden_tools/tools/slack_tool/`
- Look at `tools/src/aden_tools/tools/github_tool/`

**Steps:**
```bash
# 1. Check issue #2805 for integration guidelines
# 2. Create proposal issue if needed
# 3. Implement tool following existing patterns
# 4. Add comprehensive tests
# 5. Update BUILDING_TOOLS.md with Notion example
# 6. Submit PR
```

---

## 🎯 Success Metrics

### Week 1 (Current)
- ✅ 1 bug fix PR (#4135)
- ✅ Demonstrates code understanding
- ✅ Shows testing discipline

### Week 2
- 🎯 1 test coverage PR
- 🎯 Demonstrates quality focus
- 🎯 Shows attention to edge cases

### Week 3
- 🎯 1 documentation PR
- 🎯 Demonstrates communication skills
- 🎯 Shows empathy for new users

### Week 4+
- 🎯 1 integration PR
- 🎯 Demonstrates full-stack capability
- 🎯 Shows initiative and creativity

---

## 📞 Communication Tips

### In Issues:
- Be specific about what you'll do
- Ask clarifying questions if needed
- Update progress regularly
- Be responsive to feedback

### In PRs:
- Clear description of problem + solution
- Link to related issues
- Show test results
- Respond to reviews within 24 hours

### Example Comments:

**Claiming an issue:**
```
I'd like to work on this. My approach:
1. [Specific step]
2. [Specific step]
3. [Specific step]

Expected timeline: [X days]
Any concerns or suggestions before I start?
```

**Updating progress:**
```
Update: Completed [X], currently working on [Y].
Encountered [issue], resolved by [solution].
On track for completion by [date].
```

**Responding to review:**
```
Thanks for the feedback! I've addressed:
- ✅ [Comment 1] - Fixed in commit abc123
- ✅ [Comment 2] - Updated approach as suggested
- ❓ [Comment 3] - Could you clarify [specific question]?
```

---

## 🚀 Quick Reference

### Run Tests
```bash
# Specific test file
cd core && uv run pytest tests/test_executor_max_retries.py -v

# All core tests
cd hive && make test

# Specific tool tests
cd tools && uv run pytest tests/tools/test_slack_tool.py -v
```

### Run Linting
```bash
cd hive && make check
# or
cd core && uv run ruff check . && uv run ruff format --check .
```

### Git Workflow
```bash
# Start new feature
git checkout main
git pull upstream main
git checkout -b feature/my-feature

# Commit
git add <files>
git commit -m "type(scope): description"

# Push
git push origin feature/my-feature

# Update from upstream
git fetch upstream
git rebase upstream/main
```

---

## 📚 Resources

- **Contributing Guide:** `CONTRIBUTING.md`
- **PR Requirements:** `docs/pr-requirements.md`
- **Building Tools:** `tools/BUILDING_TOOLS.md`
- **Architecture:** `docs/architecture/README.md`
- **Discord:** https://discord.com/invite/MXE49hrKDk

---

## 🎉 You're Ready!

Your first PR is complete and ready to submit. Follow the steps above to:
1. Comment on issue #4135
2. Push your branch
3. Create the PR
4. Start planning Phase 2

Good luck! 🚀
