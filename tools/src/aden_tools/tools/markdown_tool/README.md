# Markdown Tool

Format text and convert between markdown and HTML for content-generating agents.

## Description

The `markdown_tool` provides text formatting and conversion capabilities, enabling agents to create formatted content, generate reports, and convert between markdown and HTML formats. Essential for Blog Writer Agents, Knowledge Agents, and Report Agents.

## Tools

### `markdown_to_html`

Convert markdown text to HTML for emails, web pages, or rich text display.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `content` | str | Yes | - | Markdown text to convert (1-100,000 chars) |
| `extensions` | list[str] | No | `["tables", "fenced_code", "nl2br"]` | Markdown extensions to enable |

**Returns:**
```python
{
    "success": True,
    "html": "<h1>Title</h1><p>Content...</p>",
    "input_length": 50,
    "output_length": 120
}
```

**Example:**
```python
markdown_to_html(
    content="# Report\n\n**Key findings:**\n- Sales up 20%\n- New customers: 150"
)
```

### `html_to_markdown`

Convert HTML to markdown text for processing or storage.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `html` | str | Yes | - | HTML text to convert (1-100,000 chars) |
| `strip_tags` | bool | No | `False` | Remove tags without markdown equivalents |

**Returns:**
```python
{
    "success": True,
    "markdown": "# Title\n\nContent...",
    "input_length": 120,
    "output_length": 50
}
```

**Example:**
```python
html_to_markdown(
    html="<h1>Title</h1><p>Content with <strong>bold</strong> text</p>"
)
```

### `format_text`

Apply markdown formatting to text.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `text` | str | Yes | - | Text to format (1-10,000 chars) |
| `style` | str | Yes | - | Formatting style (see below) |

**Supported Styles:**
- `bold` - **Bold text**
- `italic` - *Italic text*
- `code` - `Inline code`
- `heading1` - # Heading 1
- `heading2` - ## Heading 2
- `heading3` - ### Heading 3
- `blockquote` - > Quote
- `strikethrough` - ~~Strikethrough~~

**Returns:**
```python
{
    "success": True,
    "formatted": "**Important message**",
    "style": "bold"
}
```

**Example:**
```python
format_text(
    text="Important message",
    style="bold"
)
```

### `create_markdown_table`

Create a markdown table from headers and rows.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `headers` | list[str] | Yes | - | Column headers |
| `rows` | list[list[str]] | Yes | - | Table rows (each row is a list of cells) |
| `alignment` | list[str] | No | `["left", ...]` | Column alignments ("left", "center", "right") |

**Returns:**
```python
{
    "success": True,
    "table": "| Name | Age |\n| --- | --- |\n| Alice | 30 |",
    "num_rows": 1,
    "num_cols": 2
}
```

**Example:**
```python
create_markdown_table(
    headers=["Name", "Age", "City"],
    rows=[
        ["Alice", "30", "NYC"],
        ["Bob", "25", "LA"]
    ],
    alignment=["left", "center", "left"]
)
```

## Environment Variables

This tool does not require any environment variables.

## Dependencies

The tool requires the following Python packages:
- `markdown>=3.0.0` - For markdown to HTML conversion
- `html2text>=2020.0.0` - For HTML to markdown conversion

Install with:
```bash
pip install markdown html2text
# Or install with optional dependencies
pip install tools[markdown]
```

## Use Cases

### Blog Writer Agent
```python
# Format blog post content
content = """
# My Blog Post

This is an introduction with **bold** text.

## Key Points
- Point 1
- Point 2

Visit [my website](https://example.com) for more.
"""

result = markdown_to_html(content=content)
# Use result["html"] for publishing
```

### Report Generation Agent
```python
# Create formatted report with table
headers = ["Metric", "Q1", "Q2", "Q3"]
rows = [
    ["Revenue", "$100K", "$120K", "$150K"],
    ["Customers", "500", "650", "800"]
]

table = create_markdown_table(headers=headers, rows=rows, alignment=["left", "right", "right", "right"])

report = f"""
# Quarterly Report

{table["table"]}

## Summary
Revenue increased by **50%** over the quarter.
"""

html_report = markdown_to_html(content=report)
```

### Documentation Agent
```python
# Generate README with formatted sections
title = format_text(text="Project Name", style="heading1")
subtitle = format_text(text="Installation", style="heading2")
code = format_text(text="pip install package", style="code")

readme = f"{title['formatted']}\n\n{subtitle['formatted']}\n\nInstall with: {code['formatted']}"
```

### Email Agent
```python
# Convert markdown email to HTML
email_content = """
Hi **John**,

Your order has been shipped!

- Order #: 12345
- Tracking: ABC123

Thanks for your purchase!
"""

html_email = markdown_to_html(content=email_content)
# Send html_email["html"] via email service
```

## Error Handling

All tools return error dicts for validation issues:

- Empty content: `{"error": "content cannot be empty"}`
- Content too long: `{"error": "content must be 100,000 characters or less"}`
- Invalid style: `{"error": "Invalid style: xyz. Valid styles: ..."}`
- Missing dependency: `{"error": "markdown library not installed. Install with: ..."}`
- Table mismatch: `{"error": "Row 0 has 3 columns, but headers have 2 columns"}`

## Notes

- Default markdown extensions: `tables`, `fenced_code`, `nl2br`
- HTML conversion preserves links, images, and emphasis
- Table alignment defaults to left if not specified
- All tools validate input length to prevent memory issues
- Markdown syntax is GitHub-flavored markdown compatible
