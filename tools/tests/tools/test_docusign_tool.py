import unittest
from unittest.mock import MagicMock, patch
from aden_tools.tools.docusign_tool.docusign_tool import _DocuSignClient, register_tools

class TestDocuSignTool(unittest.TestCase):

    def setUp(self):
        self.mock_client = _DocuSignClient(
            access_token="fake_token",
            account_id="fake_account",
            base_uri="https://demo.docusign.net"
        )

    @patch("httpx.post")
    def test_create_envelope_success(self, mock_post):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "envelopeId": "env-123",
            "status": "sent",
            "statusDateTime": "2023-10-27T10:00:00Z",
            "uri": "/envelopes/env-123"
        }
        mock_post.return_value = mock_response

        # Call method
        result = self.mock_client.create_envelope(
            template_id="tpl-456",
            signer_email="test@example.com",
            signer_name="Test User",
            email_subject="Sign this",
            tab_values={"ClientName": "Acme Corp"}
        )

        # Verify output
        self.assertEqual(result["envelopeId"], "env-123")
        self.assertEqual(result["status"], "sent")

        # Verify request payload
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["templateId"], "tpl-456")
        self.assertEqual(payload["emailSubject"], "Sign this")
        self.assertEqual(payload["templateRoles"][0]["email"], "test@example.com")
        self.assertEqual(payload["templateRoles"][0]["roleName"], "Signer")
        self.assertEqual(payload["templateRoles"][0]["tabs"]["textTabs"][0]["tabLabel"], "ClientName")
        self.assertEqual(payload["templateRoles"][0]["tabs"]["textTabs"][0]["value"], "Acme Corp")
        # Check endpoint construction
        self.assertIn("/accounts/fake_account/envelopes", args[0])
    @patch("httpx.post")
    def test_create_envelope_custom_role(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"envelopeId": "env-custom"}
        mock_post.return_value = mock_response

        self.mock_client.create_envelope(
            template_id="tpl",
            signer_email="e",
            signer_name="n",
            role_name="Buyer"
        )

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["templateRoles"][0]["roleName"], "Buyer")

    @patch("httpx.get")
    def test_get_envelope_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "envelopeId": "env-123",
            "status": "completed",
            "sentDateTime": "2023-10-26T10:00:00Z",
            "completedDateTime": "2023-10-27T10:00:00Z"
        }
        mock_get.return_value = mock_response

        result = self.mock_client.get_envelope("env-123")

        self.assertEqual(result["status"], "completed")
        self.assertIn("/envelopes/env-123", mock_get.call_args[0][0])

    @patch("httpx.get")
    def test_list_envelopes(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resultSetSize": "2",
            "envelopes": [
                {"envelopeId": "env-1", "status": "sent"},
                {"envelopeId": "env-2", "status": "completed"}
            ]
        }
        mock_get.return_value = mock_response

        result = self.mock_client.list_envelopes(limit=10, status="sent")

        self.assertEqual(len(result["envelopes"]), 2)
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["count"], "10")
        self.assertEqual(kwargs["params"]["status"], "sent")
        # Check default date is present
        self.assertIn("from_date", kwargs["params"])

    @patch("httpx.get")
    def test_download_document(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_response.content = b"%PDF-1.4 mock content"
        mock_get.return_value = mock_response

        result = self.mock_client.get_document("env-123")

        self.assertEqual(result["envelopeId"], "env-123")
        self.assertEqual(result["mime_type"], "application/pdf")
        # Ensure base64 encoding happened
        import base64
        decoded = base64.b64decode(result["content_base64"])
        self.assertEqual(decoded, b"%PDF-1.4 mock content")

    @patch("httpx.post")
    def test_error_handling_401(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        result = self.mock_client.create_envelope("tpl", "e", "n")
        self.assertEqual(result["error"], "Invalid or expired DocuSign access token")

if __name__ == "__main__":
    unittest.main()
