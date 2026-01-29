"""
Math Tool - A safe arithmetic evaluator for agents.

Uses Python's AST to strictly limit operations to basic arithmetic,
preventing any arbitrary code execution.
"""

import ast
import operator
from typing import Any, Union

from fastmcp import FastMCP

# Safe operators whitelist
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: Union[ast.AST, None]) -> Union[int, float]:
    """
    Recursively evaluate an AST node if it represents a safe arithmetic operation.
    
    Args:
        node: The AST node to evaluate
        
    Returns:
        The numerical result of the evaluation
        
    Raises:
        ValueError: If the node or its children contain unsafe/unsupported operations
    """
    if node is None:
        return 0

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in OPERATORS:
            left = _safe_eval(node.left)
            right = _safe_eval(node.right)
            return OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported operator: {op_type.__name__}")

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in OPERATORS:
            operand = _safe_eval(node.operand)
            return OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    raise ValueError(f"Unsupported syntax: {type(node).__name__}")


def register_tools(mcp: FastMCP) -> None:
    """Register math tools with the MCP server."""

    @mcp.tool()
    def calculate(expression: str) -> str:
        """
        Safely evaluate a mathematical expression.
        
        Supports basic arithmetic: +, -, *, /, ** (power), and parentheses.
        Does NOT support variables, functions, or imports.
        
        Args:
            expression: The mathematical expression to evaluate (e.g., "2 + 2 * 5")
            
        Returns:
            The string result of the calculation or an error message.
        """
        try:
            # Parse the expression into an AST
            # mode='eval' ensures we only accept expressions, not statements
            tree = ast.parse(expression, mode='eval')
            
            # Evaluate the safe subset
            result = _safe_eval(tree.body)
            
            # Format result
            # If it's an integer float (e.g. 4.0), pretty print as 4
            if isinstance(result, float) and result.is_integer():
                return str(int(result))
            return str(result)

        except SyntaxError:
            return "Error: Invalid syntax in expression"
        except ZeroDivisionError:
            return "Error: Division by zero"
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
