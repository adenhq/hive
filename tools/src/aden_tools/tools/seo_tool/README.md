# SEO Audit Tool

Analyze webpages for on-page SEO optimization. This tool provides comprehensive SEO health reports to help agents automate technical marketing tasks.

## Features

- **Title Tag Analysis**: Checks presence, length (30-60 chars optimal), and content
- **Meta Description Check**: Validates presence and length (120-160 chars optimal)  
- **Heading Hierarchy**: Analyzes H1-H6 structure and detects hierarchy gaps
- **Image Alt Text**: Reports coverage percentage and identifies missing alt attributes
- **Canonical Tag**: Verifies presence and self-referencing status
- **Meta Robots**: Detects indexing/following directives
- **Open Graph Tags**: Checks social sharing metadata
- **Overall Score**: Provides 0-100 score with letter grade (A-F)

## Use Cases

1. **Content Publishing**: Check blog posts for SEO issues before publishing
2. **Competitor Analysis**: Extract heading structures and keywords from competitor pages
3. **Periodic Audits**: Detect SEO regressions after website deployments
4. **Migration Validation**: Verify SEO elements are preserved after site migrations

## Installation

The SEO tool is included in the aden-tools package. Ensure you have the dependencies:

```bash
pip install httpx beautifulsoup4
```

## Usage

### As an MCP Tool

When running with the Aden MCP server, the `analyze_on_page` tool is automatically available:

```python
# The tool is registered automatically when the server starts
# Agents can call it with:
result = await mcp.call_tool("analyze_on_page", {"url": "https://example.com"})
```

### Standalone Usage

```python
from aden_tools.tools.seo_tool import analyze_on_page

result = analyze_on_page("https://example.com")
print(f"SEO Score: {result['overall_score']['score']}/100")
print(f"Grade: {result['overall_score']['grade']}")
```

## Response Format

```json
{
  "url": "https://example.com",
  "final_url": "https://example.com/",
  "status_code": 200,
  "title": {
    "present": true,
    "content": "Example Domain",
    "length": 14,
    "optimal": false,
    "issues": ["Too short (14 chars, recommended min 30)"]
  },
  "meta_description": {
    "present": true,
    "content": "This is an example website...",
    "length": 150,
    "optimal": true,
    "issues": []
  },
  "headings": {
    "structure": {
      "h1": {"count": 1, "content": ["Example Domain"]},
      "h2": {"count": 0, "content": []},
      ...
    },
    "h1_count": 1,
    "total_headings": 1,
    "issues": []
  },
  "images": {
    "total": 5,
    "with_alt": 3,
    "missing_alt_count": 2,
    "coverage_percent": 60.0,
    "optimal": false,
    "issues": ["2 image(s) missing alt attribute"]
  },
  "canonical": {
    "present": true,
    "href": "https://example.com/",
    "self_referencing": true,
    "issues": []
  },
  "robots": {
    "present": false,
    "indexable": true,
    "followable": true,
    "issues": []
  },
  "open_graph": {
    "present": true,
    "tags": {"og:title": "...", "og:description": "..."},
    "missing_required": ["og:image"],
    "issues": ["Missing Open Graph tags: og:image"]
  },
  "overall_score": {
    "score": 75,
    "grade": "C",
    "max_score": 100,
    "issues": ["Title length not optimal (-10)", "2 images with alt text issues (-4)"],
    "passed": true
  }
}
```

## Scoring Methodology

| Component | Points | Criteria |
|-----------|--------|----------|
| Title Tag | 20 | Present and optimal length |
| Meta Description | 20 | Present and optimal length |
| H1 Tag | 20 | Exactly one H1 present |
| Image Alt Text | 20 | All images have alt attributes |
| Canonical Tag | 10 | Present |
| Heading Hierarchy | 10 | No gaps in heading levels |

Grades:
- **A**: 90-100
- **B**: 80-89  
- **C**: 70-79
- **D**: 60-69
- **F**: Below 60

## Error Handling

The tool returns error responses for common failure cases:

```json
{"error": "URL cannot be empty"}
{"error": "URL must start with http:// or https://"}
{"error": "Request timed out after 30 seconds: https://..."}
{"error": "HTTP error 404: https://..."}
{"error": "Failed to fetch URL: Connection refused"}
```

## Configuration

The tool uses sensible defaults based on SEO best practices:

| Setting | Value |
|---------|-------|
| Title Min Length | 30 characters |
| Title Max Length | 60 characters |
| Meta Desc Min Length | 120 characters |
| Meta Desc Max Length | 160 characters |
| Request Timeout | 30 seconds |
| User Agent | `AdenSEOBot/1.0` |

## Contributing

See the main [CONTRIBUTING.md](../../../CONTRIBUTING.md) for guidelines on contributing to this tool.
