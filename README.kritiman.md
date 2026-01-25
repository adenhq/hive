# 🔒 Issue B: Unsafe `eval()` in `FunctionNode.execute`

## Overview

The Hive AI agent framework currently uses Python's built-in `eval()` function in:

**File:** `hive/core/framework/graph/node.py`  
**Method:** `FunctionNode.execute`

```python
result = eval(expression)
```

This evaluates dynamically generated expressions from user input or external sources.

## Problem

Directly calling `eval()` on untrusted input introduces a **critical security vulnerability**, allowing:

- Arbitrary code execution
- Manipulation of runtime context
- Potential system compromise

## Risk

- **Code injection** via malicious expressions
- **Unauthorized access** to memory or system resources
- **Runtime instability** or denial-of-service attacks

## Recommendation

Replace the unsafe `eval()` call with a **secure expression evaluator**.

## Options

### 1. `ast.literal_eval` (Python built-in)

Safely evaluates Python literals (strings, numbers, tuples, lists, dicts, booleans, None). **Cannot execute arbitrary code.**

```python
import ast

result = ast.literal_eval(expression)
```

**Official Documentation:** [ast.literal_eval](https://docs.python.org/3/library/ast.html#ast.literal_eval)

### 2. Math expression parsers / safe evaluators

Libraries like `simpleeval` or `asteval` allow arithmetic and logical expressions safely. Can define allowed operators and functions.

**Example using `simpleeval`:**

```python
from simpleeval import simple_eval

result = simple_eval(expression)
```

## Action Items

1. Replace `eval(expression)` with one of the secure alternatives
2. Limit evaluated expressions strictly to arithmetic and safe literals
3. Add unit tests to ensure invalid expressions fail safely
4. Document allowed syntax for developers and agent authors

## References

- [Python eval() Security Warning](https://docs.python.org/3/library/functions.html#eval)
- [Python ast.literal_eval()](https://docs.python.org/3/library/ast.html#ast.literal_eval)
- [simpleeval GitHub Repository](https://github.com/danthedeckie/simpleeval)
- [asteval Documentation](https://newville.github.io/asteval/)