"""Tests for markdown_tool - Text formatting and markdown/HTML conversion."""

import pytest
from fastmcp import FastMCP

from aden_tools.tools.markdown_tool.markdown_tool import register_tools


@pytest.fixture
def markdown_tools(mcp: FastMCP):
    """Register and return markdown tool functions."""
    register_tools(mcp)
    return {
        "markdown_to_html": mcp._tool_manager._tools["markdown_to_html"].fn,
        "html_to_markdown": mcp._tool_manager._tools["html_to_markdown"].fn,
        "format_text": mcp._tool_manager._tools["format_text"].fn,
        "create_markdown_table": mcp._tool_manager._tools["create_markdown_table"].fn,
    }


class TestMarkdownToHtml:
    """Tests for markdown_to_html function."""

    def test_basic_conversion(self, markdown_tools):
        """Convert simple markdown to HTML."""
        result = markdown_tools["markdown_to_html"](content="# Hello\n\nWorld")

        assert result["success"] is True
        assert "<h1>Hello</h1>" in result["html"]
        assert "<p>World</p>" in result["html"]

    def test_bold_and_italic(self, markdown_tools):
        """Convert markdown with bold and italic."""
        result = markdown_tools["markdown_to_html"](content="**bold** and *italic*")

        assert result["success"] is True
        assert "<strong>bold</strong>" in result["html"]
        assert "<em>italic</em>" in result["html"]

    def test_lists(self, markdown_tools):
        """Convert markdown lists."""
        result = markdown_tools["markdown_to_html"](content="- Item 1\n- Item 2")

        assert result["success"] is True
        assert "<ul>" in result["html"]
        assert "<li>Item 1</li>" in result["html"]

    def test_empty_content_error(self, markdown_tools):
        """Empty content returns error."""
        result = markdown_tools["markdown_to_html"](content="")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_whitespace_only_error(self, markdown_tools):
        """Whitespace-only content returns error."""
        result = markdown_tools["markdown_to_html"](content="   \n\n   ")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_content_too_long_error(self, markdown_tools):
        """Content over 100,000 chars returns error."""
        long_content = "a" * 100_001
        result = markdown_tools["markdown_to_html"](content=long_content)

        assert "error" in result
        assert "100,000 characters" in result["error"]

    def test_max_length_valid(self, markdown_tools):
        """Content exactly 100,000 chars is valid."""
        max_content = "a" * 100_000
        result = markdown_tools["markdown_to_html"](content=max_content)

        assert result["success"] is True

    def test_returns_lengths(self, markdown_tools):
        """Returns input and output lengths."""
        result = markdown_tools["markdown_to_html"](content="# Test")

        assert "input_length" in result
        assert "output_length" in result
        assert result["input_length"] == 6


class TestHtmlToMarkdown:
    """Tests for html_to_markdown function."""

    def test_basic_conversion(self, markdown_tools):
        """Convert simple HTML to markdown."""
        result = markdown_tools["html_to_markdown"](html="<h1>Hello</h1><p>World</p>")

        assert result["success"] is True
        assert "# Hello" in result["markdown"]
        assert "World" in result["markdown"]

    def test_bold_and_italic(self, markdown_tools):
        """Convert HTML with bold and italic."""
        result = markdown_tools["html_to_markdown"](
            html="<strong>bold</strong> and <em>italic</em>"
        )

        assert result["success"] is True
        assert "**bold**" in result["markdown"]
        assert "*italic*" in result["markdown"] or "_italic_" in result["markdown"]

    def test_links(self, markdown_tools):
        """Convert HTML links."""
        result = markdown_tools["html_to_markdown"](html='<a href="https://example.com">link</a>')

        assert result["success"] is True
        assert "[link]" in result["markdown"]
        assert "https://example.com" in result["markdown"]

    def test_empty_html_error(self, markdown_tools):
        """Empty HTML returns error."""
        result = markdown_tools["html_to_markdown"](html="")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_html_too_long_error(self, markdown_tools):
        """HTML over 100,000 chars returns error."""
        long_html = "<p>" + ("a" * 100_000) + "</p>"
        result = markdown_tools["html_to_markdown"](html=long_html)

        assert "error" in result
        assert "100,000 characters" in result["error"]


class TestFormatText:
    """Tests for format_text function."""

    def test_bold_formatting(self, markdown_tools):
        """Apply bold formatting."""
        result = markdown_tools["format_text"](text="Hello", style="bold")

        assert result["success"] is True
        assert result["formatted"] == "**Hello**"
        assert result["style"] == "bold"

    def test_italic_formatting(self, markdown_tools):
        """Apply italic formatting."""
        result = markdown_tools["format_text"](text="Hello", style="italic")

        assert result["success"] is True
        assert result["formatted"] == "*Hello*"

    def test_code_formatting(self, markdown_tools):
        """Apply code formatting."""
        result = markdown_tools["format_text"](text="print('hi')", style="code")

        assert result["success"] is True
        assert result["formatted"] == "`print('hi')`"

    def test_heading1_formatting(self, markdown_tools):
        """Apply heading1 formatting."""
        result = markdown_tools["format_text"](text="Title", style="heading1")

        assert result["success"] is True
        assert result["formatted"] == "# Title"

    def test_heading2_formatting(self, markdown_tools):
        """Apply heading2 formatting."""
        result = markdown_tools["format_text"](text="Subtitle", style="heading2")

        assert result["success"] is True
        assert result["formatted"] == "## Subtitle"

    def test_heading3_formatting(self, markdown_tools):
        """Apply heading3 formatting."""
        result = markdown_tools["format_text"](text="Section", style="heading3")

        assert result["success"] is True
        assert result["formatted"] == "### Section"

    def test_blockquote_formatting(self, markdown_tools):
        """Apply blockquote formatting."""
        result = markdown_tools["format_text"](text="Quote", style="blockquote")

        assert result["success"] is True
        assert result["formatted"] == "> Quote"

    def test_strikethrough_formatting(self, markdown_tools):
        """Apply strikethrough formatting."""
        result = markdown_tools["format_text"](text="Old", style="strikethrough")

        assert result["success"] is True
        assert result["formatted"] == "~~Old~~"

    def test_case_insensitive_style(self, markdown_tools):
        """Style is case-insensitive."""
        result = markdown_tools["format_text"](text="Test", style="BOLD")

        assert result["success"] is True
        assert result["formatted"] == "**Test**"

    def test_invalid_style_error(self, markdown_tools):
        """Invalid style returns error."""
        result = markdown_tools["format_text"](text="Test", style="invalid")

        assert "error" in result
        assert "Invalid style" in result["error"]

    def test_empty_text_error(self, markdown_tools):
        """Empty text returns error."""
        result = markdown_tools["format_text"](text="", style="bold")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_text_too_long_error(self, markdown_tools):
        """Text over 10,000 chars returns error."""
        long_text = "a" * 10_001
        result = markdown_tools["format_text"](text=long_text, style="bold")

        assert "error" in result
        assert "10,000 characters" in result["error"]


class TestCreateMarkdownTable:
    """Tests for create_markdown_table function."""

    def test_basic_table(self, markdown_tools):
        """Create basic markdown table."""
        result = markdown_tools["create_markdown_table"](
            headers=["Name", "Age"], rows=[["Alice", "30"], ["Bob", "25"]]
        )

        assert result["success"] is True
        assert "| Name | Age |" in result["table"]
        assert "| --- | --- |" in result["table"]
        assert "| Alice | 30 |" in result["table"]
        assert "| Bob | 25 |" in result["table"]
        assert result["num_rows"] == 2
        assert result["num_cols"] == 2

    def test_table_with_left_alignment(self, markdown_tools):
        """Create table with left alignment."""
        result = markdown_tools["create_markdown_table"](
            headers=["A", "B"], rows=[["1", "2"]], alignment=["left", "left"]
        )

        assert result["success"] is True
        assert "| --- | --- |" in result["table"]

    def test_table_with_center_alignment(self, markdown_tools):
        """Create table with center alignment."""
        result = markdown_tools["create_markdown_table"](
            headers=["A", "B"], rows=[["1", "2"]], alignment=["center", "center"]
        )

        assert result["success"] is True
        assert "| :---: | :---: |" in result["table"]

    def test_table_with_right_alignment(self, markdown_tools):
        """Create table with right alignment."""
        result = markdown_tools["create_markdown_table"](
            headers=["A", "B"], rows=[["1", "2"]], alignment=["right", "right"]
        )

        assert result["success"] is True
        assert "| ---: | ---: |" in result["table"]

    def test_table_with_mixed_alignment(self, markdown_tools):
        """Create table with mixed alignment."""
        result = markdown_tools["create_markdown_table"](
            headers=["Name", "Score", "Status"],
            rows=[["Alice", "95", "Pass"]],
            alignment=["left", "right", "center"],
        )

        assert result["success"] is True
        assert "| --- | ---: | :---: |" in result["table"]

    def test_empty_headers_error(self, markdown_tools):
        """Empty headers returns error."""
        result = markdown_tools["create_markdown_table"](headers=[], rows=[["1"]])

        assert "error" in result
        assert "headers cannot be empty" in result["error"]

    def test_empty_rows_error(self, markdown_tools):
        """Empty rows returns error."""
        result = markdown_tools["create_markdown_table"](headers=["A"], rows=[])

        assert "error" in result
        assert "rows cannot be empty" in result["error"]

    def test_mismatched_columns_error(self, markdown_tools):
        """Mismatched column count returns error."""
        result = markdown_tools["create_markdown_table"](headers=["A", "B"], rows=[["1", "2", "3"]])

        assert "error" in result
        assert "has 3 columns" in result["error"]
        assert "headers have 2 columns" in result["error"]

    def test_mismatched_alignment_error(self, markdown_tools):
        """Mismatched alignment count returns error."""
        result = markdown_tools["create_markdown_table"](
            headers=["A", "B"], rows=[["1", "2"]], alignment=["left"]
        )

        assert "error" in result
        assert "alignment has 1 items" in result["error"]
        assert "headers have 2 columns" in result["error"]

    def test_default_alignment(self, markdown_tools):
        """Default alignment is left."""
        result = markdown_tools["create_markdown_table"](
            headers=["A"], rows=[["1"]], alignment=None
        )

        assert result["success"] is True
        assert "| --- |" in result["table"]
