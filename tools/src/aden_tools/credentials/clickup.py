"""
ClickUp tool credentials.

Contains credentials for ClickUp workspace and task API integration.
"""

from .base import CredentialSpec

CLICKUP_CREDENTIALS = {
    "clickup": CredentialSpec(
        env_var="CLICKUP_API_TOKEN",
        tools=[
            "clickup_list_workspaces",
            "clickup_list_spaces",
            "clickup_list_lists",
            "clickup_list_tasks",
            "clickup_get_task",
            "clickup_create_task",
            "clickup_update_task",
            "clickup_add_task_comment",
        ],
        required=True,
        startup_required=False,
        help_url="https://developer.clickup.com/docs/authentication",
        description="ClickUp personal API token for workspace and task operations",
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="""To get a ClickUp API token:
1. Sign in to ClickUp
2. Open your profile and go to Settings > Apps
3. Generate a personal API token
4. Copy the token and store it securely""",
        health_check_endpoint="https://api.clickup.com/api/v2/team",
        health_check_method="GET",
        credential_id="clickup",
        credential_key="api_token",
    ),
}
