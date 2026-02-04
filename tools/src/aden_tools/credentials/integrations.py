"""
Integration credentials for Aden Tools.

Contains credentials for third-party integrations like Discord.
"""

from .base import CredentialSpec

INTEGRATION_CREDENTIALS = {
    "discord": CredentialSpec(
        env_var="DISCORD_BOT_TOKEN",
        tools=[
            "discord_list_channels",
            "discord_send_message",
            "discord_get_recent_messages",
        ],
        required=True,
        startup_required=False,
        help_url="https://discord.com/developers/docs/intro",
        description="Discord Bot Token for managing channels and messages",
    ),
}
