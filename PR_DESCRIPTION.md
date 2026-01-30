# Feature: Async Parallel Execution Architecture (v0.2.0)

## 🚀 Overview
This PR implements a complete asynchronous architecture update for the Hive/Aden framework, enabling **true parallel execution** of agent nodes. This significantly improves throughput for I/O-bound tasks (e.g., concurrent web scraping, multiple tool calls).

## 📋 Comprehensive Change Log

### 1. Core Framework Refactoring (`core/`)
*   **Async Runtime**:
    *   Converted `AgentRunner.run()` and `can_handle()` to `async def`.
    *   Updated `AgentRunner` lifecycle methods (`__aenter__`, `__aexit__`) for proper async context management.
    *   Renamed `GraphExecutor` to `ParallelGraphExecutor` in internal logic.
*   **Parallel Execution Engine**:
    *   Implemented `asyncio.gather` pattern in `GraphExecutor` to execute independent nodes concurrently.
    *   Added `Semaphore` support to limit maximum concurrency (preventing API rate limits).
    *   Updated `Node` class to support async execution states.
*   **Performance Dependencies**:
    *   Added `orjson` for ultra-fast JSON serialization.
    *   Added `uvloop` (Linux/Mac) and `aiofiles` for non-blocking file I/O.
    *   Added `redis` and `asyncpg` drivers for future async storage layers.

### 2. Test Suite Overhaul & Fixes
*   **Core Tests**:
    *   Refactored `tests/test_runtime.py`, `tests/test_builder.py`, `tests/test_flexible_executor.py` to use `pytest-asyncio`.
    *   Verified 206 core tests passing.
*   **Tools Tests Fixes**:
    *   **Credential Validation**: Fixed `aden_tools/credentials/llm.py` validation logic. The `anthropic` credential is now correctly marked as `required=True` and `startup_required=True`, matching test expectations.
    *   **Windows Compatibility**:
        *   Updated `test_security.py` to skip Unix-specific symlink and absolute path tests (`/etc/passwd`) on Windows.
        *   Updated `test_file_system_toolkits.py` to use `dir` instead of `ls` on Windows environments.
    *   **Network Mocking**: Refactored `test_web_scrape_tool.py` to use `unittest.mock` for `httpx` and `RobotFileParser`, removing flaky external network dependencies.

### 3. New Async Demo Agent (`examples/async_demo`)
*   Created a benchmark agent to validate the architecture.
*   **Features**:
    *   Runs 3 "Heavy Research" tasks concurrently.
    *   Uses a custom `simulate_research` async tool with non-blocking sleep.
    *   Includes `MockLLMProvider` to allow running the full demo without API keys.
*   **Results**: Confirmed execution time matches the longest single task (~1s) rather than the sum of all tasks (~3s), proving parallel execution works.

### 4. Setup & Documentation
*   **Windows Support**: Verified and adapted `setup-python.sh` logic for PowerShell execution.
*   **Reporting**: Generated `test_execution_report.md` confirming "All Green" status across Core and Tools.

## 🧪 Verification Results
- **Core Framework**: ✅ 206 Passed
- **Tools Package**: ✅ 144 Passed (Windows-incompatible tests skipped)
- **Async Benchmark**: ✅ Success (Parallelism confirmed)

## 📦 Dependencies Added
- `pytest-asyncio`
- `orjson`
- `aiofiles`
- `fastmcp` (for Tools)
