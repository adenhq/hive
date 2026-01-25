# Issue: Fix Windows Unicode Encoding Error in Storage Backends

## Status: ✅ RESOLVED

**Issue Discovered By:** sandeepnaik  
**Resolution Date:** January 2026  
**Resolved By:** sandeepnaik  

---

## Summary

File storage operations across multiple modules fail on Windows due to missing UTF-8 encoding, causing `UnicodeEncodeError` when saving data containing Unicode characters like `✓` and `✗`.

## Affected Files

| File | Status |
|------|--------|
| `core/framework/storage/backend.py` | ✅ Fixed |
| `core/framework/testing/test_storage.py` | ✅ Fixed |
| `core/framework/mcp/agent_builder_server.py` | ✅ Fixed |

## Problem

When running on Windows, file operations use the default system encoding (cp1252), which cannot encode Unicode characters used in decision summaries:

```python
# In decision.py line 170:
status = "✓" if self.was_successful else "✗"
```

This causes 10+ tests to fail with:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2717' in position 264: character maps to <undefined>
```

## Root Cause

All `open()` calls in storage backends were missing `encoding="utf-8"`:

```python
# Before (broken on Windows)
with open(file_path, "w") as f:
    f.write(data)

# After (cross-platform)
with open(file_path, "w", encoding="utf-8") as f:
    f.write(data)
```

## Solution Implemented

Added `_open_utf8()` helper function to each affected file:

```python
def _open_utf8(path: Path, mode: str = "r") -> TextIO:
    """Open a file with UTF-8 encoding for cross-platform compatibility."""
    return open(path, mode, encoding="utf-8")
```

Updated all file operations to use this helper instead of raw `open()`.

## Files Changed

### 1. `core/framework/storage/backend.py`
- Added `_open_utf8()` helper
- Updated 7 file operations: `save_run`, `load_run`, `load_summary`, `_get_index`, `_add_to_index`, `_remove_from_index`

### 2. `core/framework/testing/test_storage.py`
- Added `_open_utf8()` helper
- Updated 8 file operations: `save_test`, `load_test`, `save_result`, `get_latest_result`, `get_result_history`, `_get_index`, `_add_to_index`, `_remove_from_index`

### 3. `core/framework/mcp/agent_builder_server.py`
- Added `_open_utf8()` helper
- Updated 9 file operations: session save/load functions, export functions

## Test Results

Before fix: **174 passed, 10 failed**  
After fix: **184 passed** ✅

## Impact

- Framework now works correctly on Windows
- Unicode characters in decision summaries are properly saved/loaded
- Cross-platform compatibility improved
