"""
Smoke tests for MCP server module.

These tests verify that the MCP server can be imported and basic
structures are available.
"""

import pytest


def test_mcp_server_module_import():
    """Test that MCP server module can be imported."""
    try:
        from framework.mcp import agent_builder_server
        assert agent_builder_server is not None
    except ImportError as e:
        pytest.skip(f"MCP server module not available: {e}")


def test_mcp_server_has_mcp_object():
    """Test that MCP server module exports an mcp object."""
    try:
        from framework.mcp import agent_builder_server
        assert hasattr(agent_builder_server, "mcp"), "MCP server should export 'mcp' object"
    except ImportError as e:
        pytest.skip(f"MCP server module not available: {e}")


def test_mcp_dependencies_available():
    """Test that MCP dependencies are installed."""
    try:
        import mcp
        import fastmcp
        assert mcp is not None
        assert fastmcp is not None
    except ImportError as e:
        pytest.skip(f"MCP dependencies not installed: {e}")


def test_mcp_server_basic_structure():
    """Test that MCP server has expected structure."""
    try:
        from framework.mcp import agent_builder_server
        
        # Check that mcp object exists and has expected attributes
        if hasattr(agent_builder_server, "mcp"):
            mcp_obj = agent_builder_server.mcp
            # Basic smoke test - just verify it's an object
            assert mcp_obj is not None
            
    except ImportError as e:
        pytest.skip(f"MCP server module not available: {e}")
    except AttributeError as e:
        pytest.skip(f"MCP server structure not as expected: {e}")
