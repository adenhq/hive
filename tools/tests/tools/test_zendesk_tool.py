"""
Tests for Zendesk integration tools including edge cases and error handling.
"""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest
import httpx
from fastmcp import FastMCP

from aden_tools.tools.zendesk_tool import register_tools
from aden_tools.credentials import CredentialManager, CredentialError

@pytest.fixture
def mcp():
    return FastMCP("test-zendesk")

@pytest.fixture
def mock_credentials():
    return CredentialManager.for_testing({
        "zendesk": "test-token",
        "zendesk_subdomain": "test-sub",
        "zendesk_email": "test@example.com"
    })

@pytest.fixture
def incomplete_credentials():
    return CredentialManager.for_testing({
        "zendesk_subdomain": "test-sub"
        # Missing token and email
    })

def test_registration(mcp, mock_credentials):
    """Test that Zendesk tools are correctly registered."""
    register_tools(mcp, credentials=mock_credentials)
    
    assert "zendesk_health_check" in mcp._tool_manager._tools
    assert "zendesk_ticket_search" in mcp._tool_manager._tools
    assert "zendesk_ticket_get" in mcp._tool_manager._tools
    assert "zendesk_ticket_update" in mcp._tool_manager._tools

@pytest.mark.asyncio
async def test_zendesk_health_check_success(mcp, mock_credentials):
    """Test health check success."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user": {"name": "Test User", "email": "test@example.com"}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        fn = mcp._tool_manager._tools["zendesk_health_check"].fn
        result = await fn()
        
        assert "✅" in result
        assert "Test User" in result

@pytest.mark.asyncio
async def test_zendesk_health_check_missing_creds(mcp, incomplete_credentials):
    """Edge Case: Missing credentials should return an error message."""
    register_tools(mcp, credentials=incomplete_credentials)
    
    fn = mcp._tool_manager._tools["zendesk_health_check"].fn
    result = await fn()
    
    assert "❌ Missing Zendesk credentials" in result

@pytest.mark.asyncio
async def test_zendesk_search_empty_results(mcp, mock_credentials):
    """Edge Case: Empty results should return valid JSON with empty list."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "count": 0}
        mock_get.return_value = mock_response
        
        fn = mcp._tool_manager._tools["zendesk_ticket_search"].fn
        result = await fn(query="nonexistent")
        
        assert result["count"] == 0
        assert len(result["results"]) == 0

@pytest.mark.asyncio
async def test_zendesk_api_error_401(mcp, mock_credentials):
    """Edge Case: Unauthorized access (401)."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response
        
        fn = mcp._tool_manager._tools["zendesk_ticket_get"].fn
        with pytest.raises(httpx.HTTPStatusError):
            await fn(ticket_id=123)

@pytest.mark.asyncio
async def test_zendesk_api_error_429_rate_limit(mcp, mock_credentials):
    """Edge Case: Rate limit exceeded (429)."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Too Many Requests", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response
        
        fn = mcp._tool_manager._tools["zendesk_ticket_get"].fn
        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            await fn(ticket_id=123)
        assert excinfo.value.response.status_code == 429

@pytest.mark.asyncio
async def test_zendesk_ticket_update_minimal(mcp, mock_credentials):
    """Test updating only one field (e.g. status)."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.put") as mock_put:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ticket": {"id": 1, "status": "pending"}}
        mock_put.return_value = mock_response
        
        fn = mcp._tool_manager._tools["zendesk_ticket_update"].fn
        await fn(ticket_id=1, status="pending")
        
        args, kwargs = mock_put.call_args
        assert kwargs["json"] == {"ticket": {"status": "pending"}}

@pytest.mark.asyncio
async def test_zendesk_ticket_update_private_comment(mcp, mock_credentials):
    """Test adding a private comment (internal note)."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.put") as mock_put:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ticket": {"id": 1}}
        mock_put.return_value = mock_response
        
        fn = mcp._tool_manager._tools["zendesk_ticket_update"].fn
        await fn(ticket_id=1, comment="Internal note test", is_public=False)
        
        args, kwargs = mock_put.call_args
        comment_data = kwargs["json"]["ticket"]["comment"]
        assert comment_data["body"] == "Internal note test"
        assert comment_data["public"] is False

@pytest.mark.asyncio
async def test_zendesk_ticket_get_not_found(mcp, mock_credentials):
    """Edge Case: Ticket not found (404)."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response
        
        fn = mcp._tool_manager._tools["zendesk_ticket_get"].fn
        with pytest.raises(httpx.HTTPStatusError):
            await fn(ticket_id=999999)

@pytest.mark.asyncio
async def test_zendesk_invalid_subdomain_handling(mcp):
    """Edge Case: When subdomain is missing from credentials."""
    creds = CredentialManager.for_testing({
        "zendesk": "token",
        "zendesk_email": "email"
    })
    register_tools(mcp, credentials=creds)
    
    fn = mcp._tool_manager._tools["zendesk_health_check"].fn
    result = await fn()
    
    # Base URL builder defaults to 'None' if missing
    assert "https://None.zendesk.com" in result or "Missing Zendesk credentials" in result
