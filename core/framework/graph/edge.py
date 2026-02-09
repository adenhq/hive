"""
Edge Protocol - How nodes connect in a graph.

Edges define:
1. Source and target nodes
2. Conditions for traversal
3. Data mapping between nodes

Schema types (EdgeCondition, EdgeSpec, AsyncEntryPointSpec, GraphSpec) live in
framework.schemas.graph.edge. This module adds traversal behavior (should_traverse,
map_inputs, validate, get_node, etc.) via subclasses and re-exports for backward compatibility.
"""

from typing import Any

from pydantic import Field

from framework.graph.safe_eval import safe_eval
from framework.schemas.graph.edge import (
    AsyncEntryPointSpec,
    EdgeCondition,
    EdgeSpec as _EdgeSpecBase,
    GraphSpec as _GraphSpecBase,
)


class EdgeSpec(_EdgeSpecBase):
    """Edge specification with traversal behavior."""

    def should_traverse(
        self,
        source_success: bool,
        source_output: dict[str, Any],
        memory: dict[str, Any],
        llm: Any | None = None,
        goal: Any | None = None,
        source_node_name: str | None = None,
        target_node_name: str | None = None,
    ) -> bool:
        """Determine if this edge should be traversed."""
        if self.condition == EdgeCondition.ALWAYS:
            return True
        if self.condition == EdgeCondition.ON_SUCCESS:
            return source_success
        if self.condition == EdgeCondition.ON_FAILURE:
            return not source_success
        if self.condition == EdgeCondition.CONDITIONAL:
            return self._evaluate_condition(source_output, memory)
        if self.condition == EdgeCondition.LLM_DECIDE:
            if llm is None or goal is None:
                return source_success
            return self._llm_decide(
                llm=llm,
                goal=goal,
                source_success=source_success,
                source_output=source_output,
                memory=memory,
                source_node_name=source_node_name,
                target_node_name=target_node_name,
            )
        return False

    def _evaluate_condition(
        self,
        output: dict[str, Any],
        memory: dict[str, Any],
    ) -> bool:
        """Evaluate a conditional expression."""
        if not self.condition_expr:
            return True
        import logging

        context = {
            "output": output,
            "memory": memory,
            "result": output.get("result"),
            "true": True,
            "false": False,
            **memory,
        }
        try:
            return bool(safe_eval(self.condition_expr, context))
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"      ⚠ Condition evaluation failed: {self.condition_expr}")
            logger.warning(f"         Error: {e}")
            logger.warning(f"         Available context keys: {list(context.keys())}")
            return False

    def _llm_decide(
        self,
        llm: Any,
        goal: Any,
        source_success: bool,
        source_output: dict[str, Any],
        memory: dict[str, Any],
        source_node_name: str | None,
        target_node_name: str | None,
    ) -> bool:
        """Use LLM to decide if this edge should be traversed."""
        import json
        import logging
        import re

        prompt = f"""You are evaluating whether to proceed along an edge in an agent workflow.

**Goal**: {goal.name}
{goal.description}

**Current State**:
- Just completed: {source_node_name or "unknown node"}
- Success: {source_success}
- Output: {json.dumps(source_output, default=str)}

**Decision**:
Should we proceed to: {target_node_name or self.target}?
Edge description: {self.description or "No description"}

**Context from memory**:
{json.dumps({k: str(v)[:100] for k, v in list(memory.items())[:5]}, indent=2)}

Evaluate whether proceeding to this next node is the right step toward achieving the goal.
Respond with ONLY a JSON object:
{{"proceed": true/false, "reasoning": "brief explanation"}}"""

        try:
            response = llm.complete(
                messages=[{"role": "user", "content": prompt}],
                system="You are a routing agent. Respond with JSON only.",
                max_tokens=150,
            )
            json_match = re.search(r"\{[^{}]*\}", response.content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                proceed = data.get("proceed", False)
                reasoning = data.get("reasoning", "")
                logger = logging.getLogger(__name__)
                logger.info(f"      🤔 LLM routing decision: {'PROCEED' if proceed else 'SKIP'}")
                logger.info(f"         Reason: {reasoning}")
                return proceed
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"      ⚠ LLM routing failed, defaulting to on_success: {e}")
        return source_success

    def map_inputs(
        self,
        source_output: dict[str, Any],
        memory: dict[str, Any],
    ) -> dict[str, Any]:
        """Map source outputs to target inputs."""
        if not self.input_mapping:
            return dict(source_output)
        result = {}
        for target_key, source_key in self.input_mapping.items():
            if source_key in source_output:
                result[target_key] = source_output[source_key]
            elif source_key in memory:
                result[target_key] = memory[source_key]
        return result


class GraphSpec(_GraphSpecBase):
    """Graph specification with lookup and validation behavior."""

    edges: list[EdgeSpec] = Field(default_factory=list, description="All edge specifications")

    def get_node(self, node_id: str) -> Any | None:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def has_async_entry_points(self) -> bool:
        """Check if this graph uses async entry points."""
        return len(self.async_entry_points) > 0

    def get_async_entry_point(self, entry_point_id: str) -> AsyncEntryPointSpec | None:
        """Get an async entry point by ID."""
        for ep in self.async_entry_points:
            if ep.id == entry_point_id:
                return ep
        return None

    def get_outgoing_edges(self, node_id: str) -> list[EdgeSpec]:
        """Get all edges leaving a node, sorted by priority."""
        edges = [e for e in self.edges if e.source == node_id]
        return sorted(edges, key=lambda e: -e.priority)

    def get_incoming_edges(self, node_id: str) -> list[EdgeSpec]:
        """Get all edges entering a node."""
        return [e for e in self.edges if e.target == node_id]

    def detect_fan_out_nodes(self) -> dict[str, list[str]]:
        """Detect nodes that fan-out to multiple targets."""
        fan_outs: dict[str, list[str]] = {}
        for node in self.nodes:
            outgoing = self.get_outgoing_edges(node.id)
            success_edges = [e for e in outgoing if e.condition == EdgeCondition.ON_SUCCESS]
            if len(success_edges) > 1:
                fan_outs[node.id] = [e.target for e in success_edges]
        return fan_outs

    def detect_fan_in_nodes(self) -> dict[str, list[str]]:
        """Detect nodes that receive from multiple sources."""
        fan_ins: dict[str, list[str]] = {}
        for node in self.nodes:
            incoming = self.get_incoming_edges(node.id)
            if len(incoming) > 1:
                fan_ins[node.id] = [e.source for e in incoming]
        return fan_ins

    def get_entry_point(self, session_state: dict | None = None) -> str:
        """Get the appropriate entry point based on session state."""
        if not session_state:
            return self.entry_node
        paused_at = session_state.get("paused_at")
        if paused_at and paused_at in self.pause_nodes:
            resume_key = f"{paused_at}_resume"
            if resume_key in self.entry_points:
                return self.entry_points[resume_key]
        resume_from = session_state.get("resume_from")
        if resume_from:
            if resume_from in self.entry_points:
                return self.entry_points[resume_from]
            if resume_from in [n.id for n in self.nodes]:
                return resume_from
        return self.entry_node

    def validate(self) -> list[str]:
        """Validate the graph structure."""
        errors = []
        if not self.get_node(self.entry_node):
            errors.append(f"Entry node '{self.entry_node}' not found")
        seen_entry_ids = set()
        for entry_point in self.async_entry_points:
            if entry_point.id in seen_entry_ids:
                errors.append(f"Duplicate async entry point ID: '{entry_point.id}'")
            seen_entry_ids.add(entry_point.id)
            if not self.get_node(entry_point.entry_node):
                errors.append(
                    f"Async entry point '{entry_point.id}' references "
                    f"missing node '{entry_point.entry_node}'"
                )
            valid_isolation = {"isolated", "shared", "synchronized"}
            if entry_point.isolation_level not in valid_isolation:
                errors.append(
                    f"Async entry point '{entry_point.id}' has invalid isolation_level "
                    f"'{entry_point.isolation_level}'. Valid: {valid_isolation}"
                )
            valid_triggers = {"webhook", "api", "timer", "event", "manual"}
            if entry_point.trigger_type not in valid_triggers:
                errors.append(
                    f"Async entry point '{entry_point.id}' has invalid trigger_type "
                    f"'{entry_point.trigger_type}'. Valid: {valid_triggers}"
                )
        for term in self.terminal_nodes:
            if not self.get_node(term):
                errors.append(f"Terminal node '{term}' not found")
        for edge in self.edges:
            if not self.get_node(edge.source):
                errors.append(f"Edge '{edge.id}' references missing source '{edge.source}'")
            if not self.get_node(edge.target):
                errors.append(f"Edge '{edge.id}' references missing target '{edge.target}'")
        reachable = set()
        to_visit = [self.entry_node]
        for entry_point_node in self.entry_points.values():
            to_visit.append(entry_point_node)
        for async_entry in self.async_entry_points:
            to_visit.append(async_entry.entry_node)
        while to_visit:
            current = to_visit.pop()
            if current in reachable:
                continue
            reachable.add(current)
            for edge in self.get_outgoing_edges(current):
                to_visit.append(edge.target)
        async_entry_nodes = {ep.entry_node for ep in self.async_entry_points}
        for node in self.nodes:
            if node.id not in reachable:
                if (
                    node.id in self.pause_nodes
                    or node.id in self.entry_points.values()
                    or node.id in async_entry_nodes
                ):
                    continue
                errors.append(f"Node '{node.id}' is unreachable from entry")
        return errors


__all__ = [
    "AsyncEntryPointSpec",
    "EdgeCondition",
    "EdgeSpec",
    "GraphSpec",
]
