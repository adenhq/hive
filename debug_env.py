
try:
    import litellm
    print("litellm imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")

import sys
print(f"Python path: {sys.path}")
