"""
CRM Tool - Manage customer relationship data.

Provides tools for creating, updating, and querying CRM records.
Supports: in-memory storage (demo), file-based, or external API.
"""
import os
import json
import datetime
from pathlib import Path
from typing import Optional, Literal, List, Dict, Any, TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialManager

# In-memory storage for demo mode
_crm_storage: Dict[str, Dict[str, Any]] = {}


def _get_storage_path() -> Optional[Path]:
    """Get file-based storage path if configured."""
    storage_path = os.getenv("CRM_STORAGE_PATH")
    if storage_path:
        return Path(storage_path)
    return None


def _load_storage() -> Dict[str, Dict[str, Any]]:
    """Load CRM data from file or return in-memory storage."""
    global _crm_storage
    storage_path = _get_storage_path()
    if storage_path and storage_path.exists():
        with open(storage_path, 'r') as f:
            _crm_storage = json.load(f)
    return _crm_storage


def _save_storage() -> None:
    """Save CRM data to file if configured."""
    storage_path = _get_storage_path()
    if storage_path:
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(storage_path, 'w') as f:
            json.dump(_crm_storage, f, indent=2, default=str)


def register_tools(
    mcp: FastMCP,
    credentials: Optional["CredentialManager"] = None,
) -> None:
    """Register CRM tools with the MCP server."""

    @mcp.tool()
    def crm_create_contact(
        name: str,
        email: str = "",
        phone: str = "",
        company: str = "",
        notes: str = "",
        tags: list = None,
    ) -> dict:
        """
        Create a new contact in the CRM.

        Use this when you need to add a new customer, lead, or business contact
        to the system.

        Args:
            name: Full name of the contact (required, max 200 chars)
            email: Email address
            phone: Phone number
            company: Company/organization name
            notes: Additional notes about the contact
            tags: List of tags for categorization (e.g., ["lead", "enterprise"])

        Returns:
            Dict with contact ID, created data, and confirmation
        """
        if not name or len(name) > 200:
            return {"error": "Name is required and must be 1-200 characters"}
        
        tags = tags or []
        storage = _load_storage()
        
        # Generate unique ID
        contact_id = f"contact_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{len(storage)}"
        
        contact = {
            "id": contact_id,
            "type": "contact",
            "name": name,
            "email": email,
            "phone": phone,
            "company": company,
            "notes": notes,
            "tags": tags,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
        }
        
        storage[contact_id] = contact
        _save_storage()
        
        return {
            "success": True,
            "action": "created",
            "contact_id": contact_id,
            "contact": contact,
        }

    @mcp.tool()
    def crm_update_contact(
        contact_id: str,
        name: str = None,
        email: str = None,
        phone: str = None,
        company: str = None,
        notes: str = None,
        tags: list = None,
    ) -> dict:
        """
        Update an existing contact in the CRM.

        Use this when you need to modify customer information or add new details.

        Args:
            contact_id: The unique ID of the contact to update
            name: New name (if changing)
            email: New email address
            phone: New phone number
            company: New company name
            notes: Updated notes (replaces existing)
            tags: New tag list (replaces existing)

        Returns:
            Dict with updated contact data
        """
        if not contact_id:
            return {"error": "contact_id is required"}
        
        storage = _load_storage()
        
        if contact_id not in storage:
            return {"error": f"Contact not found: {contact_id}"}
        
        contact = storage[contact_id]
        
        # Update fields if provided
        if name is not None:
            contact["name"] = name
        if email is not None:
            contact["email"] = email
        if phone is not None:
            contact["phone"] = phone
        if company is not None:
            contact["company"] = company
        if notes is not None:
            contact["notes"] = notes
        if tags is not None:
            contact["tags"] = tags
        
        contact["updated_at"] = datetime.datetime.now().isoformat()
        
        storage[contact_id] = contact
        _save_storage()
        
        return {
            "success": True,
            "action": "updated",
            "contact_id": contact_id,
            "contact": contact,
        }

    @mcp.tool()
    def crm_get_contact(
        contact_id: str = "",
        email: str = "",
    ) -> dict:
        """
        Retrieve a contact from the CRM.

        Use this when you need to look up customer details.

        Args:
            contact_id: The unique ID of the contact
            email: Alternatively, look up by email address

        Returns:
            Dict with contact data or error if not found
        """
        if not contact_id and not email:
            return {"error": "Provide either contact_id or email"}
        
        storage = _load_storage()
        
        if contact_id and contact_id in storage:
            return {
                "success": True,
                "contact": storage[contact_id],
            }
        
        if email:
            for record in storage.values():
                if record.get("email", "").lower() == email.lower():
                    return {
                        "success": True,
                        "contact": record,
                    }
        
        return {"error": "Contact not found"}

    @mcp.tool()
    def crm_search_contacts(
        query: str = "",
        tag: str = "",
        company: str = "",
        limit: int = 20,
    ) -> dict:
        """
        Search contacts in the CRM.

        Use this when you need to find contacts matching criteria.

        Args:
            query: Search term (matches name, email, notes)
            tag: Filter by tag
            company: Filter by company name
            limit: Maximum results (1-100)

        Returns:
            Dict with matching contacts list
        """
        storage = _load_storage()
        limit = max(1, min(100, limit))
        
        results = []
        query_lower = query.lower() if query else ""
        
        for record in storage.values():
            if record.get("type") != "contact":
                continue
            
            matches = True
            
            # Query filter
            if query_lower:
                searchable = f"{record.get('name', '')} {record.get('email', '')} {record.get('notes', '')}".lower()
                if query_lower not in searchable:
                    matches = False
            
            # Tag filter
            if tag and tag not in record.get("tags", []):
                matches = False
            
            # Company filter
            if company and company.lower() not in record.get("company", "").lower():
                matches = False
            
            if matches:
                results.append(record)
                if len(results) >= limit:
                    break
        
        return {
            "success": True,
            "query": query,
            "filters": {"tag": tag, "company": company},
            "count": len(results),
            "contacts": results,
        }

    @mcp.tool()
    def crm_delete_contact(
        contact_id: str,
    ) -> dict:
        """
        Delete a contact from the CRM.

        Use this when you need to remove a contact record.

        Args:
            contact_id: The unique ID of the contact to delete

        Returns:
            Dict with deletion confirmation
        """
        if not contact_id:
            return {"error": "contact_id is required"}
        
        storage = _load_storage()
        
        if contact_id not in storage:
            return {"error": f"Contact not found: {contact_id}"}
        
        deleted = storage.pop(contact_id)
        _save_storage()
        
        return {
            "success": True,
            "action": "deleted",
            "contact_id": contact_id,
            "deleted_contact": deleted,
        }

    @mcp.tool()
    def crm_log_activity(
        contact_id: str,
        activity_type: Literal["call", "email", "meeting", "note", "task"],
        description: str,
        outcome: str = "",
    ) -> dict:
        """
        Log an activity/interaction for a contact.

        Use this when you need to record customer interactions.

        Args:
            contact_id: The contact ID this activity relates to
            activity_type: Type of activity (call, email, meeting, note, task)
            description: Description of the activity
            outcome: Result/outcome of the activity

        Returns:
            Dict with activity record
        """
        if not contact_id:
            return {"error": "contact_id is required"}
        if not description:
            return {"error": "description is required"}
        
        storage = _load_storage()
        
        if contact_id not in storage:
            return {"error": f"Contact not found: {contact_id}"}
        
        activity_id = f"activity_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        activity = {
            "id": activity_id,
            "type": "activity",
            "contact_id": contact_id,
            "activity_type": activity_type,
            "description": description,
            "outcome": outcome,
            "created_at": datetime.datetime.now().isoformat(),
        }
        
        storage[activity_id] = activity
        
        # Update contact's last activity timestamp
        storage[contact_id]["updated_at"] = datetime.datetime.now().isoformat()
        
        _save_storage()
        
        return {
            "success": True,
            "activity": activity,
        }


__all__ = ["register_tools"]
