import ast
from typing import Any, Dict

class SafeExpressionEvaluator(ast.NodeVisitor):
    """
    Safely evaluates simple expressions (constants, basic arithmetic, comparisons)
    within a restricted AST subset.
    """
    
    # Define allowed node types for safety
    ALLOWED_NODE_TYPES = (
        ast.Expression, ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp,
        ast.Compare, ast.BoolOp, ast.Load, ast.Is, ast.IsNot, ast.In, ast.NotIn,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.List, ast.Tuple, ast.Dict, ast.Set, ast.Subscript, ast.Slice, ast.Index,
    )

    def __init__(self, variables: Dict[str, Any]):
        self.variables = variables

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        """
        Handles constants (numbers, strings, booleans, None).
        This replaces the deprecated visit_Num, visit_Str, and visit_NameConstant.
        """
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        if isinstance(node.ctx, ast.Load):
            if node.id in self.variables:
                return self.variables[node.id]
            raise NameError(f"Name '{node.id}' is not defined in context.")
        
        # Prevent assignment or deletion operations
        raise TypeError(f"Unsupported Name context: {type(node.ctx).__name__}")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = type(node.op)

        if op is ast.Add: return left + right
        if op is ast.Sub: return left - right
        if op is ast.Mult: return left * right
        if op is ast.Div: return left / right
        if op is ast.FloorDiv: return left // right
        if op is ast.Mod: return left % right
        if op is ast.Pow: return left ** right
        
        raise TypeError(f"Unsupported binary operator: {op.__name__}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        op = type(node.op)

        if op is ast.USub: return -operand
        if op is ast.UAdd: return +operand
        if op is ast.Not: return not operand
        
        raise TypeError(f"Unsupported unary operator: {op.__name__}")

    def visit_Compare(self, node: ast.Compare) -> bool:
        left = self.visit(node.left)
        
        # Handle chained comparisons (a < b < c)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            op_type = type(op)
            
            comparison_result = False
            if op_type is ast.Eq: comparison_result = (left == right)
            elif op_type is ast.NotEq: comparison_result = (left != right)
            elif op_type is ast.Lt: comparison_result = (left < right)
            elif op_type is ast.LtE: comparison_result = (left <= right)
            elif op_type is ast.Gt: comparison_result = (left > right)
            elif op_type is ast.GtE: comparison_result = (left >= right)
            elif op_type is ast.Is: comparison_result = (left is right)
            elif op_type is ast.IsNot: comparison_result = (left is not right)
            elif op_type is ast.In: comparison_result = (left in right)
            elif op_type is ast.NotIn: comparison_result = (left not in right)
            else:
                raise TypeError(f"Unsupported comparison operator: {op_type.__name__}")

            if not comparison_result:
                return False
            
            # For chained comparisons, the right operand becomes the new left operand
            left = right
            
        return True

    def visit_BoolOp(self, node: ast.BoolOp) -> bool:
        op_type = type(node.op)
        
        if op_type is ast.And:
            for value_node in node.values:
                if not self.visit(value_node):
                    return False
            return True
        
        if op_type is ast.Or:
            for value_node in node.values:
                if self.visit(value_node):
                    return True
            return False
            
        raise TypeError(f"Unsupported boolean operator: {op_type.__name__}")

    def visit_List(self, node: ast.List) -> list:
        return [self.visit(el) for el in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple:
        return tuple(self.visit(el) for el in node.elts)

    def visit_Dict(self, node: ast.Dict) -> dict:
        # Note: keys and values are parallel lists in ast.Dict
        return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}

    def visit_Set(self, node: ast.Set) -> set:
        return {self.visit(el) for el in node.elts}

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        value = self.visit(node.value)
        
        if isinstance(node.slice, ast.Index):
            # Simple index access (e.g., a[0])
            index = self.visit(node.slice.value)
            return value[index]
        
        if isinstance(node.slice, ast.Slice):
            # Slicing (e.g., a[1:5:2])
            lower = self.visit(node.slice.lower) if node.slice.lower else None
            upper = self.visit(node.slice.upper) if node.slice.upper else None
            step = self.visit(node.slice.step) if node.slice.step else None
            return value[slice(lower, upper, step)]

        raise TypeError(f"Unsupported subscript slice type: {type(node.slice).__name__}")

    def generic_visit(self, node: ast.AST) -> None:
        """
        Catch all unsupported AST nodes to prevent execution of arbitrary code.
        """
        if type(node) not in self.ALLOWED_NODE_TYPES:
            raise TypeError(f"Unsupported AST node type encountered: {type(node).__name__}")
        
        # If it's an allowed type but we didn't implement a specific visitor (e.g., ast.Load),
        # we rely on the specific visitor (e.g., visit_Name) to handle the context.
        super().generic_visit(node)


def safe_eval(expression: str, variables: Dict[str, Any] | None = None) -> Any:
    """
    Parses and safely evaluates a Python expression string using a restricted AST visitor.
    """
    variables = variables or {}
    
    try:
        # Use mode='eval' to ensure only expressions are parsed
        tree = ast.parse(expression, mode='eval')
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {e}")

    evaluator = SafeExpressionEvaluator(variables=variables)
    
    try:
        return evaluator.visit(tree)
    except Exception as e:
        # Re-raise evaluation errors clearly
        raise RuntimeError(f"Error evaluating expression '{expression}': {e}")
