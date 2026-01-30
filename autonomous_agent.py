"""
Hive Autonomous Agent
=====================
Fully autonomous agent that:
1. Scans all connected platforms (Jira, Slack, Salesforce, Local DB)
2. Identifies unresolved issues and problems
3. Analyzes and proposes solutions
4. Executes solutions automatically
5. Generates a comprehensive report

Run with:
    cd c:\\Users\\M.S.Seshashayanan\\Desktop\\Aden\\hive
    python autonomous_agent.py

Press Ctrl+C at any time to stop and generate the final report.
"""
import os
import sys
import time
import json
import threading
from pathlib import Path
from datetime import datetime

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

# Global flag for stopping
RUNNING = True
REPORT = {
    "start_time": None,
    "end_time": None,
    "platforms_scanned": [],
    "issues_found": [],
    "actions_taken": [],
    "errors": [],
    "summary": {}
}


def log(message, level="INFO"):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "[*]", "OK": "[+]", "WARN": "[!]", "ERROR": "[X]", "ACTION": "[>]"}.get(level, "[*]")
    print(f"{timestamp} {prefix} {message}")


def section(title):
    """Print section header."""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()


class AutonomousAgent:
    """Fully autonomous Hive agent."""
    
    def __init__(self):
        log("Initializing Hive Autonomous Agent...")
        self.mcp = FastMCP("autonomous-agent")
        self.tools = register_all_tools(self.mcp)
        self.issues = []
        self.actions = []
        log(f"Loaded {len(self.tools)} tools", "OK")
    
    def get_tool(self, name):
        """Get tool function by name."""
        return self.mcp._tool_manager._tools[name].fn
    
    def scan_slack(self):
        """Scan Slack for unread messages and issues."""
        section("SCANNING SLACK")
        
        log("Testing Slack connection...")
        status = self.get_tool("slack_test_connection")()
        
        if not status.get("connected"):
            log(f"Slack not connected: {status.get('error')}", "WARN")
            REPORT["errors"].append(f"Slack: {status.get('error')}")
            return []
        
        log(f"Connected to Slack team: {status.get('team')}", "OK")
        REPORT["platforms_scanned"].append({
            "platform": "Slack",
            "status": "connected",
            "team": status.get("team"),
            "user": status.get("user")
        })
        
        # Try to get channels
        channels = self.get_tool("slack_list_channels")(limit=10)
        if channels.get("success"):
            log(f"Found {channels.get('count', 0)} accessible channels", "OK")
        else:
            log(f"Could not list channels: {channels.get('error')}", "WARN")
        
        return []  # Would return unread messages/alerts in production
    
    def scan_jira(self):
        """Scan Jira for unresolved issues."""
        section("SCANNING JIRA")
        
        log("Testing Jira connection...")
        status = self.get_tool("jira_test_connection")()
        
        if not status.get("connected"):
            log(f"Jira not connected: {status.get('error')}", "WARN")
            REPORT["errors"].append(f"Jira: {status.get('error')}")
            REPORT["platforms_scanned"].append({
                "platform": "Jira",
                "status": "error",
                "error": str(status.get("error"))[:100]
            })
            return []
        
        log(f"Connected as: {status.get('user', {}).get('display_name')}", "OK")
        REPORT["platforms_scanned"].append({
            "platform": "Jira",
            "status": "connected",
            "user": status.get("user", {}).get("display_name")
        })
        
        # Get projects
        projects = self.get_tool("jira_list_projects")(limit=10)
        if projects.get("success"):
            log(f"Found {projects.get('count', 0)} projects", "OK")
            
            issues_found = []
            for proj in projects.get("projects", [])[:3]:  # Check first 3 projects
                log(f"Scanning project: {proj.get('key')}...")
                
                issues = self.get_tool("jira_get_issues")(
                    project_key=proj.get("key"),
                    status="To Do,In Progress",
                    limit=10
                )
                
                if issues.get("success"):
                    for issue in issues.get("issues", []):
                        issues_found.append({
                            "source": "jira",
                            "id": issue.get("key"),
                            "title": issue.get("summary"),
                            "status": issue.get("status"),
                            "priority": issue.get("priority"),
                            "type": issue.get("issue_type"),
                            "url": issue.get("url")
                        })
            
            log(f"Found {len(issues_found)} unresolved Jira issues", "OK")
            return issues_found
        
        return []
    
    def scan_salesforce(self):
        """Scan Salesforce for opportunities and issues."""
        section("SCANNING SALESFORCE")
        
        log("Testing Salesforce connection...")
        status = self.get_tool("salesforce_test_connection")()
        
        if not status.get("connected"):
            log(f"Salesforce not connected: {status.get('error')}", "WARN")
            REPORT["errors"].append(f"Salesforce: {status.get('error')}")
            REPORT["platforms_scanned"].append({
                "platform": "Salesforce",
                "status": "error",
                "error": str(status.get("error"))[:100]
            })
            return []
        
        log(f"Connected to: {status.get('instance_url')}", "OK")
        REPORT["platforms_scanned"].append({
            "platform": "Salesforce",
            "status": "connected",
            "instance": status.get("instance_url")
        })
        
        # Get open opportunities
        log("Fetching open opportunities...")
        opps = self.get_tool("salesforce_get_opportunities")(stage="Open", limit=10)
        
        issues_found = []
        if opps.get("success"):
            for opp in opps.get("opportunities", []):
                issues_found.append({
                    "source": "salesforce",
                    "id": opp.get("Id"),
                    "title": opp.get("Name"),
                    "status": opp.get("StageName"),
                    "priority": "medium",
                    "type": "opportunity",
                    "value": opp.get("Amount")
                })
            log(f"Found {len(issues_found)} open opportunities", "OK")
        
        return issues_found
    
    def scan_local_tickets(self):
        """Scan local database for unresolved tickets."""
        section("SCANNING LOCAL DATABASE")
        
        log("Fetching local ticket summary...")
        summary = self.get_tool("get_ticket_summary")()
        
        log(f"Total tickets: {summary.get('total', 0)}", "OK")
        log(f"By status: {summary.get('by_status', {})}", "OK")
        
        REPORT["platforms_scanned"].append({
            "platform": "Local Database",
            "status": "connected",
            "total_tickets": summary.get("total", 0),
            "by_status": summary.get("by_status", {})
        })
        
        # Get open tickets
        log("Fetching open tickets...")
        tickets = self.get_tool("search_tickets")(status="open", limit=20)
        
        issues_found = []
        if tickets.get("success"):
            for ticket in tickets.get("tickets", []):
                issues_found.append({
                    "source": "local",
                    "id": ticket.get("id"),
                    "title": ticket.get("title"),
                    "status": ticket.get("status"),
                    "priority": ticket.get("priority"),
                    "type": "ticket",
                    "created": ticket.get("created_at")
                })
            log(f"Found {len(issues_found)} open local tickets", "OK")
        
        return issues_found
    
    def analyze_issues(self, issues):
        """Analyze issues and propose solutions."""
        section("ANALYZING ISSUES")
        
        if not issues:
            log("No unresolved issues found!", "OK")
            return []
        
        log(f"Analyzing {len(issues)} unresolved issues...")
        
        solutions = []
        for issue in issues:
            solution = self.propose_solution(issue)
            solutions.append({
                "issue": issue,
                "solution": solution
            })
            log(f"  [{issue['source'].upper()}] {issue['id']}: {issue['title'][:40]}...")
            log(f"    -> Proposed: {solution['action']}", "ACTION")
        
        return solutions
    
    def propose_solution(self, issue):
        """Propose a solution for an issue based on its type and priority."""
        source = issue.get("source", "unknown")
        priority = issue.get("priority", "medium")
        status = issue.get("status", "unknown")
        
        # Simple rule-based solutions
        if source == "jira":
            if priority in ["High", "Highest", "critical"]:
                return {
                    "action": "Escalate to on-call team via Slack",
                    "steps": ["Send Slack alert", "Update Jira status", "Log activity"],
                    "auto_execute": True
                }
            else:
                return {
                    "action": "Create follow-up reminder",
                    "steps": ["Add comment", "Set reminder"],
                    "auto_execute": False
                }
        
        elif source == "salesforce":
            return {
                "action": "Sync to local CRM and create follow-up task",
                "steps": ["Sync opportunity", "Create local contact", "Log activity"],
                "auto_execute": True
            }
        
        elif source == "local":
            if priority in ["high", "critical"]:
                return {
                    "action": "Send notification and update assignee",
                    "steps": ["Send alert", "Update ticket", "Log action"],
                    "auto_execute": True
                }
            else:
                return {
                    "action": "Add to daily review queue",
                    "steps": ["Tag for review", "Log activity"],
                    "auto_execute": False
                }
        
        return {
            "action": "Flag for manual review",
            "steps": ["Create report entry"],
            "auto_execute": False
        }
    
    def execute_solutions(self, solutions):
        """Execute proposed solutions automatically."""
        section("EXECUTING SOLUTIONS")
        
        if not solutions:
            log("No solutions to execute", "OK")
            return
        
        executed = 0
        skipped = 0
        
        for sol in solutions:
            if not RUNNING:
                log("Stopping execution (user requested)")
                break
            
            issue = sol["issue"]
            solution = sol["solution"]
            
            if not solution.get("auto_execute"):
                log(f"Skipping {issue['id']} (manual review required)", "WARN")
                skipped += 1
                continue
            
            log(f"Executing solution for {issue['id']}...", "ACTION")
            
            try:
                # Execute based on action type
                if "Slack" in solution["action"]:
                    self.execute_slack_alert(issue)
                elif "Sync" in solution["action"]:
                    self.execute_sync(issue)
                elif "notification" in solution["action"]:
                    self.execute_notification(issue)
                
                executed += 1
                REPORT["actions_taken"].append({
                    "issue_id": issue["id"],
                    "action": solution["action"],
                    "status": "executed",
                    "timestamp": datetime.now().isoformat()
                })
                
                log(f"  Completed: {solution['action']}", "OK")
                
            except Exception as e:
                log(f"  Failed: {str(e)}", "ERROR")
                REPORT["errors"].append(f"Execution failed for {issue['id']}: {str(e)}")
            
            time.sleep(0.5)  # Small delay between actions
        
        log(f"Executed: {executed}, Skipped: {skipped}", "OK")
    
    def execute_slack_alert(self, issue):
        """Send Slack alert for an issue."""
        status = self.get_tool("slack_test_connection")()
        if not status.get("connected"):
            raise Exception("Slack not connected")
        
        # Get channels
        channels = self.get_tool("slack_list_channels")(limit=5)
        if not channels.get("success") or not channels.get("channels"):
            raise Exception("No Slack channels available")
        
        # Find a channel we can post to
        target = None
        for ch in channels.get("channels", []):
            if ch.get("is_member"):
                target = ch
                break
        
        if target:
            self.get_tool("slack_send_rich_message")(
                channel=target["id"],
                title=f"[ALERT] {issue['id']}",
                message=f"*Issue:* {issue['title']}\n*Priority:* {issue.get('priority', 'N/A')}\n*Status:* {issue.get('status', 'N/A')}",
                color="#ff0000" if issue.get("priority") in ["High", "critical", "high"] else "#ff9900"
            )
    
    def execute_sync(self, issue):
        """Sync an issue to local database."""
        if issue["source"] == "salesforce":
            self.get_tool("salesforce_sync_to_local")(limit=5)
        elif issue["source"] == "jira":
            # Would sync Jira issue to local
            pass
    
    def execute_notification(self, issue):
        """Send notification for an issue."""
        self.get_tool("send_notification")(
            recipient="team@company.com",
            message=f"Issue {issue['id']}: {issue['title']} requires attention",
            channel="email"
        )
    
    def generate_report(self):
        """Generate final report."""
        section("FINAL REPORT")
        
        REPORT["end_time"] = datetime.now().isoformat()
        
        # Calculate duration
        start = datetime.fromisoformat(REPORT["start_time"])
        end = datetime.fromisoformat(REPORT["end_time"])
        duration = (end - start).seconds
        
        print(f"Duration: {duration} seconds")
        print()
        
        # Platforms
        print("PLATFORMS SCANNED:")
        for p in REPORT["platforms_scanned"]:
            status_symbol = "[OK]" if p["status"] == "connected" else "[--]"
            print(f"  {status_symbol} {p['platform']}: {p['status']}")
        print()
        
        # Issues
        print(f"ISSUES FOUND: {len(REPORT['issues_found'])}")
        for issue in REPORT["issues_found"][:10]:  # Show first 10
            print(f"  - [{issue['source'].upper()}] {issue['id']}: {issue['title'][:50]}")
        if len(REPORT["issues_found"]) > 10:
            print(f"  ... and {len(REPORT['issues_found']) - 10} more")
        print()
        
        # Actions
        print(f"ACTIONS TAKEN: {len(REPORT['actions_taken'])}")
        for action in REPORT["actions_taken"]:
            print(f"  [OK] {action['issue_id']}: {action['action']}")
        print()
        
        # Errors
        if REPORT["errors"]:
            print(f"ERRORS: {len(REPORT['errors'])}")
            for error in REPORT["errors"]:
                print(f"  [!] {error}")
            print()
        
        # Summary
        REPORT["summary"] = {
            "duration_seconds": duration,
            "platforms_scanned": len(REPORT["platforms_scanned"]),
            "issues_found": len(REPORT["issues_found"]),
            "actions_taken": len(REPORT["actions_taken"]),
            "errors": len(REPORT["errors"])
        }
        
        print("SUMMARY:")
        print(f"  Platforms: {REPORT['summary']['platforms_scanned']}")
        print(f"  Issues: {REPORT['summary']['issues_found']}")
        print(f"  Actions: {REPORT['summary']['actions_taken']}")
        print(f"  Errors: {REPORT['summary']['errors']}")
        print()
        
        # Save report to file
        report_path = Path(__file__).parent / "agent_report.json"
        with open(report_path, "w") as f:
            json.dump(REPORT, f, indent=2, default=str)
        
        print(f"Report saved to: {report_path}")
        print()
    
    def run(self):
        """Run the autonomous agent."""
        global RUNNING
        
        print()
        print("=" * 70)
        print("  HIVE AUTONOMOUS AGENT")
        print("  Press Ctrl+C to stop and generate report")
        print("=" * 70)
        print()
        
        REPORT["start_time"] = datetime.now().isoformat()
        
        try:
            # Phase 1: Scan all platforms
            log("Starting autonomous scan...")
            
            issues = []
            issues.extend(self.scan_slack())
            issues.extend(self.scan_jira())
            issues.extend(self.scan_salesforce())
            issues.extend(self.scan_local_tickets())
            
            REPORT["issues_found"] = issues
            
            if not RUNNING:
                return
            
            # Phase 2: Analyze and propose solutions
            solutions = self.analyze_issues(issues)
            
            if not RUNNING:
                return
            
            # Phase 3: Execute solutions
            self.execute_solutions(solutions)
            
            # Phase 4: Generate report
            self.generate_report()
            
        except KeyboardInterrupt:
            RUNNING = False
            log("Received stop signal", "WARN")
            self.generate_report()
        
        except Exception as e:
            log(f"Agent error: {str(e)}", "ERROR")
            REPORT["errors"].append(f"Agent error: {str(e)}")
            self.generate_report()
        
        print("=" * 70)
        print("  AGENT COMPLETE")
        print("=" * 70)


def main():
    """Entry point."""
    agent = AutonomousAgent()
    agent.run()


if __name__ == "__main__":
    main()
