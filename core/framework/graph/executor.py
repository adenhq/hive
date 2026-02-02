"""
Graph Executor - Runs agent graphs.

The executor:
1. Takes a GraphSpec and Goal
2. Initializes shared memory
3. Executes nodes following edges
4. Records all decisions to Runtime
5. Returns the final result
"""

import logging
import json
import time
from typing import Any, Callable
from dataclasses import dataclass, field

from framework.runtime.core import Runtime
from framework.graph.goal import Goal
from framework.graph.node import (
    NodeSpec,
    NodeContext,
    NodeResult,
    NodeProtocol,
    SharedMemory,
    LLMNode,
    RouterNode,
    FunctionNode,
)
from framework.graph.edge import GraphSpec
from framework.graph.validator import OutputValidator
from framework.graph.output_cleaner import OutputCleaner, CleansingConfig
from framework.llm.provider import LLMProvider
from framework.tools.base import Tool
from framework.tools.registry import ToolRegistry


@dataclass
class ExecutionResult:
    """Result of executing a graph."""
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    steps_executed: int = 0
    total_tokens: int = 0
    total_latency_ms: int = 0
    path: list[str] = field(default_factory=list)  # Node IDs traversed
    history: list[dict] = field(default_factory=list) # <--- ADDED: Track History
    paused_at: str | None = None  # Node ID where execution paused for HITL
    session_state: dict[str, Any] = field(default_factory=dict)  # State to resume from


class GraphExecutor:
    """
    Executes agent graphs.
    """

    def __init__(
        self,
        runtime: Runtime,
        llm: LLMProvider | None = None,
        tools: list[Tool] | None = None,
        tool_executor: Callable | None = None,
        node_registry: dict[str, NodeProtocol] | None = None,
        approval_callback: Callable | None = None,
        cleansing_config: CleansingConfig | None = None,
    ):
        """
        Initialize the executor.
        """
        self.runtime = runtime
        self.llm = llm
        self.tools = tools or []
        self.tool_executor = tool_executor
        self.node_registry = node_registry or {}
        self.approval_callback = approval_callback
        self.validator = OutputValidator()
        self.logger = logging.getLogger(__name__)

        # Initialize output cleaner
        self.cleansing_config = cleansing_config or CleansingConfig()
        self.output_cleaner = OutputCleaner(
            config=self.cleansing_config,
            llm_provider=llm,
        )

    def _validate_tools(self, graph: GraphSpec) -> list[str]:
        """
        Validate that all tools declared by nodes are available.
        """
        errors = []
        available_tool_names = {t.name for t in self.tools}

        for node in graph.nodes:
            if node.tools:
                missing = set(node.tools) - available_tool_names
                if missing:
                    errors.append(
                        f"Node '{node.name}' (id={node.id}) requires tools {sorted(missing)} "
                        f"but they are not registered. Available tools: {sorted(available_tool_names) if available_tool_names else 'none'}"
                    )

        return errors


    async def execute(
        self,
        graph: GraphSpec,
        goal: Goal,
        input_data: dict[str, Any] | None = None,
        session_state: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """
        Execute a graph for a goal.
        """
        # Validate graph
        errors = graph.validate()
        if errors:
            return ExecutionResult(
                success=False,
                error=f"Invalid graph: {errors}",
            )

        # Validate tool availability
        tool_errors = self._validate_tools(graph)
        if tool_errors:
            self.logger.error("❌ Tool validation failed:")
            for err in tool_errors:
                self.logger.error(f"   • {err}")
            return ExecutionResult(
                success=False,
                error=f"Missing tools: {'; '.join(tool_errors)}. Register tools via ToolRegistry or remove tool declarations from nodes.",
            )
        
        # --- NEW: Initialize Registry ---
        registry = ToolRegistry()
        for t in self.tools:
            registry.register(t)

        # Initialize execution state
        memory = SharedMemory()

        # Restore session state if provided
        if session_state and "memory" in session_state:
            # Restore memory from previous session
            for key, value in session_state["memory"].items():
                memory.write(key, value)
            self.logger.info(f"📥 Restored session state with {len(session_state['memory'])} memory keys")

        # Write new input data to memory (each key individually)
        if input_data:
            for key, value in input_data.items():
                memory.write(key, value)

        path: list[str] = []
        history: list[dict] = [] # <--- NEW: Track History
        total_tokens = 0
        total_latency = 0
        node_retry_counts: dict[str, int] = {}  # Track retries per node

        # Determine entry point (may differ if resuming)
        current_node_id = graph.get_entry_point(session_state)
        steps = 0

        if session_state and current_node_id != graph.entry_node:
            self.logger.info(f"🔄 Resuming from: {current_node_id}")

        # Start run
        _run_id = self.runtime.start_run(
            goal_id=goal.id,
            goal_description=goal.description,
            input_data=input_data or {},
        )

        self.logger.info(f"🚀 Starting execution: {goal.name}")
        self.logger.info(f"   Goal: {goal.description}")
        self.logger.info(f"   Entry node: {graph.entry_node}")

        try:
            while steps < graph.max_steps:
                steps += 1

                # Get current node
                node_spec = graph.get_node(current_node_id)
                if node_spec is None:
                    raise RuntimeError(f"Node not found: {current_node_id}")

                path.append(current_node_id)

                # Check if pause (HITL) before execution
                if current_node_id in graph.pause_nodes:
                    self.logger.info(f"⏸ Paused at HITL node: {node_spec.name}")
                    # Execute this node, then pause
                    # (We'll check again after execution and save state)

                self.logger.info(f"\n▶ Step {steps}: {node_spec.name} ({node_spec.node_type})")
                self.logger.info(f"   Inputs: {node_spec.input_keys}")
                self.logger.info(f"   Outputs: {node_spec.output_keys}")

                # Build context for node
                ctx = self._build_context(
                    node_spec=node_spec,
                    memory=memory,
                    goal=goal,
                    input_data=input_data or {},
                    history=history # <--- PASSING HISTORY
                )

                # Log actual input data being read
                if node_spec.input_keys:
                    self.logger.info("   Reading from memory:")
                    for key in node_spec.input_keys:
                        value = memory.read(key)
                        if value is not None:
                            # Truncate long values for readability
                            value_str = str(value)
                            if len(value_str) > 200:
                                value_str = value_str[:200] + "..."
                            self.logger.info(f"      {key}: {value_str}")

                # Get or create node implementation
                node_impl = self._get_node_implementation(node_spec)

                # Validate inputs
                validation_errors = node_impl.validate_input(ctx)
                if validation_errors:
                    self.logger.warning(f"⚠ Validation warnings: {validation_errors}")
                    self.runtime.report_problem(
                        severity="warning",
                        description=f"Validation errors for {current_node_id}: {validation_errors}",
                    )

                # Execute node
                self.logger.info("   Executing...")
                result = await node_impl.execute(ctx)

                # --- START: TOOL EXECUTION LOOP ---
                if result.success and getattr(result, "tool_calls", None):
                    self.logger.info(f"   🛠️ Agent requested {len(result.tool_calls)} tool(s)...")
                    
                    # 1. Add the Assistant's "Call" message to history
                    if result.messages:
                        history.extend(result.messages)

                    for call in result.tool_calls:
                        tool_name = call.function.name
                        try:
                            args = json.loads(call.function.arguments)
                        except:
                            args = {}
                        
                        self.logger.info(f"      Running: {tool_name}({args})")
                        
                        # 2. Execute
                        try:
                            tool_output = registry.execute(tool_name, args)
                        except Exception as e:
                            tool_output = f"Error executing tool: {str(e)}"

                        # 3. Add Result to History
                        tool_msg = {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": tool_name,
                            "content": str(tool_output)
                        }
                        history.append(tool_msg)
                    
                    self.logger.info(f"   🔄 Tool execution done. Re-invoking node '{current_node_id}'...")
                    # Loop back to same node (without incrementing next_node logic)
                    continue 
                # --- END: TOOL EXECUTION LOOP ---

                if result.success:
                    # Validate output before accepting it
                    if result.output and node_spec.output_keys:
                        validation = self.validator.validate_all(
                            output=result.output,
                            expected_keys=node_spec.output_keys,
                            check_hallucination=True,
                        )
                        if not validation.success:
                            self.logger.error(f"   ✗ Output validation failed: {validation.error}")
                            result = NodeResult(
                                success=False,
                                error=f"Output validation failed: {validation.error}",
                                output={},
                                tokens_used=result.tokens_used,
                                latency_ms=result.latency_ms,
                            )

                if result.success:
                    self.logger.info(f"   ✓ Success (tokens: {result.tokens_used}, latency: {result.latency_ms}ms)")
                    
                    # Add messages to history if present
                    if result.messages:
                        history.extend(result.messages)

                    # Generate and log human-readable summary
                    summary = result.to_summary(node_spec)
                    self.logger.info(f"   📝 Summary: {summary}")

                    # Log what was written to memory (detailed view)
                    if result.output:
                        self.logger.info("   Written to memory:")
                        for key, value in result.output.items():
                            value_str = str(value)
                            if len(value_str) > 200:
                                value_str = value_str[:200] + "..."
                            self.logger.info(f"      {key}: {value_str}")
                else:
                    self.logger.error(f"   ✗ Failed: {result.error}")

                total_tokens += result.tokens_used
                total_latency += result.latency_ms

                # Handle failure
                if not result.success:
                    # Track retries per node
                    node_retry_counts[current_node_id] = node_retry_counts.get(current_node_id, 0) + 1

                    if node_retry_counts[current_node_id] < node_spec.max_retries:
                        # Retry - don't increment steps for retries
                        steps -= 1
                        self.logger.info(f"   ↻ Retrying ({node_retry_counts[current_node_id]}/{node_spec.max_retries})...")
                        continue
                    else:
                        # Max retries exceeded - fail the execution
                        self.logger.error(f"   ✗ Max retries ({node_spec.max_retries}) exceeded for node {current_node_id}")
                        self.runtime.report_problem(
                            severity="critical",
                            description=f"Node {current_node_id} failed after {node_spec.max_retries} attempts: {result.error}",
                        )
                        self.runtime.end_run(
                            success=False,
                            output_data=memory.read_all(),
                            narrative=f"Failed at {node_spec.name} after {node_spec.max_retries} retries: {result.error}",
                        )
                        return ExecutionResult(
                            success=False,
                            error=f"Node '{node_spec.name}' failed after {node_spec.max_retries} attempts: {result.error}",
                            output=memory.read_all(),
                            steps_executed=steps,
                            total_tokens=total_tokens,
                            total_latency_ms=total_latency,
                            path=path,
                            history=history,
                        )

                # Check if we just executed a pause node - if so, save state and return
                # This must happen BEFORE determining next node, since pause nodes may have no edges
                if node_spec.id in graph.pause_nodes:
                    self.logger.info("💾 Saving session state after pause node")
                    saved_memory = memory.read_all()
                    session_state_out = {
                        "paused_at": node_spec.id,
                        "resume_from": f"{node_spec.id}_resume",  # Resume key
                        "memory": saved_memory,
                        "next_node": None,  # Will resume from entry point
                        "history": history # <--- Save history
                    }

                    self.runtime.end_run(
                        success=True,
                        output_data=saved_memory,
                        narrative=f"Paused at {node_spec.name} after {steps} steps",
                    )

                    return ExecutionResult(
                        success=True,
                        output=saved_memory,
                        steps_executed=steps,
                        total_tokens=total_tokens,
                        total_latency_ms=total_latency,
                        path=path,
                        paused_at=node_spec.id,
                        session_state=session_state_out,
                        history=history,
                    )

                # Check if this is a terminal node - if so, we're done
                if node_spec.id in graph.terminal_nodes:
                    self.logger.info(f"✓ Reached terminal node: {node_spec.name}")
                    break

                # Determine next node
                if result.next_node:
                    # Router explicitly set next node
                    self.logger.info(f"   → Router directing to: {result.next_node}")
                    current_node_id = result.next_node
                else:
                    # Follow edges
                    next_node = self._follow_edges(
                        graph=graph,
                        goal=goal,
                        current_node_id=current_node_id,
                        current_node_spec=node_spec,
                        result=result,
                        memory=memory,
                    )
                    if next_node is None:
                        self.logger.info("   → No more edges, ending execution")
                        break  # No valid edge, end execution
                    next_spec = graph.get_node(next_node)
                    self.logger.info(f"   → Next: {next_spec.name if next_spec else next_node}")
                    current_node_id = next_node

                # Update input_data for next node
                input_data = result.output

            # Collect output
            output = memory.read_all()
            
            # --- START: TIMEOUT FIX ---
            if steps >= graph.max_steps:
                error_msg = f"Max steps exceeded ({graph.max_steps}). Agent failed to reach a conclusion."
                self.logger.error(f"❌ {error_msg}")
                self.runtime.report_problem(severity="error", description=error_msg)
                
                return ExecutionResult(
                    success=False,
                    error=error_msg,
                    output=output,
                    history=history,
                    steps_executed=steps
                )
            # --- END: TIMEOUT FIX ---

            self.logger.info("\n✓ Execution complete!")
            self.logger.info(f"   Steps: {steps}")
            self.logger.info(f"   Path: {' → '.join(path)}")
            self.logger.info(f"   Total tokens: {total_tokens}")
            self.logger.info(f"   Total latency: {total_latency}ms")

            self.runtime.end_run(
                success=True,
                output_data=output,
                narrative=f"Executed {steps} steps through path: {' -> '.join(path)}",
            )

            return ExecutionResult(
                success=True,
                output=output,
                steps_executed=steps,
                total_tokens=total_tokens,
                total_latency_ms=total_latency,
                path=path,
                history=history,
            )

        except Exception as e:
            self.runtime.report_problem(
                severity="critical",
                description=str(e),
            )
            self.runtime.end_run(
                success=False,
                narrative=f"Failed at step {steps}: {e}",
            )
            return ExecutionResult(
                success=False,
                error=str(e),
                steps_executed=steps,
                path=path,
                history=history,
            )

    def _build_context(
        self,
        node_spec: NodeSpec,
        memory: SharedMemory,
        goal: Goal,
        input_data: dict[str, Any],
        history: list[dict], # <--- ADDED ARGUMENT
    ) -> NodeContext:
        """Build execution context for a node."""
        # Filter tools to those available to this node
        available_tools = []
        if node_spec.tools:
            available_tools = [t for t in self.tools if t.name in node_spec.tools]

        # Create scoped memory view
        scoped_memory = memory.with_permissions(
            read_keys=node_spec.input_keys,
            write_keys=node_spec.output_keys,
        )

        return NodeContext(
            runtime=self.runtime,
            node_id=node_spec.id,
            node_spec=node_spec,
            memory=scoped_memory,
            input_data=input_data,
            llm=self.llm,
            available_tools=available_tools,
            goal_context=goal.to_prompt_context(),
            goal=goal,  # Pass Goal object for LLM-powered routers
            history=history, # <--- PASSING HISTORY
        )

    # Valid node types - no ambiguous "llm" type allowed
    VALID_NODE_TYPES = {"llm_tool_use", "llm_generate", "router", "function", "human_input"}

    def _get_node_implementation(self, node_spec: NodeSpec) -> NodeProtocol:
        """Get or create a node implementation."""
        # Check registry first
        if node_spec.id in self.node_registry:
            return self.node_registry[node_spec.id]

        # Validate node type
        if node_spec.node_type not in self.VALID_NODE_TYPES:
            raise RuntimeError(
                f"Invalid node type '{node_spec.node_type}' for node '{node_spec.id}'. "
                f"Must be one of: {sorted(self.VALID_NODE_TYPES)}. "
                f"Use 'llm_tool_use' for nodes that call tools, 'llm_generate' for text generation."
            )

        # Create based on type
        if node_spec.node_type == "llm_tool_use":
            if not node_spec.tools:
                raise RuntimeError(
                    f"Node '{node_spec.id}' is type 'llm_tool_use' but declares no tools. "
                    "Either add tools to the node or change type to 'llm_generate'."
                )
            return LLMNode(tool_executor=self.tool_executor, require_tools=True)

        if node_spec.node_type == "llm_generate":
            return LLMNode(tool_executor=None, require_tools=False)

        if node_spec.node_type == "router":
            return RouterNode()

        if node_spec.node_type == "function":
            # Function nodes need explicit registration
            raise RuntimeError(
                f"Function node '{node_spec.id}' not registered. "
                "Register with node_registry."
            )

        if node_spec.node_type == "human_input":
            # Human input nodes are handled specially by HITL mechanism
            return LLMNode(tool_executor=None, require_tools=False)

        # Should never reach here due to validation above
        raise RuntimeError(f"Unhandled node type: {node_spec.node_type}")

    def _follow_edges(
        self,
        graph: GraphSpec,
        goal: Goal,
        current_node_id: str,
        current_node_spec: Any,
        result: NodeResult,
        memory: SharedMemory,
    ) -> str | None:
        """Determine the next node by following edges."""
        edges = graph.get_outgoing_edges(current_node_id)

        for edge in edges:
            target_node_spec = graph.get_node(edge.target)

            if edge.should_traverse(
                source_success=result.success,
                source_output=result.output,
                memory=memory.read_all(),
                llm=self.llm,
                goal=goal,
                source_node_name=current_node_spec.name if current_node_spec else current_node_id,
                target_node_name=target_node_spec.name if target_node_spec else edge.target,
            ):
                # Validate and clean output before mapping inputs
                if self.cleansing_config.enabled and target_node_spec:
                    output_to_validate = result.output

                    validation = self.output_cleaner.validate_output(
                        output=output_to_validate,
                        source_node_id=current_node_id,
                        target_node_spec=target_node_spec,
                    )

                    if not validation.valid:
                        self.logger.warning(
                            f"⚠ Output validation failed: {validation.errors}"
                        )

                        # Clean the output
                        cleaned_output = self.output_cleaner.clean_output(
                            output=output_to_validate,
                            source_node_id=current_node_id,
                            target_node_spec=target_node_spec,
                            validation_errors=validation.errors,
                        )

                        # Update result with cleaned output
                        result.output = cleaned_output

                        # Write cleaned output back to memory
                        for key, value in cleaned_output.items():
                            memory.write(key, value)

                        # Revalidate
                        revalidation = self.output_cleaner.validate_output(
                            output=cleaned_output,
                            source_node_id=current_node_id,
                            target_node_spec=target_node_spec,
                        )

                        if revalidation.valid:
                            self.logger.info("✓ Output cleaned and validated successfully")
                        else:
                            self.logger.error(
                                f"✗ Cleaning failed, errors remain: {revalidation.errors}"
                            )
                            # Continue anyway if fallback_to_raw is True

                # Map inputs
                mapped = edge.map_inputs(result.output, memory.read_all())
                for key, value in mapped.items():
                    memory.write(key, value)

                return edge.target

        return None

    def register_node(self, node_id: str, implementation: NodeProtocol) -> None:
        """Register a custom node implementation."""
        self.node_registry[node_id] = implementation

    def register_function(self, node_id: str, func: Callable) -> None:
        """Register a function as a node."""
        self.node_registry[node_id] = FunctionNode(func)