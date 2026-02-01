"""
Airtable credential specifications.

Provides credential specifications for Airtable API access.
Supports Personal Access Token authentication.
"""

from .base import CredentialSpec

AIRTABLE_CREDENTIALS = {
    "airtable_api_key": CredentialSpec(
        env_var="AIRTABLE_API_KEY",
        tools=[
            "airtable_list_bases",
            "airtable_list_tables",
            "airtable_list_records",
            "airtable_create_record",
            "airtable_update_record",
        ],
        required=True,
        description=(
            "Personal Access Token for Airtable API. "
            "Required for all Airtable operations."
        ),
        help_url="https://airtable.com/create/tokens",
    ),
}
