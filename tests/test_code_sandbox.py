import sys
import os

# Get the absolute path to the 'core' folder
# 1. Get current folder (tests/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Get parent folder (hive/)
repo_root = os.path.dirname(current_dir)
# 3. Target the 'core' folder (hive/core/)
core_path = os.path.join(repo_root, "core")

# Add 'core' to sys.path so Python can find 'framework'
sys.path.insert(0, core_path)

import pytest
# Now this import will work because we are pointing to 'core'
from framework.graph.code_sandbox import safe_exec

def test_pow_is_not_available():
    """
    Regression test for SECURITY issue #2686:
    pow() should not be available in SAFE_BUILTINS to prevent DoS.
    """
    # Attempting to use pow() should raise a NameError (because it's removed)
    with pytest.raises(NameError):
        safe_exec("pow(2, 100000000)")
