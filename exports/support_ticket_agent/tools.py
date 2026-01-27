"""Tools for the support ticket agent."""

from framework.runner.tool_registry import tool


@tool
def parse_ticket_content(ticket_content: str, customer_id: str, ticket_id: str) -> dict:
    """Parse ticket content and determine priority."""
    # Simple priority logic based on keywords
    content_lower = ticket_content.lower()

    if any(word in content_lower for word in ["urgent", "emergency", "critical", "down"]):
        priority = "high"
    elif any(word in content_lower for word in ["bug", "error", "issue", "problem"]):
        priority = "medium"
    else:
        priority = "low"

    return {
        "parsed_content": ticket_content,
        "priority": priority
    }