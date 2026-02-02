# Migrating from CrewAI to Hive

*A practical guide for teams moving from role-based crews to goal-driven graphs*

---

## Overview

This guide helps you migrate existing CrewAI applications to Hive. The migration transforms your role-based crew structure into Hive's goal-driven graphs while adding self-improvement, observability, and more sophisticated routing.

**Estimated effort:**
- Simple crews: 2-4 hours
- Complex multi-crew systems: 2-3 days
- Enterprise deployments: 1 week

---

## Why Migrate?

### CrewAI Pain Points Addressed by Hive

| CrewAI Limitation | Hive Solution |
|-------------------|---------------|
| Manager-worker pattern often doesn't coordinate effectively | Explicit graph edges define exact flow |
| No self-improvement from failures | Automatic evolution based on failure analysis |
| Limited debugging ("why did this fail?") | Atomic decision logging with reasoning |
| Basic HITL support | Native pause nodes with state preservation |
| Sequential/parallel only | 5 edge condition types for complex routing |

---

## Concept Mapping

| CrewAI Concept | Hive Equivalent |
|----------------|-----------------|
| Agent | Node (LLM or function type) |
| Crew | Graph |
| Task | Node with specific goal |
| Process (sequential/parallel) | Edge conditions |
| Role | Node description + system prompt |
| Goal (agent-level) | Goal success criteria |
| Backstory | System prompt context |
| Tools | MCP tools or function nodes |

---

## Step 1: Convert Agents to Nodes

### Before: CrewAI Agent

```python
from crewai import Agent

researcher = Agent(
    role="Senior Research Analyst",
    goal="Uncover cutting-edge developments in AI",
    backstory="""You are a seasoned researcher with a passion for
    uncovering the latest developments in AI and technology.""",
    tools=[search_tool, web_scraper],
    verbose=True,
    allow_delegation=True
)

writer = Agent(
    role="Content Writer",
    goal="Create engaging blog content",
    backstory="""You are a skilled content writer with expertise
    in making complex topics accessible.""",
    tools=[],
    verbose=True
)
```

### After: Hive Nodes

```python
from framework.graph.node import NodeSpec

researcher = NodeSpec(
    id="researcher",
    name="Senior Research Analyst",
    description="Uncover cutting-edge developments in AI",
    node_type="llm_tool_use",
    input_keys=["topic"],
    output_keys=["research_findings"],
    tools=["web_search", "web_scraper"],
    system_prompt="""You are a seasoned researcher with a passion for
    uncovering the latest developments in AI and technology.

    Your task: Research the given topic thoroughly and provide
    comprehensive findings with sources.""",
    max_retries=2
)

writer = NodeSpec(
    id="writer",
    name="Content Writer",
    description="Create engaging blog content",
    node_type="llm_generate",
    input_keys=["research_findings"],
    output_keys=["blog_post"],
    system_prompt="""You are a skilled content writer with expertise
    in making complex topics accessible.

    Your task: Transform the research findings into an engaging
    blog post that educates and informs."""
)
```

**Key differences:**
- `role` → `name`
- `goal` → `description` + success criteria in Goal
- `backstory` → `system_prompt`
- `tools` → `tools` list (MCP names)
- Explicit `input_keys` and `output_keys` define data flow

---

## Step 2: Convert Tasks to Goal + Flow

### Before: CrewAI Tasks

```python
from crewai import Task

research_task = Task(
    description="Research the latest AI agent frameworks",
    agent=researcher,
    expected_output="Comprehensive analysis with key findings"
)

writing_task = Task(
    description="Write a blog post about AI agent frameworks",
    agent=writer,
    expected_output="Engaging 1000-word blog post",
    context=[research_task]  # Depends on research
)
```

### After: Hive Goal + Edges

```python
from framework.graph.goal import Goal
from framework.graph.edge import EdgeSpec

# Define the overall goal with success criteria
goal = Goal(
    id="ai-blog-creation",
    name="AI Agent Framework Blog",
    description="Research AI agent frameworks and create an engaging blog post",
    success_criteria=[
        {"metric": "output_contains", "target": "blog_post"},
        {"metric": "llm_judge", "target": "Blog post is engaging and accurate"},
        {"metric": "custom", "target": "word_count >= 1000"}
    ]
)

# Define flow with edges (replaces task context)
edges = [
    EdgeSpec(
        id="research-to-write",
        source="researcher",
        target="writer",
        condition="on_success"
    )
]
```

---

## Step 3: Convert Crew to Graph

### Before: CrewAI Crew

```python
from crewai import Crew, Process

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, writing_task],
    process=Process.sequential,  # or Process.hierarchical
    verbose=True
)

result = crew.kickoff()
```

### After: Hive Graph + Executor

```python
from framework.graph.edge import GraphSpec
from framework.graph.executor import GraphExecutor

# Create graph
graph = GraphSpec(
    id="blog-creation-graph",
    goal_id=goal.id,
    nodes=[researcher, writer],
    edges=edges,
    entry_node="researcher",
    terminal_nodes=["writer"]
)

# Execute
executor = GraphExecutor(runtime=runtime)
result = await executor.execute(graph=graph, goal=goal)
```

---

## Step 4: Handle Process Types

### Sequential Process

CrewAI's `Process.sequential` maps directly to Hive's linear edge chain:

```python
# CrewAI
process=Process.sequential

# Hive
edges = [
    EdgeSpec(source="agent1", target="agent2", condition="on_success"),
    EdgeSpec(source="agent2", target="agent3", condition="on_success"),
    EdgeSpec(source="agent3", target="agent4", condition="on_success"),
]
```

### Parallel Process

CrewAI's parallel execution maps to Hive's fan-out:

```python
# Multiple edges from same source = parallel execution
edges = [
    EdgeSpec(source="dispatcher", target="worker1", condition="on_success"),
    EdgeSpec(source="dispatcher", target="worker2", condition="on_success"),
    EdgeSpec(source="dispatcher", target="worker3", condition="on_success"),
    # Fan-in: all workers connect to aggregator
    EdgeSpec(source="worker1", target="aggregator", condition="on_success"),
    EdgeSpec(source="worker2", target="aggregator", condition="on_success"),
    EdgeSpec(source="worker3", target="aggregator", condition="on_success"),
]
```

### Hierarchical Process

CrewAI's hierarchical (manager) process maps to Hive's router pattern:

```python
# Manager node that routes to specialists
manager = NodeSpec(
    id="manager",
    name="Manager",
    node_type="router",
    routes={
        "research": "researcher",
        "writing": "writer",
        "review": "reviewer"
    }
)

# Or use LLM-decide edges for dynamic routing
edges = [
    EdgeSpec(
        source="manager",
        target="researcher",
        condition="llm_decide"  # LLM chooses based on goal
    ),
    EdgeSpec(
        source="manager",
        target="writer",
        condition="llm_decide"
    )
]
```

---

## Step 5: Migrate Tools

### Before: CrewAI Tools

```python
from crewai_tools import SerperDevTool, WebsiteSearchTool

search_tool = SerperDevTool()
web_tool = WebsiteSearchTool()

agent = Agent(
    role="Researcher",
    tools=[search_tool, web_tool],
    # ...
)
```

### After: Hive MCP Tools

```python
# tools.py - MCP server
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("research-tools")

@mcp.tool()
def web_search(query: str, num_results: int = 10) -> str:
    """Search the web for information.

    Args:
        query: Search query
        num_results: Number of results to return
    """
    # Implementation (can wrap existing CrewAI tool)
    from crewai_tools import SerperDevTool
    tool = SerperDevTool()
    return tool.run(query)

@mcp.tool()
def scrape_website(url: str) -> str:
    """Scrape content from a website.

    Args:
        url: URL to scrape
    """
    # Implementation
    pass
```

---

## Step 6: Add Hive-Specific Features

### Human-in-the-Loop (Better than CrewAI's)

```python
# CrewAI: Basic human input
# agent.human_input = True

# Hive: Dedicated pause node with full state preservation
review_node = NodeSpec(
    id="human_review",
    name="Editorial Review",
    node_type="human_input",
    input_keys=["draft_post"],
    output_keys=["approved_post", "editor_feedback"]
)

graph = GraphSpec(
    # ...
    pause_nodes=["human_review"]
)

# Execution pauses, state saved, resume continues exactly where left off
```

### Self-Improvement (CrewAI doesn't have this)

```python
# Hive automatically tracks failures and evolves
# Just define what success looks like

goal = Goal(
    success_criteria=[
        {"metric": "llm_judge", "target": "Content is engaging"},
        {"metric": "llm_judge", "target": "Facts are accurate"},
        {"metric": "custom", "target": "readability_score > 60"}
    ]
)

# When agents fail these criteria, Hive:
# 1. Captures the failure pattern
# 2. Analyzes root cause
# 3. Suggests graph modifications
# 4. Tracks improvement over time
```

### Conditional Routing (More flexible than CrewAI)

```python
# CrewAI: Limited to sequential/parallel/hierarchical
# Hive: 5 edge condition types

edges = [
    # Always traverse
    EdgeSpec(source="start", target="process", condition="always"),

    # Only on success
    EdgeSpec(source="process", target="complete", condition="on_success"),

    # Only on failure
    EdgeSpec(source="process", target="retry", condition="on_failure"),

    # Expression-based
    EdgeSpec(
        source="classify",
        target="urgent_path",
        condition="conditional",
        condition_expr="priority == 'high' and confidence > 0.8"
    ),

    # LLM decides based on goal context
    EdgeSpec(
        source="ambiguous",
        target="best_handler",
        condition="llm_decide"
    )
]
```

---

## Common Migration Patterns

### Pattern 1: Research → Write → Edit Crew

```python
# CrewAI
crew = Crew(
    agents=[researcher, writer, editor],
    tasks=[research_task, write_task, edit_task],
    process=Process.sequential
)

# Hive
graph = GraphSpec(
    nodes=[researcher, writer, editor],
    edges=[
        EdgeSpec(source="researcher", target="writer", condition="on_success"),
        EdgeSpec(source="writer", target="editor", condition="on_success"),
        # Add retry loops
        EdgeSpec(source="editor", target="writer", condition="on_failure"),
    ],
    entry_node="researcher",
    terminal_nodes=["editor"]
)
```

### Pattern 2: Manager with Specialists

```python
# CrewAI hierarchical
crew = Crew(
    agents=[manager, specialist1, specialist2, specialist3],
    process=Process.hierarchical,
    manager_agent=manager
)

# Hive with router
graph = GraphSpec(
    nodes=[
        manager_router,  # node_type="router"
        specialist1,
        specialist2,
        specialist3,
        aggregator
    ],
    edges=[
        EdgeSpec(source="manager", target="specialist1", condition="conditional",
                 condition_expr="task_type == 'research'"),
        EdgeSpec(source="manager", target="specialist2", condition="conditional",
                 condition_expr="task_type == 'analysis'"),
        EdgeSpec(source="manager", target="specialist3", condition="conditional",
                 condition_expr="task_type == 'writing'"),
        # All specialists feed to aggregator
        EdgeSpec(source="specialist1", target="aggregator", condition="on_success"),
        EdgeSpec(source="specialist2", target="aggregator", condition="on_success"),
        EdgeSpec(source="specialist3", target="aggregator", condition="on_success"),
    ]
)
```

### Pattern 3: Parallel Worker Crew

```python
# CrewAI parallel
crew = Crew(
    agents=[worker1, worker2, worker3],
    process=Process.parallel
)

# Hive fan-out/fan-in
graph = GraphSpec(
    nodes=[dispatcher, worker1, worker2, worker3, collector],
    edges=[
        # Fan-out
        EdgeSpec(source="dispatcher", target="worker1", condition="on_success"),
        EdgeSpec(source="dispatcher", target="worker2", condition="on_success"),
        EdgeSpec(source="dispatcher", target="worker3", condition="on_success"),
        # Fan-in
        EdgeSpec(source="worker1", target="collector", condition="on_success"),
        EdgeSpec(source="worker2", target="collector", condition="on_success"),
        EdgeSpec(source="worker3", target="collector", condition="on_success"),
    ],
    entry_node="dispatcher",
    terminal_nodes=["collector"]
)
```

---

## Handling CrewAI-Specific Features

### Agent Delegation

CrewAI's `allow_delegation=True` lets agents delegate to others.

In Hive, use explicit router nodes or conditional edges:

```python
# Node can route to specialists
router_node = NodeSpec(
    id="delegator",
    node_type="router",
    description="Analyze task and delegate to appropriate specialist",
    routes={
        "complex_research": "senior_researcher",
        "simple_lookup": "junior_researcher",
        "writing": "writer"
    }
)
```

### Memory (CrewAI's memory types)

```python
# CrewAI: Short-term, long-term, entity memory
# Hive: SharedMemory with explicit keys

# All memory access is explicit and thread-safe
node = NodeSpec(
    input_keys=["user_query", "conversation_history", "user_profile"],
    output_keys=["response", "conversation_history", "learned_preferences"]
)

# Long-term storage: Use database tools or external services
```

### Verbose Mode

```python
# CrewAI: verbose=True
# Hive: Runtime decision logging

# All decisions are logged by default with:
# - Intent
# - Options considered
# - Choice made
# - Reasoning
# - Outcome

# Query logs via BuilderQuery or runtime events
```

---

## Migration Checklist

### Pre-Migration
- [ ] List all CrewAI agents and their roles
- [ ] Document task dependencies (context)
- [ ] Identify custom tools being used
- [ ] Note any human input requirements

### Migration
- [ ] Convert each agent to a NodeSpec
- [ ] Convert tasks to goal success criteria
- [ ] Create edge graph from task context
- [ ] Migrate or wrap tools as MCP
- [ ] Add human_input nodes where needed

### Post-Migration
- [ ] Define goal with clear success criteria
- [ ] Add failure handling edges
- [ ] Enable decision logging
- [ ] Configure evolution settings
- [ ] Test with same inputs, compare outputs

### Validation
- [ ] All crew functionality preserved
- [ ] Error handling improved
- [ ] HITL properly pauses/resumes
- [ ] Observability working
- [ ] Performance comparable or better

---

## Getting Help

- **Discord**: https://discord.com/invite/MXE49hrKDk
- **GitHub Issues**: https://github.com/adenhq/hive/issues
- **Documentation**: https://github.com/adenhq/hive/docs

---

*Last updated: February 2026*
