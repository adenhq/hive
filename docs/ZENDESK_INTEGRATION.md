# Zendesk Integration Guide

This guide explains how to configure and use the Zendesk toolkit in Hive.

---

## 🔐 1. Authentication & Setup

### Environment Variables
Add the following to your `.env` file:
```bash
ZENDESK_SUBDOMAIN=your_subdomain  # e.g., adenhq
ZENDESK_EMAIL=your_email@domain.com
ZENDESK_API_TOKEN=your_zendesk_api_token
```

### Obtaining an API Token
1.  Log in to your Zendesk Admin Center.
2.  Navigate to **Apps and Integrations > APIs > Zendesk API**.
3.  Enable **Token Access** and click **Add API token**.
4.  Copy the token immediately (it won't be shown again).

---

## 🛠 2. Tool Overview

### `zendesk_health_check`
Verifies your credentials and authenticated user status.

### `zendesk_ticket_search`
Search for tickets using simple or advanced queries.
- **Example query**: `keyboard issue`
- **Advanced query**: `status:open priority:high`

### `zendesk_ticket_get`
Retrieves the full JSON object for a specific ticket ID.

### `zendesk_ticket_update`
Updates ticket properties and adds comments.
- **Internal Note**: Set `is_public=False` (default) to add a private note.
- **Public Reply**: Set `is_public=True` to send a message to the customer.

---

## 🤖 3. Reference Workflow: "Morning Support Brief"

This agent lists high-priority open tickets and summarizes them.

**Agent Configuration Concept**:
```json
{
  "name": "Zendesk Briefing Agent",
  "nodes": [
    {
      "id": "list_tickets",
      "type": "tool_use",
      "tool": "zendesk_ticket_search",
      "args": {
        "query": "status<solved priority:high",
        "status": "open"
      }
    },
    {
      "id": "summarize",
      "type": "llm_generate",
      "prompt": "Here are the high priority tickets from Zendesk: {{list_tickets.results}}. Please summarize the top 3 critical issues for our Slack channel."
    }
  ]
}
```
