
import pytest
from framework.graph.edge import GraphSpec, EdgeSpec, EdgeCondition
from framework.graph.node import NodeSpec

def test_divergent_cycle_detection():
    """
    Test that a divergent cycle (no exit) is detected.
    
    A divergent cycle is a cycle where all edges in the cycle are unconditional
    (ALWAYS, ON_SUCCESS, ON_FAILURE) and there are no alternative exit paths
    from the nodes in the cycle.
    """
    # Define a graph with A -> B -> A (unconditional loop)
    nodes = [
        NodeSpec(id="node_a", name="Node A", description="A", node_type="llm_generate"),
        NodeSpec(id="node_b", name="Node B", description="B", node_type="llm_generate"),
    ]
    
    edges = [
        # A -> B (Always)
        EdgeSpec(
            id="a_to_b",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ALWAYS
        ),
        # B -> A (Always) - This creates the infinite loop
        EdgeSpec(
            id="b_to_a",
            source="node_b",
            target="node_a",
            condition=EdgeCondition.ALWAYS
        )
    ]
    
    graph = GraphSpec(
        id="divergent_graph",
        goal_id="g1",
        entry_node="node_a",
        terminal_nodes=[], # No terminal nodes reachable
        nodes=nodes,
        edges=edges
    )
    
    # CURRENT BEHAVIOR: Validation returns an error about the cycle
    errors = graph.validate()
    
    print(f"Validation errors (Divergent): {errors}")
    assert len(errors) > 0, "Divergent cycle should be detected"
    assert "Strictly divergent cycle detected" in errors[0]

def test_convergent_cycle_valid():
    """
    Test that a convergent cycle (has exit) is considered valid.
    """
    # Define a graph with A <-> B loop, but B has conditional exit to C
    nodes = [
        NodeSpec(id="node_a", name="Node A", description="A", node_type="llm_generate"),
        NodeSpec(id="node_b", name="Node B", description="B", node_type="llm_generate"),
        NodeSpec(id="node_c", name="Node C", description="C", node_type="llm_generate"), # Terminal
    ]
    
    edges = [
        # A -> B (Always)
        EdgeSpec(
            id="a_to_b",
            source="node_a",
            target="node_b",
            condition=EdgeCondition.ALWAYS
        ),
        # B -> A (Conditional: Only if count < 5)
        EdgeSpec(
            id="b_to_a",
            source="node_b",
            target="node_a",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="memory.count < 5",
            priority=1
        ),
        # B -> C (Conditional: If count >= 5)
        EdgeSpec(
            id="b_to_c",
            source="node_b",
            target="node_c",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="memory.count >= 5",
            priority=2 # Higher priority exit
        )
    ]
    
    graph = GraphSpec(
        id="convergent_graph",
        goal_id="g2",
        entry_node="node_a",
        terminal_nodes=["node_c"],
        nodes=nodes,
        edges=edges
    )
    
    errors = graph.validate()
    print(f"Validation errors (Convergent): {errors}")
    assert len(errors) == 0, "Convergent cycle should be valid"

if __name__ == "__main__":
    test_divergent_cycle_detection()
    test_convergent_cycle_valid()
    print("Reproduction script finished.")
