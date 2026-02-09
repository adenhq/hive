"""Tests for safe_eval — the sandboxed expression evaluator used by EdgeSpec conditions.

Covers:
  - Basic arithmetic, comparisons, and boolean logic
  - Short-circuit semantics for ``and`` / ``or`` (fixes #4010)
  - Guard-pattern expressions that rely on short-circuiting
  - Return-value semantics (actual values, not coerced bools)
"""

import pytest

from framework.graph.safe_eval import safe_eval

# ---------------------------------------------------------------------------
# Basic boolean operations
# ---------------------------------------------------------------------------


class TestBoolOpBasic:
    """Verify that and/or produce correct truth values."""

    def test_and_true(self) -> None:
        assert safe_eval("a and b", {"a": 1, "b": 2}) == 2

    def test_and_false(self) -> None:
        assert safe_eval("a and b", {"a": 0, "b": 2}) == 0

    def test_or_true(self) -> None:
        assert safe_eval("a or b", {"a": 1, "b": 2}) == 1

    def test_or_false(self) -> None:
        assert safe_eval("a or b", {"a": 0, "b": 0}) == 0

    def test_chained_and(self) -> None:
        assert safe_eval("a and b and c", {"a": 1, "b": 2, "c": 3}) == 3

    def test_chained_or(self) -> None:
        assert safe_eval("a or b or c", {"a": 0, "b": 0, "c": 3}) == 3

    def test_mixed_not_or(self) -> None:
        assert safe_eval("not a or b", {"a": True, "b": 42}) == 42


# ---------------------------------------------------------------------------
# Short-circuit semantics  (the core fix for #4010)
# ---------------------------------------------------------------------------


class TestBoolOpShortCircuit:
    """``and``/``or`` must short-circuit to avoid crashes on guard patterns."""

    def test_and_short_circuits_on_none(self) -> None:
        """``None and x['key']`` must return None without evaluating x['key']."""
        # If short-circuiting is broken, this would raise TypeError
        # because None is not subscriptable.
        result = safe_eval("x and x['key']", {"x": None})
        assert result is None

    def test_and_short_circuits_skips_undefined(self) -> None:
        """Falsy first operand must skip evaluation of undefined second operand."""
        # If short-circuiting is broken, this raises NameError.
        result = safe_eval("a and undefined_var", {"a": False})
        assert result is False

    def test_and_evaluates_when_truthy(self) -> None:
        """When the guard passes, the second operand should be evaluated."""
        result = safe_eval("x and x['key']", {"x": {"key": "value"}})
        assert result == "value"

    def test_or_short_circuits_on_truthy(self) -> None:
        """``'hello' or expensive()`` must return 'hello' without evaluating."""
        # If "undefined_var" were evaluated, it would raise NameError.
        result = safe_eval("x or undefined_var", {"x": "hello"})
        assert result == "hello"

    def test_or_falls_through_to_default(self) -> None:
        """Falsy first operand should cause evaluation of the second."""
        result = safe_eval("x or 'default'", {"x": None})
        assert result == "default"

    def test_or_falls_through_empty_string(self) -> None:
        result = safe_eval("x or 'fallback'", {"x": ""})
        assert result == "fallback"

    def test_and_guard_with_get(self) -> None:
        """Common pattern: ``output.get('x') is not None and output['x']``."""
        ctx = {"output": {"x": 42}}
        result = safe_eval("output.get('x') is not None and output['x']", ctx)
        assert result == 42

    def test_and_guard_with_get_missing(self) -> None:
        """When .get() returns None, short-circuit prevents KeyError."""
        ctx = {"output": {}}
        # ``None is not None`` → False, so ``and`` short-circuits to False.
        result = safe_eval("output.get('x') is not None and output.get('x')", ctx)
        assert result is False

    def test_chained_or_fallback(self) -> None:
        """``a or b or 'none'`` — common fallback chain."""
        ctx = {"output": {}}
        result = safe_eval(
            "output.get('primary') or output.get('secondary') or 'none'",
            ctx,
        )
        assert result == "none"

    def test_chained_or_first_truthy_wins(self) -> None:
        ctx = {"output": {"secondary": "found"}}
        result = safe_eval(
            "output.get('primary') or output.get('secondary') or 'none'",
            ctx,
        )
        assert result == "found"


# ---------------------------------------------------------------------------
# Return-value semantics (Python-accurate, not bool-coerced)
# ---------------------------------------------------------------------------


class TestBoolOpReturnValues:
    """``and``/``or`` return the deciding value, not True/False."""

    def test_and_returns_last_truthy(self) -> None:
        assert safe_eval("a and b", {"a": "yes", "b": "also"}) == "also"

    def test_and_returns_first_falsy(self) -> None:
        assert safe_eval("a and b", {"a": "", "b": "also"}) == ""

    def test_or_returns_first_truthy(self) -> None:
        assert safe_eval("a or b", {"a": "yes", "b": "also"}) == "yes"

    def test_or_returns_last_falsy(self) -> None:
        assert safe_eval("a or b", {"a": 0, "b": ""}) == ""

    def test_and_returns_zero_not_false(self) -> None:
        result = safe_eval("a and b", {"a": 0, "b": 1})
        assert result == 0
        assert result is not False

    def test_or_returns_none_not_false(self) -> None:
        result = safe_eval("a or b", {"a": None, "b": None})
        assert result is None


# ---------------------------------------------------------------------------
# Edge-condition expressions (real-world usage in EdgeSpec.condition_expr)
# ---------------------------------------------------------------------------


class TestEdgeConditionExpressions:
    """Expressions commonly used in graph edge conditions."""

    def test_simple_key_check(self) -> None:
        ctx = {"output": {"status": "ok"}}
        assert safe_eval("output.get('status') == 'ok'", ctx) is True

    def test_nested_guard_pattern(self) -> None:
        ctx = {"result": {"data": {"score": 0.95}}}
        assert (
            safe_eval(
                "result.get('data') is not None and result['data']['score'] > 0.9",
                ctx,
            )
            is True
        )

    def test_nested_guard_pattern_missing(self) -> None:
        ctx = {"result": {}}
        # ``None is not None`` → False, so ``and`` short-circuits to False
        # without attempting result['data']['score'].
        result = safe_eval(
            "result.get('data') is not None and result.get('data')",
            ctx,
        )
        assert result is False

    def test_len_check(self) -> None:
        ctx = {"items": [1, 2, 3]}
        assert safe_eval("len(items) > 0", ctx) is True

    def test_type_coercion_in_or(self) -> None:
        ctx = {"count": 0}
        assert safe_eval("count or 'empty'", ctx) == "empty"


# ---------------------------------------------------------------------------
# Security boundary — disallowed operations still raise
# ---------------------------------------------------------------------------


class TestSafeEvalSecurityBoundary:
    """Verify that disallowed operations are rejected."""

    def test_lambda_disallowed(self) -> None:
        with pytest.raises(ValueError, match="is not allowed"):
            safe_eval("(lambda: 1)()", {})

    def test_private_attribute_disallowed(self) -> None:
        with pytest.raises(ValueError, match="private attribute"):
            safe_eval("x.__class__", {"x": 42})
