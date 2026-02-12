"""Tests for framework.graph.safe_eval (AST-based safe expression evaluation)."""

from __future__ import annotations

import pytest

from framework.graph.safe_eval import safe_eval


class TestSafeEval:
    """Tests for safe_eval used in edge condition expressions."""

    def test_isinstance_in_condition(self) -> None:
        """Edge condition using isinstance should evaluate correctly (Fixes #1128)."""
        context = {"output": {"success": True, "data": "ok"}}
        result = safe_eval(
            "isinstance(output, dict) and output.get('success')",
            context,
        )
        assert result is True

    def test_isinstance_false_when_not_dict(self) -> None:
        """isinstance(output, dict) is False when output is not a dict."""
        context = {"output": "not a dict"}
        result = safe_eval("isinstance(output, dict)", context)
        assert result is False

    def test_other_safe_builtins_available(self) -> None:
        """zip, range, enumerate etc. are available and safe."""
        assert safe_eval("list(zip([1,2], [3,4]))", {}) == [(1, 3), (2, 4)]
        assert safe_eval("list(range(3))", {}) == [0, 1, 2]
        assert safe_eval("sorted([3,1,2])", {}) == [1, 2, 3]
