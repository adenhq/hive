"""
Aden Tools - Tool implementations for FastMCP.

Usage:
    from fastmcp import FastMCP
    from aden_tools.tools import register_all_tools
    from aden_tools.credentials import CredentialManager

    mcp = FastMCP("my-server")
    credentials = CredentialManager()
    register_all_tools(mcp, credentials=credentials)
"""
from typing import List, Optional, TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialManager

# Import register_tools from each tool module
from .example_tool import register_tools as register_example
from .web_search_tool import register_tools as register_web_search
from .web_scrape_tool import register_tools as register_web_scrape
from .pdf_read_tool import register_tools as register_pdf_read

# Import Action/Command tools (MCP Integration)
from .notification_tool import register_tools as register_notification
from .crm_tool import register_tools as register_crm
from .ticket_tool import register_tools as register_ticket

# Import External Service Integrations
from .jira_tool import register_tools as register_jira
from .slack_tool import register_tools as register_slack
from .salesforce_tool import register_tools as register_salesforce

# Import file system toolkits
from .file_system_toolkits.view_file import register_tools as register_view_file
from .file_system_toolkits.write_to_file import register_tools as register_write_to_file
from .file_system_toolkits.list_dir import register_tools as register_list_dir
from .file_system_toolkits.replace_file_content import register_tools as register_replace_file_content
from .file_system_toolkits.apply_diff import register_tools as register_apply_diff
from .file_system_toolkits.apply_patch import register_tools as register_apply_patch
from .file_system_toolkits.grep_search import register_tools as register_grep_search
from .file_system_toolkits.execute_command_tool import register_tools as register_execute_command


def register_all_tools(
    mcp: FastMCP,
    credentials: Optional["CredentialManager"] = None,
) -> List[str]:
    """
    Register all tools with a FastMCP server.

    Args:
        mcp: FastMCP server instance
        credentials: Optional CredentialManager for centralized credential access.
                     If not provided, tools fall back to direct os.getenv() calls.

    Returns:
        List of registered tool names
    """
    # Tools that don't need credentials
    register_example(mcp)
    register_web_scrape(mcp)
    register_pdf_read(mcp)

    # Tools that need credentials (pass credentials if provided)
    # web_search handles both credential sources internally:
    # - If credentials provided: uses credentials.get("brave_search")
    # - If credentials is None: falls back to os.getenv("BRAVE_SEARCH_API_KEY")
    register_web_search(mcp, credentials=credentials)

    # Register file system toolkits
    register_view_file(mcp)
    register_write_to_file(mcp)
    register_list_dir(mcp)
    register_replace_file_content(mcp)
    register_apply_diff(mcp)
    register_apply_patch(mcp)
    register_grep_search(mcp)
    register_execute_command(mcp)

    # Register Action/Command tools (MCP Integration)
    register_notification(mcp, credentials=credentials)
    register_crm(mcp, credentials=credentials)
    register_ticket(mcp, credentials=credentials)

    # Register External Service Integrations
    register_jira(mcp, credentials=credentials)
    register_slack(mcp, credentials=credentials)
    register_salesforce(mcp, credentials=credentials)

    return [
        "example_tool",
        "web_search",
        "web_scrape",
        "pdf_read",
        "view_file",
        "write_to_file",
        "list_dir",
        "replace_file_content",
        "apply_diff",
        "apply_patch",
        "grep_search",
        "execute_command_tool",
        # Action/Command tools
        "send_notification",
        "send_bulk_notification",
        "crm_create_contact",
        "crm_update_contact",
        "crm_get_contact",
        "crm_search_contacts",
        "crm_delete_contact",
        "crm_log_activity",
        "create_ticket",
        "update_ticket",
        "get_ticket",
        "search_tickets",
        "add_ticket_comment",
        "get_ticket_summary",
        # Jira Integration
        "jira_test_connection",
        "jira_list_projects",
        "jira_get_issues",
        "jira_get_issue",
        "jira_create_issue",
        "jira_update_issue",
        "jira_sync_to_local",
        # Slack Integration
        "slack_test_connection",
        "slack_list_channels",
        "slack_send_message",
        "slack_send_rich_message",
        # Salesforce Integration
        "salesforce_test_connection",
        "salesforce_query",
        "salesforce_get_contacts",
        "salesforce_get_opportunities",
        "salesforce_create_contact",
        "salesforce_sync_to_local",
    ]


__all__ = ["register_all_tools"]
