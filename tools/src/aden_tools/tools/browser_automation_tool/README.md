# Browser Automation Tool

Browser automation capabilities for interacting with JavaScript-rendered pages, filling forms, taking screenshots, and extracting dynamic content.

## Description

This tool provides browser-based web interaction capabilities using Playwright. It complements the existing `web_scrape_tool` by adding support for:

- JavaScript-rendered content (SPAs, React, Vue, Angular)
- Form filling and submission
- Screenshot capture
- Interactive page elements (clicks, waits)
- Content extraction from dynamic pages

**When to use Browser Automation vs. `web_scrape_tool`:**

- **Use `web_scrape_tool`** for simple, static HTML pages (faster, lighter)
- **Use Browser Automation tools** when:
  - Content is rendered by JavaScript
  - You need to interact with the page (click, fill forms)
  - You need screenshots
  - Static scraping returns empty/incomplete results

## Setup

Playwright is already included as a dependency. You only need to install browser binaries:

```bash
playwright install chromium
```

This downloads Chromium (~150MB) which is sufficient for MVP. Firefox and WebKit can be added later if needed.

## Functions

### `browser_get_page_content`

Navigate to a URL and return fully rendered HTML content.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `url` | str | Yes | - | The URL to navigate to |
| `wait_for` | str | No | `None` | CSS selector to wait for before extracting content |
| `timeout` | int | No | `30000` | Maximum time in ms to wait (5000-300000) |

**Returns:**

```json
{
  "html": "<html>...</html>",
  "title": "Page Title",
  "url": "https://final-url-after-redirects.com"
}
```

**Example:**

```python
result = await browser_get_page_content(
    url="https://example.com",
    wait_for=".main-content",
    timeout=30000
)
```

---

### `browser_screenshot`

Capture a screenshot of a webpage.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `url` | str | Yes | - | The URL to screenshot |
| `output_path` | str | No | `"screenshot.png"` | File path to save the screenshot |
| `full_page` | bool | No | `True` | If True, capture full scrollable page |
| `timeout` | int | No | `30000` | Maximum time in ms to wait (5000-300000) |

**Returns:**

```json
{
  "path": "screenshot.png",
  "width": 1920,
  "height": 1080
}
```

**Example:**

```python
result = await browser_screenshot(
    url="https://example.com/dashboard",
    output_path="dashboard.png",
    full_page=True
)
```

---

### `browser_extract_text`

Extract visible text content from a page (stripped of HTML tags).

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `url` | str | Yes | - | The URL to extract text from |
| `selector` | str | No | `None` | CSS selector for specific element (defaults to body) |
| `timeout` | int | No | `30000` | Maximum time in ms to wait (5000-300000) |

**Returns:**

```json
{
  "text": "Visible text content...",
  "title": "Page Title",
  "url": "https://final-url.com"
}
```

**Example:**

```python
result = await browser_extract_text(
    url="https://example.com/article",
    selector="article"
)
```

---

### `browser_click_and_extract`

Click an element on a page and extract the resulting content.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `url` | str | Yes | - | The URL to navigate to |
| `click_selector` | str | Yes | - | CSS selector of element to click |
| `wait_for_selector` | str | No | `None` | CSS selector to wait for after clicking |
| `timeout` | int | No | `30000` | Maximum time in ms to wait (5000-300000) |

**Returns:**

```json
{
  "html": "<html>...</html>",
  "title": "Page Title",
  "url": "https://final-url.com",
  "clicked_element": "#button-id"
}
```

**Example:**

```python
result = await browser_click_and_extract(
    url="https://example.com/products",
    click_selector=".load-more-button",
    wait_for_selector=".product-list"
)
```

---

### `browser_inspect_form`

Inspect a form on a webpage and return human-readable field information with CSS selectors.

**Use this before `browser_fill_form`** to discover what fields are available. The LLM can use this information to ask users for values, then convert those values to CSS selectors for `browser_fill_form`.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `url` | str | Yes | - | The URL to navigate to |
| `form_selector` | str | No | `None` | CSS selector for a specific form element (if None, inspects all forms) |
| `timeout` | int | No | `30000` | Maximum time in ms to wait (5000-300000) |

**Returns:**

```json
{
  "form_fields": [
    {
      "label": "Email Address",
      "name": "email",
      "type": "email",
      "selector": "#email",
      "required": true,
      "placeholder": "Enter your email",
      "value": "",
      "disabled": false
    },
    {
      "label": "Password",
      "name": "password",
      "type": "password",
      "selector": "#password",
      "required": true,
      "placeholder": "Enter your password",
      "value": "",
      "disabled": false
    },
    {
      "label": "Country",
      "name": "country",
      "type": "select",
      "selector": "#country",
      "required": false,
      "options": [
        {"value": "us", "text": "United States", "selected": false},
        {"value": "uk", "text": "United Kingdom", "selected": false}
      ]
    }
  ],
  "forms_found": 1,
  "title": "Login Page",
  "url": "https://example.com/login"
}
```

**Example:**

```python
# Step 1: Inspect the form to see what fields are available
result = await browser_inspect_form(
    url="https://example.com/login"
)

# Step 2: LLM asks user for values based on the form_fields
# Step 3: LLM converts user inputs to CSS selectors and calls browser_fill_form
result = await browser_fill_form(
    url="https://example.com/login",
    form_fields='{"#email": "user@example.com", "#password": "secret123"}',
    submit=True
)
```

**Workflow:**

1. **LLM calls `browser_inspect_form`** → Gets human-readable field descriptions
2. **LLM asks user** → "I found a login form. Please provide your email and password."
3. **User provides values** → "Email: user@example.com, Password: secret123"
4. **LLM maps values to selectors** → Uses the `selector` field from inspection results
5. **LLM calls `browser_fill_form`** → Passes CSS selectors with user values

---

### `browser_fill_form`

Fill form fields and optionally submit the form.

**Note:** If you don't know the CSS selectors for form fields, use `browser_inspect_form` first to discover them.

**Arguments:**

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `url` | str | Yes | - | The URL to navigate to |
| `form_fields` | str | Yes | - | JSON string mapping CSS selectors to values |
| `submit` | bool | No | `False` | Whether to submit the form after filling |
| `submit_selector` | str | No | `None` | CSS selector of submit button (if different) |
| `wait_for_selector` | str | No | `None` | CSS selector to wait for after submission |
| `timeout` | int | No | `30000` | Maximum time in ms to wait (5000-300000) |

**Form Fields Format:**

The `form_fields` parameter should be a JSON string mapping CSS selectors to values. Use `browser_inspect_form` to get the correct selectors:

```json
{
  "#username": "user@example.com",
  "#password": "secret123",
  "#remember-me": "true"
}
```

Supported field types:
- Text inputs (`input[type="text"]`, `textarea`)
- Select dropdowns (`<select>`)
- Checkboxes (`input[type="checkbox"]`)
- Radio buttons (`input[type="radio"]`)

**Returns:**

```json
{
  "html": "<html>...</html>",
  "title": "Page Title",
  "url": "https://final-url.com",
  "filled_fields": {
    "#username": "user@example.com",
    "#password": "secret123"
  },
  "submitted": true
}
```

**Example:**

```python
result = await browser_fill_form(
    url="https://example.com/login",
    form_fields='{"#username": "user@example.com", "#password": "secret123"}',
    submit=True,
    wait_for_selector=".dashboard"
)
```

---

## Environment Variables

This tool does not require any environment variables. Browser binaries are installed locally via `playwright install chromium`.

## Error Handling

All functions return error dicts for common issues:

- `Request timed out after {timeout}ms` - Page load exceeded timeout
- `Browser error: {error}` - Playwright/Chromium error
- `Failed to {action}: {error}` - General error during execution
- `Element not found: {selector}` - CSS selector matched nothing
- `Invalid JSON in form_fields: {error}` - Malformed form_fields JSON

## Resource Considerations

- **Memory**: Each browser instance uses ~100-200MB RAM
- **CPU**: Browser rendering is CPU-intensive
- **Disk**: Screenshots are saved to disk (PNG format)
- **Network**: Full page loads including all assets

**Best Practices:**

- Use `web_scrape_tool` first for simple pages
- Fall back to Playwright only when needed
- Set appropriate timeouts to avoid hanging
- Clean up screenshots periodically

## Common Patterns

### Wait for Dynamic Content

```python
# Wait for a specific element to appear
result = await browser_get_page_content(
    url="https://spa.example.com",
    wait_for=".dynamic-content",
    timeout=60000
)
```

### Handle Timeouts

```python
# Increase timeout for slow pages
result = await browser_extract_text(
    url="https://slow-site.com",
    timeout=60000  # 60 seconds
)
```

### Extract After Interaction

```python
# Click a button and wait for content to load
result = await browser_click_and_extract(
    url="https://example.com/products",
    click_selector=".load-more",
    wait_for_selector=".new-products"
)
```

### Form Submission with Credentials

```python
# Fill login form and wait for dashboard
result = await browser_fill_form(
    url="https://portal.example.com/login",
    form_fields='{"#email": "user@example.com", "#password": "password123"}',
    submit=True,
    wait_for_selector=".dashboard"
)
```

## Limitations (MVP)

The MVP focuses on simple, stateless browser interactions:

- ✅ Single-page interactions
- ✅ Form filling and submission
- ✅ Screenshot capture
- ✅ Content extraction

**Not included in MVP:**

- ❌ Persistent browser sessions / cookie reuse
- ❌ Multi-tab or multi-page workflows
- ❌ PDF generation from pages
- ❌ Network interception / request mocking
- ❌ Video recording of browser sessions
- ❌ Browser extension support

These features can be added in future iterations based on user needs.

## Related Tools

- **`web_scrape_tool`**: Fast text extraction from static HTML pages
- **`web_search_tool`**: Search the web for URLs (use with Browser Automation to scrape results)

## Notes

- Uses Chromium browser (headless mode)
- Automatically handles redirects
- Waits for network idle by default
- Supports all standard CSS selectors
- URLs without protocol are automatically prefixed with `https://`

