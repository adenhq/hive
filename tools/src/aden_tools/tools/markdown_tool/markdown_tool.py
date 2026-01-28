"""
Markdown Tool - Format text and convert between markdown and HTML.

Provides text formatting and conversion capabilities for content-generating agents.
"""

from __future__ import annotations

from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Register markdown formatting tools with the MCP server."""

    @mcp.tool()
    def markdown_to_html(
        content: str,
        extensions: list[str] | None = None,
    ) -> dict:
        """
        Convert markdown text to HTML.

        Use this when you need to convert markdown content to HTML for emails,
        web pages, or rich text display.

        Args:
            content: Markdown text to convert (1-100,000 chars)
            extensions: Optional list of markdown extensions to enable
                       (e.g., ["tables", "fenced_code", "codehilite"])

        Returns:
            Dict with HTML output or error message
        """
        try:
            import markdown
        except ImportError:
            return {
                "error": (
                    "markdown library not installed. Install with: "
                    "pip install markdown  or  pip install tools[markdown]"
                )
            }

        try:
            # Validate input
            if not content or not content.strip():
                return {"error": "content cannot be empty"}
            if len(content) > 100_000:
                return {"error": "content must be 100,000 characters or less"}

            # Convert markdown to HTML
            if extensions:
                md = markdown.Markdown(extensions=extensions)
            else:
                # Default extensions for common use cases
                md = markdown.Markdown(extensions=["tables", "fenced_code", "nl2br"])

            html = md.convert(content)

            return {
                "success": True,
                "html": html,
                "input_length": len(content),
                "output_length": len(html),
            }

        except Exception as e:
            return {"error": f"Conversion failed: {str(e)}"}

    @mcp.tool()
    def html_to_markdown(
        html: str,
        strip_tags: bool = False,
    ) -> dict:
        """
        Convert HTML to markdown text.

        Use this when you need to convert HTML content to markdown for
        processing or storage.

        Args:
            html: HTML text to convert (1-100,000 chars)
            strip_tags: If True, remove tags that don't have markdown equivalents

        Returns:
            Dict with markdown output or error message
        """
        try:
            import html2text
        except ImportError:
            return {
                "error": (
                    "html2text library not installed. Install with: "
                    "pip install html2text  or  pip install tools[markdown]"
                )
            }

        try:
            # Validate input
            if not html or not html.strip():
                return {"error": "html cannot be empty"}
            if len(html) > 100_000:
                return {"error": "html must be 100,000 characters or less"}

            # Convert HTML to markdown
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.ignore_emphasis = False
            h.body_width = 0  # Don't wrap lines
            h.skip_internal_links = strip_tags

            markdown_text = h.handle(html)

            return {
                "success": True,
                "markdown": markdown_text,
                "input_length": len(html),
                "output_length": len(markdown_text),
            }

        except Exception as e:
            return {"error": f"Conversion failed: {str(e)}"}

    @mcp.tool()
    def format_text(
        text: str,
        style: str,
    ) -> dict:
        """
        Apply markdown formatting to text.

        Use this when you need to format text with markdown syntax.

        Args:
            text: Text to format (1-10,000 chars)
            style: Formatting style - "bold", "italic", "code", "heading1",
                   "heading2", "heading3", "blockquote", "strikethrough"

        Returns:
            Dict with formatted text or error message
        """
        try:
            # Validate input
            if not text or not text.strip():
                return {"error": "text cannot be empty"}
            if len(text) > 10_000:
                return {"error": "text must be 10,000 characters or less"}

            # Apply formatting
            style = style.lower().strip()
            formatted = text

            if style == "bold":
                formatted = f"**{text}**"
            elif style == "italic":
                formatted = f"*{text}*"
            elif style == "code":
                formatted = f"`{text}`"
            elif style == "heading1":
                formatted = f"# {text}"
            elif style == "heading2":
                formatted = f"## {text}"
            elif style == "heading3":
                formatted = f"### {text}"
            elif style == "blockquote":
                formatted = f"> {text}"
            elif style == "strikethrough":
                formatted = f"~~{text}~~"
            else:
                return {
                    "error": (
                        f"Invalid style: {style}. "
                        "Valid styles: bold, italic, code, heading1, heading2, "
                        "heading3, blockquote, strikethrough"
                    )
                }

            return {
                "success": True,
                "formatted": formatted,
                "style": style,
            }

        except Exception as e:
            return {"error": f"Formatting failed: {str(e)}"}

    @mcp.tool()
    def create_markdown_table(
        headers: list[str],
        rows: list[list[str]],
        alignment: list[str] | None = None,
    ) -> dict:
        """
        Create a markdown table from headers and rows.

        Use this when you need to format data as a markdown table.

        Args:
            headers: List of column headers
            rows: List of rows, where each row is a list of cell values
            alignment: Optional list of alignments for each column
                      ("left", "center", "right"). Defaults to left.

        Returns:
            Dict with markdown table or error message
        """
        try:
            # Validate input
            if not headers:
                return {"error": "headers cannot be empty"}
            if not rows:
                return {"error": "rows cannot be empty"}

            num_cols = len(headers)

            # Validate all rows have same number of columns
            for i, row in enumerate(rows):
                if len(row) != num_cols:
                    return {
                        "error": (
                            f"Row {i} has {len(row)} columns, "
                            f"but headers have {num_cols} columns"
                        )
                    }

            # Set default alignment
            if alignment is None:
                alignment = ["left"] * num_cols
            elif len(alignment) != num_cols:
                return {
                    "error": (
                        f"alignment has {len(alignment)} items, "
                        f"but headers have {num_cols} columns"
                    )
                }

            # Build table
            lines = []

            # Header row
            header_row = "| " + " | ".join(headers) + " |"
            lines.append(header_row)

            # Separator row with alignment
            separators = []
            for align in alignment:
                align = align.lower().strip()
                if align == "center":
                    separators.append(":---:")
                elif align == "right":
                    separators.append("---:")
                else:  # left or default
                    separators.append("---")
            separator_row = "| " + " | ".join(separators) + " |"
            lines.append(separator_row)

            # Data rows
            for row in rows:
                data_row = "| " + " | ".join(str(cell) for cell in row) + " |"
                lines.append(data_row)

            table = "\n".join(lines)

            return {
                "success": True,
                "table": table,
                "num_rows": len(rows),
                "num_cols": num_cols,
            }

        except Exception as e:
            return {"error": f"Table creation failed: {str(e)}"}
