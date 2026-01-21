---
name: testing-agent
description: Run goal-based evaluation tests for agents. Use when you need to verify an agent meets its goals, debug failing tests, or iterate on agent improvements based on test results.
---

# Testing Agents

Run goal-based evaluation tests for agents built with the building-agents skill.

## Quick Start

1. **Check existing state first** - See if tests already exist
2. Generate tests from goal (only if needed)
3. Approve tests (mandatory human approval)
4. Run tests against agent
5. Debug failures and iterate

## Check Existing State First

**CRITICAL**: Before generating any tests, ALWAYS check if tests already exist for the goal.

```python
# Check what tests exist for this goal
result = list_tests(goal_id="youtube-research")

# Returns:
{
    "goal_id": "youtube-research",
    "total": 42,
    "by_status": {
        "pending": 10,
        "approved": 30,
        "modified": 2,
        "rejected": 0
    },
    "by_type": {
        "constraint": 15,
        "success_criteria": 25,
        "edge_case": 2
    },
    "tests": [...]  # List of test summaries
}
```

### Decision Tree

Based on existing state, choose the right action:

```
list_tests(goal_id) → Check existing tests
        ↓
┌───────┴────────────────────────────────────────┐
│                                                │
No tests exist                    Tests exist
│                                      │
↓                            ┌─────────┴─────────┐
Generate tests               │                   │
(constraint first,           Has pending         All approved
then success_criteria)       tests               │
                             │                   ↓
                             ↓                   Run tests
                             Approve pending     directly
                             tests first
```

### Resuming a Testing Session

When the user asks to test an agent that may have been tested before:

1. **Always check first**: `list_tests(goal_id="...")`
2. **Show the user what exists**:
   - "Found 42 existing tests: 30 approved, 10 pending, 2 modified"
   - "Last run: 28/30 passed (93.3%)"
3. **Ask what they want to do**:

```python
AskUserQuestion(
    questions=[{
        "question": "Tests already exist for this agent. What would you like to do?",
        "header": "Existing Tests",
        "options": [
            {
                "label": "Run existing tests (Recommended)",
                "description": "Run the 32 approved tests against the agent"
            },
            {
                "label": "Approve pending tests",
                "description": "Review and approve the 10 pending tests first"
            },
            {
                "label": "Regenerate all tests",
                "description": "Delete existing and generate fresh tests (loses approvals)"
            },
            {
                "label": "Show test details",
                "description": "List all tests with their status and last results"
            }
        ],
        "multiSelect": false
    }]
)
```

### Why This Matters

- **Saves time**: Approved tests don't need re-approval
- **Preserves work**: User's previous approvals/modifications are kept
- **Clear state**: User knows exactly what exists before taking action
- **Prevents duplicates**: Won't generate tests that already exist

## Core Concepts

**Test Types**: Three types of tests, generated at different stages:
- `constraint` - Generated during Goal stage (agent-agnostic boundaries)
- `success_criteria` - Generated during Eval stage (after agent exists)
- `edge_case` - Generated when new scenarios discovered during debugging

**Approval**: All LLM-generated tests require explicit user approval before running.

**Error Categories**: Failed tests are categorized to guide iteration:
- `LOGIC_ERROR` - Goal definition is wrong → Update goal, restart full flow
- `IMPLEMENTATION_ERROR` - Code bug → Fix agent, re-run Eval
- `EDGE_CASE` - New scenario discovered → Add test, continue Eval

**Iteration**: Each error category has a specific fix path (see Error Categorization section).

## Workflow (HITL Required)

**CRITICAL**: Each step requires human approval before proceeding.
**CRITICAL**: Use structured questions (AskUserQuestion) with fallback to text mode.

### Approval Strategy

**Always try structured questions first**, with graceful fallback:

1. **Attempt**: Call AskUserQuestion with clickable options
2. **Catch**: If tool fails/rejected, fall back to text prompt
3. **Parse**: Accept text input like "approve", "reject", "skip"

This ensures the workflow works in all environments (VSCode extension, CLI, web).

### Test Loop

```
For each test generated:
1. DISPLAY → Show the test details to the human
2. VALIDATE → Check test syntax and structure
3. ASK APPROVAL → Use AskUserQuestion with clickable options
4. Only run tests after approval
```

### Checklist (ask approval at each check)

```
Agent Testing Progress:
- [ ] Load goal and agent → VERIFY PATHS
- [ ] CHECK EXISTING TESTS → list_tests, show stats, ask what to do
- [ ] If no tests OR user wants fresh: Generate tests → ASK APPROVAL
- [ ] If pending tests exist: Approve pending tests first
- [ ] Run all approved tests → SHOW RESULTS
- [ ] Debug failed tests → SHOW CATEGORIZATION
- [ ] Iterate based on category → ASK APPROVAL for changes
```

## The Three-Stage Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           GOAL STAGE                                     │
│  1. Define success_criteria and constraints (building-agents skill)      │
│  2. Generate CONSTRAINT TESTS → USER APPROVAL → tests stored             │
└─────────────────────────────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          AGENT STAGE                                     │
│  Build nodes + edges (building-agents skill)                             │
│  Constraint tests can run during development for early feedback          │
└─────────────────────────────────────────────────────────────────────────┘
                                   ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                           EVAL STAGE (this skill)                        │
│  1. Generate SUCCESS_CRITERIA TESTS → USER APPROVAL → tests stored       │
│  2. Run all tests in parallel → pass/fail summary                        │
│  3. On failure → Debug tool with categorization                          │
│  4. Iterate based on error category                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Test Generation

### When to Generate Each Type

| Test Type | When Generated | Why |
|-----------|----------------|-----|
| **Constraint Tests** | During Goal stage (before agent exists) | Constraints are agent-agnostic boundaries |
| **Success Criteria Tests** | During Eval stage (after agent exists) | May depend on agent flow/nodes |
| **Edge Case Tests** | During debugging (when new scenario found) | Discovered through test failures |

### Generating Tests

```python
import json

# 1. Generate constraint tests (Goal stage)
result = generate_constraint_tests(
    goal_id="youtube-research",
    goal_json=json.dumps({
        "id": "youtube-research",
        "name": "YouTube Research Agent",
        "description": "Find relevant YouTube videos on a topic",
        "success_criteria": [
            {
                "id": "find_videos",
                "description": "Find 3-5 relevant videos",
                "metric": "video_count",
                "target": "3-5",
                "weight": 1.0
            }
        ],
        "constraints": [
            {
                "id": "api_limits",
                "description": "Must respect YouTube API rate limits",
                "constraint_type": "hard",
                "category": "reliability",
                "check": "llm_judge"  # Optional: how to validate
            }
        ]
    })
)

# 2. Generate success criteria tests (Eval stage, after agent built)
result = generate_success_tests(
    goal_id="youtube-research",
    goal_json='...',  # Same structure as above
    node_names="search_node,filter_node,format_node",
    tool_names="youtube_search,video_details"
)
```

**After generation**, tests are stored as PENDING. They must be approved before running.

## Approval Patterns

### Interactive Approval Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Generated Tests for: youtube-research (3 tests)                  │
├─────────────────────────────────────────────────────────────────┤
│ [1/3] test_find_videos_happy_path                               │
│       Type: SUCCESS_CRITERIA                                     │
│       Confidence: 92%                                            │
│       Input: {"topic": "machine learning tutorials"}             │
│       Expected: 3-5 videos with titles and IDs                   │
│                                                                  │
│       def test_find_videos_happy_path(agent):                    │
│           result = agent.run({"topic": "machine learning"})      │
│           assert 3 <= len(result.videos) <= 5                    │
│           assert all(v.title for v in result.videos)             │
│                                                                  │
│       [a]pprove  [r]eject  [e]dit  [s]kip                       │
└─────────────────────────────────────────────────────────────────┘
```

### Approval Actions

| Action | Description | Result |
|--------|-------------|--------|
| **approve** | Accept test as-is | Status → APPROVED, test will run |
| **reject** | Decline with reason | Status → REJECTED, test won't run |
| **edit** | Modify code before accepting | Status → MODIFIED, original preserved |
| **skip** | Leave for later | Status → PENDING, decide later |

### Approval Code Pattern

```python
# After generating tests, approve them
result = approve_tests(
    goal_id="youtube-research",
    approvals='[
        {"test_id": "test_001", "action": "approve"},
        {"test_id": "test_002", "action": "modify", "modified_code": "def test_..."},
        {"test_id": "test_003", "action": "reject", "reason": "Not a valid scenario"},
        {"test_id": "test_004", "action": "skip"}
    ]'
)
```

### Structured Approval Questions

```python
# Try structured approval first
try:
    response = AskUserQuestion(
        questions=[{
            "question": "Do you approve this test?",
            "header": "Test Approval",
            "options": [
                {
                    "label": "Approve (Recommended)",
                    "description": "Test looks good, include in test suite"
                },
                {
                    "label": "Reject",
                    "description": "Test is invalid or unnecessary"
                },
                {
                    "label": "Edit",
                    "description": "Modify the test code before accepting"
                },
                {
                    "label": "Skip",
                    "description": "Decide later, leave as pending"
                }
            ],
            "multiSelect": false
        }]
    )
except:
    # Fallback to text mode
    print("Do you approve this test? Type: approve | reject | edit | skip")
```

## Test Execution

### Parallel Configuration

```python
# Tests run in parallel with these defaults
ParallelConfig(
    num_workers=cpu_count(),    # Use all CPU cores
    timeout_per_test=60.0,      # 60 seconds per test
    fail_fast=False,            # Run all tests, don't stop on first failure
    mode="loadfile",            # Group tests by parent_criteria_id
)
```

### Running Tests

```python
# Run all approved tests
result = run_tests(
    goal_id="youtube-research",
    agent_path="exports/youtube-agent",
    test_types='["all"]',  # or ["constraint", "success_criteria", "edge_case"]
    parallel=4,            # Number of workers
    fail_fast=False        # Run all tests
)

# Result structure
{
    "goal_id": "youtube-research",
    "overall_passed": false,
    "summary": {
        "total": 15,
        "passed": 12,
        "failed": 3,
        "pass_rate": "80.0%"
    },
    "duration_ms": 5432,
    "results": [
        {"test_id": "test_001", "passed": true, "duration_ms": 234},
        {"test_id": "test_002", "passed": false, "duration_ms": 567, "error_category": "IMPLEMENTATION_ERROR"},
        ...
    ]
}
```

### Execution Flow

1. Load only APPROVED and MODIFIED tests (skip PENDING and REJECTED)
2. Group tests by `parent_criteria_id` for shared fixture setup
3. Run groups in parallel with process isolation
4. Aggregate results with timing information

## Error Categorization & Iteration

### Decision Tree

```
Test Fails → Categorize Error
                ↓
    ┌───────────┴─────────────────┬────────────────────┐
    │                             │                    │
LOGIC ERROR               IMPLEMENTATION ERROR      EDGE CASE
(criteria wrong)          (code bug)                (new scenario)
    │                             │                    │
    ↓                             ↓                    ↓
Update goal               Fix nodes/edges          Generate new
success_criteria          in Agent stage           edge case test
    ↓                             ↓                    │
FULL 3-STEP               Re-run Eval              Continue in
FLOW RESTART              (skip Goal stage)        Eval stage
```

### Pattern-Based Heuristics

The categorizer uses these patterns to classify errors:

**LOGIC_ERROR** (goal definition is wrong):
- "goal not achieved"
- "constraint violated: core"
- "fundamental assumption"
- "success criteria mismatch"
- "expected behavior incorrect"

**IMPLEMENTATION_ERROR** (code bug in agent):
- TypeError, AttributeError, KeyError, ValueError
- "tool call failed"
- "node execution error"
- "assertion failed"
- "null pointer", "undefined"

**EDGE_CASE** (new scenario discovered):
- "boundary condition"
- "timeout", "rate limit"
- "empty result", "no results"
- "unexpected format"
- "rare input", "unusual"

### Iteration Guidance

```python
# After categorization, you get guidance
{
    "error_category": "IMPLEMENTATION_ERROR",
    "iteration_guidance": {
        "stage": "Agent",
        "action": "Fix the code in nodes/edges",
        "restart_required": false,
        "description": "The goal is correct, but the implementation has a bug. Fix the agent code and re-run Eval."
    }
}
```

| Category | Go To Stage | Restart Required | Action |
|----------|-------------|------------------|--------|
| LOGIC_ERROR | Goal | Yes | Update success_criteria/constraints, rebuild agent |
| IMPLEMENTATION_ERROR | Agent | No | Fix nodes/edges, re-run Eval only |
| EDGE_CASE | Eval | No | Generate edge case test, continue in Eval |

## Debugging Failed Tests

### Debug Tool

```python
# Get detailed debug info for a failed test
result = debug_test(
    goal_id="youtube-research",
    test_id="test_find_videos_no_results"
)

# Returns comprehensive debug info
{
    "test_id": "test_find_videos_no_results",
    "test_name": "test_find_videos_no_results",
    "input": {"topic": "xyzabc123nonsense"},
    "expected": {"videos": [], "message": "No results found"},
    "actual": {"error": "NullPointerException at node_3"},
    "passed": false,
    "error_message": "TypeError: 'NoneType' has no attribute 'get'",
    "error_category": "IMPLEMENTATION_ERROR",
    "stack_trace": "Traceback (most recent call last):\n  ...",
    "logs": [
        {"timestamp": "...", "node": "search_node", "level": "INFO", "msg": "..."},
        {"timestamp": "...", "node": "filter_node", "level": "ERROR", "msg": "..."}
    ],
    "runtime_data": {
        "execution_path": ["start", "search_node", "filter_node"],
        "node_outputs": {...}
    },
    "suggested_fix": "Check null handling in filter_node when no results returned",
    "iteration_guidance": {
        "stage": "Agent",
        "action": "Fix the code in nodes/edges",
        "restart_required": false
    }
}
```

### Debug Workflow

1. **Run all tests** → Get pass/fail summary
2. **Select failed test** → Get detailed DebugInfo
3. **Review categorization** → Understand error type
4. **Check suggested fix** → Get actionable guidance
5. **Follow iteration guidance** → Go to correct stage

## Example: Testing YouTube Agent

See [examples/testing-youtube-agent.md](examples/testing-youtube-agent.md) for a complete walkthrough.

## Common Patterns

### Happy Path Tests
Test normal successful execution with valid inputs:
```python
def test_find_videos_happy_path(agent):
    result = agent.run({"topic": "python tutorials"})
    assert result.success
    assert len(result.videos) >= 3
    assert all(v.title for v in result.videos)
```

### Boundary Condition Tests
Test exactly at target thresholds:
```python
def test_find_videos_minimum_count(agent):
    result = agent.run({"topic": "very specific niche topic"})
    assert len(result.videos) >= 1  # At least one result
```

### Error Handling Tests
Test graceful handling of failures:
```python
def test_find_videos_invalid_input(agent):
    result = agent.run({"topic": ""})  # Empty input
    assert not result.success or result.message == "Invalid input"
```

### Constraint Violation Tests
Test that constraints are respected:
```python
def test_api_rate_limit_respected(agent):
    # Run multiple times quickly
    for _ in range(5):
        result = agent.run({"topic": "test"})
    # Should not hit rate limit errors
    assert "rate limit" not in str(result).lower()
```

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Auto-approve tests | Always require explicit user approval |
| Run PENDING/REJECTED tests | Only run APPROVED/MODIFIED tests |
| Generate success tests during Goal stage | Wait until agent exists |
| Treat all failures the same | Categorize and iterate appropriately |
| Restart full flow for IMPLEMENTATION_ERROR | Fix agent, re-run Eval only |
| Add test for LOGIC_ERROR | Fix the goal definition instead |
| Ignore confidence scores | Review low-confidence categorizations manually |
| Skip the approval step | Tests must be reviewed before running |

## Tools Reference

### Testing Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `generate_constraint_tests` | Generate tests from goal constraints | Goal stage |
| `generate_success_tests` | Generate tests from success criteria | Eval stage (after agent built) |
| `approve_tests` | Approve/reject/modify generated tests | After generation |
| `run_tests` | Execute tests in parallel | After approval |
| `debug_test` | Analyze failed test with categorization | After test fails |
| `list_tests` | List tests for a goal by status | Anytime |
| `get_pending_tests` | Get tests awaiting approval | Before approval |

### Building Tools (for iteration)

When iteration requires modifying the agent, use these from the building-agents skill:

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `set_goal` | Update goal definition | LOGIC_ERROR iteration |
| `add_node` | Add or modify nodes | IMPLEMENTATION_ERROR iteration |
| `add_edge` | Add or modify edges | IMPLEMENTATION_ERROR iteration |
| `validate_graph` | Validate changes | After any modification |
| `export_graph` | Re-export agent | After fixes complete |

## CLI Commands

```bash
# Generate tests from goal
python -m core test-generate goal.json --type all

# Interactive approval of pending tests
python -m core test-approve <goal_id>

# Run tests for an agent
python -m core test-run <agent_path> --goal <goal_id> --parallel 4

# Debug a failed test
python -m core test-debug <goal_id> <test_id>

# List tests by status
python -m core test-list <goal_id> --status approved

# Show test statistics
python -m core test-stats <goal_id>
```

## Integration with building-agents

### Handoff Points

| Scenario | From | To | Action |
|----------|------|-----|--------|
| Agent built, ready to test | building-agents | testing-agent | Generate success tests |
| LOGIC_ERROR found | testing-agent | building-agents | Update goal, rebuild |
| IMPLEMENTATION_ERROR found | testing-agent | building-agents | Fix nodes/edges |
| EDGE_CASE found | testing-agent | testing-agent | Generate edge case test |
| All tests pass | testing-agent | Done | Agent is validated |

### When to Switch Skills

**Use building-agents when:**
- Defining goals and constraints
- Building agent nodes and edges
- Fixing LOGIC_ERROR or IMPLEMENTATION_ERROR

**Use testing-agent when:**
- Generating tests from goals
- Approving and running tests
- Debugging failures
- Categorizing errors

### Shared Patterns

Both skills use:
- AskUserQuestion with structured options
- HITL at every critical step
- Fallback to text mode when widgets unavailable
- Session state management for continuity
