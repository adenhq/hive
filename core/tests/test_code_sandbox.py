"""
Tests for CodeSandbox thread safety and execution isolation.

These tests verify that the sandbox correctly captures stdout
without cross-contamination when run concurrently.
"""

import concurrent.futures

import pytest

from framework.graph.code_sandbox import (
    CodeSandbox,
    safe_exec,
    safe_eval,
)


class TestCodeSandboxBasics:
    """Basic execution tests for CodeSandbox."""

    def test_simple_execution(self):
        """Test simple code execution."""
        result = safe_exec("x = 1 + 2\nresult = x * 3")
        assert result.success is True
        assert result.variables.get("x") == 3
        assert result.result == 9

    def test_stdout_capture(self):
        """Test that stdout is captured correctly."""
        result = safe_exec("print('hello world')")
        assert result.success is True
        assert "hello world" in result.stdout

    def test_input_injection(self):
        """Test passing inputs to sandbox."""
        result = safe_exec(
            "result = x + y",
            inputs={"x": 10, "y": 20},
        )
        assert result.success is True
        assert result.result == 30


class TestCodeSandboxThreadSafety:
    """Tests for concurrent execution thread safety (Issue #2283)."""

    def test_concurrent_stdout_isolation(self):
        """
        Test that concurrent sandbox executions don't interfere with each other.

        This is the core test for Issue #2283: each execution should capture
        only its own stdout without cross-contamination.
        """
        sandbox = CodeSandbox(timeout_seconds=10)

        def run_sandbox(execution_id: int) -> tuple[int, str]:
            """Run a sandbox that prints its unique ID."""
            code = f"print('execution-{execution_id}')"
            result = sandbox.execute(code, inputs={})
            return (execution_id, result.stdout.strip())

        # Run 20 concurrent executions
        num_executions = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_sandbox, i) for i in range(num_executions)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verify each execution captured only its own output
        for execution_id, stdout in results:
            expected_output = f"execution-{execution_id}"
            assert stdout == expected_output, (
                f"Execution {execution_id} captured wrong output: "
                f"expected '{expected_output}', got '{stdout}'"
            )

    def test_concurrent_variable_isolation(self):
        """Test that concurrent executions don't share variable state."""
        sandbox = CodeSandbox(timeout_seconds=10)

        def run_sandbox(value: int) -> int:
            """Run a sandbox that computes based on input value."""
            result = sandbox.execute(
                "result = value * 2",
                inputs={"value": value},
            )
            return result.result

        # Run concurrent executions with different inputs
        num_executions = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(run_sandbox, i): i for i in range(num_executions)}

            for future in concurrent.futures.as_completed(futures):
                input_value = futures[future]
                result = future.result()
                expected = input_value * 2
                assert result == expected, (
                    f"Input {input_value} gave result {result}, expected {expected}"
                )

    def test_concurrent_mixed_success_failure(self):
        """Test concurrent executions with mixed success and failure."""
        sandbox = CodeSandbox(timeout_seconds=10)

        def run_sandbox(should_fail: bool) -> tuple[bool, bool]:
            """Run a sandbox that either succeeds or fails."""
            if should_fail:
                code = "x = undefined_variable"  # Will cause NameError
            else:
                code = "result = 'success'"

            result = sandbox.execute(code, inputs={})
            return (should_fail, result.success)

        # Run mix of successful and failing executions
        patterns = [True, False, True, False, True, False] * 3  # 18 total

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_sandbox, should_fail) for should_fail in patterns]

            for future in concurrent.futures.as_completed(futures):
                should_fail, success = future.result()
                if should_fail:
                    assert not success, "Expected failure but got success"
                else:
                    assert success, "Expected success but got failure"


class TestCodeSandboxStdoutEdgeCases:
    """Edge case tests for stdout capture."""

    def test_multiline_stdout(self):
        """Test capturing multiline stdout."""
        result = safe_exec("""
print('line 1')
print('line 2')
print('line 3')
""")
        assert result.success is True
        assert "line 1" in result.stdout
        assert "line 2" in result.stdout
        assert "line 3" in result.stdout

    def test_empty_stdout(self):
        """Test execution with no stdout."""
        result = safe_exec("x = 42")
        assert result.success is True
        assert result.stdout == ""

    def test_stdout_on_error(self):
        """Test that stdout is captured even when code errors."""
        result = safe_exec("""
print('before error')
raise ValueError('test error')
""")
        assert result.success is False
        assert "before error" in result.stdout
        assert "ValueError" in result.error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
