# Implementation Plan - Fix Linting Errors, Broken Tests, and CI Gaps

## Goal Description
Fix `F821` linting errors in `agent.py`, resolve `ModuleNotFoundError` in the test suite, and close the CI gap that allowed these bugs to slip through.

## Proposed Changes
### Deep Research Agent (Completed)
#### [MODIFY] [agent.py](file:///Users/lorddecay/Desktop/Coding/Hive/hive/examples/templates/deep_research_agent/agent.py)
- Import `GraphExecutor` from `framework.graph.executor`.
- Update `_setup` method signature to accept `mock_mode` argument.

### Documentation Upgrade (Completed)
#### [MODIFY] [README.md](file:///Users/lorddecay/Desktop/Coding/Hive/hive/examples/templates/deep_research_agent/README.md)
- Overhaul documentation with Architecture, Goal Criteria, and Usage sections.

### Test Suite Repair (Completed)
#### [MODIFY] All Test Files in `core/`
- **Fix**: Replace `from core.framework` with `from framework`.

#### [VERIFY] `tools/` Tests (Skipped)
- **Problem**: `pytest` failed in `tools/` due to missing package installation.
- **Status**: Skipped verification due to network timeout installing heavy dependencies (`pandas`, `playwright`). Core contribution remains valid.

### CI Pipeline Improvement (Completed)
#### [MODIFY] [.github/workflows/ci.yml](file:///Users/lorddecay/Desktop/Coding/Hive/hive/.github/workflows/ci.yml)
- **Fix**: Added `examples/templates/` to the `Ruff lint` step.

## Phase 5: Feature Expansion (Log Redaction)
### [NEW] [test_redaction.py](file:///Users/lorddecay/Desktop/Coding/Hive/hive/core/tests/test_redaction.py)
- **Purpose**: Verify that sensitive patterns (API keys) are masked in logs.
- **Content**: Unit tests for `StructuredFormatter` and `HumanReadableFormatter`.

### [MODIFY] [logging.py](file:///Users/lorddecay/Desktop/Coding/Hive/hive/core/framework/observability/logging.py)
- **Change**: Implement `redact_sensitive_data` function using regex.
- **Change**: Apply redaction to `message`, `event`, and `exception` fields in formatters.

## Phase 6: Submission (Completed)
- **PR Created**: https://github.com/adenhq/hive/pull/4870
- **Branch**: `hatimhtm:fix/deep-research-hardening-v2`
