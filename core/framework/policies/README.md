# Hive Guardrails (Policy Engine)

Policy enforcement layer for the Hive agent runtime. Intercepts tool calls during execution and evaluates them against configurable policies before allowing, blocking, or requiring human confirmation.

## How It Works

```
Agent LLM decides to call a tool
        |
        v
  PolicyEngine.evaluate(TOOL_CALL)
        |
   +---------+-----------+----------------+
   |         |           |                |
 ALLOW    BLOCK    REQUIRE_CONFIRM     SUGGEST
   |         |           |                |
   v         v           v                v
 Execute   Return     Route to        Log and
  tool     error     approval_cb      execute
           result    (HITL)
```

When a `PolicyEngine` is configured on the `GraphExecutor`, every tool call passes through a policy-aware wrapper that:

1. Creates a `TOOL_CALL` event with the tool name and arguments
2. Evaluates all registered policies against the event
3. Acts on the aggregated decision (allow, block, require confirmation, or suggest)
4. If allowed, executes the tool and evaluates a `TOOL_RESULT` event (post-call)
5. Records blocked/flagged calls in the Runtime via `report_problem()`

## Quick Start

```python
from framework import AgentRunner, PolicyConfig

# Configure policies
config = PolicyConfig(
    enable_tool_gating=True,          # Block/confirm high-risk tools
    tool_gating_mode="balanced",       # "permissive", "balanced", "strict"

    enable_domain_allowlist=True,      # Restrict network access
    allowed_domains=["api.example.com", "*.internal.net"],

    enable_budget_limits=True,         # Enforce resource budgets
    token_limit=100_000,
    cost_limit_usd=1.00,

    enable_injection_guard=True,       # Detect prompt injection in tool results
    injection_mode="balanced",
)

# Load agent with policies
runner = AgentRunner.load(
    "exports/my-agent",
    policy_config=config,
)

# Policies are automatically enforced during execution
result = await runner.run({"input": "value"})
```

## Built-in Policies

### HighRiskToolGatingPolicy

Evaluates tool names against glob patterns to identify high-risk operations (file deletion, code execution, credential access). Matching tools trigger `REQUIRE_CONFIRM`; safe-pattern matches are allowed.

**Default high-risk patterns:** `*_delete`, `*_remove`, `*execute*`, `*credential*`, `*password*`, `*secret*`, etc.

**Modes via `tool_gating_mode`:**
| Mode | Behavior for unmatched tools |
|------|------------------------------|
| `permissive` | Allow |
| `balanced` | Require confirmation |
| `strict` | Block |

### DomainAllowlistPolicy

Controls which domains agents can reach via network tools (`http_request`, `web_scrape`, `api_call`, etc.). Checks URLs in tool arguments against allowlists and blocklists.

**Modes via `domain_allowlist_mode`:**
| Mode | Behavior for unknown domains |
|------|------------------------------|
| `permissive` | Log suggestion, allow |
| `balanced` | Require confirmation |
| `strict` | Block |

### BudgetLimitPolicy

Enforces resource budgets on token usage, cost, and execution time. Evaluates `RUN_CONTROL` events emitted by the runtime with current usage metrics.

**Config fields:** `token_limit`, `cost_limit_usd`, `time_limit_seconds`

Soft limits are auto-set at 80% of the hard limit. In `balanced` mode, soft limit triggers a warning; hard limit blocks.

### InjectionGuardPolicy

Detects prompt injection patterns in tool results (post-call evaluation). Flags content that appears to contain instruction-like patterns attempting to manipulate the agent.

**Modes via `injection_mode`:**
| Mode | Behavior for detected injection |
|------|--------------------------------|
| `permissive` | Log suggestion |
| `balanced` | Require confirmation |
| `strict` | Block |

## HITL (Human-in-the-Loop) Integration

`REQUIRE_CONFIRM` decisions route through the existing `approval_callback` on `AgentRunner`:

```python
runner = AgentRunner.load("exports/my-agent", policy_config=config)

def my_approval_handler(info: dict) -> bool:
    """Called when a policy requires human confirmation."""
    print(f"Tool: {info['tool_name']}")
    print(f"Reason: {info['reason']}")
    print(f"Policy: {info['policy_id']}")
    return input("Approve? (y/n): ").lower() == "y"

runner.set_approval_callback(my_approval_handler)
```

If no callback is set, `REQUIRE_CONFIRM` decisions are denied by default.

## Advanced: Direct PolicyEngine Usage

For custom policies or programmatic control, use the `PolicyEngine` directly:

```python
from framework import PolicyEngine, PolicyConfig
from framework.policies.builtin.tool_gating import HighRiskToolGatingPolicy
from framework.graph.executor import GraphExecutor

engine = PolicyEngine(raise_on_block=False)
engine.register_policy(HighRiskToolGatingPolicy(default_action="confirm"))

executor = GraphExecutor(
    runtime=runtime,
    llm=llm,
    tools=tools,
    tool_executor=tool_executor,
    policy_engine=engine,
)
```

### Custom Policies

Implement the `Policy` protocol:

```python
from framework.policies.base import BasePolicy
from framework.policies.decisions import PolicyDecision, Severity
from framework.policies.events import PolicyEvent, PolicyEventType

class MyCustomPolicy(BasePolicy):
    _id = "my-custom-policy"
    _name = "My Custom Policy"
    _description = "Blocks calls to deprecated tools"
    _event_types = [PolicyEventType.TOOL_CALL]

    @property
    def id(self): return self._id
    @property
    def name(self): return self._name
    @property
    def description(self): return self._description
    @property
    def event_types(self): return self._event_types

    async def evaluate(self, event: PolicyEvent) -> PolicyDecision:
        tool_name = event.payload.get("tool_name", "")
        if tool_name.startswith("deprecated_"):
            return PolicyDecision.block(
                policy_id=self.id,
                reason=f"Tool '{tool_name}' is deprecated",
                severity=Severity.HIGH,
            )
        return PolicyDecision.allow(policy_id=self.id)

engine.register_policy(MyCustomPolicy())
```

## Architecture

```
runner/runner.py          PolicyConfig → _build_policy_engine() → PolicyEngine
                                                                      |
graph/executor.py         GraphExecutor.__init__(policy_engine=...)   |
                                |                                     |
                          _wrap_with_policy(tool_executor)            |
                                |                                     |
                          policy_executor(tool_use)  ←────── evaluates policies
                                |
                          original_executor(tool_use) ← only if allowed

runtime/agent_runtime.py  policy_engine threaded through AgentRuntime
                                |
runtime/execution_stream.py     → ExecutionStream → GraphExecutor (per execution)
```

**Files modified for runtime wiring:**
- `core/framework/graph/executor.py` — `_wrap_with_policy()`, `policy_engine` param
- `core/framework/runner/runner.py` — `PolicyConfig`, `_build_policy_engine()`
- `core/framework/runtime/agent_runtime.py` — `policy_engine` param threaded through
- `core/framework/runtime/execution_stream.py` — `policy_engine` param forwarded to executor
- `core/framework/__init__.py` — `PolicyConfig` exported

## Testing

```bash
# Integration tests (policy + runtime wiring)
PYTHONPATH=core pytest core/tests/test_policy_integration.py -v

# Standalone policy unit tests
pytest tests/ -v

# Full Hive suite
PYTHONPATH=core pytest core/tests/ -v
```

Current: **285 Hive tests + 90 standalone tests**, all passing.
