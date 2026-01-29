"""
PDF Read Tool - Parse and extract text from PDF files.

Uses pypdf to read PDF documents and extract text content
along with metadata.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

import logging

from fastmcp import FastMCP
from pypdf import PdfReader

from aden_tools.utils.logging import get_logger

logger = get_logger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register PDF read tools with the MCP server."""

    def parse_page_range(
        pages: str | None, total_pages: int, max_pages: int
    ) -> List[int] | dict:
        """
        Parse page range string into list of 0-indexed page numbers.

        Returns list of indices or error dict.
        """
        if pages is None or pages.lower() == "all":
            indices = list(range(min(total_pages, max_pages)))
            return indices

        try:
            # Single page: "5"
            if pages.isdigit():
                page_num = int(pages)
                if page_num < 1 or page_num > total_pages:
                    return {"error": f"Page {page_num} out of range. PDF has {total_pages} pages."}
                return [page_num - 1]

            # Range: "1-10"
            if "-" in pages and "," not in pages:
                start_str, end_str = pages.split("-", 1)
                start, end = int(start_str), int(end_str)
                if start > end:
                    return {"error": f"Invalid page range: {pages}. Start must be less than end."}
                if start < 1:
                    return {"error": f"Page numbers start at 1, got {start}."}
                if end > total_pages:
                    return {"error": f"Page {end} out of range. PDF has {total_pages} pages."}
                indices = list(range(start - 1, min(end, start - 1 + max_pages)))
                return indices

            # Comma-separated: "1,3,5"
            if "," in pages:
                page_nums = [int(p.strip()) for p in pages.split(",")]
                for p in page_nums:
                    if p < 1 or p > total_pages:
                        return {"error": f"Page {p} out of range. PDF has {total_pages} pages."}
                indices = [p - 1 for p in page_nums[:max_pages]]
                return indices

            return {"error": f"Invalid page format: '{pages}'. Use 'all', '5', '1-10', or '1,3,5'."}

        except ValueError as e:
            return {"error": f"Invalid page format: '{pages}'. {str(e)}"}

    @mcp.tool()
    def pdf_read(
        file_path: str,
        pages: str | None = None,
        max_pages: int = 100,
        include_metadata: bool = True,
    ) -> dict:
        """
        Read and extract text content from a PDF file.

        Returns text content with page markers and optional metadata.
        Use for reading PDFs, reports, documents, or any PDF file.

        Args:
            file_path: Path to the PDF file to read (absolute or relative)
            pages: Page range to extract - 'all'/None for all, '5' for single, '1-10' for range, '1,3,5' for specific
            max_pages: Maximum number of pages to process (1-1000, memory safety)
            include_metadata: Include PDF metadata (author, title, creation date, etc.)

        Returns:
            Dict with extracted text and metadata, or error dict
        """

        log_ctx = {"input": {"file_path": file_path, "pages_req": pages, "max_pages": max_pages}}
        try:
            path = Path(file_path).resolve()

            #Update context with absolute path (more secure)
            log_ctx["abs_path"] = str(path)

            # Validate file exists
            if not path.exists():
                logger.warning("PDF file not found", extra=log_ctx)
                return {"error": f"PDF file not found: {file_path}"}

            if not path.is_file():
                logger.warning("Path is not a file", extra=log_ctx)
                return {"error": f"Not a file: {file_path}"}

            # Check extension
            if path.suffix.lower() != ".pdf":
                logger.warning("Invalid file extension", extra=log_ctx)
                return {"error": f"Not a PDF file (expected .pdf): {file_path}"}

            # Validate max_pages
            if max_pages < 1:
                max_pages = 1
            elif max_pages > 1000:
                max_pages = 1000

            #-- START PROCESSING --#

            logger.info("Opening PDF file", extra=log_ctx)

            # Open and read PDF
            reader = PdfReader(path)

            # Check for encryption
            if reader.is_encrypted:
                # logger.warning("Cannot read encrypted PDF. Password required.", extra={"file_path": str(path), "pages": pages})
                return {"error": "Cannot read encrypted PDF. Password required."}

            total_pages = len(reader.pages)

            # Parse page range
            page_indices = parse_page_range(pages, total_pages, max_pages)
            if isinstance(page_indices, dict):  # Error dict
                #Log detail error parsing page
                log_ctx["error_detail"] = page_indices.get("error")
                logger.warning("Invalid page range requested", extra=log_ctx)
                return page_indices

            # Extract text from pages
            content_parts = []
            for i in page_indices:
                page_text = reader.pages[i].extract_text() or ""
                content_parts.append(f"--- Page {i + 1} ---\n{page_text}")

            content = "\n\n".join(content_parts)

            result: dict[str, Any] = {
                "path": str(path),
                "name": path.name,
                "total_pages": total_pages,
                "pages_extracted": len(page_indices),
                "content": content,
                "char_count": len(content),
            }

            # Add metadata if requested
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

            # --SUCCESS LOGGING--#
            logger.info(
                "PDF read success", 
                extra={
                "abs_path": str(path),
                "total_pages":total_pages, 
                "extracted_pages": len(page_indices), 
                "char_count":len(content)
                }
            )

            return result

        except PermissionError:
            logger.error("Permission denied", extra=log_ctx)
            return {"error": f"Permission denied: {file_path}"}
        
        except Exception as e:
            log_ctx["error_msg"]=str(e)
            logger.error("Unexpected error reading PDF", extra=log_ctx)
            return {"error": f"Failed to read PDF: {str(e)}"}
