"""
Dropbox tool credentials.

Contains credentials for Dropbox integration.
"""

from .base import CredentialSpec

DROPBOX_CREDENTIALS = {
    "dropbox": CredentialSpec(
        env_var="DROPBOX_ACCESS_TOKEN",
        tools=[
            "dropbox_upload_file",
            "dropbox_download_file",
            "dropbox_list_folder",
            "dropbox_create_shared_link",
        ],
        required=True,
        startup_required=False,
        help_url="https://www.dropbox.com/developers/apps",
        description="Dropbox API access token",
        api_key_instructions="""To get a Dropbox access token:
1. Go to https://www.dropbox.com/developers/apps
2. Click "Create app"
3. Choose "Scoped access" and "Full Dropbox" or "App folder"
4. Name your app and click "Create"
5. Under "Permissions", enable files.content.read and files.content.write
6. Generate an access token in the "Settings" tab""",
        health_check_endpoint="https://api.dropboxapi.com/2/users/get_current_account",
        health_check_method="POST",
    ),
}
