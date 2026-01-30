### Summary
This PR improves Hive’s first-run experience by adding a minimal, zero-compute
example agent that runs without LLMs, tools, or API keys.

### Motivation
After setup, new users currently do not have a runnable agent example without
configuring LLMs or tools. This introduces unnecessary cognitive and computational
overhead early in the experience.

### What’s included
- `goal_breakdown_agent` under `exports/`
  - Deterministic output
  - No external dependencies
  - Instant execution
- (Optional) Documentation clarification for first-run usage

### Impact
- Faster first success for new users
- Reduced compute and setup requirements
- Better accessibility for low-resource environments
