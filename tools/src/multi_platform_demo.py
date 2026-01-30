"""
Multi-Platform Agent Demo
=========================
This script demonstrates a mock support scenario where the Hive agent:
1. Receives a customer complaint
2. Looks up customer info from CRM database
3. Creates a support ticket
4. Sends a Slack notification to the support team

Run with:
    cd c:\\Users\\M.S.Seshashayanan\\Desktop\\Aden\\hive
    set HTTPS_PROXY=
    python tools\\src\\multi_platform_demo.py
"""
import os
import sys

# Clear proxy settings that cause issues
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Fix path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastmcp import FastMCP
from aden_tools.tools import register_all_tools
from aden_tools.db import Database

# Initialize MCP with all tools
mcp = FastMCP("multi-platform-demo")
tools = register_all_tools(mcp)


def get_tool(name):
    """Get tool function by name."""
    return mcp._tool_manager._tools[name].fn


print("=" * 70)
print("MULTI-PLATFORM AGENT DEMO")
print("=" * 70)
print("Tools available: %d" % len(tools))
print()

# ============================================================================
# MOCK SCENARIO: High-Priority Customer Complaint
# ============================================================================
print("=" * 70)
print("SCENARIO: High-Priority Customer Complaint")
print("=" * 70)
print()

# Mock input data (would come from email, chat, etc.)
mock_complaint = {
    "customer_email": "john.smith@acmecorp.com",
    "customer_name": "John Smith",
    "company": "Acme Corporation",
    "subject": "Production System Down",
    "description": "Our production environment has been experiencing critical errors since 10:30 AM. Multiple services are affected and we're losing revenue. This is impacting our 1000+ users.",
    "priority": "critical"
}

print("   Customer: %s (%s)" % (mock_complaint['customer_name'], mock_complaint['customer_email']))
print("   Company: %s" % mock_complaint['company'])
print("   Issue: %s" % mock_complaint['subject'])
print("   Priority: %s" % mock_complaint['priority'].upper())
print()


# ============================================================================
# STEP 1: Look up customer in CRM
# ============================================================================
print("-" * 70)
print("STEP 1: Looking up customer in CRM...")
print("-" * 70)
print()

# Try to find existing customer using CRM tool
crm_result = get_tool("crm_search_contacts")(query=mock_complaint['customer_email'], limit=5)

customer_id = None
if crm_result.get("success") and crm_result.get("count", 0) > 0:
    customer = crm_result.get("contacts", [])[0]
    customer_id = customer.get("id")
    print("   [FOUND] Existing customer record:")
    print("           ID: %s" % customer_id)
    print("           Name: %s" % customer.get('name'))
    print("           Company: %s" % customer.get('company', 'N/A'))
else:
    # Create new customer
    print("   [NEW] Creating new customer record...")
    create_result = get_tool("crm_create_contact")(
        name=mock_complaint["customer_name"],
        email=mock_complaint["customer_email"],
        company=mock_complaint["company"],
        tags=["vip", "enterprise"]
    )
    if create_result.get("success"):
        customer_id = create_result.get("contact_id")
        print("   [OK] Created customer: %s" % customer_id)
    else:
        print("   [ERROR] %s" % create_result.get("error", "Unknown error"))
print()


# ============================================================================
# STEP 2: Create support ticket
# ============================================================================
print("-" * 70)
print("STEP 2: Creating support ticket...")
print("-" * 70)
print()

ticket_result = get_tool("create_ticket")(
    title="[CRITICAL] %s - %s" % (mock_complaint['subject'], mock_complaint['company']),
    description=mock_complaint["description"],
    priority="critical",
    category="production_issue",
    assignee="on-call-engineer"
)

ticket_id = None
if ticket_result.get("success"):
    ticket_id = ticket_result.get("ticket_id")
    print("   [OK] Ticket created:")
    print("        ID: %s" % ticket_id)
    ticket_data = ticket_result.get("ticket", {})
    print("        Status: %s" % ticket_data.get('status', 'open'))
    print("        Priority: %s" % ticket_data.get('priority', 'critical'))
else:
    print("   [ERROR] %s" % ticket_result.get("error", "Unknown error"))
print()


# ============================================================================
# STEP 3: Log activity in CRM
# ============================================================================
print("-" * 70)
print("STEP 3: Logging activity in CRM...")
print("-" * 70)
print()

if customer_id:
    activity_result = get_tool("crm_log_activity")(
        contact_id=customer_id,
        activity_type="note",
        description="Created critical ticket %s for production issue" % ticket_id
    )
    if activity_result.get("success"):
        activity = activity_result.get("activity", {})
        print("   [OK] Activity logged: %s" % activity.get('id'))
    else:
        print("   [SKIP] %s" % activity_result.get("error", "Could not log activity"))
else:
    print("   [SKIP] No customer ID to log activity against")
print()


# ============================================================================
# STEP 4: Send Slack notification to support team
# ============================================================================
print("-" * 70)
print("STEP 4: Sending Slack notification to support team...")
print("-" * 70)
print()

# Test Slack connection first
slack_status = get_tool("slack_test_connection")()

if slack_status.get("connected"):
    print("   [OK] Slack connected: %s" % slack_status.get('team'))
    
    # List channels to find general or alerts channel
    channels = get_tool("slack_list_channels")(limit=10)
    
    if channels.get("success") and channels.get("channels"):
        # Find a suitable channel (prefer #general or any private channel we're a member of)
        target_channel = None
        for ch in channels.get("channels", []):
            if ch.get("is_member"):
                target_channel = ch
                break
        
        if target_channel:
            print("   [OK] Target channel: #%s" % target_channel.get('name'))
            
            # Send rich notification
            message_result = get_tool("slack_send_rich_message")(
                channel=target_channel["id"],
                title="[!] Critical Support Ticket: %s" % (ticket_id or "NEW"),
                message="*Customer:* %s (%s)\n\n*Issue:* %s\n\n*Description:* %s..." % (
                    mock_complaint['customer_name'],
                    mock_complaint['company'],
                    mock_complaint['subject'],
                    mock_complaint['description'][:200]
                ),
                color="#ff0000",
                fields=[
                    {"title": "Priority", "value": "CRITICAL", "short": True},
                    {"title": "Status", "value": "Open", "short": True},
                    {"title": "Assignee", "value": "On-Call Engineer", "short": True},
                    {"title": "Ticket", "value": ticket_id or "NEW", "short": True},
                ],
                footer="Aden Hive Agent"
            )
            
            if message_result.get("delivered"):
                print("   [OK] Message delivered to #%s" % target_channel.get('name'))
            else:
                print("   [WARN] Message delivery failed: %s" % message_result.get('error', 'Unknown'))
        else:
            print("   [SKIP] No channels available for bot")
    else:
        print("   [SKIP] Could not list channels: %s" % channels.get('error', 'Unknown'))
else:
    print("   [SKIP] Slack not connected: %s" % slack_status.get('error', 'Unknown'))
print()


# ============================================================================
# STEP 5: Generate ticket summary
# ============================================================================
print("-" * 70)
print("STEP 5: Generating summary...")
print("-" * 70)
print()

summary = get_tool("get_ticket_summary")()
print("   Total tickets: %d" % summary.get('total', 0))
print("   By status: %s" % summary.get('by_status', {}))
print("   By priority: %s" % summary.get('by_priority', {}))
print()


# ============================================================================
# DEMO COMPLETE
# ============================================================================
print("=" * 70)
print("DEMO COMPLETE")
print("=" * 70)
print()
print("The agent successfully:")
print("  1. %s Looked up customer in CRM database" % ("[OK]" if customer_id else "[--]"))
print("  2. %s Created a critical support ticket" % ("[OK]" if ticket_id else "[--]"))
print("  3. %s Logged activity against the customer record" % ("[OK]" if customer_id else "[--]"))
print("  4. %s Sent Slack notification to support team" % ("[OK]" if slack_status.get('connected') else "[--]"))
print("  5. [OK] Generated ticket summary")
print()
print("Next steps:")
print("  - Set JIRA_EMAIL in .env to enable Jira integration")
print("  - Configure Salesforce Connected App for SF integration")
print("=" * 70)
