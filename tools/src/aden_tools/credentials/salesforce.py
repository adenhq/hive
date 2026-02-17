"""
Salesforce credential specifications.
"""

from __future__ import annotations

from .base import CredentialSpec

SALESFORCE_CREDENTIALS = {
    "salesforce_instance_url": CredentialSpec(
        env_var="SALESFORCE_INSTANCE_URL",
        description="Salesforce instance URL (e.g., https://na1.salesforce.com)",
        required=True,
        tools=[
            "salesforce_query",
            "salesforce_create_record",
            "salesforce_update_record",
            "salesforce_get_record",
            "salesforce_describe_object",
            "salesforce_search_leads",
            "salesforce_search_contacts",
            "salesforce_search_opportunities",
        ],
    ),
    "salesforce_access_token": CredentialSpec(
        env_var="SALESFORCE_ACCESS_TOKEN",
        description="Salesforce OAuth2 access token",
        required=True,
        tools=[
            "salesforce_query",
            "salesforce_create_record",
            "salesforce_update_record",
            "salesforce_get_record",
            "salesforce_describe_object",
            "salesforce_search_leads",
            "salesforce_search_contacts",
            "salesforce_search_opportunities",
        ],
    ),
}
