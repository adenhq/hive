try:
    import framework
    print("framework: OK")
except ImportError as e:
    print(f"framework: FAIL - {e}")

try:
    import aden_tools
    print("aden_tools: OK")
except ImportError as e:
    print(f"aden_tools: FAIL - {e}")

try:
    import litellm
    print("litellm: OK")
except ImportError as e:
    print(f"litellm: FAIL - {e}")
