#!/usr/bin/env python3
"""
Run tests affected by Issue #1691 (tool error sanitization) without relying on
pytest plugins. Use when pytest-asyncio/pytest version conflict prevents normal pytest.

Usage:
  cd tools && python run_affected_tests.py

Or run normally if your env is fine:
  cd tools && python -m pytest tests/test_error_sanitizer.py tests/tools/test_tool_error_no_leak.py tests/tools/test_security.py tests/tools/test_file_system_toolkits.py tests/tools/test_csv_tool.py tests/tools/test_pdf_read_tool.py tests/tools/test_example_tool.py -v
"""

from __future__ import annotations

import os
import sys
import traceback

# Add src to path so aden_tools is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def run_error_sanitizer_tests() -> tuple[int, int]:
    """Run error_sanitizer unit tests manually (import utils only to avoid fastmcp)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "error_sanitizer",
        os.path.join(os.path.dirname(__file__), "src", "aden_tools", "utils", "error_sanitizer.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    error_response = mod.error_response
    sanitize_error = mod.sanitize_error

    passed, failed = 0, 0
    # Test 1: sanitize_error returns generic only
    try:
        exc = ValueError("/home/secret/.hive/workdir/xyz")
        result = sanitize_error(exc, "File not found", path="/tmp/secret")
        assert result == "File not found", result
        assert "/home" not in result and "secret" not in result
        passed += 1
    except Exception as e:
        failed += 1
        traceback.print_exc()

    # Test 2: error_response returns dict with generic only
    try:
        exc = FileNotFoundError(2, "No such file", "/etc/passwd")
        result = error_response(exc, "File not found", path="/home/user/.hive/workspace")
        assert result == {"error": "File not found"}, result
        assert "/etc" not in str(result) and "passwd" not in str(result)
        passed += 1
    except Exception as e:
        failed += 1
        traceback.print_exc()

    # Test 3: PermissionError
    try:
        exc = PermissionError(13, "Permission denied: '/var/secret/data'")
        result = error_response(exc, "Permission denied")
        assert result["error"] == "Permission denied"
        assert "/var" not in result["error"] and "secret" not in result["error"]
        passed += 1
    except Exception as e:
        failed += 1
        traceback.print_exc()

    return passed, failed


def run_security_tests() -> tuple[int, int]:
    """Run security.get_secure_path tests (ValueError message change)."""
    passed, failed = 0, 0
    import tempfile
    security_path = os.path.join(
        os.path.dirname(__file__), "src", "aden_tools", "tools", "file_system_toolkits", "security.py"
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(security_path) as f:
            code = compile(f.read(), security_path, "exec")
        ns = {"__name__": "security", "os": __import__("os")}
        exec(code, ns)
        ns["WORKSPACES_DIR"] = tmpdir  # override so get_secure_path uses tmpdir
        get_secure_path = ns["get_secure_path"]
        ids = {"workspace_id": "w", "agent_id": "a", "session_id": "s"}
        try:
            try:
                get_secure_path("../../../etc/passwd", **ids)
            except ValueError as e:
                if "outside the session sandbox" in str(e):
                    passed += 1
                else:
                    failed += 1
                    print("ValueError must contain 'outside the session sandbox':", str(e))
            else:
                failed += 1
                print("Expected ValueError for path traversal")
        except Exception as e:
            failed += 1
            traceback.print_exc()
    return passed, failed


def run_tool_error_sanitized_tests() -> tuple[int, int]:
    """Run tool error response checks (view_file, list_dir, replace, csv, pdf)."""
    from unittest.mock import patch
    import tempfile
    from pathlib import Path

    passed, failed = 0, 0
    try:
        from fastmcp import FastMCP
    except ImportError:
        print("Skipping tool tests: fastmcp not installed")
        return passed, failed

    mcp = FastMCP("test")
    workspace = {"workspace_id": "w", "agent_id": "a", "session_id": "s"}

    with tempfile.TemporaryDirectory() as tmpdir:
        def _get_secure_path(path, workspace_id, agent_id, session_id):
            return os.path.join(tmpdir, path)

        # view_file: nonexistent
        from aden_tools.tools.file_system_toolkits.view_file import register_tools as reg_view
        reg_view(mcp)
        view_fn = mcp._tool_manager._tools["view_file"].fn
        with patch("aden_tools.tools.file_system_toolkits.view_file.view_file.get_secure_path", side_effect=_get_secure_path):
            result = view_fn(path="nonexistent.txt", **workspace)
        if "error" in result and "not found" in result["error"].lower():
            if "/" not in result["error"] and "\\" not in result["error"]:
                passed += 1
            else:
                failed += 1
                print("view_file error should not contain path:", result["error"])
        else:
            failed += 1
            print("view_file expected error with 'not found':", result)

        # list_dir: nonexistent
        from aden_tools.tools.file_system_toolkits.list_dir import register_tools as reg_list
        reg_list(mcp)
        list_fn = mcp._tool_manager._tools["list_dir"].fn
        with patch("aden_tools.tools.file_system_toolkits.list_dir.list_dir.get_secure_path", side_effect=_get_secure_path):
            result = list_fn(path="nonexistent_dir", **workspace)
        if "error" in result and ("not found" in result["error"].lower() or "directory" in result["error"].lower()):
            if "/" not in result["error"] and "\\" not in result["error"]:
                passed += 1
            else:
                failed += 1
        else:
            failed += 1

        # replace_file_content: file not found
        from aden_tools.tools.file_system_toolkits.replace_file_content import register_tools as reg_replace
        reg_replace(mcp)
        replace_fn = mcp._tool_manager._tools["replace_file_content"].fn
        with patch("aden_tools.tools.file_system_toolkits.replace_file_content.replace_file_content.get_secure_path", side_effect=_get_secure_path):
            result = replace_fn(path="nonexistent.txt", target="x", replacement="y", **workspace)
        if "error" in result and "not found" in result["error"].lower():
            if "/" not in result["error"] and "\\" not in result["error"]:
                passed += 1
            else:
                failed += 1
        else:
            failed += 1

        # csv_read: file not found (need session dir)
        session_dir = Path(tmpdir) / "w" / "a" / "s"
        session_dir.mkdir(parents=True)
        from aden_tools.tools.csv_tool.csv_tool import register_tools as reg_csv
        reg_csv(mcp)
        csv_read_fn = mcp._tool_manager._tools["csv_read"].fn
        with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", tmpdir):
            result = csv_read_fn(path="missing.csv", workspace_id="w", agent_id="a", session_id="s")
        if "error" in result and "not found" in result["error"].lower():
            if "/" not in result["error"] and "\\" not in result["error"]:
                passed += 1
            else:
                failed += 1
        else:
            failed += 1

        # pdf_read: file not found
        from aden_tools.tools.pdf_read_tool import register_tools as reg_pdf
        reg_pdf(mcp)
        pdf_fn = mcp._tool_manager._tools["pdf_read"].fn
        result = pdf_fn(file_path=str(Path(tmpdir) / "missing.pdf"))
        if "error" in result and "not found" in result["error"].lower():
            if "/" not in result["error"] and "\\" not in result["error"]:
                passed += 1
            else:
                failed += 1
        else:
            failed += 1

    return passed, failed


def main() -> int:
    print("=== Issue #1691 affected tests (standalone) ===\n")
    total_passed, total_failed = 0, 0

    print("1. error_sanitizer unit tests")
    p, f = run_error_sanitizer_tests()
    total_passed += p
    total_failed += f
    print(f"   Passed: {p}, Failed: {f}\n")

    print("2. security.get_secure_path (ValueError message)")
    p, f = run_security_tests()
    total_passed += p
    total_failed += f
    print(f"   Passed: {p}, Failed: {f}\n")

    print("3. Tool error responses (no path/str(e) in error)")
    p, f = run_tool_error_sanitized_tests()
    total_passed += p
    total_failed += f
    print(f"   Passed: {p}, Failed: {f}\n")

    print(f"=== Total: {total_passed} passed, {total_failed} failed ===")
    return 1 if total_failed else 0


if __name__ == "__main__":
    sys.exit(main())
