"""
Ticket Tool - Manage support tickets and issues.

Provides tools for creating, updating, and tracking support tickets.
"""
import os
import json
import datetime
from pathlib import Path
from typing import Optional, Literal, Dict, Any, TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialManager

# In-memory storage for demo mode
_ticket_storage: Dict[str, Dict[str, Any]] = {}
_ticket_counter = 0


def _get_storage_path() -> Optional[Path]:
    """Get file-based storage path if configured."""
    storage_path = os.getenv("TICKET_STORAGE_PATH")
    if storage_path:
        return Path(storage_path)
    return None


def _load_storage() -> Dict[str, Dict[str, Any]]:
    """Load ticket data from file or return in-memory storage."""
    global _ticket_storage
    storage_path = _get_storage_path()
    if storage_path and storage_path.exists():
        with open(storage_path, 'r') as f:
            _ticket_storage = json.load(f)
    return _ticket_storage


def _save_storage() -> None:
    """Save ticket data to file if configured."""
    storage_path = _get_storage_path()
    if storage_path:
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(storage_path, 'w') as f:
            json.dump(_ticket_storage, f, indent=2, default=str)


def register_tools(
    mcp: FastMCP,
    credentials: Optional["CredentialManager"] = None,
) -> None:
    """Register ticket tools with the MCP server."""

    @mcp.tool()
    def create_ticket(
        title: str,
        description: str,
        priority: Literal["low", "medium", "high", "critical"] = "medium",
        category: Literal["bug", "feature", "support", "question", "other"] = "support",
        assignee: str = "",
        reporter: str = "agent",
        due_date: str = "",
        labels: list = None,
    ) -> dict:
        """
        Create a new support ticket or issue.

        Use this when you need to track a problem, request, or task.

        Args:
            title: Short summary of the ticket (required, max 200 chars)
            description: Detailed description of the issue
            priority: Urgency level (low, medium, high, critical)
            category: Type of ticket (bug, feature, support, question, other)
            assignee: Person/team assigned to handle this
            reporter: Who created the ticket
            due_date: Expected completion date (YYYY-MM-DD format)
            labels: List of labels for categorization

        Returns:
            Dict with ticket ID and full ticket data
        """
        global _ticket_counter
        
        if not title or len(title) > 200:
            return {"error": "Title is required and must be 1-200 characters"}
        if not description:
            return {"error": "Description is required"}
        
        labels = labels or []
        storage = _load_storage()
        
        # Generate ticket number
        _ticket_counter = len([k for k in storage.keys() if k.startswith("TICKET-")]) + 1
        ticket_id = f"TICKET-{_ticket_counter:04d}"
        
        ticket = {
            "id": ticket_id,
            "title": title,
            "description": description,
            "priority": priority,
            "category": category,
            "status": "open",
            "assignee": assignee,
            "reporter": reporter,
            "due_date": due_date,
            "labels": labels,
            "comments": [],
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "resolved_at": None,
        }
        
        storage[ticket_id] = ticket
        _save_storage()
        
        return {
            "success": True,
            "action": "created",
            "ticket_id": ticket_id,
            "ticket": ticket,
        }

    @mcp.tool()
    def update_ticket(
        ticket_id: str,
        status: Literal["open", "in_progress", "waiting", "resolved", "closed"] = None,
        priority: Literal["low", "medium", "high", "critical"] = None,
        assignee: str = None,
        title: str = None,
        description: str = None,
        due_date: str = None,
        labels: list = None,
    ) -> dict:
        """
        Update an existing ticket.

        Use this when you need to change ticket status, reassign, or update details.

        Args:
            ticket_id: The ticket ID (e.g., TICKET-0001)
            status: New status (open, in_progress, waiting, resolved, closed)
            priority: New priority level
            assignee: New assignee
            title: Updated title
            description: Updated description
            due_date: Updated due date
            labels: Updated labels (replaces existing)

        Returns:
            Dict with updated ticket data
        """
        if not ticket_id:
            return {"error": "ticket_id is required"}
        
        storage = _load_storage()
        
        if ticket_id not in storage:
            return {"error": f"Ticket not found: {ticket_id}"}
        
        ticket = storage[ticket_id]
        
        # Track what changed
        changes = []
        
        if status is not None:
            old_status = ticket["status"]
            ticket["status"] = status
            changes.append(f"status: {old_status} -> {status}")
            
            if status in ["resolved", "closed"]:
                ticket["resolved_at"] = datetime.datetime.now().isoformat()
        
        if priority is not None:
            changes.append(f"priority: {ticket['priority']} -> {priority}")
            ticket["priority"] = priority
        
        if assignee is not None:
            changes.append(f"assignee: {ticket['assignee']} -> {assignee}")
            ticket["assignee"] = assignee
        
        if title is not None:
            ticket["title"] = title
            changes.append("title updated")
        
        if description is not None:
            ticket["description"] = description
            changes.append("description updated")
        
        if due_date is not None:
            ticket["due_date"] = due_date
            changes.append(f"due_date: {due_date}")
        
        if labels is not None:
            ticket["labels"] = labels
            changes.append("labels updated")
        
        ticket["updated_at"] = datetime.datetime.now().isoformat()
        
        storage[ticket_id] = ticket
        _save_storage()
        
        return {
            "success": True,
            "action": "updated",
            "ticket_id": ticket_id,
            "changes": changes,
            "ticket": ticket,
        }

    @mcp.tool()
    def get_ticket(
        ticket_id: str,
    ) -> dict:
        """
        Retrieve a ticket by ID.

        Args:
            ticket_id: The ticket ID (e.g., TICKET-0001)

        Returns:
            Dict with full ticket data
        """
        if not ticket_id:
            return {"error": "ticket_id is required"}
        
        storage = _load_storage()
        
        if ticket_id not in storage:
            return {"error": f"Ticket not found: {ticket_id}"}
        
        return {
            "success": True,
            "ticket": storage[ticket_id],
        }

    @mcp.tool()
    def search_tickets(
        status: str = "",
        priority: str = "",
        assignee: str = "",
        category: str = "",
        query: str = "",
        limit: int = 20,
    ) -> dict:
        """
        Search and filter tickets.

        Use this when you need to find tickets matching specific criteria.

        Args:
            status: Filter by status (open, in_progress, resolved, etc.)
            priority: Filter by priority (low, medium, high, critical)
            assignee: Filter by assignee
            category: Filter by category
            query: Search in title and description
            limit: Maximum results (1-100)

        Returns:
            Dict with matching tickets
        """
        storage = _load_storage()
        limit = max(1, min(100, limit))
        
        results = []
        query_lower = query.lower() if query else ""
        
        for ticket in storage.values():
            if not isinstance(ticket, dict) or "id" not in ticket:
                continue
            
            matches = True
            
            if status and ticket.get("status") != status:
                matches = False
            if priority and ticket.get("priority") != priority:
                matches = False
            if assignee and assignee.lower() not in ticket.get("assignee", "").lower():
                matches = False
            if category and ticket.get("category") != category:
                matches = False
            if query_lower:
                searchable = f"{ticket.get('title', '')} {ticket.get('description', '')}".lower()
                if query_lower not in searchable:
                    matches = False
            
            if matches:
                results.append(ticket)
                if len(results) >= limit:
                    break
        
        return {
            "success": True,
            "filters": {
                "status": status,
                "priority": priority,
                "assignee": assignee,
                "category": category,
                "query": query,
            },
            "count": len(results),
            "tickets": results,
        }

    @mcp.tool()
    def add_ticket_comment(
        ticket_id: str,
        comment: str,
        author: str = "agent",
    ) -> dict:
        """
        Add a comment to a ticket.

        Use this when you need to add updates or notes to a ticket.

        Args:
            ticket_id: The ticket ID
            comment: Comment text (max 5000 chars)
            author: Who is adding the comment

        Returns:
            Dict with updated ticket comments
        """
        if not ticket_id:
            return {"error": "ticket_id is required"}
        if not comment or len(comment) > 5000:
            return {"error": "Comment must be 1-5000 characters"}
        
        storage = _load_storage()
        
        if ticket_id not in storage:
            return {"error": f"Ticket not found: {ticket_id}"}
        
        ticket = storage[ticket_id]
        
        comment_obj = {
            "id": f"comment_{len(ticket.get('comments', []))+1}",
            "author": author,
            "text": comment,
            "created_at": datetime.datetime.now().isoformat(),
        }
        
        if "comments" not in ticket:
            ticket["comments"] = []
        
        ticket["comments"].append(comment_obj)
        ticket["updated_at"] = datetime.datetime.now().isoformat()
        
        storage[ticket_id] = ticket
        _save_storage()
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "comment": comment_obj,
            "total_comments": len(ticket["comments"]),
        }

    @mcp.tool()
    def get_ticket_summary(
    ) -> dict:
        """
        Get summary statistics of all tickets.

        Use this to understand the current ticket workload.

        Returns:
            Dict with counts by status, priority, and category
        """
        storage = _load_storage()
        
        summary = {
            "total": 0,
            "by_status": {},
            "by_priority": {},
            "by_category": {},
            "overdue": 0,
        }
        
        today = datetime.date.today().isoformat()
        
        for ticket in storage.values():
            if not isinstance(ticket, dict) or "id" not in ticket:
                continue
            
            summary["total"] += 1
            
            status = ticket.get("status", "unknown")
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            
            priority = ticket.get("priority", "unknown")
            summary["by_priority"][priority] = summary["by_priority"].get(priority, 0) + 1
            
            category = ticket.get("category", "unknown")
            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
            
            due_date = ticket.get("due_date", "")
            if due_date and due_date < today and ticket.get("status") not in ["resolved", "closed"]:
                summary["overdue"] += 1
        
        return {
            "success": True,
            "summary": summary,
        }


__all__ = ["register_tools"]
