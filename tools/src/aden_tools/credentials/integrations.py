"""
Integration-related credential specifications (News, Memory).
"""

from .base import CredentialSpec

INTEGRATIONS_CREDENTIALS = {
    "memori": CredentialSpec(
        env_var="MEMORI_API_KEY",
        tools=[
            "memori_add",
            "memori_recall",
            "memori_delete",
            "memori_health_check",
        ],
        description="API Key for Memori.ai (Persistent Memory Layer).",
        help_url="https://memorilabs.ai/docs",
    ),
}
