# 🔒 Issue B: Unsafe `eval()` in `FunctionNode.execute`

## Overview
The Hive AI agent framework currently uses Python’s built-in `eval()` function in:

hive/core/framework/graph/node.py
FunctionNode.execute method

```python
result = eval(expression)
This evaluates dynamically generated expressions from user input or external sources.
Problem
Directly calling eval() on untrusted input introduces a critical security vulnerability, allowing:
Arbitrary code execution
Manipulation of runtime context
Potential system compromise
Risk
Code injection via malicious expressions
Unauthorized access to memory or system resources
Runtime instability or denial-of-service attacks
Recommendation
Replace the unsafe eval() call with a secure expression evaluator.
Options
1. ast.literal_eval (Python built-in)
Safely evaluates Python literals (strings, numbers, tuples, lists, dicts, booleans, None)
Cannot execute arbitrary code
import ast

result = ast.literal_eval(expression)
Official Documentation: ast.literal_eval
2. Math expression parsers / safe evaluators
Libraries like simpleeval or asteval allow arithmetic and logical expressions safely
Can define allowed operators and functions
Example using simpleeval:
from simpleeval import simple_eval

result = simple_eval(expression)
Action Items
Replace eval(expression) with one of the secure alternatives
Limit evaluated expressions strictly to arithmetic and safe literals
Add unit tests to ensure invalid expressions fail safely
Document allowed syntax for developers and agent authors
References
Python eval() Security Warning
Python ast.literal_eval()
simpleeval GitHub Repository
asteval Documentation

---

If you want, I can also **write a super concise version** specifically for a GitHub PR description — it’ll be short, formal, and ready to paste. Do you want me to do that?