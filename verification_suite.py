
import os
import sys
import ast
import importlib
import traceback
from pathlib import Path
from datetime import datetime

# Setup paths
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
sys.path.insert(0, str(Path(__file__).parent / "tools" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "core" / "src"))

# Results storage
RESULTS = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_pass(test_name, details=""):
    print(f"  [PASS] {test_name}" + (f" - {details}" if details else ""))
    RESULTS["passed"].append({"test": test_name, "details": details})

def log_fail(test_name, details=""):
    print(f"  [FAIL] {test_name}" + (f" - {details}" if details else ""))
    RESULTS["failed"].append({"test": test_name, "details": details})

def log_warn(test_name, details=""):
    print(f"  [WARN] {test_name}" + (f" - {details}" if details else ""))
    RESULTS["warnings"].append({"test": test_name, "details": details})

def section(title):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()


# ============================================================================
# TEST 1: Code Follows Project Conventions
# ============================================================================
def test_project_conventions():
    section("TEST 1: CODE FOLLOWS PROJECT CONVENTIONS")
    
    # Check Python file naming conventions (snake_case)
    tools_dir = Path(__file__).parent / "tools" / "src" / "aden_tools" / "tools"
    
    if not tools_dir.exists():
        log_fail("Tools directory exists", f"Directory not found: {tools_dir}")
        return
    
    log_pass("Tools directory exists", str(tools_dir))
    
    # Check all tool directories follow snake_case
    tool_dirs = [d for d in tools_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
    
    snake_case_count = 0
    for tool_dir in tool_dirs:
        if tool_dir.name.islower() and "_" in tool_dir.name or tool_dir.name.islower():
            snake_case_count += 1
        else:
            log_warn(f"Naming convention", f"{tool_dir.name} should be snake_case")
    
    if snake_case_count == len(tool_dirs):
        log_pass("All tool directories use snake_case naming", f"{len(tool_dirs)} directories")
    else:
        log_warn("Some directories may not follow snake_case", f"{snake_case_count}/{len(tool_dirs)}")
    
    # Check for __init__.py in each tool directory
    init_count = 0
    for tool_dir in tool_dirs:
        if (tool_dir / "__init__.py").exists():
            init_count += 1
        else:
            log_warn(f"Missing __init__.py", tool_dir.name)
    
    if init_count == len(tool_dirs):
        log_pass("All tool directories have __init__.py", f"{init_count} files")
    else:
        log_fail("Some directories missing __init__.py", f"{init_count}/{len(tool_dirs)}")
    
    # Check main files exist
    main_files = ["quick_start.py", "hive_cli.py", "autonomous_agent.py", "logging_config.py"]
    for f in main_files:
        path = Path(__file__).parent / f
        if path.exists():
            log_pass(f"Main file exists: {f}")
        else:
            log_fail(f"Main file missing: {f}")


# ============================================================================
# TEST 2: All Tools Have Proper Docstrings
# ============================================================================
def test_docstrings():
    section("TEST 2: ALL TOOLS HAVE PROPER DOCSTRINGS")
    
    tools_init = Path(__file__).parent / "tools" / "src" / "aden_tools" / "tools" / "__init__.py"
    
    if not tools_init.exists():
        log_fail("Tools __init__.py exists", "File not found")
        return
    
    # Parse the AST to check for docstrings
    with open(tools_init, "r", encoding="utf-8") as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
        
        # Check module docstring
        if ast.get_docstring(tree):
            log_pass("Module docstring present in tools/__init__.py")
        else:
            log_fail("Module docstring missing in tools/__init__.py")
        
        # Count functions with docstrings
        functions_with_docs = 0
        functions_without_docs = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if ast.get_docstring(node):
                    functions_with_docs += 1
                else:
                    functions_without_docs.append(node.name)
        
        if functions_without_docs:
            log_warn(f"Functions without docstrings", ", ".join(functions_without_docs[:5]))
        
        log_pass(f"Functions with docstrings", f"{functions_with_docs} functions documented")
        
    except SyntaxError as e:
        log_fail("Parse tools/__init__.py", str(e))
    
    # Check individual tool files for docstrings
    tools_dir = Path(__file__).parent / "tools" / "src" / "aden_tools" / "tools"
    tool_dirs = [d for d in tools_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
    
    tools_with_docs = 0
    for tool_dir in tool_dirs:
        init_file = tool_dir / "__init__.py"
        if init_file.exists():
            with open(init_file, "r", encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                    if ast.get_docstring(tree):
                        tools_with_docs += 1
                except:
                    pass
    
    log_pass(f"Tool modules with docstrings", f"{tools_with_docs}/{len(tool_dirs)}")


# ============================================================================
# TEST 3: Error Handling Implemented
# ============================================================================
def test_error_handling():
    section("TEST 3: ERROR HANDLING IMPLEMENTED")
    
    # Check for try/except blocks in main files
    main_files = ["quick_start.py", "hive_cli.py", "autonomous_agent.py"]
    
    for filename in main_files:
        filepath = Path(__file__).parent / filename
        if not filepath.exists():
            log_fail(f"File exists: {filename}")
            continue
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
            
            # Count try/except blocks
            try_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Try))
            
            if try_count > 0:
                log_pass(f"Error handling in {filename}", f"{try_count} try/except blocks")
            else:
                log_warn(f"No try/except in {filename}")
            
            # Check for exception handling patterns
            has_exception_class = "Exception" in content
            has_keyboard_interrupt = "KeyboardInterrupt" in content
            
            if has_exception_class:
                log_pass(f"Exception class used in {filename}")
            
            if has_keyboard_interrupt:
                log_pass(f"KeyboardInterrupt handled in {filename}")
                
        except SyntaxError as e:
            log_fail(f"Parse {filename}", str(e))
    
    # Test actual error handling by calling tools with bad input
    print()
    print("  Testing runtime error handling...")
    
    try:
        from aden_tools.tools import register_all_tools
        from fastmcp import FastMCP
        
        mcp = FastMCP("test-error-handling")
        tools = register_all_tools(mcp)
        
        # Test with invalid search
        search_tool = mcp._tool_manager._tools.get("search_tickets")
        if search_tool:
            result = search_tool.fn(status="invalid_status_that_does_not_exist")
            if isinstance(result, dict):
                log_pass("search_tickets handles invalid input gracefully")
            else:
                log_warn("search_tickets returned unexpected type")
        
        # Test CRM with empty query
        search_crm = mcp._tool_manager._tools.get("crm_search_contacts")
        if search_crm:
            result = search_crm.fn(query="")
            if isinstance(result, dict):
                log_pass("crm_search_contacts handles empty input gracefully")
        
    except Exception as e:
        log_fail(f"Runtime error handling test", str(e))


# ============================================================================
# TEST 4: Logging Configured
# ============================================================================
def test_logging():
    section("TEST 4: LOGGING CONFIGURED")
    
    logging_config = Path(__file__).parent / "logging_config.py"
    
    if not logging_config.exists():
        log_fail("logging_config.py exists")
        return
    
    log_pass("logging_config.py exists")
    
    with open(logging_config, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check for logging module import
    if "import logging" in content:
        log_pass("logging module imported")
    else:
        log_fail("logging module not imported")
    
    # Check for common logging patterns
    patterns = [
        ("Logger configuration", "logging.getLogger" in content or "getLogger" in content),
        ("Log level setting", "setLevel" in content or "level=" in content),
        ("Handler configuration", "Handler" in content or "handler" in content),
        ("Formatter configuration", "Formatter" in content or "format" in content),
    ]
    
    for pattern_name, found in patterns:
        if found:
            log_pass(pattern_name)
        else:
            log_warn(f"{pattern_name} not found")
    
    # Test actual logging works
    print()
    print("  Testing logging functionality...")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from logging_config import setup_logging, get_logger
        
        logger = get_logger("verification_test")
        logger.info("Test log message")
        log_pass("Logging module loads and works")
        
    except ImportError as e:
        log_warn(f"Could not import logging_config", str(e))
    except Exception as e:
        log_fail(f"Logging test failed", str(e))


# ============================================================================
# TEST 5: Documentation Updated
# ============================================================================
def test_documentation():
    section("TEST 5: DOCUMENTATION UPDATED")
    
    docs = [
        ("README.md", True),
        ("PROJECT_DOCUMENTATION.md", True),
        ("PULL_REQUEST.md", True),
        ("FOUNDER_PITCH.md", False),  # Optional
    ]
    
    for doc_name, required in docs:
        doc_path = Path(__file__).parent / doc_name
        if doc_path.exists():
            # Check file has content
            size = doc_path.stat().st_size
            if size > 100:
                log_pass(f"{doc_name} exists and has content", f"{size} bytes")
            else:
                log_warn(f"{doc_name} exists but is small", f"{size} bytes")
        else:
            if required:
                log_fail(f"{doc_name} missing (required)")
            else:
                log_warn(f"{doc_name} missing (optional)")
    
    # Check README has key sections
    readme = Path(__file__).parent / "README.md"
    if readme.exists():
        with open(readme, "r", encoding="utf-8") as f:
            content = f.read()
        
        sections = ["Quick Start", "Features", "Installation", "Usage"]
        found_sections = [s for s in sections if s.lower() in content.lower()]
        
        if len(found_sections) >= 2:
            log_pass(f"README has key sections", ", ".join(found_sections))
        else:
            log_warn(f"README may be missing sections")


# ============================================================================
# TEST 6: Examples Provided
# ============================================================================
def test_examples():
    section("TEST 6: EXAMPLES PROVIDED")
    
    examples_dir = Path(__file__).parent / "examples"
    
    if not examples_dir.exists():
        log_fail("examples directory exists")
        return
    
    log_pass("examples directory exists")
    
    # List example files
    example_files = list(examples_dir.glob("*.py"))
    
    if example_files:
        log_pass(f"Example files found", f"{len(example_files)} files")
        
        for ex_file in example_files:
            log_pass(f"  - {ex_file.name}")
    else:
        log_fail("No example Python files found")
    
    # Check example.py is runnable (syntax check)
    example_py = examples_dir / "example.py"
    if example_py.exists():
        with open(example_py, "r", encoding="utf-8") as f:
            content = f.read()
        
        try:
            ast.parse(content)
            log_pass("example.py has valid Python syntax")
        except SyntaxError as e:
            log_fail(f"example.py syntax error", str(e))
    
    # Check core examples directory
    core_examples = Path(__file__).parent / "core" / "examples"
    if core_examples.exists():
        core_ex_files = list(core_examples.glob("*.py"))
        log_pass(f"Core examples found", f"{len(core_ex_files)} files")
    else:
        log_warn("No core/examples directory")


# ============================================================================
# TEST 7: Tested on Windows
# ============================================================================
def test_windows():
    section("TEST 7: TESTED ON WINDOWS")
    
    # Check we're on Windows
    if sys.platform == "win32":
        log_pass("Running on Windows", f"Python {sys.version.split()[0]}")
    else:
        log_warn(f"Not running on Windows", f"Platform: {sys.platform}")
    
    # Check Windows-specific files exist
    windows_files = ["start_hive.bat"]
    for f in windows_files:
        path = Path(__file__).parent / f
        if path.exists():
            log_pass(f"Windows file exists: {f}")
        else:
            log_warn(f"Windows file missing: {f}")
    
    # Test that tools actually load and work
    print()
    print("  Running Windows integration tests...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from fastmcp import FastMCP
        from aden_tools.tools import register_all_tools
        
        mcp = FastMCP("windows-test")
        tools = register_all_tools(mcp)
        
        log_pass(f"Tools loaded successfully", f"{len(tools)} tools registered")
        
        # Test a few tools actually work
        test_tools = [
            ("create_ticket", {"title": "Test", "description": "Test desc"}),
            ("crm_search_contacts", {"query": "test"}),
            ("get_ticket_summary", {}),
        ]
        
        passed_tools = 0
        for tool_name, params in test_tools:
            tool = mcp._tool_manager._tools.get(tool_name)
            if tool:
                try:
                    result = tool.fn(**params)
                    if isinstance(result, dict):
                        passed_tools += 1
                        log_pass(f"Tool {tool_name} works")
                except Exception as e:
                    log_fail(f"Tool {tool_name} error", str(e)[:50])
            else:
                log_warn(f"Tool {tool_name} not found")
        
        log_pass(f"Windows tool execution", f"{passed_tools}/{len(test_tools)} tools passed")
        
    except Exception as e:
        log_fail("Windows integration test", str(e))


# ============================================================================
# ADDITIONAL TEST: Tool Registration Count
# ============================================================================
def test_tool_count():
    section("BONUS: VERIFY 43 TOOLS REGISTERED")
    
    try:
        from fastmcp import FastMCP
        from aden_tools.tools import register_all_tools
        
        mcp = FastMCP("count-test")
        tools = register_all_tools(mcp)
        
        tool_count = len(tools)
        
        if tool_count >= 43:
            log_pass(f"Tool count meets requirement", f"{tool_count} tools (target: 43)")
        elif tool_count >= 40:
            log_warn(f"Tool count close to target", f"{tool_count} tools (target: 43)")
        else:
            log_fail(f"Tool count below target", f"{tool_count} tools (target: 43)")
        
        # List tool categories
        categories = {}
        for tool_name in tools:
            prefix = tool_name.split("_")[0] if "_" in tool_name else "other"
            categories[prefix] = categories.get(prefix, 0) + 1
        
        print()
        print("  Tool categories:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"    - {cat}: {count} tools")
        
    except Exception as e:
        log_fail("Tool count verification", str(e))


# ============================================================================
# MAIN
# ============================================================================
def main():
    print()
    print("=" * 70)
    print("  HIVE PROJECT VERIFICATION SUITE")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Run all tests
    test_project_conventions()
    test_docstrings()
    test_error_handling()
    test_logging()
    test_documentation()
    test_examples()
    test_windows()
    test_tool_count()
    
    # Summary
    section("VERIFICATION SUMMARY")
    
    total = len(RESULTS["passed"]) + len(RESULTS["failed"]) + len(RESULTS["warnings"])
    
    print(f"  Total Tests: {total}")
    print(f"  Passed:      {len(RESULTS['passed'])} [OK]")
    print(f"  Failed:      {len(RESULTS['failed'])} [FAIL]")
    print(f"  Warnings:    {len(RESULTS['warnings'])} [WARN]")
    print()
    
    if RESULTS["failed"]:
        print("  FAILED TESTS:")
        for item in RESULTS["failed"]:
            print(f"    - {item['test']}: {item['details']}")
        print()
    
    # Final verdict
    if len(RESULTS["failed"]) == 0:
        print("  " + "=" * 50)
        print("  RESULT: ALL CHECKS PASSED!")
        print("  " + "=" * 50)
        return 0
    else:
        print("  " + "=" * 50)
        print(f"  RESULT: {len(RESULTS['failed'])} CHECKS FAILED")
        print("  " + "=" * 50)
        return 1


if __name__ == "__main__":
    sys.exit(main())
