"""
Tests for Memori persistent memory tools.
"""

from unittest.mock import MagicMock, patch

import pytest
import httpx
from fastmcp import FastMCP

from aden_tools.tools.memori_tool import register_tools
from aden_tools.credentials import CredentialManager

@pytest.fixture
def mcp():
    return FastMCP("test-memori")

@pytest.fixture
def mock_credentials():
    return CredentialManager.for_testing({
        "memori": "test-memori-key"
    })

def test_registration(mcp, mock_credentials):
    """Test that Memori tools are correctly registered."""
    register_tools(mcp, credentials=mock_credentials)
    
    tool_names = mcp._tool_manager._tools.keys()
    assert "memori_add" in tool_names
    assert "memori_recall" in tool_names
    assert "memori_delete" in tool_names
    assert "memori_health_check" in tool_names

@pytest.mark.asyncio
async def test_memori_add_success(mcp, mock_credentials):
    """Test memori_add success case."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "mem_123", "status": "added"}
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response
        
        fn = mcp._tool_manager._tools["memori_add"].fn
        result = await fn(content="Test memory", user_id="user_1")
        
        assert result["id"] == "mem_123"
        
        # Verify call args
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert "/memories" in args[1]
        assert kwargs["json"]["user_id"] == "user_1"
        assert "Bearer test-memori-key" in kwargs["headers"]["Authorization"]

@pytest.mark.asyncio
async def test_memori_recall_success(mcp, mock_credentials):
    """Test memori_recall success case."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"content": "Memory 1"}, {"content": "Memory 2"}]
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response
        
        fn = mcp._tool_manager._tools["memori_recall"].fn
        result = await fn(query="find memories", limit=2)
        
        assert len(result) == 2
        assert result[0]["content"] == "Memory 1"
        
        # Verify search endpoint
        args, kwargs = mock_request.call_args
        assert "/memories/search" in args[1]
        assert kwargs["json"]["limit"] == 2

@pytest.mark.asyncio
async def test_memori_delete_success(mcp, mock_credentials):
    """Test memori_delete success case (204 No Content)."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response
        
        fn = mcp._tool_manager._tools["memori_delete"].fn
        result = await fn(memory_id="mem_123")
        
        assert result["status"] == "success"
        
        # Verify correct ID in path
        args, kwargs = mock_request.call_args
        assert args[0] == "DELETE"
        assert "/memories/mem_123" in args[1]

@pytest.mark.asyncio
async def test_memori_error_handling(mcp, mock_credentials):
    """Test API error handling (401 Unauthorized)."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response
        
        fn = mcp._tool_manager._tools["memori_add"].fn
        result = await fn(content="Bad key")
        
        assert result["status"] == "error"
        assert "Invalid Memori API key" in result["message"]

@pytest.mark.asyncio
async def test_missing_credentials(mcp):
    """Test handling of missing MEMORI_API_KEY."""
    # Empty creds
    empty_creds = CredentialManager.for_testing({})
    register_tools(mcp, credentials=empty_creds)
    
    fn = mcp._tool_manager._tools["memori_add"].fn
    result = await fn(content="No key")
    
    assert result["status"] == "error"
    assert "Memori API key missing" in result["message"]
