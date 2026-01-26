"""
Tests for Tool Access Layer.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
import json

from framework.graph.tool_access_layer import (
    ToolAccessLayer,
    ToolPermission,
    ToolMetadata,
    ToolExecutionResult,
)
from framework.llm.provider import Tool, ToolUse, ToolResult
from framework.runtime.core import Runtime


@pytest.fixture
def mock_runtime():
    """Create a mock runtime."""
    runtime = Mock(spec=Runtime)
    runtime.decide = Mock(return_value="decision_123")
    runtime.record_outcome = Mock()
    return runtime


@pytest.fixture
def sample_tools():
    """Create sample tools for testing."""
    return {
        "web_search": Tool(
            name="web_search",
            description="Search the web",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        ),
        "file_read": Tool(
            name="file_read",
            description="Read a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        ),
    }


@pytest.fixture
def mock_tool_executor():
    """Create a mock tool executor."""
    def executor(tool_use: ToolUse) -> ToolResult:
        if tool_use.name == "web_search":
            return ToolResult(
                tool_use_id=tool_use.id,
                content=json.dumps({"results": ["result1", "result2"]}),
                is_error=False,
            )
        elif tool_use.name == "file_read":
            return ToolResult(
                tool_use_id=tool_use.id,
                content=json.dumps({"content": "file content"}),
                is_error=False,
            )
        else:
            return ToolResult(
                tool_use_id=tool_use.id,
                content=json.dumps({"error": "Tool not found"}),
                is_error=True,
            )
    return executor


@pytest.fixture
def tool_access_layer(mock_runtime, sample_tools, mock_tool_executor):
    """Create a ToolAccessLayer instance."""
    return ToolAccessLayer(
        tools=sample_tools,
        tool_executor=mock_tool_executor,
        runtime=mock_runtime,
        node_id="test_node",
    )


class TestToolDiscovery:
    """Test tool discovery methods."""
    
    def test_list_tools(self, tool_access_layer):
        """Test listing all tools."""
        tools = tool_access_layer.list_tools()
        assert len(tools) == 2
        assert "web_search" in tools
        assert "file_read" in tools
    
    def test_list_tools_by_category(self, tool_access_layer):
        """Test listing tools by category."""
        web_tools = tool_access_layer.list_tools(category="web")
        assert "web_search" in web_tools
        
        file_tools = tool_access_layer.list_tools(category="file_system")
        assert "file_read" in file_tools
    
    def test_has_tool(self, tool_access_layer):
        """Test checking if tool exists."""
        assert tool_access_layer.has_tool("web_search")
        assert tool_access_layer.has_tool("file_read")
        assert not tool_access_layer.has_tool("nonexistent")
    
    def test_get_tool_metadata(self, tool_access_layer):
        """Test getting tool metadata."""
        metadata = tool_access_layer.get_tool_metadata("web_search")
        assert metadata is not None
        assert metadata.name == "web_search"
        assert metadata.description == "Search the web"
        assert "query" in metadata.parameters
        assert "query" in metadata.required_params
    
    def test_get_tool_metadata_nonexistent(self, tool_access_layer):
        """Test getting metadata for nonexistent tool."""
        metadata = tool_access_layer.get_tool_metadata("nonexistent")
        assert metadata is None
    
    def test_search_tools(self, tool_access_layer):
        """Test searching tools."""
        results = tool_access_layer.search_tools("web")
        assert "web_search" in results
        
        results = tool_access_layer.search_tools("file")
        assert "file_read" in results


class TestToolExecution:
    """Test tool execution."""
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, tool_access_layer):
        """Test successful tool execution."""
        result = await tool_access_layer.execute_tool(
            name="web_search",
            params={"query": "Python"},
        )
        
        assert result.success
        assert result.result is not None
        assert "results" in result.result
        assert result.execution_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_execute_tool_missing_params(self, tool_access_layer):
        """Test tool execution with missing required parameters."""
        result = await tool_access_layer.execute_tool(
            name="web_search",
            params={},  # Missing required "query"
        )
        
        assert not result.success
        assert "Missing required parameters" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_tool_nonexistent(self, tool_access_layer):
        """Test executing nonexistent tool."""
        result = await tool_access_layer.execute_tool(
            name="nonexistent",
            params={},
        )
        
        assert not result.success
        assert "not available" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_tool_read_only_permission(self, mock_runtime, sample_tools, mock_tool_executor):
        """Test tool execution with read-only permission."""
        layer = ToolAccessLayer(
            tools=sample_tools,
            tool_executor=mock_tool_executor,
            runtime=mock_runtime,
            node_id="test_node",
            permission_level=ToolPermission.READ_ONLY,
        )
        
        result = await layer.execute_tool(
            name="web_search",
            params={"query": "test"},
        )
        
        assert not result.success
        assert "read-only permission" in result.error


class TestToolComposition:
    """Test tool composition features."""
    
    @pytest.mark.asyncio
    async def test_execute_tool_chain(self, tool_access_layer):
        """Test executing a chain of tools."""
        tool_calls = [
            {"name": "web_search", "params": {"query": "Python"}},
            {"name": "file_read", "params": {"path": "/tmp/test.txt"}},
        ]
        
        results = await tool_access_layer.execute_tool_chain(tool_calls)
        
        assert len(results) == 2
        assert results[0].success
        assert results[1].success
    
    @pytest.mark.asyncio
    async def test_execute_tool_chain_stop_on_error(self, tool_access_layer):
        """Test tool chain stops on error."""
        tool_calls = [
            {"name": "web_search", "params": {"query": "Python"}},
            {"name": "nonexistent", "params": {}},  # This will fail
            {"name": "file_read", "params": {"path": "/tmp/test.txt"}},
        ]
        
        results = await tool_access_layer.execute_tool_chain(
            tool_calls,
            stop_on_error=True,
        )
        
        assert len(results) == 2  # Stops after first failure
        assert results[0].success
        assert not results[1].success


class TestObservability:
    """Test observability features."""
    
    @pytest.mark.asyncio
    async def test_usage_stats(self, tool_access_layer):
        """Test usage statistics tracking."""
        # Execute a tool
        await tool_access_layer.execute_tool(
            name="web_search",
            params={"query": "test"},
        )
        
        # Check stats
        stats = tool_access_layer.get_usage_stats("web_search")
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 0
        assert stats["avg_time_ms"] >= 0  # Can be 0 for very fast mock executions
    
    @pytest.mark.asyncio
    async def test_usage_stats_all_tools(self, tool_access_layer):
        """Test getting stats for all tools."""
        await tool_access_layer.execute_tool("web_search", {"query": "test"})
        await tool_access_layer.execute_tool("file_read", {"path": "/tmp/test"})
        
        all_stats = tool_access_layer.get_usage_stats()
        assert "web_search" in all_stats
        assert "file_read" in all_stats


class TestToolFiltering:
    """Test tool filtering by allowed_tools."""
    
    def test_allowed_tools_filtering(self, mock_runtime, sample_tools, mock_tool_executor):
        """Test that only allowed tools are accessible."""
        layer = ToolAccessLayer(
            tools=sample_tools,
            tool_executor=mock_tool_executor,
            runtime=mock_runtime,
            node_id="test_node",
            allowed_tools=["web_search"],  # Only allow web_search
        )
        
        assert layer.has_tool("web_search")
        assert not layer.has_tool("file_read")
        
        tools = layer.list_tools()
        assert "web_search" in tools
        assert "file_read" not in tools

