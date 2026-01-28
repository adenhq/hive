from __future__ import annotations

import inspect
from typing import Any

import pytest

from framework.runner.tool_registry import ToolRegistry


class SampleTools:
    def no_params(self) -> str:
        return "ok"

    def with_required_and_optional(
        self,
        a: int,
        b: str,
        c: float | None = None,
    ) -> dict[str, Any]:
        return {"a": a, "b": b, "c": c}

    def with_kwargs(
        self,
        a: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {"a": a, "extra": kwargs}


class TestValidateAndBindArguments:
    def setup_method(self) -> None:
        self.registry = ToolRegistry()
        self.tools = SampleTools()

    def _call_validate(
        self,
        func_name: str,
        inputs: dict[str, Any],
    ):
        func = getattr(self.tools, func_name)
        sig = inspect.signature(func)
        return self.registry._validate_and_bind_arguments(func_name, func, sig, inputs)

    def test_success_basic_binding(self) -> None:
        bound = self._call_validate(
            "with_required_and_optional",
            {"a": 1, "b": "x"},
        )

        assert bound.arguments["a"] == 1
        assert bound.arguments["b"] == "x"
        assert "c" in bound.arguments

    def test_missing_required_parameters_raise(self) -> None:
        with pytest.raises(
            ValueError,
            match="missing.*required.*argument",
        ):
            self._call_validate(
                "with_required_and_optional",
                {},
            )

    def test_unexpected_parameters_without_kwargs_raise(self) -> None:
        with pytest.raises(
            ValueError,
            match="unexpected.*keyword.*argument.*extra",
        ):
            self._call_validate(
                "with_required_and_optional",
                {"a": 1, "b": "x", "extra": 42},
            )

    def test_allows_extra_parameters_with_kwargs(self) -> None:
        bound = self._call_validate(
            "with_kwargs",
            {"a": 1, "extra": 2},
        )

        assert bound.arguments["a"] == 1
        assert bound.arguments["kwargs"]["extra"] == 2

    def test_filters_out_self_and_cls_from_inputs(self) -> None:
        bound = self._call_validate(
            "with_required_and_optional",
            {
                "self": "should_be_ignored",
                "cls": "also_ignored",
                "a": 10,
                "b": "ok",
            },
        )

        assert "self" not in bound.arguments
        assert "cls" not in bound.arguments
        assert bound.arguments["a"] == 10
        assert bound.arguments["b"] == "ok"

    @pytest.mark.parametrize(
        "param_name,value,expected_message",
        [
            ("a", "not-int", "parameter 'a' must be int, got str"),
            ("b", 123, "parameter 'b' must be str, got int"),
            ("c", "not-float", "parameter 'c' must be float, got str"),
        ],
    )
    def test_basic_type_validation_errors(
        self,
        param_name: str,
        value: Any,
        expected_message: str,
    ) -> None:
        inputs: dict[str, Any] = {"a": 1, "b": "ok"}
        inputs[param_name] = value

        with pytest.raises(
            ValueError,
            match=expected_message,
        ):
            self._call_validate(
                "with_required_and_optional",
                inputs,
            )

    def test_optional_none_skips_type_check(self) -> None:
        bound = self._call_validate(
            "with_required_and_optional",
            {"a": 1, "b": "ok", "c": None},
        )

        assert bound.arguments["c"] is None

    def test_positional_only_parameter_rejects_keyword(self) -> None:
        """Positional-only parameters should reject keyword arguments."""

        def positional_only_func(a: int, /, b: str) -> dict[str, Any]:
            return {"a": a, "b": b}

        sig = inspect.signature(positional_only_func)
        with pytest.raises(
            ValueError,
            match="positional only",
        ):
            self.registry._validate_and_bind_arguments(
                "positional_only_func",
                positional_only_func,
                sig,
                {"a": 1, "b": "ok"},
            )

    def test_keyword_only_parameter_requires_keyword(self) -> None:
        """Keyword-only parameters must be passed as keywords."""

        def keyword_only_func(a: int, *, b: str) -> dict[str, Any]:
            return {"a": a, "b": b}

        sig = inspect.signature(keyword_only_func)
        # This should work - both passed as keywords
        bound = self.registry._validate_and_bind_arguments(
            "keyword_only_func",
            keyword_only_func,
            sig,
            {"a": 1, "b": "ok"},
        )
        assert bound.arguments["a"] == 1
        assert bound.arguments["b"] == "ok"

    def test_numeric_widening_allows_int_for_float(self) -> None:
        """Pragmatic: int should be accepted for float parameters."""

        def float_func(x: float) -> float:
            return x

        sig = inspect.signature(float_func)
        # int should be accepted for float (numeric widening)
        bound = self.registry._validate_and_bind_arguments(
            "float_func",
            float_func,
            sig,
            {"x": 42},
        )
        assert bound.arguments["x"] == 42
