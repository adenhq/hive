"""Tests for Twilio tool - SMS and WhatsApp messaging integration."""

from unittest.mock import MagicMock, patch

import pytest

from aden_tools.tools.twilio_tool.twilio_tool import (
    _get_client,
    _get_from_number,
    register_tools,
)


# Global fixture to prevent .env file loading in all tests
@pytest.fixture(autouse=True)
def mock_dotenv():
    """Automatically mock load_dotenv for all tests."""
    with patch("aden_tools.tools.twilio_tool.twilio_tool.load_dotenv"):
        yield


class TestCredentialResolution:
    """Test that credentials are resolved correctly."""

    def test_get_client_with_credentials(self):
        """Should use CredentialStoreAdapter when provided."""
        creds = MagicMock()
        creds.get.side_effect = lambda k: {
            "twilio_account_sid": "AC123",
            "twilio_auth_token": "token123"
        }[k]

        with patch("twilio.rest.Client") as mock_client:
            _get_client(creds)
            mock_client.assert_called_once_with("AC123", "token123")

    def test_get_client_with_env_vars(self, monkeypatch):
        """Should fall back to environment variables."""
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC456")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token456")

        with patch("twilio.rest.Client") as mock_client:
            _get_client(credentials=None)
            mock_client.assert_called_once_with("AC456", "token456")

    def test_missing_credentials_raises_error(self, monkeypatch):
        """Should raise ValueError when credentials missing."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)

        with patch("twilio.rest.Client"):
            with pytest.raises(ValueError, match="Missing TWILIO"):
                _get_client(credentials=None)

    def test_get_from_number_with_credentials(self):
        """Should use CredentialStoreAdapter when provided."""
        creds = MagicMock()
        creds.get.return_value = "+155512xxxxx"

        result = _get_from_number(creds)

        assert result == "+155512xxxxx"
        creds.get.assert_called_once_with("twilio_from_number")

    def test_get_from_number_with_env_var(self, monkeypatch):
        """Should fall back to environment variable."""
        monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15559876543")

        result = _get_from_number(credentials=None)

        assert result == "+15559876543"


class TestTools:
    """Test that tools work correctly."""

    def setup_method(self):
        """Setup mocks."""
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn

        self.cred = MagicMock()
        self.cred.get.side_effect = lambda k: {
            "twilio_account_sid": "AC123",
            "twilio_auth_token": "token",
            "twilio_from_number": "+155512xxxxx"
        }.get(k)

        register_tools(self.mcp, credentials=self.cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("twilio.rest.Client")
    def test_send_sms_success(self, mock_client_cls):
        """Should send SMS successfully."""
        mock_client = MagicMock()
        mock_msg = MagicMock(sid="SM123", status="queued")
        mock_client.messages.create.return_value = mock_msg
        mock_client_cls.return_value = mock_client

        result = self._fn("send_sms")(to="+15559876543", body="Test")

        assert result["sid"] == "SM123"
        assert result["status"] == "queued"
        mock_client.messages.create.assert_called_once()

    @patch("twilio.rest.Client")
    def test_send_whatsapp_adds_prefix(self, mock_client_cls):
        """Should add whatsapp: prefix."""
        mock_client = MagicMock()
        mock_msg = MagicMock(sid="SM456")
        mock_client.messages.create.return_value = mock_msg
        mock_client_cls.return_value = mock_client

        result = self._fn("send_whatsapp")(to="+15559876543", body="Test")

        call_args = mock_client.messages.create.call_args.kwargs
        assert call_args["to"] == "whatsapp:+15559876543"
        assert call_args["from_"] == "whatsapp:+155512xxxxx"
        assert result["to"] == "whatsapp:+15559876543"

    @patch("twilio.rest.Client")
    def test_fetch_history(self, mock_client_cls):
        """Should fetch message history."""
        mock_client = MagicMock()
        mock_client.messages.list.return_value = []
        mock_client_cls.return_value = mock_client

        result = self._fn("fetch_history")(limit=10)

        assert "messages" in result
        mock_client.messages.list.assert_called_once_with(limit=10, to=None)

    @patch("twilio.rest.Client")
    def test_validate_number(self, mock_client_cls):
        """Should validate phone number."""
        mock_client = MagicMock()
        mock_info = MagicMock(valid=True, phone_number="+155512xxxxx", country_code="US")
        mock_client.lookups.v2.phone_numbers.return_value.fetch.return_value = mock_info
        mock_client_cls.return_value = mock_client

        result = self._fn("validate_number")(phone_number="+155512xxxxx")

        assert result["valid"] is True
        assert result["formatted"] == "+155512xxxxx"

    @patch("twilio.rest.Client")
    def test_error_without_credentials(self, mock_client_cls):
        """Should return error dict when no credentials."""
        mcp = MagicMock()
        fns = []
        mcp.tool.return_value = lambda fn: fns.append(fn) or fn

        with patch.dict("os.environ", {}, clear=True):
            register_tools(mcp, credentials=None)
            send_sms = next(f for f in fns if f.__name__ == "send_sms")
            result = send_sms(to="+1234", body="Test")

            assert "error" in result
            assert "Missing TWILIO" in result["error"]
