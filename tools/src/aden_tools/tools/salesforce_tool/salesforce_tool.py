"""
Salesforce Integration Tool - Connect to Salesforce CRM.

Provides tools to:
- Authenticate with Salesforce
- Query and search records
- Create and update contacts, leads, opportunities
- Sync to local CRM database
"""
import os
import json
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
    """Register Salesforce tools with the MCP server."""

    # Cache for auth token
    _auth_cache = {}

    def _get_salesforce_config() -> Dict[str, str]:
        """Get Salesforce configuration from environment."""
        return {
            "username": os.getenv("SALESFORCE_USERNAME", "").strip(),
            "password": os.getenv("SALESFORCE_PASSWORD", "").strip(),
            "security_token": os.getenv("SALESFORCE_SECURITY_TOKEN", "").strip(),
            "client_id": os.getenv("SALESFORCE_CLIENT_ID", "").strip(),
            "client_secret": os.getenv("SALESFORCE_CLIENT_SECRET", "").strip(),
            "instance_url": os.getenv("SALESFORCE_INSTANCE_URL", "").strip(),
        }

    def _salesforce_login() -> Dict[str, Any]:
        """Authenticate with Salesforce and get access token."""
        config = _get_salesforce_config()
        
        if not config["username"]:
            return {"error": "SALESFORCE_USERNAME not configured. Set in .env file."}
        if not config["password"]:
            return {"error": "SALESFORCE_PASSWORD not configured. Set in .env file."}
        
        # Use login.salesforce.com for production, test.salesforce.com for sandbox
        login_url = "https://login.salesforce.com/services/oauth2/token"
        
        # Username-password OAuth flow
        data = urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": config["client_id"] or "3MVG9d8..placeholder",  # Default connected app
            "client_secret": config["client_secret"] or "",
            "username": config["username"],
            "password": config["password"] + config["security_token"],
        }).encode("utf-8")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        try:
            req = urllib.request.Request(login_url, data=data, headers=headers, method="POST")
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                
                _auth_cache["access_token"] = result.get("access_token")
                _auth_cache["instance_url"] = result.get("instance_url")
                _auth_cache["token_type"] = result.get("token_type", "Bearer")
                
                return {
                    "success": True,
                    "instance_url": result.get("instance_url"),
                    "issued_at": result.get("issued_at"),
                }
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            try:
                error_json = json.loads(error_body)
                return {
                    "error": error_json.get("error_description", "Authentication failed"),
                    "error_code": error_json.get("error"),
                }
            except:
                return {"error": f"Authentication failed: {error_body[:200]}"}
        except Exception as e:
            return {"error": f"Login failed: {str(e)}"}

    def _salesforce_request(
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Salesforce API."""
        if not _auth_cache.get("access_token"):
            login_result = _salesforce_login()
            if "error" in login_result:
                return login_result
        
        url = f"{_auth_cache['instance_url']}/services/data/v58.0{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {_auth_cache['access_token']}",
            "Content-Type": "application/json",
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
            # Handle 401 - re-authenticate
            if e.code == 401:
                _auth_cache.clear()
                return {"error": "Session expired. Please try again."}
            
            error_body = e.read().decode("utf-8") if e.fp else ""
            return {
                "error": f"Salesforce API error: {e.code}",
                "details": error_body[:500],
            }
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    @mcp.tool()
    def salesforce_test_connection() -> dict:
        """
        Test connection to Salesforce and get org info.

        Use this to verify Salesforce credentials are working.

        Returns:
            Dict with connection status and org info
        """
        config = _get_salesforce_config()
        
        if not config["username"]:
            return {
                "connected": False,
                "error": "SALESFORCE_USERNAME not set",
                "help": "Edit .env file and set SALESFORCE_USERNAME and SALESFORCE_PASSWORD",
            }
        
        # Try to login
        login_result = _salesforce_login()
        if "error" in login_result:
            return {
                "connected": False,
                **login_result,
            }
        
        # Get org info
        org_result = _salesforce_request("/sobjects/")
        
        if "error" in org_result:
            return {
                "connected": False,
                **org_result,
            }
        
        return {
            "connected": True,
            "instance_url": _auth_cache.get("instance_url"),
            "username": config["username"],
            "sobjects_count": len(org_result.get("sobjects", [])),
        }

    @mcp.tool()
    def salesforce_query(
        soql: str,
    ) -> dict:
        """
        Execute a SOQL query against Salesforce.

        Use this to retrieve records from Salesforce.

        Args:
            soql: SOQL query string (e.g., "SELECT Id, Name FROM Account LIMIT 10")

        Returns:
            Dict with query results
        """
        if not soql:
            return {"error": "soql query is required"}
        
        encoded_query = urllib.parse.quote(soql)
        result = _salesforce_request(f"/query?q={encoded_query}")
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "total_size": result.get("totalSize", 0),
            "done": result.get("done", True),
            "records": result.get("records", []),
        }

    @mcp.tool()
    def salesforce_get_contacts(
        limit: int = 50,
        search_name: str = "",
    ) -> dict:
        """
        Get contacts from Salesforce.

        Args:
            limit: Maximum contacts to return
            search_name: Filter by name (optional)

        Returns:
            Dict with contacts list
        """
        limit = max(1, min(200, limit))
        
        where_clause = ""
        if search_name:
            where_clause = f"WHERE Name LIKE '%{search_name}%'"
        
        soql = f"SELECT Id, Name, Email, Phone, Account.Name, Title FROM Contact {where_clause} LIMIT {limit}"
        
        result = _salesforce_request(f"/query?q={urllib.parse.quote(soql)}")
        
        if "error" in result:
            return result
        
        contacts = []
        for record in result.get("records", []):
            contacts.append({
                "id": record.get("Id"),
                "name": record.get("Name"),
                "email": record.get("Email"),
                "phone": record.get("Phone"),
                "company": record.get("Account", {}).get("Name") if record.get("Account") else None,
                "title": record.get("Title"),
            })
        
        return {
            "success": True,
            "count": len(contacts),
            "contacts": contacts,
        }

    @mcp.tool()
    def salesforce_get_opportunities(
        status: str = "",
        limit: int = 50,
    ) -> dict:
        """
        Get opportunities from Salesforce.

        Args:
            status: Filter by stage (e.g., "Prospecting", "Closed Won")
            limit: Maximum results

        Returns:
            Dict with opportunities list
        """
        limit = max(1, min(200, limit))
        
        where_clause = ""
        if status:
            where_clause = f"WHERE StageName = '{status}'"
        
        soql = f"SELECT Id, Name, StageName, Amount, CloseDate, Account.Name FROM Opportunity {where_clause} ORDER BY CloseDate DESC LIMIT {limit}"
        
        result = _salesforce_request(f"/query?q={urllib.parse.quote(soql)}")
        
        if "error" in result:
            return result
        
        opportunities = []
        for record in result.get("records", []):
            opportunities.append({
                "id": record.get("Id"),
                "name": record.get("Name"),
                "stage": record.get("StageName"),
                "amount": record.get("Amount"),
                "close_date": record.get("CloseDate"),
                "account": record.get("Account", {}).get("Name") if record.get("Account") else None,
            })
        
        return {
            "success": True,
            "count": len(opportunities),
            "opportunities": opportunities,
        }

    @mcp.tool()
    def salesforce_create_contact(
        first_name: str,
        last_name: str,
        email: str = "",
        phone: str = "",
        title: str = "",
        account_id: str = "",
    ) -> dict:
        """
        Create a new contact in Salesforce.

        Args:
            first_name: Contact's first name
            last_name: Contact's last name (required)
            email: Email address
            phone: Phone number
            title: Job title
            account_id: Associated account ID

        Returns:
            Dict with created contact ID
        """
        if not last_name:
            return {"error": "last_name is required"}
        
        data = {
            "FirstName": first_name,
            "LastName": last_name,
        }
        
        if email:
            data["Email"] = email
        if phone:
            data["Phone"] = phone
        if title:
            data["Title"] = title
        if account_id:
            data["AccountId"] = account_id
        
        result = _salesforce_request("/sobjects/Contact", method="POST", data=data)
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "created": True,
            "id": result.get("id"),
            "name": f"{first_name} {last_name}",
        }

    @mcp.tool()
    def salesforce_sync_to_local(
        limit: int = 50,
    ) -> dict:
        """
        Sync Salesforce contacts to local CRM database.

        Use this to import Salesforce contacts for offline work.

        Args:
            limit: Maximum contacts to sync

        Returns:
            Dict with sync results
        """
        from aden_tools.db import Database
        
        # Fetch contacts from Salesforce
        contacts_result = salesforce_get_contacts(limit=limit)
        
        if "error" in contacts_result:
            return contacts_result
        
        imported = 0
        updated = 0
        
        for sf_contact in contacts_result.get("contacts", []):
            # Generate local ID
            local_id = f"sf_{sf_contact['id']}"
            
            contact_data = {
                "id": local_id,
                "name": sf_contact["name"],
                "email": sf_contact.get("email", ""),
                "phone": sf_contact.get("phone", ""),
                "company": sf_contact.get("company", ""),
                "notes": f"Title: {sf_contact.get('title', '')}",
                "tags": ["salesforce", "synced"],
                "external_id": sf_contact["id"],
                "external_source": "salesforce",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            # Check if exists
            existing = Database.get_contact(local_id)
            
            if existing:
                Database.update_contact(local_id, contact_data)
                updated += 1
            else:
                Database.create_contact(contact_data)
                imported += 1
        
        return {
            "success": True,
            "imported": imported,
            "updated": updated,
            "total": imported + updated,
        }


__all__ = ["register_tools"]
