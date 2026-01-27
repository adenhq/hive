**Problem**
The `tools/pyproject.toml` declares `RestrictedPython>=7.0` as an optional dependency for the `sandbox` extra. However, a scan of the codebase reveals that `RestrictedPython` is **never imported or used** in the `tools` source code. This suggests either a missing feature (sandboxing was planned but not written) or a dead dependency.

**Evidence**
File: `tools/pyproject.toml` (Line 39): `"RestrictedPython>=7.0",`
Search: `grep -r "RestrictedPython" tools/src` returns 0 results.

**Impact**
**Code Quality**. Misleads users into thinking there is a Python code sandbox capability when there isn't one.

**Proposed Solution**
1.  If sandboxing is planned, treat this as a "Missing Feature" and implement it.
2.  If not, remove the dependency from `pyproject.toml` to clean up the build.

**Priority**
Medium
