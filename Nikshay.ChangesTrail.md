# Nikshay.ChangesTrail - Change Log
Date: 2026-01-29
Branch: NikshayReddy.UpdateTrails

## 1. Critical Fixes

### Python 3.14 Compatibility
- **File**: `core/framework/graph/safe_eval.py`
- **Issue**: `DeprecationWarning: ast.Num is deprecated`. The code was using AST visitors (`visit_Num`, `visit_Str`, `visit_NameConstant`) that are slated for removal in Python 3.14.
- **Fix**: Removed these deprecated methods. The `SafeEvalVisitor` now relies on the modern `visit_Constant` method (which was already implemented) to handle numbers, strings, and constants.

### Dependency Conflicts
- **File**: `core/pyproject.toml`
- **Issue**: Installation failed due to version conflicts with `websockets` and `rich` packages (clashing with other installed tools like `frida-tools`).
- **Fix**: Added explicit version constraints:
  - `websockets>=13.0,<14.0`
  - `rich>=10.14,<14.0`

### Setup Script Robustness
- **File**: `scripts/setup-python.sh`
- **Issue**: The script failed immediately if the `uv` package manager was not installed.
- **Fix**: 
  - Added a fallback mechanism to use standard `pip` and `venv` if `uv` is missing.
  - Improved Python executable detection on Windows (checking both `Scripts/` and `bin/` directories).

## 2. Improvements & Modifications

### Agent Visibility
- **File**: `core/examples/manual_agent.py`
- **Change**: Enabled logging by default (`logging.basicConfig(level=logging.INFO)`).
- **Reason**: To visualize the internal decision flow and graph execution steps during testing.

## 3. Execution Status
- **Action**: Ran `python core/examples/manual_agent.py`
- **Result**: Success.
  - The agent successfully executed the "Greet User" goal.
  - Path: `greeter` -> `uppercaser`.
  - Final Output: `HELLO, ALICE!`

## 4. Pending Recommendations
- **JSON Parsing**: Replace regex-based cleaning in `node.py` with a robust library like `json_repair`.
- **Type Safety**: strict type checking with `mypy` for `GraphExecutor`.
- **CLI Error Handling**: Improve user-friendly error messages in `cli.py`.
