**Problem**
The core `NodeResult` class contains a hardcoded dependency on the `anthropic` library and a specific model `claude-3-5-haiku-20241022` for summarizing node outputs. This violates the project's provider-agnostic architecture (which uses `LiteLLM` elsewhere) and forces users to have an `ANTHROPIC_API_KEY` specifically for summaries, even if they are using OpenAI or Local models for the agent.

**Evidence**
File: `core/framework/graph/node.py`
Line 397: `import anthropic`
Line 414: `model="claude-3-5-haiku-20241022"`
Line 412: `client = anthropic.Anthropic(api_key=api_key)`

**Impact**
**Maintainability & Usability Risk**.
1.  Breaks for users without an Anthropic key.
2.  Creates hidden costs (API usage) that are not tracked by the main `LiteLLM` budget manager.
3.  Couples the core framework to a specific vendor.

**Proposed Solution**
Refactor `to_summary` to use the injected `ctx.llm` (LiteLLM provider) that is already present in the `NodeContext`. If a summarizer is needed, it should use the globally configured model, not a hardcoded side-channel request.

**Priority**
High
