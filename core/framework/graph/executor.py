"""
Graph Executor - Runs agent graphs.

The executor:
1. Takes a GraphSpec and Goal
2. Initializes shared memory
3. Executes nodes following edges
4. Records all decisions to Runtime
5. Returns the final result

Error Handling:
- All errors are classified as ExecutionError with specific codes and categories
- Retriable errors trigger automatic retries
- Fatal errors terminate execution immediately
- Consistent error contract ensures predictable failure semantics
"""

import logging
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
from framework.llm.provider import LLMProvider, Tool
from framework.graph.execution_errors import (
    ExecutionError,
    FatalExecutionError,
    RetriableExecutionError,
    ValidationExecutionError,
    DependencyExecutionError,
    ErrorCode,
    ErrorCategory,
    classify_error,
)


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
    paused_at: str | None = None  # Node ID where execution paused for HITL
    session_state: dict[str, Any] = field(default_factory=dict)  # State to resume from


class GraphExecutor:
    """
    Executes agent graphs.

    Example:
        executor = GraphExecutor(
            runtime=runtime,
            llm=llm,
            tools=tools,
            tool_executor=my_tool_executor,
        )

        result = await executor.execute(
            graph=graph_spec,
            goal=goal,
            input_data={"expression": "2 + 3"},
        )
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

        Args:
            runtime: Runtime for decision logging
            llm: LLM provider for LLM nodes
            tools: Available tools
            tool_executor: Function to execute tools
            node_registry: Custom node implementations by ID
            approval_callback: Optional callback for human-in-the-loop approval
            cleansing_config: Optional output cleansing configuration
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

        Returns:
            List of error messages (empty if all tools are available)
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

        Args:
            graph: The graph specification
            goal: The goal driving execution
            input_data: Initial input data
            session_state: Optional session state to resume from (with paused_at, memory, etc.)

        Returns:
            ExecutionResult with output and metrics
        
        Raises:
            ExecutionError: For unrecoverable failures after max retries
        """
        try:
            # Validate graph
            errors = graph.validate()
            if errors:
                raise FatalExecutionError(
                    code=ErrorCode.INVALID_CONFIGURATION,
                    message=f"Invalid graph: {errors}",
                    context={"graph_id": graph.id}
                )

            # Validate tool availability
            tool_errors = self._validate_tools(graph)
            if tool_errors:
                self.logger.error("❌ Tool validation failed:")
                for err in tool_errors:
                    self.logger.error(f"   • {err}")
                raise FatalExecutionError(
                    code=ErrorCode.MISSING_TOOL,
                    message=f"Missing tools: {'; '.join(tool_errors)}. Register tools via ToolRegistry or remove tool declarations from nodes.",
                    context={"graph_id": graph.id, "errors": tool_errors}
                )

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
            total_tokens = 0
            total_latency = 0
            node_retry_counts: dict[str, int] = {}  # Track retries per node
            max_retries_per_node = 3

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

            while steps < graph.max_steps:
                steps += 1

                # Get current node
                node_spec = graph.get_node(current_node_id)
                if node_spec is None:
                    raise FatalExecutionError(
                        code=ErrorCode.NODE_NOT_FOUND,
                        message=f"Node not found: {current_node_id}",
                        context={"node_id": current_node_id, "graph_id": graph.id}
                    )

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
                try:
                    node_impl = self._get_node_implementation(node_spec)
                except ExecutionError:
                    # Re-raise ExecutionErrors as-is
                    raise
                except Exception as e:
                    # Wrap unexpected errors
                    raise FatalExecutionError(
                        code=ErrorCode.INVALID_NODE_TYPE,
                        message=f"Failed to instantiate node '{node_spec.id}': {str(e)}",
                        context={"node_id": node_spec.id, "node_type": node_spec.node_type},
                        original_error=e
                    )

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
                try:
                    result = await node_impl.execute(ctx)
                except ExecutionError:
                    # Re-raise ExecutionErrors
                    raise
                except Exception as e:
                    # Wrap execution errors
                    exec_error = classify_error(e, default_code=ErrorCode.EXECUTION_FAILED)
                    exec_error.context.update({"node_id": node_spec.id})
                    raise exec_error

                if result.success:
                    # Validate output before accepting it
                    if result.output and node_spec.output_keys:
                        try:
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
                        except Exception as e:
                            # Wrap validation errors
                            raise ValidationExecutionError(
                                message=f"Output validation failed: {str(e)}",
                                context={"node_id": node_spec.id},
                                original_error=e
                            )

                if result.success:
                    self.logger.info(f"   ✓ Success (tokens: {result.tokens_used}, latency: {result.latency_ms}ms)")

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

                    if node_retry_counts[current_node_id] < max_retries_per_node:
                        # Retry - don't increment steps for retries
                        steps -= 1
                        self.logger.info(f"   ↻ Retrying ({node_retry_counts[current_node_id]}/{max_retries_per_node})...")
                        continue
                    else:
                        # Max retries exceeded - fail the execution
                        self.logger.error(f"   ✗ Max retries ({max_retries_per_node}) exceeded for node {current_node_id}")
                        self.runtime.report_problem(
                            severity="critical",
                            description=f"Node {current_node_id} failed after {max_retries_per_node} attempts: {result.error}",
                        )
                        
                        # Raise consistent error
                        raise FatalExecutionError(
                            code=ErrorCode.EXECUTION_FAILED,
                            message=f"Node '{node_spec.name}' failed after {max_retries_per_node} attempts: {result.error}",
                            context={
                                "node_id": current_node_id,
                                "node_name": node_spec.name,
                                "attempts": max_retries_per_node,
                                "error": result.error
                            }
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
            )

        except ExecutionError as e:
            # Log and report the structured error
            self.logger.error(f"❌ Execution error: {e}")
            self.logger.debug(f"   Error details: {e.to_dict()}")
            
            self.runtime.report_problem(
                severity="critical",
                description=str(e),
            )
            self.runtime.end_run(
                success=False,
                narrative=f"Execution failed: {e}",
            )
            
            # Return failed result (don't re-raise for expected ExecutionErrors)
            return ExecutionResult(
                success=False,
                error=str(e),
                steps_executed=steps,
                path=path,
            )
        except Exception as e:
            # Catch any remaining unexpected exceptions and wrap them
            exec_error = classify_error(e, default_code=ErrorCode.UNKNOWN_ERROR)
            self.logger.error(f"❌ Unexpected error: {exec_error}")
            self.logger.debug(f"   Error details: {exec_error.to_dict()}")
            
            self.runtime.report_problem(
                severity="critical",
                description=str(exec_error),
            )
            self.runtime.end_run(
                success=False,
                narrative=f"Failed: {exec_error}",
            )
            
            return ExecutionResult(
                success=False,
                error=str(exec_error),
                steps_executed=steps,
                path=path,
            )

    def _build_context(
        self,
        node_spec: NodeSpec,
        memory: SharedMemory,
        goal: Goal,
        input_data: dict[str, Any],
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
        )

    def _get_node_implementation(self, node_spec: NodeSpec) -> NodeProtocol:
        """Get or create a node implementation."""
        # Check registry first
        if node_spec.id in self.node_registry:
            return self.node_registry[node_spec.id]

        # Validate node type
        if node_spec.node_type not in self.VALID_NODE_TYPES:
            raise FatalExecutionError(
                code=ErrorCode.INVALID_NODE_TYPE,
                message=f"Invalid node type '{node_spec.node_type}' for node '{node_spec.id}'. "
                        f"Must be one of: {sorted(self.VALID_NODE_TYPES)}. "
                        f"Use 'llm_tool_use' for nodes that call tools, 'llm_generate' for text generation.",
                context={"node_id": node_spec.id, "node_type": node_spec.node_type, "valid_types": list(self.VALID_NODE_TYPES)}
            )

        # Create based on type
        if node_spec.node_type == "llm_tool_use":
            if not node_spec.tools:
                raise FatalExecutionError(
                    code=ErrorCode.INVALID_CONFIGURATION,
                    message=f"Node '{node_spec.id}' is type 'llm_tool_use' but declares no tools. "
                            "Either add tools to the node or change type to 'llm_generate'.",
                    context={"node_id": node_spec.id, "node_type": "llm_tool_use"}
                )
            return LLMNode(tool_executor=self.tool_executor, require_tools=True)

        if node_spec.node_type == "llm_generate":
            return LLMNode(tool_executor=None, require_tools=False)

        if node_spec.node_type == "router":
            return RouterNode()

        if node_spec.node_type == "function":
            # Function nodes need explicit registration
            raise FatalExecutionError(
                code=ErrorCode.INVALID_CONFIGURATION,
                message=f"Function node '{node_spec.id}' not registered. "
                        "Register with node_registry.",
                context={"node_id": node_spec.id, "node_type": "function"}
            )

        if node_spec.node_type == "human_input":
            # Human input nodes are handled specially by HITL mechanism
            return LLMNode(tool_executor=None, require_tools=False)

        # Should never reach here due to validation above
        raise FatalExecutionError(
            code=ErrorCode.INVALID_NODE_TYPE,
            message=f"Unhandled node type: {node_spec.node_type}",
            context={"node_id": node_spec.id, "node_type": node_spec.node_type}
        )

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
