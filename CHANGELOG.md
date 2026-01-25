# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-01-25

### Added
- **Async Architecture**: Ported core `AgentRunner` and `GraphExecutor` to fully asynchronous execution with `asyncio`.
- **Parallel Execution**: Agents can now execute independent nodes concurrently, significantly improving throughput for I/O-bound tasks.
- **Async Demo Agent**: Added `examples/async_demo` to benchmark parallel performance improvements.
- **Performance Dependencies**: Added `orjson` (fast JSON), `uvloop` (fast event loop), and `aiofiles` (async file I/O).
- **Concurrency Control**: Implemented `Semaphore` support in node execution to respect API rate limits.

### Changed
- **Runtime Interface**: `AgentRunner.run()` and `can_handle()` are now `async` functions (Breaking Change).
- **Tooling**: Updated `tool_registry` to look for `@tool` decorators instead of raw list exports.

### Fixed
- **Windows Compatibility**: Fixed `aden_tools` test suite on Windows (symlink handling, path traversal).
- **Credential Validation**: Enforced correct failure on missing required credentials (e.g., Anthropic API key).


### Added
- Initial project structure
- React frontend (honeycomb) with Vite and TypeScript
- Node.js backend (hive) with Express and TypeScript
- Docker Compose configuration for local development
- Configuration system via `config.yaml`
- GitHub Actions CI/CD workflows
- Comprehensive documentation

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.1.0] - 2025-01-13

### Added
- Initial release

[Unreleased]: https://github.com/adenhq/hive/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/adenhq/hive/releases/tag/v0.1.0
