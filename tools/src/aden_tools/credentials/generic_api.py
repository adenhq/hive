"""
Generic API connector credentials.

Provides a single, reusable credential entry for calling arbitrary REST APIs.
Users may configure multiple instances for different target APIs.
"""

from .base import CredentialSpec

GENERIC_API_CREDENTIALS = {
    "generic_api": CredentialSpec(
        env_var="GENERIC_API_TOKEN",
        tools=[
            "generic_api_get",
            "generic_api_post",
            "generic_api_request",
        ],
        node_types=[],
        required=True,
        startup_required=False,
        help_url="",
        description=(
            "API token for the Generic API Connector. "
            "Supports bearer tokens, API keys, basic auth credentials, "
            "and custom header values depending on the target API."
        ),
        # Auth method support
        direct_api_key_supported=True,
        api_key_instructions=(
            "To configure a Generic API credential:\n"
            "1. Navigate to your target API's developer dashboard or settings\n"
            "2. Generate a new API key, access token, or service credential\n"
            "3. Configure required permissions/scopes for your use case\n"
            "4. Copy the credential value\n"
            "5. Set it as the GENERIC_API_TOKEN environment variable\n"
            "   or add it to Hive's credential store"
        ),
        # Health check — user-configurable; no default endpoint.
        health_check_endpoint="",
        health_check_method="GET",
        # Credential store mapping
        credential_id="generic_api",
        credential_key="api_token",
    ),
}
