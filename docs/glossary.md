# Glossary

This glossary defines core Hive concepts in plain, beginner-friendly language to help you get started quickly.

## Core Concepts

### Agent
An AI worker that performs specific tasks by following a generated workflow. Agents are created from natural language goals and can self-improve when they fail.

### Coding Agent
The AI assistant that helps you build agents by converting your natural language goals into executable code and workflows.

### Node
A single step in an agent's workflow that performs one specific action, like making an LLM call, running a function, or making a decision.

### Graph
The complete workflow structure that connects multiple nodes to achieve an agent's goal. Think of it as a flowchart for your AI agent.

### Workflow
The sequence of steps an agent follows to complete a task. In Hive, workflows are dynamically generated rather than hardcoded.

### Executor
The engine that runs the agent graph by executing nodes in the correct order and handling the flow between them.

### Tools
Pre-built functions that agents can use, like web search, file operations, or API calls. Hive includes 19 MCP tools out of the box.

### Runtime
The environment that provides agents with memory, LLM access, and tool capabilities while they're running.

### Memory
The storage system where agents keep information during and between runs, including both short-term and long-term data.

### Tasks
Specific units of work that agents need to accomplish as part of their overall goal.

## Advanced Concepts

### Self-Improving
The ability of agents to automatically fix their own failures by analyzing what went wrong and updating their workflow.

### Goal-Driven Development
The approach of describing what you want to achieve (the goal) instead of how to achieve it (the implementation).

### Human-in-the-Loop
Nodes that pause execution to ask for human input, allowing collaboration between people and AI agents.

### SDK-Wrapped Nodes
Nodes that automatically come with built-in capabilities like memory access, monitoring, and tool integration.

### MCP (Model Context Protocol)
A standard that allows agents to securely access external tools and services in a controlled way.

### GraphSpec
The configuration file (agent.json) that defines an agent's complete structure, including nodes, connections, and goals.

### AgentRunner
The component that loads, validates, and starts running an agent from its GraphSpec configuration.

### NodeContext
The environment each node runs in, providing access to memory, LLM connections, and tools.

---

*Need more details? Check out our [complete documentation](https://docs.adenhq.com/).*
