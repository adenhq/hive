"""the old convergence finder only looked at immediate successors
which broke on any non-trivial parallel fork.  now it does BFS.
"""

from types import SimpleNamespace

from framework.graph.edge import EdgeCondition, EdgeSpec, GraphSpec
from framework.graph.executor import GraphExecutor


def _node(nid: str) -> SimpleNamespace:
    return SimpleNamespace(id=nid)


def _edge(src: str, tgt: str) -> EdgeSpec:
    return EdgeSpec(
        id=f"{src}->{tgt}",
        source=src,
        target=tgt,
        condition=EdgeCondition.ALWAYS,
    )


def _ex() -> GraphExecutor:
    return object.__new__(GraphExecutor)


class TestFindConvergenceNodeBFS:
    def test_immediate_convergence(self):
        # A->C, B->C => C
        g = GraphSpec(
            id="g",
            goal_id="g",
            entry_node="start",
            nodes=[_node("A"), _node("B"), _node("C")],
            edges=[_edge("A", "C"), _edge("B", "C")],
        )
        assert _ex()._find_convergence_node(g, ["A", "B"]) == "C"

    def test_multi_hop_convergence(self):
        # A->X->C, B->C   should still find C
        g = GraphSpec(
            id="g",
            goal_id="g",
            entry_node="start",
            nodes=[_node(n) for n in ["A", "B", "X", "C"]],
            edges=[_edge("A", "X"), _edge("X", "C"), _edge("B", "C")],
        )
        assert _ex()._find_convergence_node(g, ["A", "B"]) == "C"

    def test_deep_convergence(self):
        g = GraphSpec(
            id="g",
            goal_id="g",
            entry_node="start",
            nodes=[_node(n) for n in ["A", "B", "X", "Y", "Z", "P"]],
            edges=[
                _edge("A", "X"),
                _edge("X", "Y"),
                _edge("Y", "Z"),
                _edge("B", "P"),
                _edge("P", "Z"),
            ],
        )
        assert _ex()._find_convergence_node(g, ["A", "B"]) == "Z"

    def test_no_convergence(self):
        g = GraphSpec(
            id="g",
            goal_id="g",
            entry_node="start",
            nodes=[_node("A"), _node("B"), _node("X"), _node("Y")],
            edges=[_edge("A", "X"), _edge("B", "Y")],
        )
        result = _ex()._find_convergence_node(g, ["A", "B"])
        assert result in ("X", "Y") or result is None

    def test_empty_targets(self):
        g = GraphSpec(
            id="g",
            goal_id="g",
            entry_node="start",
            nodes=[],
            edges=[],
        )
        assert _ex()._find_convergence_node(g, []) is None

    def test_single_branch(self):
        g = GraphSpec(
            id="g",
            goal_id="g",
            entry_node="start",
            nodes=[_node("A"), _node("B")],
            edges=[_edge("A", "B")],
        )
        result = _ex()._find_convergence_node(g, ["A"])
        assert result in ("B", None)

    def test_diamond(self):
        # classic diamond pattern
        g = GraphSpec(
            id="g",
            goal_id="g",
            entry_node="S",
            nodes=[_node(n) for n in ["S", "A", "B", "C"]],
            edges=[_edge("S", "A"), _edge("S", "B"), _edge("A", "C"), _edge("B", "C")],
        )
        assert _ex()._find_convergence_node(g, ["A", "B"]) == "C"

    def test_nearest_convergence_preferred(self):
        # A->X->M->Z, B->M->Z  -- M is closer so pick that
        g = GraphSpec(
            id="g",
            goal_id="g",
            entry_node="start",
            nodes=[_node(n) for n in ["A", "B", "X", "M", "Z"]],
            edges=[
                _edge("A", "X"),
                _edge("X", "M"),
                _edge("M", "Z"),
                _edge("B", "M"),
            ],
        )
        assert _ex()._find_convergence_node(g, ["A", "B"]) == "M"
