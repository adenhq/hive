# Goal Creation Guide

This guide explains how to define **Goals** for your agents in the Aden Agent Framework. Goals are the foundation of goal-driven agents - they define WHAT your agent should achieve, not HOW.

## What is a Goal?

A Goal contains:
- **Success Criteria** - Measurable conditions that define success
- **Constraints** - Boundaries the agent must respect
- **Context** - Additional information for decision-making

```python
from framework.graph.goal import Goal, SuccessCriterion, Constraint

goal = Goal(
    id="my-goal",
    name="My Agent Goal",
    description="What this agent should accomplish",
    success_criteria=[...],
    constraints=[...],
)
```

## Defining Success Criteria

Success criteria are **measurable conditions** that determine if your agent succeeded.

### Structure

```python
SuccessCriterion(
    id="unique-id",
    description="Human-readable description",
    metric="how to measure",
    target="target value",
    weight=1.0,  # Relative importance (0-1)
)
```

### Metric Types

| Metric | Use Case | Example Target |
|--------|----------|----------------|
| `output_contains` | Check if output has specific content | `"success"` |
| `output_equals` | Exact match | `"expected_value"` |
| `llm_judge` | LLM evaluates quality | `">= 0.8"` |
| `custom` | Custom evaluation function | varies |

### Example

```python
success_criteria = [
    SuccessCriterion(
        id="completeness",
        description="Response covers all requested topics",
        metric="llm_judge",
        target=">= 0.9",
        weight=0.5,
    ),
    SuccessCriterion(
        id="accuracy",
        description="Information is factually correct",
        metric="llm_judge",
        target=">= 0.95",
        weight=0.5,
    ),
]
```

## Defining Constraints

Constraints are **boundaries** your agent must respect during execution.

### Constraint Types

| Type | Meaning | Effect |
|------|---------|--------|
| `hard` | Must not violate | Violation = failure |
| `soft` | Should avoid violating | Violation = warning |

### Categories

- `time` - Execution time limits
- `cost` - Token/API cost limits
- `safety` - Safety requirements
- `scope` - What the agent should/shouldn't do
- `quality` - Quality requirements

### Example

```python
constraints = [
    Constraint(
        id="no-external-apis",
        description="Do not call external APIs without user approval",
        constraint_type="hard",
        category="safety",
    ),
    Constraint(
        id="response-length",
        description="Keep responses under 500 words",
        constraint_type="soft",
        category="quality",
    ),
]
```

## Complete Example

Here's a complete goal for a research agent:

```python
from framework.graph.goal import Goal, SuccessCriterion, Constraint

research_goal = Goal(
    id="research-agent-goal",
    name="Technical Research Agent",
    description="Research technical topics and provide comprehensive summaries",
    
    success_criteria=[
        SuccessCriterion(
            id="topic-coverage",
            description="Covers all major aspects of the topic",
            metric="llm_judge",
            target=">= 0.9",
            weight=0.4,
        ),
        SuccessCriterion(
            id="source-quality",
            description="Uses credible sources",
            metric="llm_judge",
            target=">= 0.8",
            weight=0.3,
        ),
        SuccessCriterion(
            id="clarity",
            description="Output is clear and well-structured",
            metric="llm_judge",
            target=">= 0.85",
            weight=0.3,
        ),
    ],
    
    constraints=[
        Constraint(
            id="verify-sources",
            description="All information must be from verifiable sources",
            constraint_type="hard",
            category="quality",
        ),
        Constraint(
            id="no-speculation",
            description="Do not include unverified speculation",
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="time-limit",
            description="Complete research within 5 minutes",
            constraint_type="soft",
            category="time",
        ),
    ],
    
    required_capabilities=["web_search", "llm"],
    
    context={
        "domain": "technology",
        "audience": "developers",
    },
)
```

## Best Practices

### ✅ Do

- Use **specific, measurable** success criteria
- Include **3-5 success criteria** with different weights
- Define **hard constraints** for critical requirements
- Add **context** to help the agent make better decisions

### ❌ Don't

- Use vague criteria like "do a good job"
- Skip constraints entirely
- Set all weights to 1.0 (use relative importance)
- Forget to specify required capabilities

## Next Steps

After defining your goal:

1. **Build your graph** - Define nodes and edges
2. **Export your agent** - Create the agent package
3. **Test your agent** - Verify it meets the goal

See [Getting Started](getting-started.md) for the complete workflow.

## API Reference

For complete API details, see the source:
- [`framework/graph/goal.py`](../core/framework/graph/goal.py)
