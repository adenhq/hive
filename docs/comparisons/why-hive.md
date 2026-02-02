# When to Use Hive

*A clear guide for developers evaluating AI agent frameworks*

---

## The 30-Second Answer

**Use Hive when you need AI agents that:**
- Work reliably in production, not just demos
- Improve automatically from failures
- Provide full audit trails for every decision
- Support real human oversight without breaking flow
- Work with any LLM, not just one vendor

**Consider alternatives when you:**
- Need a quick prototype with minimal setup
- Are fully committed to a single LLM vendor
- Have simple, linear workflows
- Don't need observability or audit trails

---

## Hive is Built For

### 1. Production Workloads

If your agents need to handle real traffic with real consequences, Hive provides:

| Production Concern | Hive's Solution |
|-------------------|-----------------|
| Transient failures | Exponential backoff retry per node |
| Invalid outputs | Pydantic validation + hallucination detection |
| Race conditions | Per-key locking in SharedMemory |
| Cost overruns | Token tracking at node granularity |
| Debugging | Atomic decision logging with reasoning |

**Ask yourself:** "What happens when this fails at 2 AM?"

If the answer matters, Hive is designed for you.

### 2. Compliance & Audit Requirements

Hive logs every decision with:
- **Intent**: What the agent was trying to do
- **Options**: What choices were available
- **Chosen**: What was selected
- **Reasoning**: Why it was selected
- **Outcome**: What happened

This creates a complete audit trail that answers: "Why did the agent do that?"

**Ideal for:** Healthcare, finance, legal, enterprise applications where you need to explain agent behavior.

### 3. Human-in-the-Loop Workflows

Hive's HITL is native, not bolted on:

```python
# Agents pause at designated nodes
graph = GraphSpec(
    pause_nodes=["human_approval"],
    # ...
)

# State is fully preserved
result = await executor.execute(graph, goal)
# result.paused_at == "human_approval"
# result.session_state contains full memory snapshot

# Resume continues exactly where it stopped
result2 = await executor.execute(
    graph, goal,
    session_state=result.session_state
)
```

**Ideal for:** Approval workflows, content moderation, high-stakes decisions.

### 4. Evolving Requirements

Traditional frameworks require code changes when requirements evolve. Hive:

1. Captures failures and their patterns
2. Analyzes what went wrong
3. Suggests or applies graph modifications
4. Tracks improvement over time

**Ideal for:** Long-running projects where "version 1" is just the beginning.

### 5. Multi-Model Strategies

Hive isn't locked to any LLM vendor:

```python
# Use different models for different purposes
nodes = [
    NodeSpec(id="fast_triage", model="haiku"),      # Fast, cheap
    NodeSpec(id="deep_analysis", model="opus"),     # Smart, thorough
    NodeSpec(id="json_cleanup", model="gemini"),    # Good at structured
]
```

**Ideal for:** Cost optimization, model comparison, avoiding vendor lock-in.

---

## Hive is NOT Built For

### Quick Prototypes

If you need something running in 30 minutes and don't care about production readiness, simpler frameworks like CrewAI or OpenAI Agents SDK have lower setup overhead.

**Hive's minimum setup:**
1. Define a Goal with success criteria
2. Create or generate a GraphSpec
3. Configure node implementations

This is intentionally more structured than "just call the API."

### Simple Q&A Chatbots

If your use case is:
- Single-turn question answering
- Basic RAG retrieval
- Simple conversation

You probably don't need a full agent framework. Consider LangChain's simpler patterns or direct API calls.

### Research & Experimentation

If you're exploring agent architectures and need maximum flexibility to try unusual patterns, AutoGen's conversation-driven approach gives you more room to experiment.

Hive is opinionated about graph-based execution. That's a strength for production but a constraint for pure research.

---

## Decision Matrix

| If you need... | Choose... | Why |
|----------------|-----------|-----|
| **Fastest prototype** | CrewAI, OpenAI SDK | Lower ceremony, quick start |
| **Best RAG ecosystem** | LangChain | 50+ vector store integrations |
| **Research flexibility** | AutoGen | Conversation patterns, experimentation |
| **Production reliability** | **Hive** | Built-in resilience, observability |
| **Self-improvement** | **Hive** | Only framework with automatic evolution |
| **Full audit trails** | **Hive** | Atomic decision logging |
| **Native HITL** | **Hive** | Pause/resume with state preservation |
| **Model flexibility** | **Hive** | 100+ models via LiteLLM |

---

## The Hive Philosophy

### Goals Over Code

Other frameworks ask: "What steps should the agent take?"

Hive asks: "What outcome do you want?"

```python
# Other frameworks: Define every step
chain = step1 | step2 | step3 | step4

# Hive: Define the outcome
goal = Goal(
    name="customer-onboarding",
    description="Successfully onboard new customers",
    success_criteria=[
        {"metric": "output_contains", "target": "welcome_email_sent"},
        {"metric": "output_contains", "target": "account_configured"},
        {"metric": "llm_judge", "target": "Customer received all information"}
    ]
)
```

### Evolution Over Rewriting

When agents fail:

| Traditional | Hive |
|-------------|------|
| Debug manually | Failure automatically captured |
| Rewrite code | Graph evolution suggested |
| Hope it works | Success rate tracked |
| Repeat | Continuous improvement |

### Verification Over Trust

Hive doesn't trust that outputs are correct. It verifies:

1. **Rules**: Fast, deterministic checks
2. **LLM Judge**: Semantic evaluation when rules can't decide
3. **Human Escalation**: For edge cases requiring judgment

This "trust but verify" approach catches issues before they reach users.

---

## Getting Started

If Hive sounds right for your use case:

```bash
# Clone and setup
git clone https://github.com/adenhq/hive.git
cd hive && ./quickstart.sh

# Run the example
cd core && python examples/manual_agent.py

# Build your first agent
claude> /building-agents-construction
```

### Resources

- [Quick Start Guide](../../README.md)
- [Building Agents](../../ENVIRONMENT_SETUP.md)
- [Comparison with Alternatives](./README.md)
- [Architecture Decisions](../architecture/)

---

## Summary

**Hive is for teams who:**
- Are past the "can we build an agent?" phase
- Need agents that work reliably in production
- Want to understand why agents make decisions
- Need human oversight that doesn't break workflows
- Want agents that improve over time

**Hive is NOT for teams who:**
- Need a quick demo
- Want maximum flexibility for research
- Have simple, single-step use cases

The goal-driven, self-improving approach requires more upfront structure but pays off in reliability, observability, and long-term maintainability.

---

*Last updated: February 2026*
