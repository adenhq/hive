# Example: Sales Opportunity Agent

A multi-node agent that analyzes sales opportunities and recommends actions.

## Goal

```python
goal = Goal(
    id="sales-opportunity",
    name="Sales Opportunity Automation",
    description="Analyze opportunities, qualify leads, recommend next actions",
    success_criteria=[
        SuccessCriterion(
            id="accurate-qualification",
            description="Correctly qualify leads as hot/warm/cold",
            metric="qualification_accuracy",
            target=">0.85",
            weight=0.4,
        ),
        SuccessCriterion(
            id="actionable-recommendations",
            description="Provide specific next steps",
            metric="recommendation_specificity",
            target="always_specific",
            weight=0.3,
        ),
    ],
    constraints=[
        Constraint(
            id="no-false-promises",
            description="Never suggest outcomes without data support",
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="privacy",
            description="Handle data in compliance with privacy regulations",
            constraint_type="hard",
            category="safety",
        ),
    ],
)
```

## Nodes

### 1. Lead Analyzer (Entry)

```python
NodeSpec(
    id="lead-analyzer",
    name="Lead Analyzer",
    description="Extract engagement signals from opportunity data",
    node_type="llm_generate",
    input_keys=["opportunity"],
    output_keys=["signals", "company_profile", "engagement_summary"],
    system_prompt="""Analyze the opportunity and extract:
1. Engagement signals (response times, meeting attendance)
2. Company profile (size, industry, fit)
3. Deal signals (budget, timeline, decision-maker)

Output JSON with: signals, company_profile, engagement_summary""",
)
```

### 2. Opportunity Scorer

```python
NodeSpec(
    id="opportunity-scorer",
    name="Opportunity Scorer",
    description="Score opportunity based on signals",
    node_type="llm_tool_use",
    input_keys=["signals", "company_profile", "engagement_summary"],
    output_keys=["score", "qualification", "score_breakdown"],
    tools=["historical_lookup"],
    system_prompt="""Score this opportunity 0-100:
- Engagement (30%)
- Company fit (25%)
- Deal signals (25%)
- Historical similarity (20%)

Qualify as:
- HOT (80-100): High intent, active engagement
- WARM (50-79): Some interest, needs nurturing
- COLD (0-49): Low engagement or poor fit

Use historical_lookup to find similar deals.""",
)
```

### 3. Action Recommender

```python
NodeSpec(
    id="action-recommender",
    name="Action Recommender",
    description="Generate specific next steps",
    node_type="llm_tool_use",
    input_keys=["score", "qualification", "engagement_summary", "opportunity"],
    output_keys=["recommended_actions", "reasoning", "priority"],
    tools=["calendar_availability", "email_templates"],
    system_prompt="""Recommend actions based on qualification:

HOT: Check calendar, schedule meeting, send proposal
WARM: Send nurturing content, plan discovery call
COLD: Re-engagement campaign or deprioritize

Output JSON with: recommended_actions, reasoning, priority""",
)
```

### 4. Output Formatter (Terminal)

```python
NodeSpec(
    id="output-formatter",
    name="Output Formatter",
    description="Format final analysis",
    node_type="llm_generate",
    input_keys=["qualification", "score", "recommended_actions", "reasoning"],
    output_keys=["result"],
    system_prompt="""Format into clean report:
- qualification
- score
- recommended_actions
- reasoning
- one-sentence summary""",
)
```

## Edges

```python
edges = [
    EdgeSpec(id="analyze-to-score", source="lead-analyzer", target="opportunity-scorer", condition=EdgeCondition.ON_SUCCESS),
    EdgeSpec(id="score-to-recommend", source="opportunity-scorer", target="action-recommender", condition=EdgeCondition.ON_SUCCESS),
    EdgeSpec(id="recommend-to-format", source="action-recommender", target="output-formatter", condition=EdgeCondition.ON_SUCCESS),
]
```

## Architecture

```
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────┐
│ Lead Analyzer │──►│Opportunity      │──►│ Action          │──►│ Output      │
│ (generate)    │   │Scorer (tool_use)│   │ Recommender     │   │ Formatter   │
└───────────────┘   └─────────────────┘   │ (tool_use)      │   │ (generate)  │
                           │              └─────────────────┘   └─────────────┘
                    historical_lookup           │
                                         calendar_availability
                                         email_templates
```

## Tools

```python
tools = [
    Tool(
        name="historical_lookup",
        description="Find similar past opportunities",
        parameters={
            "type": "object",
            "properties": {
                "company_size": {"type": "string"},
                "industry": {"type": "string"},
            },
        },
    ),
    Tool(
        name="calendar_availability",
        description="Check calendar for meeting slots",
        parameters={
            "type": "object",
            "properties": {
                "timeframe": {"type": "string"},
            },
        },
    ),
    Tool(
        name="email_templates",
        description="Get email templates for sales scenarios",
        parameters={
            "type": "object",
            "properties": {
                "template_type": {"type": "string"},
            },
        },
    ),
]
```

## Test Cases

```python
# Hot lead test
{"opportunity": {"engagement": "high", "budget_confirmed": True, "decision_maker": True}}
# Expected: qualification = "HOT", priority = "high"

# Cold lead test
{"opportunity": {"engagement": "low", "budget_confirmed": False, "last_contact": "3 months ago"}}
# Expected: qualification = "COLD", priority = "low"

# Warm lead test
{"opportunity": {"engagement": "medium", "budget_confirmed": False, "decision_maker": True}}
# Expected: qualification = "WARM", priority = "medium"
```
