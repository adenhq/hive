import sys
sys.path.insert(0, 'core')

print("Checking dependencies...")
try:
    import pydantic
    print(f"✓ pydantic {pydantic.VERSION}")
except ImportError:
    print("✗ pydantic - NOT INSTALLED")

try:
    import framework
    print("✓ framework - OK")
except ImportError as e:
    print(f"✗ framework - {e}")

try:
    import litellm
    print("✓ litellm - OK")
except ImportError:
    print("✗ litellm - NOT INSTALLED")

print("\nReady to run agent!" if 'pydantic' in dir() else "\nWaiting for dependencies...")
