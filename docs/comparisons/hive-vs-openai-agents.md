# Hive vs OpenAI Agents SDK

*Comparing goal-driven evolution with vendor-optimized agent development*

---

## Overview

| Aspect | OpenAI Agents SDK | Hive |
|--------|-------------------|------|
| **Developer** | OpenAI | Aden (YC-backed) |
| **Philosophy** | Routines and handoffs | Goal-driven, self-evolving graphs |
| **LLM Support** | OpenAI models only | Any LLM via LiteLLM (100+ models) |
| **Self-Improvement** | No | Yes, automatic evolution |
| **Predecessor** | Swarm (experimental) | Original architecture |
| **Best For** | OpenAI-native applications | Model-agnostic production systems |
| **License** | MIT | Apache 2.0 |

---

## Background

The OpenAI Agents SDK is the **production-ready evolution of Swarm**, OpenAI's experimental multi-agent framework. It addresses Swarm's limitations (stateless, experimental) while maintaining the lightweight, ergonomic approach.

**Key improvements from Swarm:**
- Session memory for conversation history
- Built-in tracing
- Guardrails for safety
- Production support from OpenAI

---

## Philosophy & Approach

### OpenAI Agents SDK

The SDK uses **routines and handoffs** as core primitives. Agents are defined with instructions and tools, and can hand off control to other agents when needed.

```python
# OpenAI Agents SDK: Routines and handoffs
from agents import Agent, handoff

triage_agent = Agent(
    name="Triage",
    instructions="Determine the type of request and route appropriately",
    handoffs=[sales_agent, support_agent, billing_agent]
)

sales_agent = Agent(
    name="Sales",
    instructions="Handle sales inquiries and product questions",
    tools=[lookup_pricing, check_inventory]
)

# Run the agent
response = triage_agent.run("I want to buy your enterprise plan")
```

### Hive

Hive uses **goals and graphs** as core primitives. You define success criteria, and the framework generates and evolves the execution flow.

```python
# Hive: Goal-driven graphs
goal = Goal(
    name="customer-request-handling",
    description="Route and resolve customer requests appropriately",
    success_criteria=[
        {"metric": "output_contains", "target": "resolution"},
        {"metric": "llm_judge", "target": "Customer request fully addressed"}
    ]
)

graph = GraphSpec(
    nodes=[triage_node, sales_node, support_node, resolution_node],
    edges=[
        EdgeSpec(source="triage", target="sales", condition="conditional",
                 condition_expr="request_type == 'sales'"),
        EdgeSpec(source="triage", target="support", condition="conditional",
                 condition_expr="request_type == 'support'"),
        # ... more edges
    ],
    entry_node="triage"
)
```

---

## Feature Comparison

### LLM Support

| Feature | OpenAI Agents SDK | Hive |
|---------|-------------------|------|
| OpenAI models | Native, optimized | Via LiteLLM |
| Anthropic Claude | No | Native + LiteLLM |
| Google Gemini | No | Via LiteLLM |
| Local models | No | Via LiteLLM |
| Azure OpenAI | No | Via LiteLLM |
| Model switching | N/A | Configuration change |

**Key difference:** OpenAI Agents SDK locks you into OpenAI's ecosystem. Hive supports 100+ models through LiteLLM, letting you switch providers without code changes.

### Agent Definition

| Feature | OpenAI Agents SDK | Hive |
|---------|-------------------|------|
| Definition method | Agent class with instructions | NodeSpec or goal-driven generation |
| Routing | Handoffs between agents | Edge conditions (5 types) |
| State management | Session memory | SharedMemory with per-key locks |
| Tool binding | Function decorators | Tool registry + MCP |

### Execution Flow

| Feature | OpenAI Agents SDK | Hive |
|---------|-------------------|------|
| Flow control | Handoffs | Graph traversal with conditions |
| Parallel execution | Sequential | Fan-out/fan-in with convergence |
| Conditional routing | Via handoff logic | 5 edge types (always, on_success, on_failure, conditional, llm_decide) |
| Retry logic | Basic | Exponential backoff per node |

### Human-in-the-Loop

| Feature | OpenAI Agents SDK | Hive |
|---------|-------------------|------|
| HITL mechanism | Via tools | Native pause_nodes |
| Session persistence | Session memory | Full state snapshot + resume |
| Approval workflows | Custom implementation | Built-in pause/resume |
| Escalation | Manual | HybridJudge (rules → LLM → human) |

**Key difference:** OpenAI's HITL requires implementing human interaction as a tool. Hive has dedicated pause nodes that preserve complete state and resume exactly where execution stopped.

### Observability

| Feature | OpenAI Agents SDK | Hive |
|---------|-------------------|------|
| Tracing | Built-in | Built-in |
| Decision logging | Trace spans | Atomic decision records |
| Token tracking | Per-run | Per-node granularity |
| Custom processors | Trace processors | Event bus + runtime hooks |

**Key difference:** Both offer tracing, but Hive's decision logging captures the reasoning behind each choice—not just what happened, but why.

### Safety & Verification

| Feature | OpenAI Agents SDK | Hive |
|---------|-------------------|------|
| Input validation | Guardrails | Pydantic models |
| Output validation | Guardrails | Pydantic + hallucination detection |
| Tripwire guardrails | Yes | Via constraints |
| Judgment system | No | HybridJudge triangulation |

---

## Common Pain Points (and How Hive Addresses Them)

### 1. "I'm locked into OpenAI"

**OpenAI Agents SDK:** Works exclusively with OpenAI models. If you want to use Claude, Gemini, or local models, you need a different framework.

**Hive:** Model-agnostic architecture:

```python
# Switch models with configuration
llm_config = {
    "provider": "anthropic",  # or "openai", "google", "local"
    "model": "claude-3-opus"
}

# Or use LiteLLM for any of 100+ models
llm_config = {
    "provider": "litellm",
    "model": "gpt-4"  # or "claude-3-opus", "gemini-pro", etc.
}
```

### 2. "My agents don't improve from failures"

**OpenAI Agents SDK:** When agents fail, you debug and rewrite code manually.

**Hive:** Self-improvement loop:

```
Execution → Failure → Analysis → Graph Evolution → Retry
                          ↓
              Captures patterns for future improvement
```

The framework learns from failures and evolves the graph structure automatically.

### 3. "Handoffs lose context"

**OpenAI Agents SDK:** Handoffs pass control but state management depends on session memory.

**Hive:** SharedMemory with explicit access control:

```python
# Each node declares what it reads and writes
node = NodeSpec(
    id="process_order",
    input_keys=["customer_id", "order_details"],
    output_keys=["order_id", "confirmation"],
    # ...
)

# Memory access is scoped and thread-safe
# Per-key locks prevent race conditions in parallel execution
```

### 4. "I need more control over routing"

**OpenAI Agents SDK:** Routing happens via handoffs, which are essentially function calls that transfer control.

**Hive:** Five types of edge conditions for precise control:

| Condition | Use Case |
|-----------|----------|
| `always` | Unconditional flow |
| `on_success` | Only if previous node succeeded |
| `on_failure` | Error handling and retry paths |
| `conditional` | Expression-based routing (safe eval) |
| `llm_decide` | Goal-aware intelligent routing |

```python
edges = [
    EdgeSpec(source="validate", target="process", condition="on_success"),
    EdgeSpec(source="validate", target="error_handler", condition="on_failure"),
    EdgeSpec(source="classify", target="urgent_path",
             condition="conditional", condition_expr="priority == 'high'"),
    EdgeSpec(source="ambiguous", target="best_handler",
             condition="llm_decide")  # LLM chooses based on goal context
]
```

---

## When to Choose Each

### Choose OpenAI Agents SDK when:

- You're **100% committed to OpenAI** models
- You want the **simplest possible** multi-agent setup
- You're building a **prototype or MVP** quickly
- You value **official OpenAI support** and documentation
- Your use case fits the **routines and handoffs** mental model

### Choose Hive when:

- You need **model flexibility** (Anthropic, Google, local, etc.)
- You want agents that **improve from failures** automatically
- **Production reliability** is a requirement (retry, validation, observability)
- You need **sophisticated routing** beyond simple handoffs
- **Human-in-the-loop** must preserve complete state
- You're building for **enterprise** with audit requirements

---

## Migration Path

### Step 1: Extract Goals from Agents

OpenAI agents have implicit goals in their instructions. Make them explicit:

```python
# Before (OpenAI implicit goal)
sales_agent = Agent(
    instructions="Handle sales inquiries and close deals"
)

# After (Hive explicit goal)
goal = Goal(
    name="sales-inquiry-handling",
    description="Handle sales inquiries and close deals",
    success_criteria=[
        {"metric": "output_contains", "target": "next_steps"},
        {"metric": "llm_judge", "target": "Inquiry addressed professionally"}
    ]
)
```

### Step 2: Convert Handoffs to Edges

```python
# Before (OpenAI handoffs)
triage = Agent(handoffs=[sales, support])

# After (Hive edges)
edges = [
    EdgeSpec(source="triage", target="sales",
             condition="conditional", condition_expr="intent == 'buy'"),
    EdgeSpec(source="triage", target="support",
             condition="conditional", condition_expr="intent == 'help'"),
]
```

### Step 3: Replace Guardrails with Constraints

```python
# Before (OpenAI guardrails)
@guardrail
def check_pii(message):
    if contains_pii(message):
        return GuardrailResult.BLOCK

# After (Hive constraints)
goal.constraints = [
    {"type": "hard", "category": "safety", "check": "no_pii_in_output"}
]
```

### Step 4: Add Evolution

The key addition Hive provides—automatic improvement:

```python
# Hive captures failures and evolves
# No equivalent in OpenAI Agents SDK—this is automatic

# When a node fails repeatedly, the framework:
# 1. Analyzes failure patterns
# 2. Suggests graph modifications
# 3. Applies improvements
# 4. Tracks success rate changes
```

---

## Technical Comparison Summary

| Dimension | OpenAI Agents SDK | Hive |
|-----------|-------------------|------|
| **Mental Model** | Routines + handoffs | Goals + graphs |
| **LLM Lock-in** | OpenAI only | Any (100+ via LiteLLM) |
| **Evolution** | Manual rewrites | Automatic improvement |
| **Routing** | Handoffs | 5 edge condition types |
| **HITL** | Via tools | Native pause nodes |
| **Production** | Growing maturity | Built-in resilience |
| **Best For** | OpenAI-native prototypes | Model-agnostic production |

---

## Summary

The OpenAI Agents SDK is an excellent choice for teams fully committed to OpenAI's ecosystem who want a lightweight, well-supported framework for building multi-agent systems.

Hive is the better choice when you need model flexibility, self-improvement, sophisticated routing, or enterprise-grade observability. The goal-driven approach with automatic evolution means your agents get better over time without manual intervention.

**The key questions:**
1. Are you committed to OpenAI models only, or do you need flexibility?
2. Do you want agents that improve automatically, or are you okay with manual iteration?
3. Is "good enough" routing sufficient, or do you need precise flow control?

If flexibility, evolution, and control matter to you, Hive is worth evaluating.

---

*Last updated: February 2026*
