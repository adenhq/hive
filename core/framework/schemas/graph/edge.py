"""
Edge Schema - Specification for edges and graph structure.

Edges define source, target, and traversal conditions.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EdgeCondition(StrEnum):
    """When an edge should be traversed."""

    ALWAYS = "always"
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"
    CONDITIONAL = "conditional"
    LLM_DECIDE = "llm_decide"


class EdgeSpec(BaseModel):
    """Specification for an edge between nodes."""

    id: str
    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    condition: EdgeCondition = EdgeCondition.ALWAYS
    condition_expr: str | None = Field(
        default=None,
        description="Expression for CONDITIONAL edges, e.g., 'output.confidence > 0.8'",
    )
    input_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Map source outputs to target inputs: {target_key: source_key}",
    )
    priority: int = Field(default=0, description="Higher priority edges are evaluated first")
    description: str = ""
    model_config = {"extra": "allow"}


class AsyncEntryPointSpec(BaseModel):
    """Specification for an asynchronous entry point."""

    id: str = Field(description="Unique identifier for this entry point")
    name: str = Field(description="Human-readable name")
    entry_node: str = Field(description="Node ID to start execution from")
    trigger_type: str = Field(
        default="manual",
        description="How this entry point is triggered: webhook, api, timer, event, manual",
    )
    trigger_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Trigger-specific configuration (e.g., webhook URL, timer interval)",
    )
    isolation_level: str = Field(
        default="shared", description="State isolation: isolated, shared, or synchronized"
    )
    priority: int = Field(default=0, description="Execution priority (higher = more priority)")
    max_concurrent: int = Field(
        default=10, description="Maximum concurrent executions for this entry point"
    )
    model_config = {"extra": "allow"}


class GraphSpec(BaseModel):
    """Complete specification of an agent graph."""

    id: str
    goal_id: str
    version: str = "1.0.0"
    entry_node: str = Field(description="ID of the first node to execute")
    entry_points: dict[str, str] = Field(
        default_factory=dict,
        description="Named entry points for resuming execution. Format: {name: node_id}",
    )
    async_entry_points: list[AsyncEntryPointSpec] = Field(
        default_factory=list,
        description=(
            "Asynchronous entry points for concurrent execution streams (used with AgentRuntime)"
        ),
    )
    terminal_nodes: list[str] = Field(
        default_factory=list, description="IDs of nodes that end execution"
    )
    pause_nodes: list[str] = Field(
        default_factory=list, description="IDs of nodes that pause execution for HITL input"
    )
    nodes: list[Any] = Field(default_factory=list, description="All node specifications")
    edges: list[EdgeSpec] = Field(default_factory=list, description="All edge specifications")
    memory_keys: list[str] = Field(
        default_factory=list, description="Keys available in shared memory"
    )
    default_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 1024
    cleanup_llm_model: str | None = None
    max_steps: int = Field(default=100, description="Maximum node executions before timeout")
    max_retries_per_node: int = 3
    description: str = ""
    created_by: str = ""
    model_config = {"extra": "allow"}
