"""Tests for email tool."""

import pytest
from fastmcp import FastMCP

from aden_tools.tools.email_tool import register_tools
from aden_tools.credentials import CredentialManager


@pytest.fixture
def mcp():
    """Create a test MCP server."""
    return FastMCP("test-email-server")


@pytest.fixture
def mock_credentials():
    """Create mock credentials manager."""
    return CredentialManager.for_testing({"resend": "re_test_key_12345"})


class TestEmailToolRegistration:
    """Test email tool registration."""

    def test_register_tools_with_credentials(self, mcp, mock_credentials):
        """Test tools are registered successfully with credentials."""
        # Registration should not raise errors
        register_tools(mcp, credentials=mock_credentials)
        # If we reach here, registration succeeded

    def test_register_tools_without_credentials(self, mcp):
        """Test tools can be registered without credentials."""
        # Should not raise even without credentials
        register_tools(mcp, credentials=None)


class TestEmailToolIntegration:
    """Integration tests for email tools."""

    def test_registration_with_env_fallback(self, mcp, monkeypatch):
        """Test registration with environment variable fallback."""
        monkeypatch.setenv("RESEND_API_KEY", "re_from_env_123")
        
        register_tools(mcp, credentials=None)
        # Registration succeeded

    def test_registration_without_api_key(self, mcp, monkeypatch):
        """Test registration without API key doesn't fail."""
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        monkeypatch.delenv("EMAIL_RESEND_API_KEY", raising=False)
        
        # Registration should not fail even without API key
        # (API key is checked at send time, not registration time)
        register_tools(mcp, credentials=None)


class TestEmailToolTemplates:
    """Test email template rendering functions."""

    def test_template_rendering(self):
        """Test that template rendering functions exist and work."""
        from aden_tools.tools.email_tool.email_tool import (
            _render_notification_template,
            _render_report_template,
            _render_approval_request_template,
            _render_completion_template,
        )
        
        # Test notification template
        html = _render_notification_template({
            "title": "Test",
            "message": "<p>Test message</p>",
            "icon": "📧",
        })
        assert "Test" in html
        assert "<p>Test message</p>" in html
        assert "📧" in html
        
        # Test report template
        html = _render_report_template({
            "title": "Report",
            "content": "<h2>Data</h2>",
            "date": "2026-01-24",
        })
        assert "Report" in html
        assert "<h2>Data</h2>" in html
        assert "2026-01-24" in html
        
        # Test approval request template
        html = _render_approval_request_template({
            "title": "Approval",
            "description": "Please approve",
            "action_url": "https://example.com",
        })
        assert "Approval" in html
        assert "Please approve" in html
        assert "https://example.com" in html
        
        # Test completion template
        html = _render_completion_template({
            "title": "Complete",
            "task_name": "Task",
            "summary": "Done",
        })
        assert "Complete" in html
        assert "Task" in html
        assert "Done" in html


class TestEmailToolCredentialIntegration:
    """Test credential manager integration."""

    def test_credential_manager_integration(self):
        """Test that email credentials are properly defined."""
        from aden_tools.credentials import CREDENTIAL_SPECS
        
        # Email credentials should be registered
        assert "resend" in CREDENTIAL_SPECS
        
        # Check credential spec
        spec = CREDENTIAL_SPECS["resend"]
        assert spec.env_var == "RESEND_API_KEY"
        assert "send_email" in spec.tools
        assert "send_templated_email" in spec.tools
        assert spec.help_url == "https://resend.com/api-keys"
