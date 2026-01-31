# Notion Tool

Interact with Notion pages and databases via the Notion API.

## Setup

### 1. Create a Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **+ New integration**
3. Name your integration (e.g., "Hive Agent")
4. Select the workspace to associate it with
5. Click **Submit**
6. Copy the **Internal Integration Secret** (starts with `secret_`)

### 2. Share Resources with the Integration

For each page or database you want the agent to access:

1. Open the page/database in Notion
2. Click the **...** menu in the top right
3. Select **Add connections**
4. Choose your integration

### 3. Configure Credentials

Set the environment variable:

```bash
export NOTION_API_KEY="secret_your_integration_token"
```

Or configure via the Hive credential store.

## Available Tools

### `notion_search`

Search Notion pages and databases by title or content.

```python
# Search for pages containing "project"
result = notion_search(query="project", filter_type="page", page_size=10)
```

**Parameters:**
- `query` (str): Search query string
- `filter_type` (str, optional): Filter by "page" or "database"
- `page_size` (int): Max results (1-100, default 10)

### `notion_get_page`

Retrieve a Notion page by ID, optionally including its content blocks.

```python
# Get page metadata
result = notion_get_page(page_id="abc123...")

# Get page with content
result = notion_get_page(page_id="abc123...", include_content=True)
```

**Parameters:**
- `page_id` (str): The Notion page ID
- `include_content` (bool): Include page content blocks (default False)

### `notion_create_page`

Create a new page under a parent page or in a database.

```python
# Create a simple page
result = notion_create_page(
    parent_id="parent_page_id",
    title="My New Page",
    parent_type="page"
)

# Create a page with content
result = notion_create_page(
    parent_id="parent_page_id",
    title="My New Page",
    content=[
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": "Hello, world!"}}]
            }
        }
    ]
)

# Create a database entry
result = notion_create_page(
    parent_id="database_id",
    title="Task Title",
    parent_type="database",
    properties={
        "Name": {"title": [{"text": {"content": "Task Title"}}]},
        "Status": {"select": {"name": "In Progress"}}
    }
)
```

**Parameters:**
- `parent_id` (str): Parent page ID or database ID
- `title` (str): Page title
- `parent_type` (str): "page" or "database" (default "page")
- `content` (list, optional): List of block objects
- `properties` (dict, optional): Properties for database pages

### `notion_update_page`

Update a page's properties or archive/unarchive it.

```python
# Update page title
result = notion_update_page(
    page_id="page_id",
    properties={"title": {"title": [{"text": {"content": "Updated Title"}}]}}
)

# Archive a page
result = notion_update_page(page_id="page_id", archived=True)
```

**Parameters:**
- `page_id` (str): The page ID to update
- `properties` (dict, optional): Properties to update
- `archived` (bool, optional): Archive status

### `notion_query_database`

Query a Notion database with filters and sorting.

```python
# Get all items
result = notion_query_database(database_id="db_id")

# Filter by status
result = notion_query_database(
    database_id="db_id",
    filter_conditions={"property": "Status", "select": {"equals": "Done"}},
    sorts=[{"property": "Created", "direction": "descending"}],
    page_size=20
)
```

**Parameters:**
- `database_id` (str): The database ID
- `filter_conditions` (dict, optional): Filter object
- `sorts` (list, optional): List of sort objects
- `page_size` (int): Max results (1-100, default 10)

### `notion_append_blocks`

Append content blocks to an existing page or block.

```python
# Add a paragraph and heading to a page
result = notion_append_blocks(
    block_id="page_id",
    children=[
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "New Section"}}]
            }
        },
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "This is new content."}}]
            }
        }
    ]
)
```

**Parameters:**
- `block_id` (str): The page ID or block ID to append to
- `children` (list): List of block objects to append

**Supported block types:**
- `paragraph`, `heading_1`, `heading_2`, `heading_3`
- `bulleted_list_item`, `numbered_list_item`, `to_do`
- `toggle`, `quote`, `callout`, `divider`
- `code`, `image`, `bookmark`, `embed`

## Error Handling

All tools return a dict with an `"error"` key on failure:

```python
{"error": "Notion credentials not configured", "help": "..."}
{"error": "Access denied. Ensure the integration has access to this resource."}
{"error": "Resource not found. Check the ID and ensure the integration has access."}
{"error": "Notion rate limit exceeded. Try again later."}
```

## API Reference

- [Notion API Documentation](https://developers.notion.com/reference)
- [Authentication](https://developers.notion.com/docs/authorization)
- [Working with Pages](https://developers.notion.com/docs/working-with-pages)
- [Working with Databases](https://developers.notion.com/docs/working-with-databases)
