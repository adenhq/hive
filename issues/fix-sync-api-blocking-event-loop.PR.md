## Description

Convert `NodeResult.to_summary()` from synchronous to async to prevent blocking the event loop during Anthropic API calls. Adds timeout handling to prevent indefinite hangs.

## Type of Change

- [x] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Related Issues

Fixes #(issue: Synchronous API Call in to_summary() Blocks Event Loop)

## Changes Made

- Converted `NodeResult.to_summary()` to `async def to_summary()` in `core/framework/graph/node.py`
- Replaced `anthropic.Anthropic` (sync) with `anthropic.AsyncAnthropic` (async)
- Added 10-second timeout using `asyncio.wait_for()` to prevent indefinite hangs
- Updated `GraphExecutor.execute()` in `core/framework/graph/executor.py` to `await` the async method
- Fallback behavior preserved for missing API key or API errors
- Added comprehensive unit tests in `core/tests/test_node_result.py`

## Testing

Describe the tests you ran to verify your changes:

- [x] Unit tests pass (`cd core && pytest tests/`)
- [x] Lint passes (`cd core && ruff check .`)
- [x] Manual testing performed
  - Verified async execution no longer blocks on summary generation
  - Verified timeout triggers graceful fallback
  - Verified fallback summary works when API key missing

New tests added in `core/tests/test_node_result.py`:
- test_failed_result_returns_error_message
- test_empty_output_returns_completed_message
- test_fallback_when_no_api_key
- test_fallback_on_api_error
- test_timeout_triggers_fallback
- test_successful_api_call_returns_summary
- test_is_truly_async_non_blocking

## Checklist

- [x] My code follows the project's style guidelines
- [x] I have performed a self-review of my code
- [x] I have commented my code, particularly in hard-to-understand areas
- [x] I have made corresponding changes to the documentation
- [x] My changes generate no new warnings
- [x] I have added tests that prove my fix is effective or that my feature works
- [x] New and existing unit tests pass locally with my changes

## Screenshots (if applicable)

Not applicable - this is a backend async performance fix with no UI impact.
