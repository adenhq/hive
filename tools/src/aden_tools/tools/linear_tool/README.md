# Linear Tool

This tool allows Hive agents to interact with [Linear](https://linear.app/), a modern issue tracking system.

## Setup

1.  **Get an API Key**:
    *   Go to [Linear API Settings](https://linear.app/settings/api).
    *   Create a "Personal API Key".

2.  **Configure Credentials**:
    *   Set the `LINEAR_API_KEY` environment variable.
    *   Or add `linear_api_key` to your credentials store.

## Features

*   **Create Issue**: Report bugs or feature requests directly to a specific team.
*   **Get Issue**: Retrieve issue details by ID (e.g., `LIN-123`).
*   **Search Issues**: Find issues using Linear's search syntax.

## Usage

```python
# Create an issue
linear_create_issue(
    title="Bug: Agent fails to sync with Linear",
    team_id="team-uuid-1234",
    description="Steps to reproduce...",
    priority=2  # High
)

# Get issue details
linear_get_issue(issue_id="LIN-456")

# Search issues
linear_search_issues(query="bug in login")
```

## Notes

*   `team_id` requires the UUID of the team. You can find this in the Linear URL when viewing a team or via query.
*   Priorities: 0 (No Priority), 1 (Urgent), 2 (High), 3 (Normal), 4 (Low).
