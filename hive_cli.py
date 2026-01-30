"""
Hive Interactive CLI - Production Ready
========================================
Interactive command-line interface for Hive agent automation.

Features:
- Menu-driven interface
- Automatic agent selection and execution
- Integration with Jira, Slack, CRM, Tickets
- Real-time task execution with LLM reasoning

Run with:
    cd c:\\Users\\M.S.Seshashayanan\\Desktop\\Aden\\hive
    set HTTPS_PROXY=
    python hive_cli.py
"""
import os
import sys
import asyncio
from pathlib import Path

# Clear proxy settings
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent / "tools" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "core" / "src"))

from fastmcp import FastMCP
from aden_tools.tools import register_all_tools
from framework.llm.litellm import LiteLLMProvider
from framework.graph import Goal, NodeSpec, EdgeSpec, GraphSpec
from framework.graph.executor import GraphExecutor
from framework.runtime.core import Runtime


class HiveCLI:
    """Interactive CLI for Hive agent automation."""
    
    def __init__(self):
        self.mcp = FastMCP("hive-cli")
        self.tools = register_all_tools(self.mcp)
        self.llm = None
        self.runtime = None
        
    def get_tool(self, name):
        """Get tool function by name."""
        return self.mcp._tool_manager._tools[name].fn
    
    def initialize_llm(self):
        """Initialize LLM provider."""
        api_key = os.environ.get("CEREBRAS_API_KEY")
        if not api_key:
            print("[WARN] CEREBRAS_API_KEY not set. Agent automation disabled.")
            print("       Set with: set CEREBRAS_API_KEY=your-key-here")
            return False
        
        try:
            self.llm = LiteLLMProvider(
                model="cerebras/llama-3.3-70b",
                api_key=api_key,
            )
            self.runtime = Runtime()
            print("[OK] LLM initialized: cerebras/llama-3.3-70b")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to initialize LLM: {e}")
            return False
    
    def show_banner(self):
        """Display welcome banner."""
        print("=" * 70)
        print("HIVE INTERACTIVE CLI - Production Ready")
        print("=" * 70)
        print(f"Tools available: {len(self.tools)}")
        print()
    
    def show_menu(self):
        """Display main menu."""
        print("\n" + "=" * 70)
        print("MAIN MENU - What would you like to do?")
        print("=" * 70)
        print()
        print("  1. Create a Support Ticket")
        print("  2. Send a Notification")
        print("  3. Manage CRM Contact")
        print("  4. Sync with Jira")
        print("  5. Send Slack Message")
        print("  6. Check System Status")
        print("  7. Run Custom Agent Task")
        print("  0. Exit")
        print()
    
    async def create_ticket_flow(self):
        """Interactive ticket creation with agent assistance."""
        print("\n" + "-" * 70)
        print("CREATE SUPPORT TICKET")
        print("-" * 70)
        print()
        
        # Gather input
        title = input("Ticket Title: ").strip()
        if not title:
            print("[ERROR] Title is required")
            return
        
        description = input("Description: ").strip()
        priority = input("Priority (low/medium/high/critical) [medium]: ").strip() or "medium"
        category = input("Category [support]: ").strip() or "support"
        
        print("\n[*] Creating ticket...")
        
        # Create ticket using tool
        result = self.get_tool("create_ticket")(
            title=title,
            description=description,
            priority=priority,
            category=category
        )
        
        if result.get("success"):
            ticket_id = result.get("ticket_id")
            print(f"\n[OK] Ticket created successfully!")
            print(f"     ID: {ticket_id}")
            print(f"     Status: {result.get('ticket', {}).get('status', 'open')}")
            print(f"     Priority: {priority}")
            
            # Ask if they want to notify via Slack
            notify = input("\nSend Slack notification? (y/n) [n]: ").strip().lower()
            if notify == 'y':
                await self.send_slack_notification(ticket_id, title, priority)
        else:
            print(f"\n[ERROR] {result.get('error', 'Failed to create ticket')}")
    
    async def send_slack_notification(self, ticket_id, title, priority):
        """Send Slack notification about a ticket."""
        print("\n[*] Checking Slack connection...")
        
        status = self.get_tool("slack_test_connection")()
        if not status.get("connected"):
            print(f"[ERROR] Slack not connected: {status.get('error')}")
            return
        
        print(f"[OK] Connected to Slack team: {status.get('team')}")
        
        # List channels
        channels = self.get_tool("slack_list_channels")(limit=10)
        if not channels.get("success") or not channels.get("channels"):
            print("[WARN] No channels available")
            return
        
        # Find a channel we're a member of
        target_channel = None
        for ch in channels.get("channels", []):
            if ch.get("is_member"):
                target_channel = ch
                break
        
        if not target_channel:
            print("[WARN] Not a member of any channels")
            return
        
        print(f"[*] Sending to #{target_channel.get('name')}...")
        
        # Send notification
        result = self.get_tool("slack_send_rich_message")(
            channel=target_channel["id"],
            title=f"New Support Ticket: {ticket_id}",
            message=f"*Title:* {title}\n*Priority:* {priority.upper()}",
            color="#ff9900" if priority == "high" else "#36a64f",
            fields=[
                {"title": "Ticket ID", "value": ticket_id, "short": True},
                {"title": "Priority", "value": priority.upper(), "short": True},
            ]
        )
        
        if result.get("delivered"):
            print(f"[OK] Notification sent to #{target_channel.get('name')}")
        else:
            print(f"[ERROR] {result.get('error', 'Failed to send')}")
    
    def send_notification_flow(self):
        """Send a notification."""
        print("\n" + "-" * 70)
        print("SEND NOTIFICATION")
        print("-" * 70)
        print()
        
        recipient = input("Recipient (email/phone/slack): ").strip()
        message = input("Message: ").strip()
        
        if not recipient or not message:
            print("[ERROR] Recipient and message are required")
            return
        
        print("\n[*] Sending notification...")
        
        result = self.get_tool("send_notification")(
            recipient=recipient,
            message=message,
            channel="email"
        )
        
        if result.get("delivered"):
            print(f"\n[OK] Notification sent!")
            print(f"     ID: {result.get('notification_id')}")
            print(f"     Recipient: {recipient}")
        else:
            print(f"\n[ERROR] {result.get('error', 'Failed to send')}")
    
    def manage_crm_flow(self):
        """Manage CRM contacts."""
        print("\n" + "-" * 70)
        print("MANAGE CRM CONTACT")
        print("-" * 70)
        print()
        print("  1. Create new contact")
        print("  2. Search contacts")
        print("  3. Update contact")
        print()
        
        choice = input("Choose action: ").strip()
        
        if choice == "1":
            self.create_contact()
        elif choice == "2":
            self.search_contacts()
        elif choice == "3":
            self.update_contact()
        else:
            print("[ERROR] Invalid choice")
    
    def create_contact(self):
        """Create a new CRM contact."""
        print("\n[*] Create New Contact")
        name = input("Name: ").strip()
        email = input("Email: ").strip()
        company = input("Company: ").strip()
        phone = input("Phone: ").strip()
        
        if not name:
            print("[ERROR] Name is required")
            return
        
        result = self.get_tool("crm_create_contact")(
            name=name,
            email=email,
            company=company,
            phone=phone,
            tags=["cli-created"]
        )
        
        if result.get("success"):
            print(f"\n[OK] Contact created: {result.get('contact_id')}")
        else:
            print(f"\n[ERROR] {result.get('error')}")
    
    def search_contacts(self):
        """Search CRM contacts."""
        print("\n[*] Search Contacts")
        query = input("Search query (name/email/company): ").strip()
        
        result = self.get_tool("crm_search_contacts")(query=query, limit=10)
        
        if result.get("success"):
            contacts = result.get("contacts", [])
            print(f"\n[OK] Found {len(contacts)} contact(s):")
            for contact in contacts:
                print(f"     - {contact.get('name')} ({contact.get('email')}) - {contact.get('company', 'N/A')}")
        else:
            print(f"\n[ERROR] {result.get('error')}")
    
    def update_contact(self):
        """Update a CRM contact."""
        print("\n[*] Update Contact")
        contact_id = input("Contact ID: ").strip()
        
        if not contact_id:
            print("[ERROR] Contact ID is required")
            return
        
        print("Leave blank to keep current value")
        name = input("New name: ").strip() or None
        email = input("New email: ").strip() or None
        company = input("New company: ").strip() or None
        
        result = self.get_tool("crm_update_contact")(
            contact_id=contact_id,
            name=name,
            email=email,
            company=company
        )
        
        if result.get("success"):
            print(f"\n[OK] Contact updated: {contact_id}")
        else:
            print(f"\n[ERROR] {result.get('error')}")
    
    def sync_jira_flow(self):
        """Sync with Jira."""
        print("\n" + "-" * 70)
        print("SYNC WITH JIRA")
        print("-" * 70)
        print()
        
        # Test connection
        print("[*] Testing Jira connection...")
        status = self.get_tool("jira_test_connection")()
        
        if not status.get("connected"):
            print(f"[ERROR] Jira not connected: {status.get('error')}")
            print("\nPlease check:")
            print("  - JIRA_URL is set correctly")
            print("  - JIRA_EMAIL matches your API token owner")
            print("  - JIRA_API_TOKEN is valid")
            return
        
        print(f"[OK] Connected as: {status.get('user', {}).get('display_name')}")
        
        # List projects
        print("\n[*] Fetching projects...")
        projects = self.get_tool("jira_list_projects")(limit=10)
        
        if not projects.get("success"):
            print(f"[ERROR] {projects.get('error')}")
            return
        
        print(f"\n[OK] Found {projects.get('count')} project(s):")
        for proj in projects.get("projects", []):
            print(f"     - {proj.get('key')}: {proj.get('name')}")
        
        # Ask to sync
        project_key = input("\nEnter project key to sync (or press Enter to skip): ").strip()
        if project_key:
            print(f"\n[*] Syncing issues from {project_key}...")
            result = self.get_tool("jira_sync_to_local")(project_key=project_key, limit=20)
            
            if result.get("success"):
                print(f"\n[OK] Sync complete!")
                print(f"     Imported: {result.get('imported', 0)}")
                print(f"     Updated: {result.get('updated', 0)}")
            else:
                print(f"\n[ERROR] {result.get('error')}")
    
    def check_status(self):
        """Check system status."""
        print("\n" + "-" * 70)
        print("SYSTEM STATUS")
        print("-" * 70)
        print()
        
        # Check Slack
        print("[*] Slack...")
        slack = self.get_tool("slack_test_connection")()
        if slack.get("connected"):
            print(f"    [OK] Connected to {slack.get('team')}")
        else:
            print(f"    [--] Not connected")
        
        # Check Jira
        print("[*] Jira...")
        jira = self.get_tool("jira_test_connection")()
        if jira.get("connected"):
            print(f"    [OK] Connected as {jira.get('user', {}).get('display_name')}")
        else:
            print(f"    [--] Not connected: {jira.get('error', 'Unknown')[:50]}")
        
        # Check Salesforce
        print("[*] Salesforce...")
        sf = self.get_tool("salesforce_test_connection")()
        if sf.get("connected"):
            print(f"    [OK] Connected to {sf.get('instance_url')}")
        else:
            print(f"    [--] Not connected: {sf.get('error', 'Unknown')[:50]}")
        
        # Check tickets
        print("[*] Tickets...")
        summary = self.get_tool("get_ticket_summary")()
        print(f"    Total: {summary.get('total', 0)}")
        print(f"    By status: {summary.get('by_status', {})}")
    
    async def run_custom_agent(self):
        """Run a custom agent task with LLM."""
        print("\n" + "-" * 70)
        print("RUN CUSTOM AGENT TASK")
        print("-" * 70)
        print()
        
        if not self.llm:
            if not self.initialize_llm():
                print("[ERROR] LLM not available. Cannot run agent tasks.")
                return
        
        task = input("Describe what you want the agent to do: ").strip()
        if not task:
            print("[ERROR] Task description is required")
            return
        
        print(f"\n[*] Agent is analyzing your request...")
        print(f"[*] Task: {task}")
        print()
        
        # Create a simple agent that uses LLM to decide what to do
        try:
            # Use LLM to generate a plan
            response = await self.llm.generate(
                prompt=f"You are a helpful assistant. The user wants to: {task}\n\nBased on available tools (create_ticket, send_notification, crm_create_contact, slack_send_message), suggest which tool to use and what parameters. Be concise.",
                max_tokens=200
            )
            
            print("[*] Agent's plan:")
            print(f"    {response}")
            print()
            
            proceed = input("Execute this plan? (y/n) [y]: ").strip().lower()
            if proceed != 'n':
                print("\n[OK] Task would be executed here (implementation pending)")
                print("     For now, please use the specific menu options above.")
        
        except Exception as e:
            print(f"[ERROR] Agent failed: {e}")
    
    async def run(self):
        """Main CLI loop."""
        self.show_banner()
        
        while True:
            self.show_menu()
            choice = input("Enter your choice: ").strip()
            
            if choice == "0":
                print("\nGoodbye!")
                break
            elif choice == "1":
                await self.create_ticket_flow()
            elif choice == "2":
                self.send_notification_flow()
            elif choice == "3":
                self.manage_crm_flow()
            elif choice == "4":
                self.sync_jira_flow()
            elif choice == "5":
                print("\n[INFO] Use option 1 to create a ticket, then choose to send Slack notification")
            elif choice == "6":
                self.check_status()
            elif choice == "7":
                await self.run_custom_agent()
            else:
                print("\n[ERROR] Invalid choice. Please try again.")


async def main():
    """Entry point."""
    cli = HiveCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
