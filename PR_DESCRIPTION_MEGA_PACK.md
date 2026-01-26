# PR Title: Advanced Agent Capabilities: Resilience, Tools, Observability & Visualization

## Description
This PR implements a comprehensive suite of improvements for the Hive framework, focusing on production readiness, enhanced toolsets, and better developer observability.

## Key Changes

### 1. Resilience & Safety
- **Node Retries**: Added exponential backoff retry logic to `LLMNode` to handle transient failures (e.g., rate limits, network issues).
- **Global Timeout**: Implemented a global graph execution timeout to prevent runaway agent processes.
- **Security Hardening**: Enhanced code sandbox with Windows DoS prevention and stricter attribute access validation.

### 2. Enhanced Toolset
- **CSV Tool**: Intelligent inspection, metadata extraction, and sampling of CSV data.
- **System Tool**: Monitoring of OS resources including RAM, Disk, and CPU usage.
- **Python Interpreter**: Secure execution of Python code within the hardened `CodeSandbox`.

### 3. Observability & Performance Metrics
- **Runtime Metrics**: Automatic tracking of token usage, latency, and LLM call counts per run.
- **Observability Tool**: Programmatic access to run history and performance analysis.
- **State Persistence**: Automatic JSON snapshots of agent memory after every step for debugging and state recovery.

### 4. Developer Experience & Visualization
- **Graph Visualization**: Export agent graphs to Mermaid or DOT format via the CLI (`hive viz`).
- **Structured Logging**: Added `--json-logs` flag for machine-readable output integration.
- **Configurable Evaluation**: Made the `LLMJudge` pluggable with different LLM providers for semantic testing.

## Testing
- Verified all new tools via `fastmcp`.
- Verified retry and timeout logic with simulated failures.
- Verified visualization output in Mermaid Live Editor.
- Verified metrics are correctly stored in run JSONs.
