import unittest
from unittest.mock import Mock, patch, MagicMock
from integrations.tines.connector import TinesConnector
from integrations.tines.credentials import TinesCredentials


class TestTinesConnector(unittest.TestCase):
    def setUp(self):
        self.credentials = TinesCredentials(
            api_token="test_token",
            tenant="test_tenant"
        )
        self.connector = TinesConnector(self.credentials)
    
    def test_initialization(self):
        self.assertEqual(self.connector.credentials.api_token, "test_token")
        self.assertEqual(self.connector.credentials.tenant, "test_tenant")
        self.assertEqual(
            self.connector.credentials.base_url,
            "https://test_tenant.tines.com"
        )
    
    @patch('integrations.tines.connector.requests.Session')
    def test_trigger_story(self, mock_session):
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "run_123",
            "status": "running",
            "story_id": "story_456"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_session_instance = MagicMock()
        mock_session_instance.request.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Create new connector with mocked session
        connector = TinesConnector(self.credentials)
        connector.session = mock_session_instance
        
        # Test
        result = connector.trigger_story(
            story_id="story_456",
            payload={"alert_type": "suspicious_login"}
        )
        
        # Verify
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["story_id"], "story_456")
        mock_session_instance.request.assert_called_once()
    
    @patch('integrations.tines.connector.requests.Session')
    def test_get_story_status(self, mock_session):
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "runs": [
                {"id": "run_1", "status": "completed"},
                {"id": "run_2", "status": "running"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_session_instance = MagicMock()
        mock_session_instance.request.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Create new connector with mocked session
        connector = TinesConnector(self.credentials)
        connector.session = mock_session_instance
        
        # Test
        result = connector.get_story_status("story_456")
        
        # Verify
        self.assertEqual(len(result["runs"]), 2)
        self.assertEqual(result["runs"][0]["status"], "completed")
    
    @patch('integrations.tines.connector.requests.Session')
    def test_list_stories(self, mock_session):
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "stories": [
                {"id": "story_1", "name": "Phishing Response"},
                {"id": "story_2", "name": "Suspicious Login Alert"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_session_instance = MagicMock()
        mock_session_instance.request.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Create new connector with mocked session
        connector = TinesConnector(self.credentials)
        connector.session = mock_session_instance
        
        # Test
        result = connector.list_stories()
        
        # Verify
        self.assertEqual(len(result["stories"]), 2)
        self.assertEqual(result["stories"][0]["name"], "Phishing Response")
    
    def test_credentials_from_env(self):
        with patch.dict('os.environ', {
            'TINES_API_TOKEN': 'env_token',
            'TINES_TENANT': 'env_tenant'
        }):
            credentials = TinesCredentials.from_env()
            self.assertEqual(credentials.api_token, 'env_token')
            self.assertEqual(credentials.tenant, 'env_tenant')


if __name__ == '__main__':
    unittest.main()