# Example: File Monitor Agent

This example shows the complete agent-workflow in action for building a file monitoring agent.

## Initial Request

```
User: "Build an agent that monitors ~/Downloads and copies new files to ~/Documents"
```

## Phase 1: Building (20 minutes)

### Step 1: Create Structure

Agent invokes `/building-agents` skill and:

1. Creates `exports/file_monitor_agent/` package
2. Writes skeleton files (__init__.py, __main__.py, agent.py, etc.)

**Output**: Package structure visible immediately

### Step 2: Define Goal

```python
goal = Goal(
    id="file-monitor-copy",
    name="Automated File Monitor & Copy",
    success_criteria=[
        # 100% detection rate
        # 100% copy success
        # 100% conflict resolution
        # >99% uptime
    ],
    constraints=[
        # Preserve originals
        # Handle errors gracefully
        # Track state
        # Respect permissions
    ]
)
```

**Output**: Goal written to agent.py

### Step 3: Design Nodes

5 high-performance nodes approved and written incrementally:

1. `initialize-observer` - Set up observer
2. `event-listener` - Listens for file closed event
3. `filter-temp-files` - Ignores partial files
4. `zero-copy-transfer` - Moves data via kernel
5. `update-registry` - Mark as processed

**Output**: All nodes in nodes/__init__.py

### Step 4: Connect Edges

4 edges connecting the workflow loop:

```
initialize → observer
                ↓
         [OS SIGNAL: ON_CLOSED]
                ↓
         event-listener → filter → zero-copy-transfer → update
                                          ↑               ↓
                                          └────── < ──────┘
```

**Output**: Edges written to agent.py

### Step 5: Finalize

```bash
$ PYTHONPATH=core:exports python -m file_monitor_agent validate
✓ Agent is valid (Reactive Architecture Detected)

$ PYTHONPATH=core:exports python -m file_monitor_agent info
Agent: Optimized File Monitor & Copy
Nodes: 5
Edges: 4
```

**Phase 1 Complete**: Structure validated ✅

### Status After Phase 1

```
exports/file_monitor_agent/
├── __init__.py          ✅ (exports)
├── __main__.py          ✅ (CLI)
├── agent.py             ✅ (goal, reactive graph, agent class)
├── nodes/__init__.py    ✅ (5 optimized nodes)
├── config.py            ✅ (configuration)
├── implementations.py   ✅ (Watchdog & sendfile logic)
├── README.md            ✅ (documentation)
├── IMPLEMENTATION_GUIDE.md ✅ (next steps)
└── STATUS.md            ✅ (current state)
```

**Note**: Implementation gap exists - data flow needs connection (covered in STATUS.md)

## Phase 2: Testing (25 minutes)

### Step 1: Analyze Agent

Agent invokes `/testing-agent` skill and:

1. Reads goal from `exports/file_monitor_agent/agent.py`
2. Identifies 4 success criteria to test
3. Identifies 4 constraints to verify
4. Plans test coverage

### Step 2: Generate Tests

Creates test files:

```
exports/file_monitor_agent/tests/
├── conftest.py              (fixtures)
├── test_constraints.py      (4 constraint tests)
├── test_success_criteria.py (4 success tests)
└── test_edge_cases.py       (error handling)
```

Tests approved incrementally by user.

### Step 3: Run Tests

```bash
$ PYTHONPATH=core:exports pytest exports/file_monitor_agent/tests/

test_constraints.py::test_zero_cpu_idle           PASSED
test_constraints.py::test_kernel_copy_integrity   PASSED
test_success_criteria.py::test_instant_detection  PASSED
test_edge_cases.py::test_ignore_partial_files     PASSED

========================== 12 passed in 2.15s ==========================
```

**Phase 2 Complete**: All tests pass ✅

## Final Output

**Production-Ready Agent:**

```bash
# Run the agent
./RUN_AGENT.sh

# Or manually
PYTHONPATH=core:exports:tools/src python -m file_monitor_agent run
```

**Capabilities:**
- Monitors ~/Downloads continuously
- Copies new files to ~/Documents
- Resolves conflicts with timestamps
- Handles errors gracefully
- Tracks processed files
- Runs as background service

**Total Time**: ~45 minutes from concept to production

## Key Learnings

1. **Incremental building** - Files written immediately, visible throughout
2. **Validation early** - Structure validated before moving to implementation
3. **Test-driven** - Tests reveal real behavior
4. **Documentation included** - README, STATUS, and guides auto-generated
5. **Repeatable process** - Same workflow for any agent type

## Variations

**For simpler agents:**
- Fewer nodes (3-5 instead of 7)
- Simpler workflow (linear instead of looping)
- Faster build time (10-15 minutes)

**For complex agents:**
- More nodes (10-15+)
- Multiple subgraphs
- Pause/resume points for human-in-the-loop
- Longer build time (45-60 minutes)

The workflow scales to your needs!
