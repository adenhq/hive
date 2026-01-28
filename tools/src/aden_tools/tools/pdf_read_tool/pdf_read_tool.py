"""
PDF Read Tool

Provides a FastMCP-compatible tool for extracting text content
from PDF files using pypdf.

Features:
- Supports reading all pages or selected page ranges
- Enforces page limits for memory safety
- Handles common error cases (missing files, invalid PDFs, encryption)
- Optionally extracts PDF metadata (author, title, dates)

This tool is intended for document ingestion, analysis pipelines,
and agent-based workflows that require reliable PDF text extraction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from pypdf import PdfReader


def register_tools(mcp: FastMCP) -> None:
    """
    Register the PDF read tool with the FastMCP server.

    This makes the `pdf_read` tool available for invocation
    by agents and MCP-compatible clients.
    """

    def parse_page_range(
        pages: str | None, total_pages: int, max_pages: int
    ) -> list[int] | dict:
        """
        Parse a user-provided page range string into 0-indexed page numbers.

        Supported formats:
        - None or "all": extract all pages (up to max_pages)
        - "5": extract a single page
        - "1-10": extract a page range (inclusive)
        - "1,3,5": extract specific pages

        Returns:
            A list of 0-indexed page numbers on success,
            or a dict with an "error" message on failure.
        """
        if pages is None or pages.lower() == "all":
            return list(range(min(total_pages, max_pages)))

        try:
            if pages.isdigit():
                page_num = int(pages)
                if page_num < 1 or page_num > total_pages:
                    return {"error": f"Page {page_num} out of range. PDF has {total_pages} pages."}
                return [page_num - 1]

            if "-" in pages and "," not in pages:
                start_str, end_str = pages.split("-", 1)
                start, end = int(start_str), int(end_str)

                if start > end:
                    return {"error": f"Invalid page range: {pages}. Start must be <= end."}
                if start < 1:
                    return {"error": f"Page numbers start at 1, got {start}."}
                if end > total_pages:
                    return {"error": f"Page {end} out of range. PDF has {total_pages} pages."}

                return list(range(start - 1, min(end, start - 1 + max_pages)))

            if "," in pages:
                page_nums = [int(p.strip()) for p in pages.split(",")]
                for p in page_nums:
                    if p < 1 or p > total_pages:
                        return {"error": f"Page {p} out of range. PDF has {total_pages} pages."}

                return [p - 1 for p in page_nums[:max_pages]]

            return {"error": f"Invalid page format: '{pages}'."}

        except ValueError as exc:
            return {"error": f"Invalid page format: '{pages}'. {exc}"}

    @mcp.tool()
    def pdf_read(
        file_path: str,
        pages: str | None = None,
        max_pages: int = 100,
        include_metadata: bool = True,
    ) -> dict:
        """
        Extract text content from a PDF file.

        This tool reads a local PDF file and returns extracted text
        along with optional metadata. Page extraction can be limited
        using ranges or a maximum page count for safety.

        Args:
            file_path: Absolute or relative path to the PDF file.
            pages: Page selection format:
                - None or "all": all pages
                - "5": single page
                - "1-10": page range
                - "1,3,5": specific pages
            max_pages: Maximum number of pages to extract (1–1000).
            include_metadata: Whether to include PDF metadata.

        Returns:
            On success, a dict containing:
            - path: Absolute file path
            - name: File name
            - total_pages: Total page count
            - pages_extracted: Number of pages extracted
            - content: Extracted text with page markers
            - char_count: Character count of extracted text
            - metadata (optional): PDF metadata

            On failure, returns a dict with an "error" key.
        """
        try:
            path = Path(file_path).resolve()

            if not path.exists():
                return {"error": f"PDF file not found: {file_path}"}
            if not path.is_file():
                return {"error": f"Not a file: {file_path}"}
            if path.suffix.lower() != ".pdf":
                return {"error": f"Not a PDF file: {file_path}"}

            max_pages = max(1, min(max_pages, 1000))

            reader = PdfReader(path)

            if reader.is_encrypted:
                return {"error": "Cannot read encrypted PDF."}

            total_pages = len(reader.pages)

            page_indices = parse_page_range(pages, total_pages, max_pages)
            if isinstance(page_indices, dict):
                return page_indices

            content_parts = []
            for idx in page_indices:
                text = reader.pages[idx].extract_text() or ""
                content_parts.append(f"--- Page {idx + 1} ---\n{text}")

            content = "\n\n".join(content_parts)

            result: dict[str, Any] = {
                "path": str(path),
                "name": path.name,
                "total_pages": total_pages,
                "pages_extracted": len(page_indices),
                "content": content,
                "char_count": len(content),
            }

            if include_metadata and reader.metadata:
                meta = reader.metadata
                result["metadata"] = {
                    "title": meta.get("/Title"),
                    "author": meta.get("/Author"),
                    "subject": meta.get("/Subject"),
                    "creator": meta.get("/Creator"),
                    "producer": meta.get("/Producer"),
                    "created": str(meta.get("/CreationDate")) if meta.get("/CreationDate") else None,
                    "modified": str(meta.get("/ModDate")) if meta.get("/ModDate") else None,
                }

            return result

        except PermissionError:
            return {"error": f"Permission denied: {file_path}"}
        except Exception as exc:
            return {"error": f"Failed to read PDF: {exc}"}
