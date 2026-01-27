# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- React frontend (honeycomb) with Vite and TypeScript
- Node.js backend (hive) with Express and TypeScript
- Docker Compose configuration for local development
- Configuration system via `config.yaml`
- GitHub Actions CI/CD workflows
- Comprehensive documentation

### Changed
- **MCP Server**:
  - Removed hardcoded LLM dependency from test generation tools
  - Refactored test generation to use templates and guidelines
  - Made test generation provider-agnostic
  - Updated test generation to be handled by the calling agent
- **Testing**:
  - Added new test cases for LLM provider independence
  - Updated test infrastructure to work without LLM dependencies
- **Documentation**:
  - Updated MCP server documentation to reflect new test generation approach
  - Added clear guidelines for test template usage

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
