"""
Smoke tests for the MCP server module.
"""

import pytest


def _mcp_available() -> bool:
    """Check if MCP dependencies are installed."""
    try:
        import mcp
        from mcp.server import FastMCP
        return True
    except ImportError:
        return False


MCP_AVAILABLE = _mcp_available()
MCP_SKIP_REASON = "MCP dependencies not installed"


class TestMCPDependencies:
    """Tests for MCP dependency availability."""

    def test_mcp_package_available(self):
        """Test that the mcp package can be imported."""
        if not MCP_AVAILABLE:
            pytest.skip(MCP_SKIP_REASON)

        import mcp
        assert mcp is not None

    def test_fastmcp_available(self):
        """Test that FastMCP class is available from mcp server."""
        if not MCP_AVAILABLE:
            pytest.skip(MCP_SKIP_REASON)

        from mcp.server import FastMCP
        assert FastMCP is not None


class TestAgentBuilderServerModule:
    """Tests for the agent_builder_server module."""

    def test_module_importable(self):
        """Test that framework.mcp.agent_builder_server can be imported."""
        if not MCP_AVAILABLE:
            pytest.skip(MCP_SKIP_REASON)

        import framework.mcp.agent_builder_server as module
        assert module is not None

    def test_mcp_object_exported(self):
        """Test that the module exports the 'mcp' object (FastMCP instance)."""
        if not MCP_AVAILABLE:
            pytest.skip(MCP_SKIP_REASON)

        from framework.mcp.agent_builder_server import mcp
        from mcp.server import FastMCP

        assert mcp is not None
        assert isinstance(mcp, FastMCP)

    def test_mcp_server_name(self):
        """Test that the MCP server has the expected name."""
        if not MCP_AVAILABLE:
            pytest.skip(MCP_SKIP_REASON)

        from framework.mcp.agent_builder_server import mcp
        assert mcp.name == "agent-builder"


class TestMCPPackageExports:
    """Tests for the framework.mcp package exports."""

    def test_package_importable(self):
        """Test that framework.mcp package can be imported."""
        if not MCP_AVAILABLE:
            pytest.skip(MCP_SKIP_REASON)

        import framework.mcp
        assert framework.mcp is not None

    def test_agent_builder_server_exported(self):
        """Test that agent_builder_server is exported from framework.mcp."""
        if not MCP_AVAILABLE:
            pytest.skip(MCP_SKIP_REASON)

        from framework.mcp import agent_builder_server
        from mcp.server import FastMCP

        assert agent_builder_server is not None
        assert isinstance(agent_builder_server, FastMCP)

class TestAgentBuilderTools:
    """Tests for the actual MCP tools that agents use"""
    
    @pytest.mark.skipif(not MCP_AVAILABLE, reason=MCP_SKIP_REASON)
    def test_file_tools_exist(self):
        """Check if file read/write tools are actually there"""
        from framework.mcp.agent_builder_server import mcp
        
        # Get all tool names
        tool_names = [tool.name for tool in mcp.tools]
        print(f"Available tools: {tool_names}")  # for debugging
        
        # Should have some file tools at least
        file_tools = [t for t in tool_names if 'file' in t.lower() or 'read' in t.lower()]
        assert len(file_tools) > 0, f"No file tools found. Got: {tool_names}"
    
    @pytest.mark.skipif(not MCP_AVAILABLE, reason=MCP_SKIP_REASON)
    def test_server_start_no_crash(self):
        """Most important: server should start without Anthropic key"""
        # Temporarily remove Anthropic key if it exists
        import os
        had_anthropic_key = "ANTHROPIC_API_KEY" in os.environ
        if had_anthropic_key:
            os.environ.pop("ANTHROPIC_API_KEY")
        
        try:
            from framework.mcp.agent_builder_server import mcp
            # If we get here without import crash, it's good
            assert mcp.name == "agent-builder"
        finally:
            # Clean up env
            if had_anthropic_key:
                os.environ["ANTHROPIC_API_KEY"] = "dummy"  # don't actually use it
    
    @pytest.mark.skipif(not MCP_AVAILABLE, reason=MCP_SKIP_REASON)
    def test_basic_tool_call_works(self):
        """Try calling a simple tool if it exists"""
        from framework.mcp.agent_builder_server import mcp
        
        # Look for any simple tool to test
        simple_tools = [t for t in mcp.tools if not t.name.startswith('_')]
        if not simple_tools:
            pytest.skip("No public tools to test")
        
        # Just check we can access first tool's input schema
        first_tool = simple_tools[0]
        assert hasattr(first_tool, 'inputSchema'), "Tool missing inputSchema"
        print(f"Tested tool: {first_tool.name}")

# Also adding this since the issue mentioned test generation functions
def test_generate_functions_dont_crash():
    """Test the generate test functions don't require LLM anymore"""
    if not MCP_AVAILABLE:
        pytest.skip(MCP_SKIP_REASON)
    
    from framework.mcp.agent_builder_server import generate_constraint_tests, generate_success_tests
    
    # Should return something instead of crashing
    result1 = generate_constraint_tests("test1", {"goal": "do stuff"}, "tests/")
    result2 = generate_success_tests("test2", {"goal": "success"}, "tests/")
    
    # making sure they don't crash and return strings
    assert isinstance(result1, str)
    assert isinstance(result2, str)
    print(f"generate_constraint_tests returned: {result1[:100]}...")
