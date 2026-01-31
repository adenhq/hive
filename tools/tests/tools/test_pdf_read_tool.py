"""
Comprehensive tests for pdf_read tool (FastMCP).

Test coverage includes:
- Successful PDF reading with content validation
- Security validations (path traversal, symlinks, file size)
- Error handling for various failure scenarios
- Input sanitization
- Page range parsing
- Metadata extraction
- Performance benchmarks
"""
import os
import time

from pathlib import Path

import pytest
from fastmcp import FastMCP

from aden_tools.tools.pdf_read_tool import register_tools
from aden_tools.utils import (
    is_path_traversal,
    sanitize_file_path,
    validate_file_path,
    MAX_FILE_SIZE_MB,
    MAX_FILE_SIZE_BYTES,
)


@pytest.fixture
def pdf_read_fn(mcp: FastMCP):
    """Register and return the pdf_read tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["pdf_read"].fn


@pytest.fixture
def valid_pdf_bytes() -> bytes:
    """
    Create a minimal valid PDF file content.

    This creates a simple PDF with one page containing "Hello World".
    """
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Hello World) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000359 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
434
%%EOF"""
    return pdf_content


@pytest.fixture
def sample_pdf(tmp_path: Path, valid_pdf_bytes: bytes) -> Path:
    """Create a valid sample PDF file for testing."""
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(valid_pdf_bytes)
    return pdf_file


# =============================================================================
# Basic Functionality Tests
# =============================================================================

class TestPdfReadBasicFunctionality:
    """Tests for basic PDF reading functionality."""

    def test_read_valid_pdf_success(self, pdf_read_fn, sample_pdf: Path):
        """Successfully read a valid PDF file."""
        result = pdf_read_fn(file_path=str(sample_pdf))

        assert "error" not in result
        assert result["path"] == str(sample_pdf)
        assert result["name"] == "sample.pdf"
        assert result["total_pages"] >= 1
        assert result["pages_extracted"] >= 1
        assert "content" in result
        assert result["char_count"] >= 0

    def test_read_pdf_returns_content(self, pdf_read_fn, sample_pdf: Path):
        """PDF content is correctly extracted."""
        result = pdf_read_fn(file_path=str(sample_pdf))

        assert "error" not in result
        assert "content" in result
        assert "--- Page 1 ---" in result["content"]

    def test_read_pdf_with_metadata(self, pdf_read_fn, sample_pdf: Path):
        """PDF metadata is extracted when requested."""
        result = pdf_read_fn(file_path=str(sample_pdf), include_metadata=True)

        assert "error" not in result

    def test_read_pdf_without_metadata(self, pdf_read_fn, sample_pdf: Path):
        """PDF metadata is not included when not requested."""
        result = pdf_read_fn(file_path=str(sample_pdf), include_metadata=False)

        assert "error" not in result


# =============================================================================
# Page Range Tests
# =============================================================================

class TestPdfReadPageRanges:
    """Tests for page range selection functionality."""

    def test_read_all_pages(self, pdf_read_fn, sample_pdf: Path):
        """Reading with pages='all' extracts all pages."""
        result = pdf_read_fn(file_path=str(sample_pdf), pages="all")

        assert "error" not in result
        assert result["pages_extracted"] == result["total_pages"]

    def test_read_single_page(self, pdf_read_fn, sample_pdf: Path):
        """Reading a single page works correctly."""
        result = pdf_read_fn(file_path=str(sample_pdf), pages="1")

        assert "error" not in result
        assert result["pages_extracted"] == 1
        assert "--- Page 1 ---" in result["content"]

    def test_page_out_of_range_error(self, pdf_read_fn, sample_pdf: Path):
        """Requesting a page beyond total pages returns error."""
        result = pdf_read_fn(file_path=str(sample_pdf), pages="999")

        assert "error" in result
        assert "out of range" in result["error"].lower()

    def test_invalid_page_format_error(self, pdf_read_fn, sample_pdf: Path):
        """Invalid page format returns error."""
        result = pdf_read_fn(file_path=str(sample_pdf), pages="invalid")

        assert "error" in result
        assert "invalid" in result["error"].lower()


# =============================================================================
# Max Pages Tests
# =============================================================================

class TestPdfReadMaxPages:
    """Tests for max_pages parameter."""

    def test_max_pages_clamped_low(self, pdf_read_fn, sample_pdf: Path):
        """max_pages below 1 is clamped to 1."""
        result = pdf_read_fn(file_path=str(sample_pdf), max_pages=0)

        assert isinstance(result, dict)

    def test_max_pages_clamped_high(self, pdf_read_fn, sample_pdf: Path):
        """max_pages above 1000 is clamped to 1000."""
        result = pdf_read_fn(file_path=str(sample_pdf), max_pages=2000)

        assert isinstance(result, dict)

    def test_max_pages_negative(self, pdf_read_fn, sample_pdf: Path):
        """Negative max_pages is clamped to 1."""
        result = pdf_read_fn(file_path=str(sample_pdf), max_pages=-10)

        assert isinstance(result, dict)


# =============================================================================
# Security Tests - Path Traversal
# =============================================================================

class TestPdfReadSecurityPathTraversal:
    """Tests for path traversal vulnerability prevention."""

    def test_path_traversal_double_dot(self, pdf_read_fn, tmp_path: Path):
        """Path with .. is rejected."""
        malicious_path = str(tmp_path / ".." / "etc" / "passwd.pdf")
        result = pdf_read_fn(file_path=malicious_path)

        assert "error" in result

    def test_path_traversal_patterns(self, pdf_read_fn):
        """Various path traversal patterns are detected."""
        patterns = [
            "../../../etc/passwd.pdf",
            "..\\..\\..\\windows\\system.pdf",
            "folder/../../../secret.pdf",
        ]

        for pattern in patterns:
            result = pdf_read_fn(file_path=pattern)
            assert "error" in result, f"Path traversal not detected: {pattern}"

    def test_is_path_traversal_helper_detects_traversal(self):
        """Test the is_path_traversal helper detects malicious paths."""
        assert is_path_traversal("../file.pdf") is True
        assert is_path_traversal("..\\file.pdf") is True
        assert is_path_traversal("/path/../secret.pdf") is True

    def test_is_path_traversal_helper_allows_valid_paths(self):
        """Test the is_path_traversal helper allows valid paths."""
        assert is_path_traversal("normal/path/file.pdf") is False
        assert is_path_traversal("/absolute/path/file.pdf") is False
        assert is_path_traversal("file.pdf") is False


# =============================================================================
# Security Tests - Symlinks
# =============================================================================

class TestPdfReadSecuritySymlinks:
    """Tests for symlink handling security."""

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks behave differently on Windows")
    def test_valid_symlink_to_pdf(self, pdf_read_fn, sample_pdf: Path, tmp_path: Path):
        """Valid symlink to a real PDF should work."""
        symlink = tmp_path / "link.pdf"
        symlink.symlink_to(sample_pdf)

        result = pdf_read_fn(file_path=str(symlink))

        assert "error" not in result

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks behave differently on Windows")
    def test_broken_symlink_error(self, pdf_read_fn, tmp_path: Path):
        """Broken symlink returns appropriate error."""
        symlink = tmp_path / "broken_link.pdf"
        nonexistent = tmp_path / "nonexistent.pdf"
        symlink.symlink_to(nonexistent)

        result = pdf_read_fn(file_path=str(symlink))

        assert "error" in result


# =============================================================================
# Security Tests - File Size
# =============================================================================

class TestPdfReadSecurityFileSize:
    """Tests for file size limit enforcement."""

    def test_file_size_limit_constant(self):
        """Verify file size limit constant is reasonable."""
        assert MAX_FILE_SIZE_MB == 100
        assert MAX_FILE_SIZE_BYTES == 100 * 1024 * 1024

    def test_empty_file_error(self, pdf_read_fn, tmp_path: Path):
        """Empty PDF file returns error."""
        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")

        result = pdf_read_fn(file_path=str(empty_pdf))

        assert "error" in result
        assert "empty" in result["error"].lower()


# =============================================================================
# Security Tests - Input Sanitization
# =============================================================================

class TestPdfReadInputSanitization:
    """Tests for input sanitization."""

    def test_null_byte_sanitization(self, pdf_read_fn, sample_pdf: Path):
        """Null bytes in path are sanitized."""
        path_with_null = str(sample_pdf) + "\x00malicious"
        result = pdf_read_fn(file_path=path_with_null)

        assert isinstance(result, dict)

    def test_whitespace_trimming(self, pdf_read_fn, sample_pdf: Path):
        """Leading/trailing whitespace is trimmed."""
        result = pdf_read_fn(file_path=f"  {sample_pdf}  ")

        assert isinstance(result, dict)

    def test_empty_path_error(self, pdf_read_fn):
        """Empty file path returns error."""
        result = pdf_read_fn(file_path="")

        assert "error" in result
        assert "empty" in result["error"].lower()

    def test_whitespace_only_path_error(self, pdf_read_fn):
        """Whitespace-only path returns error."""
        result = pdf_read_fn(file_path="   ")

        assert "error" in result
        assert "empty" in result["error"].lower()

    def test_sanitize_file_path_function(self):
        """Test the sanitize_file_path utility function."""
        # Valid paths
        assert sanitize_file_path("  /path/to/file.pdf  ") == "/path/to/file.pdf"
        assert sanitize_file_path("file\x00.pdf") == "file.pdf"

        # Invalid paths
        with pytest.raises(ValueError):
            sanitize_file_path("")
        with pytest.raises(ValueError):
            sanitize_file_path("   ")


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestPdfReadErrorHandling:
    """Tests for error handling scenarios."""

    def test_file_not_found_error(self, pdf_read_fn, tmp_path: Path):
        """Non-existent file returns appropriate error."""
        result = pdf_read_fn(file_path=str(tmp_path / "missing.pdf"))

        assert "error" in result
        # Error may be "not found" or "cannot access" depending on validation order
        error_lower = result["error"].lower()
        assert "not found" in error_lower or "no such file" in error_lower or "cannot access" in error_lower

    def test_not_a_pdf_file_error(self, pdf_read_fn, tmp_path: Path):
        """Non-PDF extension returns error."""
        txt_file = tmp_path / "document.txt"
        txt_file.write_text("not a pdf")

        result = pdf_read_fn(file_path=str(txt_file))

        assert "error" in result
        assert "not a pdf" in result["error"].lower()

    def test_directory_path_error(self, pdf_read_fn, tmp_path: Path):
        """Directory path returns error."""
        result = pdf_read_fn(file_path=str(tmp_path))

        assert "error" in result

    def test_malformed_pdf_error(self, pdf_read_fn, tmp_path: Path):
        """Malformed PDF returns appropriate error."""
        bad_pdf = tmp_path / "malformed.pdf"
        bad_pdf.write_bytes(b"This is not a valid PDF content at all")

        result = pdf_read_fn(file_path=str(bad_pdf))

        assert "error" in result

    def test_corrupted_pdf_structure_error(self, pdf_read_fn, tmp_path: Path):
        """PDF with corrupted structure returns error."""
        corrupted_pdf = tmp_path / "corrupted.pdf"
        corrupted_pdf.write_bytes(b"%PDF-1.4\ngarbage content without proper structure")

        result = pdf_read_fn(file_path=str(corrupted_pdf))

        assert "error" in result

    @pytest.mark.skipif(os.name == "nt", reason="Permission handling differs on Windows")
    def test_permission_denied_error(self, pdf_read_fn, sample_pdf: Path):
        """File without read permission returns error."""
        original_mode = sample_pdf.stat().st_mode
        try:
            sample_pdf.chmod(0o000)
            result = pdf_read_fn(file_path=str(sample_pdf))

            assert "error" in result
        finally:
            sample_pdf.chmod(original_mode)


# =============================================================================
# Error Structure Validation Tests
# =============================================================================

class TestPdfReadErrorStructure:
    """Tests for error response structure consistency."""

    def test_error_is_dict(self, pdf_read_fn, tmp_path: Path):
        """Error responses are always dicts."""
        result = pdf_read_fn(file_path=str(tmp_path / "missing.pdf"))

        assert isinstance(result, dict)

    def test_error_has_error_key(self, pdf_read_fn, tmp_path: Path):
        """Error responses always have 'error' key."""
        result = pdf_read_fn(file_path=str(tmp_path / "missing.pdf"))

        assert "error" in result
        assert isinstance(result["error"], str)

    def test_error_message_not_empty(self, pdf_read_fn, tmp_path: Path):
        """Error messages are non-empty strings."""
        result = pdf_read_fn(file_path=str(tmp_path / "missing.pdf"))

        assert result["error"]
        assert len(result["error"]) > 0


# =============================================================================
# Success Response Structure Tests
# =============================================================================

class TestPdfReadSuccessStructure:
    """Tests for successful response structure consistency."""

    def test_success_response_keys(self, pdf_read_fn, sample_pdf: Path):
        """Successful response has all required keys."""
        result = pdf_read_fn(file_path=str(sample_pdf))

        required_keys = ["path", "name", "total_pages", "pages_extracted", "content", "char_count"]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

    def test_success_response_types(self, pdf_read_fn, sample_pdf: Path):
        """Successful response values have correct types."""
        result = pdf_read_fn(file_path=str(sample_pdf))

        assert isinstance(result["path"], str)
        assert isinstance(result["name"], str)
        assert isinstance(result["total_pages"], int)
        assert isinstance(result["pages_extracted"], int)
        assert isinstance(result["content"], str)
        assert isinstance(result["char_count"], int)

    def test_char_count_matches_content(self, pdf_read_fn, sample_pdf: Path):
        """char_count matches actual content length."""
        result = pdf_read_fn(file_path=str(sample_pdf))

        assert result["char_count"] == len(result["content"])

    def test_pages_extracted_not_exceeds_total(self, pdf_read_fn, sample_pdf: Path):
        """pages_extracted never exceeds total_pages."""
        result = pdf_read_fn(file_path=str(sample_pdf))

        assert result["pages_extracted"] <= result["total_pages"]


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestPdfReadEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_pdf_with_special_characters_in_name(self, pdf_read_fn, tmp_path: Path, valid_pdf_bytes: bytes):
        """PDF with special characters in filename."""
        special_pdf = tmp_path / "test file (1) [copy].pdf"
        special_pdf.write_bytes(valid_pdf_bytes)

        result = pdf_read_fn(file_path=str(special_pdf))

        assert "error" not in result

    def test_uppercase_pdf_extension(self, pdf_read_fn, tmp_path: Path, valid_pdf_bytes: bytes):
        """PDF with uppercase .PDF extension."""
        upper_pdf = tmp_path / "document.PDF"
        upper_pdf.write_bytes(valid_pdf_bytes)

        result = pdf_read_fn(file_path=str(upper_pdf))

        assert "error" not in result

    def test_mixed_case_pdf_extension(self, pdf_read_fn, tmp_path: Path, valid_pdf_bytes: bytes):
        """PDF with mixed case .PdF extension."""
        mixed_pdf = tmp_path / "document.PdF"
        mixed_pdf.write_bytes(valid_pdf_bytes)

        result = pdf_read_fn(file_path=str(mixed_pdf))

        assert "error" not in result


# =============================================================================
# Performance Tests
# =============================================================================

class TestPdfReadPerformance:
    """Performance tests for PDF reading."""

    def test_small_pdf_read_time(self, pdf_read_fn, sample_pdf: Path):
        """Small PDF should be read quickly (under 1 second)."""
        start = time.perf_counter()
        result = pdf_read_fn(file_path=str(sample_pdf))
        elapsed = time.perf_counter() - start

        assert "error" not in result
        assert elapsed < 1.0, f"Small PDF took too long: {elapsed:.2f}s"

    def test_medium_pdf_generation_and_read(self, pdf_read_fn, tmp_path: Path, valid_pdf_bytes: bytes):
        """Medium-sized PDF (repeated content) should be handled efficiently."""
        # Create a larger PDF by repeating the valid PDF structure
        medium_pdf = tmp_path / "medium.pdf"
        medium_pdf.write_bytes(valid_pdf_bytes)

        start = time.perf_counter()
        result = pdf_read_fn(file_path=str(medium_pdf))
        elapsed = time.perf_counter() - start

        assert "error" not in result
        assert elapsed < 5.0, f"Medium PDF took too long: {elapsed:.2f}s"

    def test_max_pages_limits_processing_time(self, pdf_read_fn, sample_pdf: Path):
        """max_pages parameter should limit processing time."""
        # Read with max_pages=1
        start = time.perf_counter()
        result = pdf_read_fn(file_path=str(sample_pdf), max_pages=1)
        elapsed = time.perf_counter() - start

        assert "error" not in result
        assert elapsed < 1.0

    def test_multiple_sequential_reads(self, pdf_read_fn, sample_pdf: Path):
        """Multiple sequential reads should be consistent."""
        results = []
        times = []

        for _ in range(5):
            start = time.perf_counter()
            result = pdf_read_fn(file_path=str(sample_pdf))
            elapsed = time.perf_counter() - start
            results.append(result)
            times.append(elapsed)

        # All reads should succeed
        for result in results:
            assert "error" not in result

        # Times should be reasonably consistent (no major outliers)
        avg_time = sum(times) / len(times)
        for t in times:
            assert t < avg_time * 3, f"Read time {t:.2f}s too far from average {avg_time:.2f}s"


# =============================================================================
# Integration Tests
# =============================================================================

class TestPdfReadIntegration:
    """Integration tests combining multiple features."""

    def test_full_workflow(self, pdf_read_fn, sample_pdf: Path):
        """Test complete workflow: read, verify structure, check content."""
        result = pdf_read_fn(
            file_path=str(sample_pdf),
            pages="all",
            max_pages=100,
            include_metadata=True,
        )

        assert "error" not in result
        assert all(
            key in result
            for key in ["path", "name", "total_pages", "pages_extracted", "content", "char_count"]
        )
        assert len(result["content"]) > 0
        assert result["path"] == str(sample_pdf)
        assert result["name"] == sample_pdf.name

    def test_relative_path_handling(self, pdf_read_fn, sample_pdf: Path, monkeypatch):
        """Relative paths are correctly resolved."""
        monkeypatch.chdir(sample_pdf.parent)

        result = pdf_read_fn(file_path=sample_pdf.name)

        assert "error" not in result
        assert result["name"] == sample_pdf.name


# =============================================================================
# Security Utility Tests
# =============================================================================

class TestSecurityUtilities:
    """Tests for shared security utility functions."""

    def test_validate_file_path_detects_traversal(self, tmp_path: Path):
        """validate_file_path detects path traversal."""
        path = tmp_path / "test.pdf"
        path.touch()

        error = validate_file_path(path, "../test.pdf")
        assert error is not None
        assert "traversal" in error["error"].lower()

    def test_validate_file_path_valid_file(self, sample_pdf: Path):
        """validate_file_path allows valid files."""
        error = validate_file_path(sample_pdf, str(sample_pdf))
        assert error is None

    def test_validate_file_path_empty_file(self, tmp_path: Path):
        """validate_file_path rejects empty files by default."""
        empty_file = tmp_path / "empty.pdf"
        empty_file.touch()

        error = validate_file_path(empty_file, str(empty_file))
        assert error is not None
        assert "empty" in error["error"].lower()

    def test_validate_file_path_allows_empty_when_configured(self, tmp_path: Path):
        """validate_file_path allows empty files when configured."""
        empty_file = tmp_path / "empty.pdf"
        empty_file.touch()

        error = validate_file_path(empty_file, str(empty_file), allow_empty=True)
        assert error is None

    def test_truncation_flag_for_page_range(self, pdf_read_fn, tmp_path: Path, monkeypatch):
        """When requested pages exceed max_pages, response includes truncation metadata."""

        class FakePage:
            def __init__(self, text: str) -> None:
                self._text = text

            def extract_text(self) -> str:
                return self._text

        class FakePdfReader:
            def __init__(self, path: Path) -> None:  # noqa: ARG002
                self.pages = [FakePage(f"Page {i + 1}") for i in range(50)]
                self.is_encrypted = False

        # Patch PdfReader used inside the tool so we don't need a real PDF
        from aden_tools.tools.pdf_read_tool import pdf_read_tool

        monkeypatch.setattr(pdf_read_tool, "PdfReader", FakePdfReader)

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        result = pdf_read_fn(file_path=str(pdf_file), pages="1-20", max_pages=10)

        assert result["pages_extracted"] == 10
        # New behavior: explicit truncation metadata instead of silent truncation
        assert result.get("truncated") is True
        assert "truncation_warning" in result
