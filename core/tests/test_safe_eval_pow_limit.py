"""make sure safe_eval caps exponentiation so nobody can DoS us
with something like 2**2**2**2**2**2
"""

import pytest

from framework.graph.safe_eval import _MAX_EXPONENT, _MAX_POW_BASE, safe_eval


class TestSafePowLimits:
    """check that pow is bounded in the expression sandbox"""

    def test_small_exponent_allowed(self):
        assert safe_eval("2 ** 10") == 1024

    def test_negative_base_allowed(self):
        assert safe_eval("(-2) ** 3") == -8

    def test_float_exponent_allowed(self):
        result = safe_eval("4.0 ** 0.5")
        assert result == pytest.approx(2.0)

    def test_zero_exponent(self):
        assert safe_eval("999 ** 0") == 1

    def test_exponent_at_limit(self):
        # 1 ** anything is just 1 so this is fine perf-wise
        assert safe_eval(f"1 ** {_MAX_EXPONENT}") == 1

    def test_exponent_exceeds_limit_raises(self):
        with pytest.raises(ValueError, match="exceeds maximum allowed value"):
            safe_eval(f"2 ** {_MAX_EXPONENT + 1}")

    def test_large_negative_exponent_rejected(self):
        with pytest.raises(ValueError, match="exceeds maximum allowed value"):
            safe_eval(f"2 ** (-{_MAX_EXPONENT + 1})")

    def test_large_base_with_large_exponent_rejected(self):
        with pytest.raises(ValueError, match="unreasonably large result"):
            safe_eval(f"{_MAX_POW_BASE + 1} ** 3")

    def test_large_base_with_small_exponent_allowed(self):
        # base > limit but exp <= 2 is still fine
        result = safe_eval(f"{_MAX_POW_BASE + 1} ** 2")
        assert result == (_MAX_POW_BASE + 1) ** 2

    def test_nested_pow_tower_rejected(self):
        # 2**2**2**2**2**2 right-associates into something ridiculous
        with pytest.raises(ValueError):
            safe_eval("2 ** 2 ** 2 ** 2 ** 2 ** 2")

    def test_pow_in_expression_context(self):
        assert safe_eval("1 + 2 ** 3") == 9

    def test_variable_exponent_within_bounds(self):
        assert safe_eval("base ** exp", {"base": 2, "exp": 8}) == 256

    def test_variable_exponent_exceeding_bounds(self):
        with pytest.raises(ValueError, match="exceeds maximum allowed value"):
            safe_eval("base ** exp", {"base": 2, "exp": _MAX_EXPONENT + 1})
