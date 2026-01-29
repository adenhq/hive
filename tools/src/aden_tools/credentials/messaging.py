"""
Messaging platform credentials.

Credentials for Slack and Discord integrations.
"""
from .base import CredentialSpec

MESSAGING_CREDENTIALS = {
    "slack": CredentialSpec(
        env_var="SLACK_BOT_TOKEN",
        tools=[
            "messaging_send",
            "messaging_read",
            "messaging_react",
            "messaging_upload",
            "messaging_list_channels",
            "messaging_validate",
        ],
        required=False,  # Optional - only needed if using Slack
        help_url="https://api.slack.com/apps",
        description="Slack Bot Token (xoxb-...) for Slack integration. "
                    "Required scopes: chat:write, channels:history, reactions:write, "
                    "files:write, channels:read",
    ),
    "discord_webhook": CredentialSpec(
        env_var="DISCORD_WEBHOOK_URL",
        tools=[
            "messaging_send",
            "messaging_upload",
            "messaging_validate",
        ],
        required=False,  # Optional - only needed if using Discord
        help_url="https://support.discord.com/hc/en-us/articles/228383668",
        description="Discord Webhook URL for sending messages. "
                    "Create in Server Settings > Integrations > Webhooks",
    ),
}
