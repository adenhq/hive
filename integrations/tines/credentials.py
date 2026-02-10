import os
from typing import Optional

class TinesCredentials:
    def __init__(
        self,
        api_token: str,
        tenant: str,
        base_url: Optional[str] = None
    ):
        self.api_token = api_token
        self.tenant = tenant
        self.base_url = base_url or f"https://{tenant}.tines.com"
    
    @classmethod
    def from_env(cls) -> 'TinesCredentials':
        return cls(
            api_token=os.getenv('TINES_API_TOKEN'),
            tenant=os.getenv('TINES_TENANT')
        )