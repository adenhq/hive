# Migrating from LangChain to Hive

*A practical guide for teams moving from component-based to goal-driven agent development*

---

## Overview

This guide helps you migrate existing LangChain applications to Hive. The migration preserves your existing logic while adding Hive's self-improvement, observability, and human-in-the-loop capabilities.

**Estimated effort:**
- Simple chains: 1-2 hours
- Complex agents: 1-2 days
- Multi-agent systems: 1 week

---

## Migration Strategy

### Recommended Approach: Gradual Migration

Don't rewrite everything at once. Instead:

1. **Phase 1**: Keep LangChain tools, wrap in Hive nodes
2. **Phase 2**: Define goals and success criteria
3. **Phase 3**: Add Hive-specific features (HITL, evolution)
4. **Phase 4**: Migrate tools to native MCP format

---

## Step 1: Map LangChain Concepts to Hive

| LangChain Concept | Hive Equivalent |
|-------------------|-----------------|
| Chain | Graph (sequence of nodes) |
| Agent | LLM node with tools |
| Tool | MCP tool or function node |
| Memory | SharedMemory |
| PromptTemplate | Node system_prompt |
| OutputParser | Pydantic output model |
| AgentExecutor | GraphExecutor |
| Callbacks | Runtime hooks / event bus |

---

## Step 2: Convert Chains to Graphs

### Before: LangChain Chain

```python
from langchain import LLMChain, PromptTemplate
from langchain.chains import SequentialChain

# Define individual chains
research_chain = LLMChain(
    llm=llm,
    prompt=PromptTemplate(template="Research: {topic}"),
    output_key="research"
)

summarize_chain = LLMChain(
    llm=llm,
    prompt=PromptTemplate(template="Summarize: {research}"),
    output_key="summary"
)

# Connect them
pipeline = SequentialChain(
    chains=[research_chain, summarize_chain],
    input_variables=["topic"],
    output_variables=["summary"]
)

result = pipeline({"topic": "AI agents"})
```

### After: Hive Graph

```python
from framework.graph.node import NodeSpec
from framework.graph.edge import EdgeSpec, GraphSpec
from framework.graph.goal import Goal

# Define goal (what LangChain doesn't have)
goal = Goal(
    id="research-summarize",
    name="Research and Summarize",
    description="Research a topic and create a summary",
    success_criteria=[
        {"metric": "output_contains", "target": "summary"},
        {"metric": "llm_judge", "target": "Summary is accurate and comprehensive"}
    ]
)

# Define nodes (equivalent to chains)
nodes = [
    NodeSpec(
        id="research",
        name="Research",
        description="Research the given topic",
        node_type="llm_generate",
        input_keys=["topic"],
        output_keys=["research"],
        system_prompt="You are a research assistant. Research the given topic thoroughly."
    ),
    NodeSpec(
        id="summarize",
        name="Summarize",
        description="Summarize the research findings",
        node_type="llm_generate",
        input_keys=["research"],
        output_keys=["summary"],
        system_prompt="You are a summarization expert. Create a clear, concise summary."
    )
]

# Define edges (equivalent to SequentialChain)
edges = [
    EdgeSpec(id="e1", source="research", target="summarize", condition="on_success")
]

# Create graph
graph = GraphSpec(
    id="research-pipeline",
    goal_id=goal.id,
    nodes=nodes,
    edges=edges,
    entry_node="research",
    terminal_nodes=["summarize"]
)
```

---

## Step 3: Convert Tools

### Before: LangChain Tool

```python
from langchain.tools import Tool, StructuredTool
from pydantic import BaseModel

class SearchInput(BaseModel):
    query: str
    max_results: int = 10

def search_web(query: str, max_results: int = 10) -> str:
    # Search implementation
    return f"Results for {query}"

search_tool = StructuredTool.from_function(
    func=search_web,
    name="web_search",
    description="Search the web for information",
    args_schema=SearchInput
)
```

### After: Hive MCP Tool

```python
# In tools.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-tools")

@mcp.tool()
def web_search(query: str, max_results: int = 10) -> str:
    """Search the web for information.

    Args:
        query: The search query
        max_results: Maximum number of results to return
    """
    # Search implementation
    return f"Results for {query}"
```

### Keeping LangChain Tools (Temporary)

You can wrap LangChain tools during migration:

```python
# Adapter to use LangChain tools in Hive
from framework.llm import Tool

def langchain_to_hive_tool(lc_tool):
    """Convert a LangChain tool to Hive format."""
    return Tool(
        name=lc_tool.name,
        description=lc_tool.description,
        parameters=lc_tool.args_schema.schema() if lc_tool.args_schema else {},
        function=lc_tool.func
    )

# Use your existing LangChain tools
hive_search_tool = langchain_to_hive_tool(search_tool)
```

---

## Step 4: Convert Memory

### Before: LangChain Memory

```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# Memory is passed to agent
agent = create_openai_tools_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, memory=memory)
```

### After: Hive SharedMemory

```python
from framework.graph.node import SharedMemory

# SharedMemory is automatically managed by GraphExecutor
# You declare what each node reads and writes

nodes = [
    NodeSpec(
        id="chat_node",
        input_keys=["user_message", "chat_history"],  # Reads from memory
        output_keys=["response", "chat_history"],     # Writes to memory
        # ...
    )
]

# Memory is thread-safe with per-key locking
# No manual memory management needed
```

---

## Step 5: Convert Agents

### Before: LangChain Agent

```python
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")

agent = create_openai_tools_agent(
    llm=llm,
    tools=tools,
    prompt=agent_prompt
)

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    max_iterations=10
)

result = executor.invoke({"input": "Help me with..."})
```

### After: Hive LLM Node with Tools

```python
from framework.graph.node import NodeSpec
from framework.graph.executor import GraphExecutor

# Node with tool access
agent_node = NodeSpec(
    id="agent",
    name="Agent",
    description="AI assistant with tools",
    node_type="llm_tool_use",  # Can use tools
    input_keys=["user_input"],
    output_keys=["response"],
    tools=["web_search", "calculator", "file_reader"],  # Available tools
    system_prompt="You are a helpful assistant...",
    max_retries=3,  # Built-in retry
    max_tool_calls=10  # Equivalent to max_iterations
)

# Execute
executor = GraphExecutor(runtime=runtime)
result = await executor.execute(graph=graph, goal=goal)
```

---

## Step 6: Add Hive-Specific Features

Once your basic migration is complete, add Hive's unique capabilities:

### Human-in-the-Loop

```python
# Add approval nodes
approval_node = NodeSpec(
    id="human_approval",
    name="Human Approval",
    description="Pause for human review",
    node_type="human_input",
    input_keys=["draft_response"],
    output_keys=["approved_response", "feedback"]
)

# Mark as pause node in graph
graph = GraphSpec(
    # ...
    pause_nodes=["human_approval"]
)
```

### Success Criteria

```python
# Define what success looks like
goal = Goal(
    success_criteria=[
        {"metric": "output_contains", "target": "answer"},
        {"metric": "llm_judge", "target": "Response is helpful and accurate"},
        {"metric": "custom", "target": "response_time_under_5s"}
    ],
    constraints=[
        {"type": "hard", "category": "cost", "check": "tokens < 10000"},
        {"type": "soft", "category": "quality", "check": "no_hedging_language"}
    ]
)
```

### Automatic Evolution

```python
# Hive automatically captures failures and suggests improvements
# No code needed - just enable evolution in your agent config

agent_config = {
    "evolution": {
        "enabled": True,
        "min_samples": 10,  # Analyze after 10 runs
        "auto_apply": False  # Suggest changes, don't auto-apply
    }
}
```

---

## Common Migration Patterns

### Pattern 1: RAG Pipeline

LangChain is strong at RAG. Keep your retrieval, add Hive orchestration:

```python
# Keep your LangChain retriever
from langchain.vectorstores import Chroma
retriever = Chroma(...).as_retriever()

# Wrap in Hive function node
def retrieve_context(query: str) -> str:
    docs = retriever.get_relevant_documents(query)
    return "\n".join([d.page_content for d in docs])

# Use in Hive graph
retrieve_node = NodeSpec(
    id="retrieve",
    node_type="function",
    function="retrieve_context",
    input_keys=["query"],
    output_keys=["context"]
)
```

### Pattern 2: Multi-Step Chains

```python
# LangChain: Sequential chain of 5 steps
# Hive: Linear graph with 5 nodes

edges = [
    EdgeSpec(source="step1", target="step2", condition="on_success"),
    EdgeSpec(source="step2", target="step3", condition="on_success"),
    EdgeSpec(source="step3", target="step4", condition="on_success"),
    EdgeSpec(source="step4", target="step5", condition="on_success"),
    # Add error handling edges
    EdgeSpec(source="step2", target="error_handler", condition="on_failure"),
    EdgeSpec(source="step3", target="error_handler", condition="on_failure"),
]
```

### Pattern 3: Conditional Branching

```python
# LangChain: RouterChain or custom logic
# Hive: Router node or conditional edges

router_node = NodeSpec(
    id="router",
    node_type="router",
    routes={
        "technical": "tech_handler",
        "billing": "billing_handler",
        "general": "general_handler"
    }
)

# Or use conditional edges
edges = [
    EdgeSpec(
        source="classify",
        target="tech_handler",
        condition="conditional",
        condition_expr="category == 'technical'"
    ),
    EdgeSpec(
        source="classify",
        target="billing_handler",
        condition="conditional",
        condition_expr="category == 'billing'"
    )
]
```

---

## Checklist

### Pre-Migration
- [ ] Inventory all LangChain chains and agents
- [ ] Document current tools and their usage
- [ ] Identify critical paths and success metrics
- [ ] Set up Hive development environment

### Migration
- [ ] Convert main chain to Hive graph
- [ ] Migrate or wrap tools
- [ ] Define goals with success criteria
- [ ] Add error handling edges
- [ ] Implement HITL where needed

### Post-Migration
- [ ] Run parallel comparison tests
- [ ] Enable observability and decision logging
- [ ] Configure evolution settings
- [ ] Remove LangChain dependencies (optional)

---

## Getting Help

- **Discord**: https://discord.com/invite/MXE49hrKDk
- **GitHub Issues**: https://github.com/adenhq/hive/issues
- **Documentation**: https://github.com/adenhq/hive/docs

---

*Last updated: February 2026*
