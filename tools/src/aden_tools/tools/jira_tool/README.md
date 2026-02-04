# Jira Tool

Interact with Jira issues, projects, and workflows within the Aden agent framework.

## Installation

The Jira tool uses `httpx` which is already included in the base dependencies. No additional installation required.

## Setup

You need a Jira API token to use this tool.

### Getting a Jira API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give your token a descriptive label (e.g., "Aden Agent Framework")
4. Click "Create"
5. Copy the token (you won't be able to see it again)

**Note:** Keep your token secure! It provides access to your Jira account.

### Configuration

Set the required environment variables:

```bash
export JIRA_BASE_URL=https://your-domain.atlassian.net
export JIRA_EMAIL=your-email@example.com
export JIRA_API_TOKEN=your_api_token_here
```

Or configure via the credential store (recommended for production).

## Available Functions

### Issue Operations

#### `jira_search_issues`

Search Jira issues using JQL (Jira Query Language).

**Parameters:**
- `jql` (str, optional): JQL query string (e.g., "project = PROJ AND status = Open")
- `fields` (list[str], optional): List of fields to return
- `max_results` (int, optional): Maximum number of results (1-100, default 50)

**Returns:**
```python
{
    "issues": [
        {
            "id": "10001",
            "key": "PROJ-123",
            "fields": {
                "summary": "Bug in login flow",
                "status": {"name": "In Progress"},
                "assignee": {"displayName": "John Doe"},
                "priority": {"name": "High"}
            }
        }
    ],
    "total": 1
}
```

**Example:**
```python
# Search for open issues in a project
result = jira_search_issues(jql="project = MYPROJ AND status = Open")

# Search for your assigned issues
result = jira_search_issues(jql="assignee = currentUser() AND status != Done")

# Search for recent issues
result = jira_search_issues(jql="created >= -7d", max_results=10)
```

#### `jira_get_issue`

Get a single Jira issue by key or ID.

**Parameters:**
- `issue_key` (str): Issue key (e.g., "PROJ-123") or ID
- `fields` (list[str], optional): List of fields to return

**Returns:**
```python
{
    "id": "10001",
    "key": "PROJ-123",
    "fields": {
        "summary": "Bug in login flow",
        "description": {...},
        "status": {"name": "In Progress"},
        "assignee": {"displayName": "John Doe"},
        "priority": {"name": "High"},
        "created": "2024-01-30T10:00:00.000+0000"
    }
}
```

**Example:**
```python
issue = jira_get_issue(issue_key="PROJ-123")
print(f"Issue: {issue['fields']['summary']}")
print(f"Status: {issue['fields']['status']['name']}")
```

#### `jira_create_issue`

Create a new Jira issue.

**Parameters:**
- `project_key` (str): Project key (e.g., "PROJ")
- `summary` (str): Issue summary/title
- `issue_type` (str, optional): Issue type (e.g., "Task", "Bug", "Story"), default "Task"
- `description` (str, optional): Issue description
- `additional_fields` (dict, optional): Additional fields to set

**Returns:**
```python
{
    "id": "10002",
    "key": "PROJ-124",
    "self": "https://your-domain.atlassian.net/rest/api/3/issue/10002"
}
```

**Example:**
```python
# Create a simple task
result = jira_create_issue(
    project_key="PROJ",
    summary="Implement user authentication",
    issue_type="Task",
    description="Add OAuth2 authentication to the API"
)
print(f"Created issue: {result['key']}")

# Create a bug with priority
result = jira_create_issue(
    project_key="PROJ",
    summary="Login page crashes on mobile",
    issue_type="Bug",
    description="The login page crashes when accessed from mobile devices",
    additional_fields={"priority": {"name": "High"}}
)
```

#### `jira_update_issue`

Update an existing Jira issue.

**Parameters:**
- `issue_key` (str): Issue key (e.g., "PROJ-123")
- `fields` (dict): Fields to update

**Returns:**
```python
{
    "success": True,
    "status_code": 204
}
```

**Example:**
```python
# Update issue summary
jira_update_issue(
    issue_key="PROJ-123",
    fields={"summary": "Updated: Bug in login flow"}
)

# Update multiple fields
jira_update_issue(
    issue_key="PROJ-123",
    fields={
        "summary": "Critical: Login bug",
        "priority": {"name": "Highest"}
    }
)
```

#### `jira_add_comment`

Add a comment to a Jira issue.

**Parameters:**
- `issue_key` (str): Issue key (e.g., "PROJ-123")
- `comment` (str): Comment text

**Returns:**
```python
{
    "id": "10050",
    "body": {...},
    "author": {"displayName": "John Doe"},
    "created": "2024-01-31T12:00:00.000+0000"
}
```

**Example:**
```python
result = jira_add_comment(
    issue_key="PROJ-123",
    comment="I've started working on this issue. ETA: 2 days."
)
```

#### `jira_get_transitions`

Get available transitions for a Jira issue.

**Parameters:**
- `issue_key` (str): Issue key (e.g., "PROJ-123")

**Returns:**
```python
{
    "transitions": [
        {
            "id": "11",
            "name": "To Do",
            "to": {"name": "To Do"}
        },
        {
            "id": "21",
            "name": "In Progress",
            "to": {"name": "In Progress"}
        },
        {
            "id": "31",
            "name": "Done",
            "to": {"name": "Done"}
        }
    ]
}
```

**Example:**
```python
# Get available transitions
transitions = jira_get_transitions(issue_key="PROJ-123")
for t in transitions["transitions"]:
    print(f"{t['id']}: {t['name']}")
```

#### `jira_transition_issue`

Transition a Jira issue to a new status.

**Parameters:**
- `issue_key` (str): Issue key (e.g., "PROJ-123")
- `transition_id` (str): Transition ID (use `jira_get_transitions` to find IDs)

**Returns:**
```python
{
    "success": True,
    "status_code": 204
}
```

**Example:**
```python
# First, get available transitions
transitions = jira_get_transitions(issue_key="PROJ-123")
done_transition = next(t for t in transitions["transitions"] if t["name"] == "Done")

# Then transition the issue
jira_transition_issue(
    issue_key="PROJ-123",
    transition_id=done_transition["id"]
)
```

### Project Operations

#### `jira_list_projects`

List all accessible Jira projects.

**Returns:**
```python
{
    "projects": [
        {
            "id": "10000",
            "key": "PROJ",
            "name": "My Project",
            "projectTypeKey": "software",
            "lead": {"displayName": "Jane Smith"}
        }
    ]
}
```

**Example:**
```python
projects = jira_list_projects()
for project in projects["projects"]:
    print(f"{project['key']}: {project['name']}")
```

## JQL (Jira Query Language)

JQL is a powerful query language for searching Jira issues. Here are common examples:

### Basic Queries
```jql
# Issues in a project
project = MYPROJ

# Issues assigned to you
assignee = currentUser()

# Open issues
status = Open

# Combining conditions
project = MYPROJ AND status = "In Progress" AND assignee = currentUser()
```

### Date Queries
```jql
# Created in the last 7 days
created >= -7d

# Updated today
updated >= startOfDay()

# Due this week
due >= startOfWeek() AND due <= endOfWeek()
```

### Advanced Queries
```jql
# High priority bugs
issuetype = Bug AND priority = High

# Issues with no assignee
assignee is EMPTY

# Issues created by specific user
reporter = "john.doe@example.com"

# Issues with specific label
labels = urgent

# Multiple projects
project in (PROJ1, PROJ2, PROJ3)

# Text search
summary ~ "authentication" OR description ~ "authentication"
```

### Sorting
```jql
# Recent issues first
order by created DESC

# Highest priority first
order by priority DESC, created DESC
```

## Error Handling

All functions return a dict with an `error` key if something goes wrong:

```python
{
    "error": "Jira API error (HTTP 404): Resource not found. Check issue key or project ID."
}
```

Common errors:
- `not configured` - No Jira credentials provided
- `Invalid Jira credentials or expired API token` - Authentication failed (401)
- `Insufficient permissions` - Check your Jira access rights (403)
- `Resource not found` - Issue or project doesn't exist (404)
- `rate limit exceeded` - Too many requests (429)
- `Request timed out` - Network timeout
- `Network error` - Connection issues

## Security

- API tokens are never logged or exposed
- All API calls use HTTPS
- Tokens are retrieved from secure credential store or environment variables
- Fine-grained permissions can be configured via Jira project roles

## Use Cases

### Automated Issue Creation from Bugs
```python
# Create issues from automated bug reports
jira_create_issue(
    project_key="BUGS",
    summary="Production error: Database connection timeout",
    issue_type="Bug",
    description="Error occurred at 2024-01-31 12:00 UTC\n\nStack trace: ...",
    additional_fields={"priority": {"name": "Critical"}}
)
```

### Sprint Planning Automation
```python
# Get all unassigned tasks
result = jira_search_issues(
    jql="project = MYPROJ AND assignee is EMPTY AND status = 'To Do'",
    max_results=50
)

for issue in result["issues"]:
    print(f"{issue['key']}: {issue['fields']['summary']}")
```

### Status Updates
```python
# Move completed issues to Done
issues = jira_search_issues(jql="assignee = currentUser() AND status = 'In Progress'")

for issue in issues["issues"]:
    # Add completion comment
    jira_add_comment(
        issue_key=issue["key"],
        comment="Work completed. Ready for review."
    )

    # Get transition ID for "Done"
    transitions = jira_get_transitions(issue["key"])
    done_id = next(t["id"] for t in transitions["transitions"] if t["name"] == "Done")

    # Transition to Done
    jira_transition_issue(issue_key=issue["key"], transition_id=done_id)
```

### Project Metrics
```python
# Analyze project health
projects = jira_list_projects()

for project in projects["projects"]:
    key = project["key"]

    # Count issues by status
    total = jira_search_issues(jql=f"project = {key}")["total"]
    open_issues = jira_search_issues(jql=f"project = {key} AND status = Open")["total"]
    in_progress = jira_search_issues(jql=f"project = {key} AND status = 'In Progress'")["total"]

    print(f"{key}: {total} total, {open_issues} open, {in_progress} in progress")
```

### CI/CD Integration
```python
# Create issue when build fails
jira_create_issue(
    project_key="CI",
    summary=f"Build failed: {build_id}",
    issue_type="Bug",
    description=f"Build #{build_id} failed on {branch}\n\nLog: {log_url}",
    additional_fields={
        "priority": {"name": "High"},
        "labels": ["ci", "automated"]
    }
)
```

### Customer Support Integration
```python
# Create Jira ticket from support request
jira_create_issue(
    project_key="SUPPORT",
    summary=f"Customer issue: {customer_name}",
    issue_type="Task",
    description=f"Customer: {customer_email}\n\n{issue_description}",
    additional_fields={
        "priority": {"name": "Medium"},
        "labels": ["customer-support"]
    }
)
```

## Jira Cloud vs Jira Server

This tool is designed for **Jira Cloud** (using REST API v3). If you're using Jira Server or Jira Data Center, you may need to:

1. Update the API endpoints from `/rest/api/3/` to `/rest/api/2/`
2. Adjust authentication (Server may use different methods)
3. Check field names (some fields differ between Cloud and Server)

## Rate Limits

Jira Cloud enforces rate limits:
- **Standard plans**: ~200 requests per minute per IP
- **Premium plans**: Higher limits available

The tool handles rate limit errors gracefully. If you hit limits frequently, consider:
- Caching results
- Batching operations
- Upgrading your Jira plan

## Additional Resources

- [Jira REST API Documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [JQL Documentation](https://support.atlassian.com/jira-software-cloud/docs/use-advanced-search-with-jira-query-language-jql/)
- [Jira Issue Fields](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-issueidorkey-get)
- [Create API Token](https://id.atlassian.com/manage-profile/security/api-tokens)
