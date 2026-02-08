"""
Support-related credential specifications.
"""

from .base import CredentialSpec

SUPPORT_CREDENTIALS = {
    "zendesk": CredentialSpec(
        env_var="ZENDESK_API_TOKEN",
        tools=[
            "zendesk_ticket_search",
            "zendesk_ticket_get",
            "zendesk_ticket_update",
            "zendesk_health_check",
        ],
        description="Zendesk API Token. Format: your_email/token:your_token",
        help_url="https://developer.zendesk.com/api-reference/ticketing/introduction/#api-token",
    ),
    "zendesk_subdomain": CredentialSpec(
        env_var="ZENDESK_SUBDOMAIN",
        tools=[
            "zendesk_ticket_search",
            "zendesk_ticket_get",
            "zendesk_ticket_update",
            "zendesk_health_check",
        ],
        description="Zendesk subdomain (e.g., 'adenhq' for adenhq.zendesk.com)",
        required=True,
    ),
    "zendesk_email": CredentialSpec(
        env_var="ZENDESK_EMAIL",
        tools=[
            "zendesk_ticket_search",
            "zendesk_ticket_get",
            "zendesk_ticket_update",
            "zendesk_health_check",
        ],
        description="Zendesk user email associated with the API token",
        required=True,
    ),
}
