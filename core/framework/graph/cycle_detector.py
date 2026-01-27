"""
Cycle detection and validation module.

Identifies "Divergent Input Cycles" - loops that have no logical exit condition
and would spin infinitely (until max_steps).
"""

from typing import Any, List, Set, Dict
from dataclasses import dataclass
from framework.graph.edge import EdgeCondition, EdgeSpec

@dataclass
class Cycle:
    """Represents a detected cycle in the graph."""
    path: List[str]  # List of node IDs in order: A -> B -> C -> A
    edges: List[EdgeSpec]  # The edges forming the cycle
    is_divergent: bool
    reason: str | None = None

class CycleDetector:
    """Detects cycles and validates if they are divergent."""

    def __init__(self, graph_spec: Any):
        """
        Initialize with a GraphSpec.
        
        Args:
            graph_spec: The GraphSpec to analyze. Type Any to avoid circular imports,
                       but expects framework.graph.edge.GraphSpec
        """
        self.graph = graph_spec

    def detect_cycles(self) -> List[Cycle]:
        """
        Find all simple cycles in the graph and analyze them.
        
        Returns:
            List of detected cycles, marked as divergent or convergent.
        """
        # Build adjacency list for DFS
        # We need to know which edges connect nodes
        adj = {node.id: [] for node in self.graph.nodes}
        for edge in self.graph.edges:
            if edge.source in adj:
                adj[edge.source].append(edge)
        
        cycles: List[Cycle] = []
        
        # Standard DFS cycle finding
        # Since we need to analyze expected behavior, simple cycle finding is enough.
        # We'll use a standard recursive DFS with path tracking.
        # To avoid exponential blowup in fully connected graphs, we can limit depth 
        # or use Tarjan's/Johnson's, but for control graphs (usually small/sparse), 
        # simple DFS is fine.
        
        visited: Set[str] = set()
        stack: List[str] = []
        edge_stack: List[EdgeSpec] = []
        
        def dfs(u: str, start_node: str):
            visited.add(u)
            stack.append(u)
            
            # Sort edges by priority (though for cycle finding order doesn't matter much, 
            # consistent order is nice)
            outgoing = sorted(adj.get(u, []), key=lambda e: -e.priority)
            
            for edge in outgoing:
                v = edge.target
                if v == start_node:
                    # Found a cycle back to start!
                    cycle_path = stack[:]  # Copy current path
                    cycle_edges = edge_stack[:] + [edge]
                    self._analyze_cycle(cycle_path, cycle_edges, cycles)
                elif v not in visited and v in stack:
                    # Found a cycle to an intermediate node on stack (sub-cycle)
                    # We handle this when we process that node as start_node
                    pass
                elif v not in visited:
                    edge_stack.append(edge)
                    dfs(v, start_node)
                    edge_stack.pop()
            
            stack.pop()
            visited.remove(u)

        # Run DFS from each node to find cycles containing it
        # Optimization: We only need to find each distinct cycle once.
        # A simple way for small graphs is to just run from every node but maintain specific uniqueness checks.
        
        # Better: Use Johnson's algorithm equivalent logic or just standard "visited in current path"
        # Let's use a simpler approach: "visited" global set across all DFS runs? No.
        # We want to find ALL elementary cycles.
        
        # Implementation of simple Cycle Finding:
        # We just need to detect *bad* cycles. 
        # Let's iterate all nodes, run DFS.
        # To avoid duplicates, we can enforce that we only report cycles where start_node is min(cycle_nodes).
        
        global_visited_complete = set() # Nodes fully processed
        
        sorted_nodes = sorted([n.id for n in self.graph.nodes])
        
        for start_node in sorted_nodes:
            # We recreate visited for each start_node to find cycles starting there
            # blocked set logic (Johnson's) is complex to implement from scratch correctly quickly.
            # Let's use a path-based DFS that backtracks. With small graph size (N<50 usually), this is instant.
            
            self._find_cycles_from_node(start_node, start_node, set(), [], [], cycles)
            
        return cycles

    def _find_cycles_from_node(self, 
                               start_node: str, 
                               current: str, 
                               visited: Set[str], 
                               path: List[str], 
                               path_edges: List[EdgeSpec],
                               cycles: List[Cycle]):
        """Recursive DFS helper."""
        visited.add(current)
        path.append(current)
        
        outgoing = self.graph.get_outgoing_edges(current)
        
        for edge in outgoing:
            target = edge.target
            
            if target == start_node:
                # Found cycle
                cycle_edges = path_edges + [edge]
                # Check for duplicates: Since we iterate start_node in order, 
                # we only accept cycles if start_node is the smallest ID in the cycle.
                # This canonically identifies each cycle once.
                if min(path) == start_node:
                    self._analyze_cycle(path[:], cycle_edges, cycles)
            elif target not in visited:
                # Continue search
                # Optimization: Only search nodes > start_node to ensure canonical ordering?
                # Actually enforcing min(path) == start_node at the end handles it, 
                # but pruning is faster: if target < start_node, we've already processed it as a start_node.
                if target > start_node: 
                    self._find_cycles_from_node(start_node, target, visited, path, path_edges + [edge], cycles)
        
        path.pop()
        visited.remove(current)

    def _analyze_cycle(self, path: List[str], edges: List[EdgeSpec], cycles: List[Cycle]):
        """Determine if a cycle is divergent and add to list."""
        
        is_divergent = True
        reason = "Infinite loop: "
        
        # Logic: A cycle is divergent if it is NOT ESCAPABLE.
        # It is escapable if any node in the cycle has a way out that is favored 
        # or if the cycle edge itself is conditional.
        
        escapable_at = []
        
        for i, node_id in enumerate(path):
            cycle_edge = edges[i] # Edge from node_id to next node
            
            # 1. Is the cycle edge conditional?
            if cycle_edge.condition in (EdgeCondition.CONDITIONAL, EdgeCondition.LLM_DECIDE):
                is_divergent = False
                escapable_at.append(f"{node_id} (conditional edge)")
                continue

            # 2. Are there any higher-priority operational edges that exit the cycle?
            outgoing = self.graph.get_outgoing_edges(node_id)
            cycle_edge_priority = cycle_edge.priority
            
            for out_edge in outgoing:
                if out_edge.id == cycle_edge.id:
                    continue
                
                # Check if this edge exits the set of cycle nodes
                # (Actually, even if it stays in the cycle, if it's a different edge that is conditional...)
                # Let's simplify: Any edge with HIGHER priority that is NOT the cycle edge?
                if out_edge.priority > cycle_edge_priority:
                    # There is a preferred path. 
                    # If this preferred path is unconditional, we definitely exit (or go to another cycle).
                    # If it's conditional, we MIGHT exit.
                    # Since we can't prove the condition is False forever, we assume it's an Escape Hatch.
                    is_divergent = False
                    escapable_at.append(f"{node_id} (higher priority exit '{out_edge.id}')")
                    break

        if is_divergent:
            # If we are here, it means we found NO node where we could reliably prove escape possibility.
            # All cycle edges are Unconditional (Always/OnSuccess/OnFailure).
            # And no higher priority edges exist to hijack control flow.
            
            # Double check ON_SUCCESS / ON_FAILURE nuance
            # If a loop is A -> A (OnSuccess) and A -> Exit (OnFailure), is it divergent?
            # It spins as long as it succeeds. This is technically an infinite loop for the success case.
            # We classify this as Divergent because it assumes infinite success.
            # The prompt example "Node A calls Node B... Node B calls Node A" implies this.
            
            path_str = " -> ".join(path) + " -> " + path[0]
            reason = f"Unconditional cycle detected: {path_str}. Nodes have no conditional edges or higher-priority exits."
            
            cycles.append(Cycle(
                path=path,
                edges=edges,
                is_divergent=True,
                reason=reason
            ))
        else:
            # We don't track convergent cycles unless valid debugging needed
            pass
