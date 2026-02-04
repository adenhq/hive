"""
Integration credentials for Aden Tools.

Contains credentials for third-party integrations like n8n.
"""

from .base import CredentialSpec

INTEGRATION_CREDENTIALS = {
    "n8n": CredentialSpec(
        env_var="N8N_API_KEY",
        tools=["n8n_trigger_workflow", "n8n_get_execution_status", "n8n_list_workflows"],
        node_types=[],
        required=False,
        startup_required=False,
        help_url="https://docs.n8n.io/api/",
        description="API key for n8n instance",
    ),
    "n8n_host": CredentialSpec(
        env_var="N8N_HOST",
        tools=["n8n_trigger_workflow", "n8n_get_execution_status", "n8n_list_workflows"],
        node_types=[],
        required=False,
        startup_required=False,
        help_url="https://docs.n8n.io/api/",
        description="Host URL for n8n instance (e.g., https://n8n.example.com)",
    ),
}
