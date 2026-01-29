"""Node definitions for Basic Worker Agent template."""

from framework.graph import NodeSpec

noop_node = NodeSpec(
    id="noop",
    name="Noop Node",
    description="Does nothing. Used as a placeholder.",
    node_type="function",
    input_keys=[],
    output_keys=[],
)

__all__ = ["noop_node"]
