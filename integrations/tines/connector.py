import requests
from typing import Dict, Any, Optional
from .credentials import TinesCredentials

class TinesConnector:
    def __init__(self, credentials: TinesCredentials):
        self.credentials = credentials
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {credentials.api_token}',
            'Content-Type': 'application/json'
        })
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        url = f"{self.credentials.base_url}/api/v1{endpoint}"
        response = self.session.request(method, url, json=data)
        response.raise_for_status()
        return response.json()
    
    def trigger_story(self, story_id: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        """Trigger a Tines story with optional payload"""
        return self._make_request(
            'POST',
            f'/stories/{story_id}/trigger',
            data=payload
        )
    
    def get_story_status(self, story_id: str) -> Dict[str, Any]:
        """Get execution status of a story"""
        return self._make_request('GET', f'/stories/{story_id}/runs')
    
    def list_stories(self) -> Dict[str, Any]:
        """List available stories"""
        return self._make_request('GET', '/stories')
    
    def get_story_details(self, story_id: str) -> Dict[str, Any]:
        """Get details of a specific story"""
        return self._make_request('GET', f'/stories/{story_id}')