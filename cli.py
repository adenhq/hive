#!/usr/bin/env python
import sys
import os
from pathlib import Path

# Add 'core' to sys.path so 'framework' can be imported as a top-level package
# This resolves the "ModuleNotFoundError: No module named 'framework'"
project_root = Path(__file__).parent
core_path = project_root / "core"
sys.path.insert(0, str(core_path))

if __name__ == "__main__":
    try:
        from framework.cli import main
        main()
    except ImportError as e:
        print(f"❌ Error bootstrapping environment: {e}")
        print(f"   Ensure dependencies are installed and 'core' directory exists.")
        sys.exit(1)
