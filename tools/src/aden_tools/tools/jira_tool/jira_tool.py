"""
Jira Integration Tool - Connect to Jira and manage issues.

Provides tools to:
- Connect to Jira with API token
- List accessible projects
- Fetch issues from projects
- Create and update issues
- Sync issues to local tickets database
"""
import os
import json
import base64
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialManager


def register_tools(
    mcp: FastMCP,
    credentials: Optional["CredentialManager"] = None,
) -> None:
    """Register Jira tools with the MCP server."""

    def _get_jira_config() -> Dict[str, str]:
        """Get Jira configuration from environment."""
        return {
            "url": os.getenv("JIRA_URL", "").strip(),
            "email": os.getenv("JIRA_EMAIL", "").strip(),
            "api_token": os.getenv("JIRA_API_TOKEN", "").strip(),
            "org_id": os.getenv("JIRA_ORG_ID", "").strip(),
        }

    def _jira_request(
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Jira API."""
        if config is None:
            config = _get_jira_config()
        
        if not config["url"]:
            return {"error": "JIRA_URL not configured. Set in .env file."}
        if not config["api_token"]:
            return {"error": "JIRA_API_TOKEN not configured. Set in .env file."}
        
        # Build URL
        base_url = config["url"].rstrip("/")
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = f"{base_url}/rest/api/3{endpoint}"
        
        # Auth header (email:token base64 encoded)
        auth_string = f"{config['email']}:{config['api_token']}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {auth_bytes}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        try:
            if data:
                request_data = json.dumps(data).encode("utf-8")
            else:
                request_data = None
            
            req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode("utf-8")
                if response_data:
                    return json.loads(response_data)
                return {"success": True}
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            return {
                "error": f"Jira API error: {e.code} {e.reason}",
                "details": error_body[:500],
            }
        except urllib.error.URLError as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    @mcp.tool()
    def jira_test_connection() -> dict:
        """
        Test connection to Jira and get current user info.

        Use this to verify Jira credentials are working.

        Returns:
            Dict with connection status and user info
        """
        config = _get_jira_config()
        
        if not config["url"]:
            return {
                "connected": False,
                "error": "JIRA_URL not set",
                "help": "Edit .env file and set JIRA_URL=https://yourorg.atlassian.net",
            }
        
        result = _jira_request("/myself", config=config)
        
        if "error" in result:
            return {
                "connected": False,
                **result,
            }
        
        return {
            "connected": True,
            "user": {
                "account_id": result.get("accountId"),
                "email": result.get("emailAddress"),
                "display_name": result.get("displayName"),
                "timezone": result.get("timeZone"),
            },
            "jira_url": config["url"],
        }

    @mcp.tool()
    def jira_list_projects(
        limit: int = 50,
    ) -> dict:
        """
        List all accessible Jira projects.

        Use this to see which projects you can work with.

        Args:
            limit: Maximum number of projects to return (1-100)

        Returns:
            Dict with list of projects (key, name, lead, type)
        """
        limit = max(1, min(100, limit))
        
        result = _jira_request(f"/project/search?maxResults={limit}")
        
        if "error" in result:
            return result
        
        projects = []
        for p in result.get("values", []):
            projects.append({
                "key": p.get("key"),
                "name": p.get("name"),
                "id": p.get("id"),
                "lead": p.get("lead", {}).get("displayName"),
                "type": p.get("projectTypeKey"),
                "style": p.get("style"),
            })
        
        return {
            "success": True,
            "count": len(projects),
            "projects": projects,
        }

    @mcp.tool()
    def jira_get_issues(
        project_key: str,
        status: str = "",
        assignee: str = "",
        limit: int = 50,
    ) -> dict:
        """
        Get issues from a Jira project.

        Use this to fetch issues that need to be worked on.

        Args:
            project_key: The project key (e.g., "PROJ", "DEV")
            status: Filter by status (e.g., "To Do", "In Progress", "Done")
            assignee: Filter by assignee email or "currentUser()"
            limit: Maximum issues to return (1-100)

        Returns:
            Dict with list of issues
        """
        if not project_key:
            return {"error": "project_key is required"}
        
        limit = max(1, min(100, limit))
        
        # Build JQL query
        jql_parts = [f"project = {project_key}"]
        if status:
            jql_parts.append(f'status = "{status}"')
        if assignee:
            if assignee == "me":
                jql_parts.append("assignee = currentUser()")
            else:
                jql_parts.append(f'assignee = "{assignee}"')
        
        jql = " AND ".join(jql_parts) + " ORDER BY updated DESC"
        
        params = urllib.parse.urlencode({
            "jql": jql,
            "maxResults": limit,
            "fields": "summary,status,priority,assignee,reporter,created,updated,description",
        })
        
        result = _jira_request(f"/search?{params}")
        
        if "error" in result:
            return result
        
        issues = []
        for issue in result.get("issues", []):
            fields = issue.get("fields", {})
            issues.append({
                "key": issue.get("key"),
                "id": issue.get("id"),
                "summary": fields.get("summary"),
                "status": fields.get("status", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                "reporter": fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None,
                "created": fields.get("created"),
                "updated": fields.get("updated"),
            })
        
        return {
            "success": True,
            "project": project_key,
            "count": len(issues),
            "issues": issues,
        }

    @mcp.tool()
    def jira_get_issue(
        issue_key: str,
    ) -> dict:
        """
        Get detailed information about a specific Jira issue.

        Args:
            issue_key: The issue key (e.g., "PROJ-123")

        Returns:
            Dict with full issue details
        """
        if not issue_key:
            return {"error": "issue_key is required"}
        
        result = _jira_request(f"/issue/{issue_key}")
        
        if "error" in result:
            return result
        
        fields = result.get("fields", {})
        
        return {
            "success": True,
            "issue": {
                "key": result.get("key"),
                "id": result.get("id"),
                "summary": fields.get("summary"),
                "description": fields.get("description"),
                "status": fields.get("status", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                "reporter": fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None,
                "labels": fields.get("labels", []),
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "url": f"{_get_jira_config()['url']}/browse/{result.get('key')}",
            },
        }

    @mcp.tool()
    def jira_create_issue(
        project_key: str,
        summary: str,
        description: str = "",
        issue_type: str = "Task",
        priority: str = "Medium",
        labels: list = None,
    ) -> dict:
        """
        Create a new issue in Jira.

        Use this when you need to create a new task, bug, or story.

        Args:
            project_key: The project key (e.g., "PROJ")
            summary: Issue title/summary (required)
            description: Detailed description
            issue_type: Type of issue (Task, Bug, Story, Epic)
            priority: Priority level (Highest, High, Medium, Low, Lowest)
            labels: List of labels to apply

        Returns:
            Dict with created issue details
        """
        if not project_key:
            return {"error": "project_key is required"}
        if not summary:
            return {"error": "summary is required"}
        
        labels = labels or []
        
        # Build issue payload
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }
        }
        
        if description:
            # Jira Cloud uses Atlassian Document Format for description
            payload["fields"]["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }
                ]
            }
        
        if labels:
            payload["fields"]["labels"] = labels
        
        result = _jira_request("/issue", method="POST", data=payload)
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "created": True,
            "issue_key": result.get("key"),
            "issue_id": result.get("id"),
            "url": f"{_get_jira_config()['url']}/browse/{result.get('key')}",
        }

    @mcp.tool()
    def jira_update_issue(
        issue_key: str,
        summary: str = None,
        description: str = None,
        status: str = None,
        assignee: str = None,
    ) -> dict:
        """
        Update an existing Jira issue.

        Args:
            issue_key: The issue key (e.g., "PROJ-123")
            summary: New summary/title
            description: New description
            status: New status (requires transition - may not work for all statuses)
            assignee: Assignee account ID or email

        Returns:
            Dict with update confirmation
        """
        if not issue_key:
            return {"error": "issue_key is required"}
        
        payload = {"fields": {}}
        
        if summary:
            payload["fields"]["summary"] = summary
        
        if description:
            payload["fields"]["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }
                ]
            }
        
        if not payload["fields"]:
            return {"error": "No updates provided"}
        
        result = _jira_request(f"/issue/{issue_key}", method="PUT", data=payload)
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "updated": True,
            "issue_key": issue_key,
        }

    @mcp.tool()
    def jira_sync_to_local(
        project_key: str,
        limit: int = 50,
    ) -> dict:
        """
        Sync Jira issues to local tickets database.

        Use this to import Jira issues for offline work or agent processing.

        Args:
            project_key: The project key to sync from
            limit: Maximum issues to sync

        Returns:
            Dict with sync results (imported count, updated count)
        """
        from aden_tools.db import Database
        
        # Fetch issues from Jira
        issues_result = jira_get_issues(project_key=project_key, limit=limit)
        
        if "error" in issues_result:
            return issues_result
        
        imported = 0
        updated = 0
        
        for issue in issues_result.get("issues", []):
            # Check if already exists
            existing = Database.get_ticket(issue["key"])
            
            ticket_data = {
                "id": issue["key"],
                "title": issue["summary"],
                "description": "",
                "priority": (issue["priority"] or "medium").lower(),
                "category": "jira",
                "status": (issue["status"] or "open").lower().replace(" ", "_"),
                "assignee": issue["assignee"] or "",
                "reporter": issue["reporter"] or "",
                "external_id": issue["key"],
                "external_source": "jira",
                "external_url": f"{_get_jira_config()['url']}/browse/{issue['key']}",
                "project_key": project_key,
                "created_at": issue["created"],
                "updated_at": issue["updated"],
            }
            
            if existing:
                Database.update_ticket(issue["key"], ticket_data)
                updated += 1
            else:
                Database.create_ticket(ticket_data)
                imported += 1
        
        return {
            "success": True,
            "project": project_key,
            "imported": imported,
            "updated": updated,
            "total": imported + updated,
        }


__all__ = ["register_tools"]
