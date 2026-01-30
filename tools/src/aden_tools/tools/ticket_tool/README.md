# Ticket Tool

Manage support tickets and issues.

## Tools

| Tool | Description |
|------|-------------|
| `create_ticket` | Create a new support ticket |
| `update_ticket` | Update ticket status, assignee, etc. |
| `get_ticket` | Retrieve ticket details |
| `search_tickets` | Find tickets with filters |
| `add_ticket_comment` | Add comment to a ticket |
| `get_ticket_summary` | Get workload statistics |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| TICKET_STORAGE_PATH | No | Path for persistent JSON storage |

## Examples

```python
# Create a bug ticket
create_ticket(
    title="Login page not loading",
    description="Users report 500 error on /login",
    priority="critical",
    category="bug",
    assignee="backend-team"
)

# Update ticket status
update_ticket(
    ticket_id="TICKET-0001",
    status="in_progress",
    assignee="john.doe"
)

# Search for open critical tickets
search_tickets(status="open", priority="critical")

# Get workload summary
get_ticket_summary()
```
