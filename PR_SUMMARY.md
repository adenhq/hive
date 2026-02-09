# PR Summary: Fix Graph-Level max_retries_per_node

## Issue
Fixes #4135 - Graph-level max_retries_per_node is ignored when node max_retries is unset

## Problem
The executor was using a hardcoded default of 3 retries when `NodeSpec.max_retries` was not explicitly set, completely ignoring the `GraphSpec.max_retries_per_node` configuration. This made graph-level retry policies unreliable.

## Solution
1. **Changed NodeSpec.max_retries default from `3` to `None`**
   - When `None`, the node inherits from `graph.max_retries_per_node`
   - When explicitly set, the node value takes precedence

2. **Updated executor retry logic in two places:**
   - Main execution loop (`executor.py` line 663)
   - Parallel execution/fanout branches (`executor.py` line 1487)

3. **Added comprehensive test coverage:**
   - New test: `test_executor_uses_graph_level_max_retries_when_node_unset`
   - Updated existing tests to reflect new behavior

## Changes Made

### Files Modified
- `core/framework/graph/node.py` - Changed max_retries default to None
- `core/framework/graph/executor.py` - Added fallback logic (2 locations)
- `core/tests/test_executor_max_retries.py` - Added new test + updated existing
- `core/tests/test_event_loop_wiring.py` - Updated assertion for new default

### Testing
✅ All 682 tests pass
✅ Linting checks pass (ruff)
✅ New test verifies graph-level fallback
✅ Existing tests verify backward compatibility

## Behavior Changes

### Before
```python
# Node without max_retries always used 3 retries
node = NodeSpec(id="n", name="N", description="test")
# node.max_retries = 3 (hardcoded)

graph = GraphSpec(max_retries_per_node=5, ...)
# Graph setting ignored! Node still uses 3
```

### After
```python
# Node without max_retries inherits from graph
node = NodeSpec(id="n", name="N", description="test")
# node.max_retries = None (inherits from graph)

graph = GraphSpec(max_retries_per_node=5, ...)
# Node now uses 5 retries from graph setting ✓
```

## Next Steps

1. **Push to your fork:**
   ```bash
   git push origin fix/graph-level-max-retries
   ```

2. **Open PR on GitHub:**
   - Go to: https://github.com/adenhq/hive/compare
   - Select your fork and branch
   - Use the PR template below

3. **Comment on issue #4135:**
   "I've submitted PR #XXXX to fix this issue. The change makes nodes inherit graph-level max_retries_per_node when not explicitly set."

---

## PR Template

```markdown
## Description
Fixes #4135 - Graph-level `max_retries_per_node` now properly applies when node `max_retries` is unset

## Problem
The executor was ignoring `GraphSpec.max_retries_per_node` and using a hardcoded default of 3 retries when `NodeSpec.max_retries` was not explicitly set. This made graph-level retry configuration unreliable and contradicted operator expectations.

## Solution
- Changed `NodeSpec.max_retries` default from `3` to `None`
- Updated executor to check node-level first, then fall back to graph-level
- Applied fallback logic in both sequential and parallel execution paths
- Added test to verify graph-level fallback behavior

## Changes
- Modified `executor.py` retry logic (2 locations: main loop + parallel execution)
- Updated `node.py` to make `max_retries` optional with `None` default
- Added test case `test_executor_uses_graph_level_max_retries_when_node_unset()`
- Updated existing tests to reflect new default behavior

## Testing
- ✅ All 682 existing tests pass
- ✅ New test verifies graph-level fallback
- ✅ Fanout/parallel execution tests pass
- ✅ Linting checks pass (`ruff check` + `ruff format --check`)

## Backward Compatibility
Nodes that explicitly set `max_retries` continue to work as before. Only nodes that rely on the default now inherit from graph-level configuration instead of using a hardcoded value.

## Checklist
- [x] Tests added/updated
- [x] `make check` passes
- [x] `make test` passes
- [x] Documentation updated (inline comments)
- [x] Linked to issue #4135
```

---

## Impact
This fix makes graph-level retry configuration work as expected, allowing operators to set a single retry policy for all nodes that don't need custom retry behavior. This is especially useful for:
- Multi-node graphs with consistent retry requirements
- Dynamic agent generation where nodes inherit sensible defaults
- Production deployments with standardized error handling policies
