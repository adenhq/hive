"""
Python Interpreter Tool - Execute Python code in a secure sandbox.
"""
import sys
import os
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP

# Add parent directory to sys.path to allow importing framework
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")))

try:
    from core.framework.graph.code_sandbox import CodeSandbox
except ImportError:
    # Fallback if path is different
    try:
        from framework.graph.code_sandbox import CodeSandbox
    except ImportError:
        CodeSandbox = None

def register_tools(mcp: FastMCP, credentials=None) -> None:
    """Register Python interpreter tools."""

    @mcp.tool()
    def execute_python(code: str, inputs: Optional[Dict[str, Any]] = None, timeout: int = 10) -> Dict[str, Any]:
        """
        Execute Python code in a secure sandbox.
        
        Args:
            code: The Python code to execute
            inputs: Optional dictionary of input variables
            timeout: Execution timeout in seconds (default 10)
        """
        if CodeSandbox is None:
            return {"error": "CodeSandbox not available. Ensure framework is in PYTHONPATH."}
            
        try:
            sandbox = CodeSandbox(timeout_seconds=timeout)
            result = sandbox.execute(code, inputs or {})
            
            return {
                "success": result.success,
                "result": result.result,
                "stdout": result.stdout,
                "variables": result.variables,
                "execution_time_ms": result.execution_time_ms,
                "error": result.error
            }
        except Exception as e:
            return {"error": str(e)}
