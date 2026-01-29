"""
Message formatting utilities for Slack and Discord.

Provides helpers for converting between formats and creating
rich message content.
"""
from __future__ import annotations

from typing import Any


def markdown_to_slack(text: str) -> str:
    """
    Convert common markdown to Slack mrkdwn format.
    
    Slack uses a slightly different markdown syntax:
    - Bold: **text** -> *text*
    - Italic: *text* or _text_ -> _text_
    - Strikethrough: ~~text~~ -> ~text~
    - Code blocks: ```lang -> ```
    - Links: [text](url) -> <url|text>
    
    Args:
        text: Standard markdown text
        
    Returns:
        Slack mrkdwn formatted text
    """
    import re
    
    # Convert bold: **text** -> *text*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    
    # Convert strikethrough: ~~text~~ -> ~text~
    text = re.sub(r'~~(.+?)~~', r'~\1~', text)
    
    # Convert links: [text](url) -> <url|text>
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<\2|\1>', text)
    
    return text


def markdown_to_discord(text: str) -> str:
    """
    Ensure markdown is Discord-compatible.
    
    Discord supports standard markdown, so minimal conversion needed.
    This function mainly validates and cleans the input.
    
    Args:
        text: Standard markdown text
        
    Returns:
        Discord-compatible markdown text
    """
    # Discord supports standard markdown, just return as-is
    # Could add validation or sanitization here if needed
    return text


def create_slack_blocks(
    text: str,
    header: str | None = None,
    footer: str | None = None,
    divider: bool = False,
) -> list[dict[str, Any]]:
    """
    Create Slack Block Kit blocks for rich formatting.
    
    Args:
        text: Main message text
        header: Optional header text
        footer: Optional footer/context text
        divider: Whether to add a divider after the message
        
    Returns:
        List of Slack block objects
    """
    blocks: list[dict[str, Any]] = []
    
    if header:
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header,
                "emoji": True,
            },
        })
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": markdown_to_slack(text),
        },
    })
    
    if footer:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": footer,
                }
            ],
        })
    
    if divider:
        blocks.append({"type": "divider"})
    
    return blocks


def create_discord_embed(
    title: str,
    description: str,
    color: int = 0x5865F2,
    fields: list[tuple[str, str, bool]] | None = None,
    footer: str | None = None,
    thumbnail_url: str | None = None,
) -> dict[str, Any]:
    """
    Create a Discord embed object.
    
    Args:
        title: Embed title
        description: Embed description (markdown supported)
        color: Embed color as integer
        fields: List of (name, value, inline) tuples
        footer: Footer text
        thumbnail_url: URL for thumbnail image
        
    Returns:
        Discord embed object
    """
    embed: dict[str, Any] = {
        "title": title,
        "description": markdown_to_discord(description),
        "color": color,
    }
    
    if fields:
        embed["fields"] = [
            {"name": name, "value": value, "inline": inline}
            for name, value, inline in fields
        ]
    
    if footer:
        embed["footer"] = {"text": footer}
    
    if thumbnail_url:
        embed["thumbnail"] = {"url": thumbnail_url}
    
    return embed


# Common emoji mappings between platforms
EMOJI_MAP = {
    # Slack -> Discord (mostly the same)
    "+1": "thumbsup",
    "-1": "thumbsdown",
    "white_check_mark": "white_check_mark",
    "x": "x",
    "eyes": "eyes",
    "rocket": "rocket",
    "tada": "tada",
    "fire": "fire",
    "heart": "heart",
    "star": "star",
}


def normalize_emoji(emoji: str, platform: str = "slack") -> str:
    """
    Normalize emoji name for a specific platform.
    
    Args:
        emoji: Emoji name (with or without colons)
        platform: Target platform ('slack' or 'discord')
        
    Returns:
        Normalized emoji name without colons
    """
    # Remove colons
    emoji = emoji.strip(":")
    
    # Apply mapping if exists
    if emoji in EMOJI_MAP:
        emoji = EMOJI_MAP[emoji]
    
    return emoji
