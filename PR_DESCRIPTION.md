# Fix Thread-Safe Stdout Capture in CodeSandbox

## Summary

Fixes #2283 - Concurrency bug where `sys.stdout` mutation in `execute()` is not thread-safe.

## Problem

The `execute()` method in `code_sandbox.py` directly mutates the global `sys.stdout` to capture execution output:

```python
old_stdout = sys.stdout
sys.stdout = captured_stdout = io.StringIO()
# ... execution ...
sys.stdout = old_stdout  # finally block
```

This is not thread-safe. In concurrent or multi-threaded executions, multiple sandbox runs can overwrite each other's `sys.stdout` state, causing:
- Cross-contamination of outputs between concurrent sandbox executions
- Corrupted or missing output
- Wrong buffer restoration

## Solution

Replaced direct `sys.stdout` mutation with Python's `contextlib.redirect_stdout()` context manager, which is the standard, thread-safe way to temporarily redirect stdout.

```python
from contextlib import redirect_stdout

captured_stdout = io.StringIO()
with redirect_stdout(captured_stdout):
    # ... execution ...
```

**Key benefits:**
- Uses an atomic context manager for proper cleanup
- Thread-safe implementation from Python's stdlib
- Cleaner code with automatic restoration on exceptions
- No `finally` block needed

## Changes

- **`core/framework/graph/code_sandbox.py`**: 
  - Replaced `sys.stdout` mutation with `redirect_stdout` context manager
  - Removed unused `sys` import
  - Added stdout capture to all exception handlers for consistency

- **`core/tests/test_code_sandbox.py`** (New):
  - Added `TestCodeSandboxBasics` - basic execution tests
  - Added `TestCodeSandboxThreadSafety` - concurrent execution tests that verify no cross-contamination
  - Added `TestCodeSandboxStdoutEdgeCases` - edge cases like multiline output and error handling

## Testing

The new test file includes:
1. **`test_concurrent_stdout_isolation`** - Runs 20 concurrent executions and verifies each captures only its own output
2. **`test_concurrent_variable_isolation`** - Verifies variable state doesn't leak between concurrent runs
3. **`test_concurrent_mixed_success_failure`** - Tests concurrent mix of successful and failing executions

## Checklist

- [x] Code follows project style guidelines
- [x] No breaking changes to public API
- [x] Added tests for the fix
- [x] All existing tests should pass (pending CI verification)
