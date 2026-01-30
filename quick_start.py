"""
Hive Quick Start - Simplified CLI
==================================
Simple command-line interface for common Hive operations.

Run with:
    python quick_start.py
"""
import os
import sys
from pathlib import Path

# Clear proxy settings
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "tools" / "src"))

from fastmcp import FastMCP
from aden_tools.tools import register_all_tools


def main():
    """Quick start menu."""
    print("=" * 70)
    print("HIVE QUICK START")
    print("=" * 70)
    
    # Initialize tools
    mcp = FastMCP("hive-quick")
    tools = register_all_tools(mcp)
    
    print(f"Tools available: {len(tools)}")
    print()
    
    def get_tool(name):
        return mcp._tool_manager._tools[name].fn
    
    while True:
        print("\n" + "=" * 70)
        print("QUICK MENU")
        print("=" * 70)
        print()
        print("  1. Create Ticket")
        print("  2. Check Status")
        print("  3. Search Contacts")
        print("  4. Test Slack")
        print("  5. Test Jira")
        print("  0. Exit")
        print()
        
        choice = input("Choose: ").strip()
        
        if choice == "0":
            print("\nGoodbye!")
            break
            
        elif choice == "1":
            # Create ticket
            print("\n--- CREATE TICKET ---")
            title = input("Title: ").strip()
            if title:
                result = get_tool("create_ticket")(
                    title=title,
                    description=input("Description: ").strip(),
                    priority=input("Priority [medium]: ").strip() or "medium"
                )
                if result.get("success"):
                    print(f"\n[OK] Created: {result.get('ticket_id')}")
                else:
                    print(f"\n[ERROR] {result.get('error')}")
        
        elif choice == "2":
            # Status check
            print("\n--- SYSTEM STATUS ---")
            
            # Slack
            slack = get_tool("slack_test_connection")()
            print(f"Slack: {'[OK] ' + slack.get('team') if slack.get('connected') else '[--] Not connected'}")
            
            # Jira
            jira = get_tool("jira_test_connection")()
            print(f"Jira:  {'[OK] Connected' if jira.get('connected') else '[--] ' + str(jira.get('error', 'Not connected'))[:40]}")
            
            # Tickets
            summary = get_tool("get_ticket_summary")()
            print(f"Tickets: {summary.get('total', 0)} total")
        
        elif choice == "3":
            # Search contacts
            print("\n--- SEARCH CONTACTS ---")
            query = input("Search: ").strip()
            if query:
                result = get_tool("crm_search_contacts")(query=query, limit=5)
                if result.get("success"):
                    contacts = result.get("contacts", [])
                    print(f"\nFound {len(contacts)}:")
                    for c in contacts:
                        print(f"  - {c.get('name')} ({c.get('email')})")
                else:
                    print(f"\n[ERROR] {result.get('error')}")
        
        elif choice == "4":
            # Test Slack
            print("\n--- SLACK TEST ---")
            result = get_tool("slack_test_connection")()
            if result.get("connected"):
                print(f"[OK] Connected to: {result.get('team')}")
                print(f"     User: {result.get('user')}")
            else:
                print(f"[ERROR] {result.get('error')}")
        
        elif choice == "5":
            # Test Jira
            print("\n--- JIRA TEST ---")
            result = get_tool("jira_test_connection")()
            if result.get("connected"):
                print(f"[OK] Connected")
                print(f"     User: {result.get('user', {}).get('display_name')}")
                print(f"     URL: {result.get('jira_url')}")
            else:
                print(f"[ERROR] {result.get('error')}")
        
        else:
            print("\n[ERROR] Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
