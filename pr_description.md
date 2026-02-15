# PR Description

## Title
fix(examples): resolve bugs in deep_research_agent and upgrade documentation

## Description
This PR addresses critical linting errors in the `deep_research_agent` template and significantly upgrades its documentation to match the project's high standards.

### 1. Bug Fixes in `deep_research_agent/agent.py`
- **Fixed `F821` Undefined Name Errors**: 
    - Imported missing `GraphExecutor`.
    - Updated `_setup()` method to accept `mock_mode` argument, fixing a scope issue where `mock_mode` was accessed but not defined.
- **Verification**: `ruff check .` now passes cleanly.

### 2. Documentation Overhaul
- **Upgraded `deep_research_agent/README.md`**: 
    - The original README was minimal. I have rewritten it to match the "gold standard" of `examples/templates/inbox_management`.
    - Added **Architecture** section with Mermaid diagram flow and detailed node descriptions.
    - Added **Goal Criteria** section listing specific Success Criteria and Constraints.
    - Improved **Usage** instructions with both CLI and Python API examples.

### 3. Fixed Broken Test Suite
- **Resolves `ModuleNotFoundError: No module named 'core'`**:
    - The test suite was failing because tests were importing from `core.framework` (directory path) instead of `framework` (package name).
    - Fixed imports across `core/` directory.
- **Verification**: `pytest` now passes with **859 tests passed**.

### 4. CI Pipeline Improvement
- **Closed CI Gap**:
    - The original bugs went unnoticed because CI only linted `core/` and `tools/`.
    - I updated `.github/workflows/ci.yml` to also lint `examples/templates/`, preventing future regressions in user-facing templates.

### 5. Security Enhancement: Log Redaction
- **Feature**:
    - Added automatic redaction for sensitive patterns (`sk-...`, `ghp_...`, `Bearer ...`) in logs.
    - Implemented in `core/framework/observability/logging.py` for both JSON and human-readable formats.
    - Verified with new test suite `core/tests/test_redaction.py`.

## Type of Change
- [x] Bug fix (non-breaking change which fixes an issue)
- [x] Documentation update
- [x] Test fix (fixes broken test suite)
- [x] CI/CD improvement (adds missing lint checks)
- [x] Security patch (log redaction)

## How Has This Been Tested?
- [x] Static analysis: Ran `ruff check .` and confirmed zero errors.
- [x] Test Suite: Ran `pytest` in `core/` and confirmed 859 tests passed.
- [x] CI Check: Verified `ruff check examples/templates` passes locally.
- [x] Manual inspection: Verified `agent.json` align with code.
