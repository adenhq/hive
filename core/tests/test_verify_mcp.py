import unittest
from unittest.mock import patch, MagicMock
import subprocess
import sys
import os

# Add parent directory to path to import verify_mcp
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verify_mcp import run_python_snippet

class TestRunPythonSnippet(unittest.TestCase):
    """
    Unit tests for the `run_python_snippet` utility function.
    
    These tests verify:
    - Successful execution of Python commands
    - Correct handling of timeouts
    - Propagation of process errors
    """
    
    @patch('subprocess.run')
    def test_run_python_snippet_success(self, mock_run):
        """
        Test that `run_python_snippet` correctly executes a command and returns stripped output.
        
        Verifies that:
        1. The correct arguments are passed to subprocess.run
        2. The return value is the stripped stdout string
        """
        # Setup mock behavior
        mock_result = MagicMock()
        mock_result.stdout = " success output \n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Call the function
        code = "print('hello')"
        result = run_python_snippet(code)

        # Assertions
        mock_run.assert_called_once_with(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
            timeout=None
        )
        self.assertEqual(result, "success output")

    @patch('subprocess.run')
    def test_run_python_snippet_with_timeout(self, mock_run):
        """
        Test that the `timeout` parameter is correctly passed to subprocess.run.
        
        This ensures that long-running operations can be terminated if they exceed
        the specified duration.
        """
        # Setup mock behavior
        mock_result = MagicMock()
        mock_result.stdout = "done"
        mock_run.return_value = mock_result

        # Call with timeout
        run_python_snippet("print('fast')", timeout=5)

        # Verify timeout was passed
        kwargs = mock_run.call_args.kwargs
        self.assertEqual(kwargs['timeout'], 5)

    @patch('subprocess.run')
    def test_run_python_snippet_failure(self, mock_run):
        """
        Test that `subprocess.CalledProcessError` is raised when the command fails.
        
        The function should not swallow exceptions from failed subprocess executions;
        it should let them bubble up to be handled by the caller.
        """
        # Setup mock to raise CalledProcessError
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=[sys.executable, "-c", "error"],
            output="output",
            stderr="error message"
        )

        # Verify exception is propogated
        with self.assertRaises(subprocess.CalledProcessError):
            run_python_snippet("raise Exception")

if __name__ == '__main__':
    unittest.main()
