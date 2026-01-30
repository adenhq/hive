"""
Database module for Aden Tools.

Provides SQLite-backed persistent storage for CRM, tickets, and activities.
Upgrade path to PostgreSQL via DATABASE_URL environment variable.
"""
import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

# Database file location (in tools directory)
DB_DIR = Path(__file__).parent.parent.parent.parent / "data"
DB_PATH = DB_DIR / "aden_tools.db"


def get_db_path() -> Path:
    """Get database file path, create directory if needed."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH


@contextmanager
def get_connection():
    """Get a database connection with proper cleanup."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Contacts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                company TEXT,
                notes TEXT,
                tags TEXT,
                external_id TEXT,
                external_source TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Tickets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT,
                category TEXT,
                status TEXT,
                assignee TEXT,
                reporter TEXT,
                due_date TEXT,
                labels TEXT,
                comments TEXT,
                external_id TEXT,
                external_source TEXT,
                external_url TEXT,
                project_key TEXT,
                created_at TEXT,
                updated_at TEXT,
                resolved_at TEXT
            )
        """)
        
        # Activities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id TEXT PRIMARY KEY,
                contact_id TEXT,
                activity_type TEXT,
                description TEXT,
                outcome TEXT,
                created_at TEXT,
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            )
        """)
        
        # External connections/auth table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id TEXT PRIMARY KEY,
                service TEXT NOT NULL,
                account_email TEXT,
                account_name TEXT,
                access_token TEXT,
                refresh_token TEXT,
                token_expires_at TEXT,
                metadata TEXT,
                connected_at TEXT,
                updated_at TEXT
            )
        """)
        
        conn.commit()


# Initialize database on module import
init_db()


class Database:
    """Database operations for Aden Tools."""
    
    # ==================== CONTACTS ====================
    
    @staticmethod
    def create_contact(contact: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contact."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO contacts (id, name, email, phone, company, notes, tags,
                                      external_id, external_source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact["id"],
                contact["name"],
                contact.get("email", ""),
                contact.get("phone", ""),
                contact.get("company", ""),
                contact.get("notes", ""),
                json.dumps(contact.get("tags", [])),
                contact.get("external_id"),
                contact.get("external_source"),
                contact.get("created_at", datetime.now().isoformat()),
                contact.get("updated_at", datetime.now().isoformat()),
            ))
        return contact
    
    @staticmethod
    def get_contact(contact_id: str) -> Optional[Dict[str, Any]]:
        """Get contact by ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
            row = cursor.fetchone()
            if row:
                return Database._row_to_contact(row)
        return None
    
    @staticmethod
    def search_contacts(query: str = "", tag: str = "", company: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        """Search contacts."""
        with get_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM contacts WHERE 1=1"
            params = []
            
            if query:
                sql += " AND (name LIKE ? OR email LIKE ? OR notes LIKE ?)"
                params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
            if company:
                sql += " AND company LIKE ?"
                params.append(f"%{company}%")
            if tag:
                sql += " AND tags LIKE ?"
                params.append(f"%{tag}%")
            
            sql += f" LIMIT {limit}"
            
            cursor.execute(sql, params)
            return [Database._row_to_contact(row) for row in cursor.fetchall()]
    
    @staticmethod
    def update_contact(contact_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update contact."""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            set_parts = []
            params = []
            for key, value in updates.items():
                if key in ["name", "email", "phone", "company", "notes"]:
                    set_parts.append(f"{key} = ?")
                    params.append(value)
                elif key == "tags":
                    set_parts.append("tags = ?")
                    params.append(json.dumps(value))
            
            if set_parts:
                set_parts.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(contact_id)
                
                sql = f"UPDATE contacts SET {', '.join(set_parts)} WHERE id = ?"
                cursor.execute(sql, params)
            
            return Database.get_contact(contact_id)
    
    @staticmethod
    def delete_contact(contact_id: str) -> bool:
        """Delete contact."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
            return cursor.rowcount > 0
    
    @staticmethod
    def _row_to_contact(row) -> Dict[str, Any]:
        """Convert database row to contact dict."""
        return {
            "id": row["id"],
            "type": "contact",
            "name": row["name"],
            "email": row["email"],
            "phone": row["phone"],
            "company": row["company"],
            "notes": row["notes"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "external_id": row["external_id"],
            "external_source": row["external_source"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    
    # ==================== TICKETS ====================
    
    @staticmethod
    def create_ticket(ticket: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new ticket."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tickets (id, title, description, priority, category, status,
                                     assignee, reporter, due_date, labels, comments,
                                     external_id, external_source, external_url, project_key,
                                     created_at, updated_at, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket["id"],
                ticket["title"],
                ticket.get("description", ""),
                ticket.get("priority", "medium"),
                ticket.get("category", "support"),
                ticket.get("status", "open"),
                ticket.get("assignee", ""),
                ticket.get("reporter", "agent"),
                ticket.get("due_date", ""),
                json.dumps(ticket.get("labels", [])),
                json.dumps(ticket.get("comments", [])),
                ticket.get("external_id"),
                ticket.get("external_source"),
                ticket.get("external_url"),
                ticket.get("project_key"),
                ticket.get("created_at", datetime.now().isoformat()),
                ticket.get("updated_at", datetime.now().isoformat()),
                ticket.get("resolved_at"),
            ))
        return ticket
    
    @staticmethod
    def get_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get ticket by ID or external ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tickets WHERE id = ? OR external_id = ?",
                (ticket_id, ticket_id)
            )
            row = cursor.fetchone()
            if row:
                return Database._row_to_ticket(row)
        return None
    
    @staticmethod
    def search_tickets(
        status: str = "",
        priority: str = "",
        project_key: str = "",
        external_source: str = "",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search tickets."""
        with get_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM tickets WHERE 1=1"
            params = []
            
            if status:
                sql += " AND status = ?"
                params.append(status)
            if priority:
                sql += " AND priority = ?"
                params.append(priority)
            if project_key:
                sql += " AND project_key = ?"
                params.append(project_key)
            if external_source:
                sql += " AND external_source = ?"
                params.append(external_source)
            
            sql += f" ORDER BY created_at DESC LIMIT {limit}"
            
            cursor.execute(sql, params)
            return [Database._row_to_ticket(row) for row in cursor.fetchall()]
    
    @staticmethod
    def update_ticket(ticket_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update ticket."""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            set_parts = []
            params = []
            for key, value in updates.items():
                if key in ["title", "description", "priority", "category", "status",
                          "assignee", "reporter", "due_date", "resolved_at"]:
                    set_parts.append(f"{key} = ?")
                    params.append(value)
                elif key in ["labels", "comments"]:
                    set_parts.append(f"{key} = ?")
                    params.append(json.dumps(value))
            
            if set_parts:
                set_parts.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(ticket_id)
                
                sql = f"UPDATE tickets SET {', '.join(set_parts)} WHERE id = ?"
                cursor.execute(sql, params)
            
            return Database.get_ticket(ticket_id)
    
    @staticmethod
    def get_ticket_summary() -> Dict[str, Any]:
        """Get ticket statistics."""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total FROM tickets")
            total = cursor.fetchone()["total"]
            
            cursor.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
            by_status = {row["status"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("SELECT priority, COUNT(*) as count FROM tickets GROUP BY priority")
            by_priority = {row["priority"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("SELECT external_source, COUNT(*) as count FROM tickets WHERE external_source IS NOT NULL GROUP BY external_source")
            by_source = {row["external_source"]: row["count"] for row in cursor.fetchall()}
            
            return {
                "total": total,
                "by_status": by_status,
                "by_priority": by_priority,
                "by_source": by_source,
            }
    
    @staticmethod
    def _row_to_ticket(row) -> Dict[str, Any]:
        """Convert database row to ticket dict."""
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "priority": row["priority"],
            "category": row["category"],
            "status": row["status"],
            "assignee": row["assignee"],
            "reporter": row["reporter"],
            "due_date": row["due_date"],
            "labels": json.loads(row["labels"]) if row["labels"] else [],
            "comments": json.loads(row["comments"]) if row["comments"] else [],
            "external_id": row["external_id"],
            "external_source": row["external_source"],
            "external_url": row["external_url"],
            "project_key": row["project_key"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "resolved_at": row["resolved_at"],
        }
    
    # ==================== CONNECTIONS ====================
    
    @staticmethod
    def save_connection(connection: Dict[str, Any]) -> Dict[str, Any]:
        """Save or update external service connection."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO connections 
                (id, service, account_email, account_name, access_token, refresh_token,
                 token_expires_at, metadata, connected_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                connection.get("id", connection["service"]),
                connection["service"],
                connection.get("account_email"),
                connection.get("account_name"),
                connection.get("access_token"),
                connection.get("refresh_token"),
                connection.get("token_expires_at"),
                json.dumps(connection.get("metadata", {})),
                connection.get("connected_at", datetime.now().isoformat()),
                datetime.now().isoformat(),
            ))
        return connection
    
    @staticmethod
    def get_connection(service: str) -> Optional[Dict[str, Any]]:
        """Get connection for a service."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM connections WHERE service = ?", (service,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "service": row["service"],
                    "account_email": row["account_email"],
                    "account_name": row["account_name"],
                    "access_token": row["access_token"],
                    "refresh_token": row["refresh_token"],
                    "token_expires_at": row["token_expires_at"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "connected_at": row["connected_at"],
                    "updated_at": row["updated_at"],
                }
        return None
    
    @staticmethod
    def list_connections() -> List[Dict[str, Any]]:
        """List all connections."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT service, account_email, account_name, connected_at FROM connections")
            return [dict(row) for row in cursor.fetchall()]


# Export
__all__ = ["Database", "init_db", "get_db_path"]
