"""Docker Hub tool credentials.

Contains credentials for Docker Hub integration.
"""

from .base import CredentialSpec

DOCKERHUB_CREDENTIALS = {
    "docker_hub": CredentialSpec(
        env_var="DOCKER_HUB_TOKEN",
        tools=[
            "dockerhub_list_repositories",
            "dockerhub_list_tags",
            "dockerhub_get_tag_metadata",
        ],
        required=True,
        startup_required=False,
        help_url="https://hub.docker.com/settings/security",
        description="Docker Hub Access Token",
        direct_api_key_supported=True,
        api_key_instructions="""To get a Docker Hub Personal Access Token:
1. Log in to Docker Hub.
2. Go to Account Settings > Security.
3. Click 'New Access Token'.
4. Description: 'Hive Agent'.
5. Access permissions: 'Read-only' is sufficient for listing repos and tags.
6. Click 'Generate' and copy the token.""",
        # Health check configuration
        health_check_endpoint="https://hub.docker.com/v2/user/",
        health_check_method="GET",
        # Credential store mapping
        credential_id="docker_hub",
        credential_key="access_token",
    ),
}
