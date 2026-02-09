"""
Node Schema - Specification for a node in the graph.

This is the declarative definition of a node - what it does,
what it needs, and what it produces.
"""

from pydantic import BaseModel, Field


class NodeSpec(BaseModel):
    """Specification for a node in the graph."""

    id: str
    name: str
    description: str
    node_type: str = Field(
        default="llm_tool_use",
        description=(
            "Type: 'event_loop', 'function', 'router', 'human_input'. "
            "Deprecated: 'llm_tool_use', 'llm_generate' (use 'event_loop' instead)."
        ),
    )
    input_keys: list[str] = Field(
        default_factory=list, description="Keys this node reads from shared memory or input"
    )
    output_keys: list[str] = Field(
        default_factory=list, description="Keys this node writes to shared memory or output"
    )
    nullable_output_keys: list[str] = Field(
        default_factory=list,
        description="Output keys that can be None without triggering validation errors",
    )
    input_schema: dict[str, dict] = Field(
        default_factory=dict,
        description=(
            "Optional schema for input validation. "
            "Format: {key: {type: 'string', required: True, description: '...'}}"
        ),
    )
    output_schema: dict[str, dict] = Field(
        default_factory=dict,
        description=(
            "Optional schema for output validation. "
            "Format: {key: {type: 'dict', required: True, description: '...'}}"
        ),
    )
    system_prompt: str | None = Field(default=None, description="System prompt for LLM nodes")
    tools: list[str] = Field(default_factory=list, description="Tool names this node can use")
    model: str | None = Field(
        default=None, description="Specific model to use (defaults to graph default)"
    )
    function: str | None = Field(
        default=None, description="Function name or path for function nodes"
    )
    routes: dict[str, str] = Field(
        default_factory=dict, description="Condition -> target_node_id mapping for routers"
    )
    max_retries: int = Field(default=3)
    retry_on: list[str] = Field(default_factory=list, description="Error types to retry on")
    max_node_visits: int = Field(
        default=1,
        description=(
            "Max times this node executes in one graph run. "
            "Set >1 for feedback loops. 0 = unlimited (max_steps guards)."
        ),
    )
    output_model: type[BaseModel] | None = Field(
        default=None,
        description=(
            "Optional Pydantic model class for validating and parsing LLM output. "
            "When set, the LLM response will be validated against this model."
        ),
    )
    max_validation_retries: int = Field(
        default=2,
        description="Maximum retries when Pydantic validation fails (with feedback to LLM)",
    )
    client_facing: bool = Field(
        default=False,
        description="If True, this node streams output to the end user and can request input.",
    )
    model_config = {"extra": "allow", "arbitrary_types_allowed": True}
