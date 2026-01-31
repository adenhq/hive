"""
Security utilities for file path validation and input sanitization.

This module provides reusable security functions for validating file paths,
detecting path traversal attempts, and enforcing file size limits.

These utilities follow the security patterns established in file_system_toolkits
but are designed for tools that don't require the full sandbox architecture.
"""
from __future__ import annotations

import os
from pathlib import Path

# Security constants
MAX_FILE_SIZE_MB = 100  # Maximum file size in megabytes
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def is_path_traversal(file_path: str) -> bool:
    """
    Check if the path contains path traversal attempts.

    Detects common path traversal patterns like '../' and '..\\' that could
    be used to access files outside the intended directory.

    Args:
        file_path: The file path to check

    Returns:
        True if path traversal is detected, False otherwise

    Examples:
        >>> is_path_traversal("../etc/passwd")
        True
        >>> is_path_traversal("/normal/path/file.pdf")
        False
    """
    traversal_patterns = [
        "..",
        "..\\",
        "../",
        "/..",
        "\\..",
    ]

    for pattern in traversal_patterns:
        if pattern in file_path:
            return True

    return False


def sanitize_file_path(file_path: str) -> str:
    """
    Sanitize a file path by removing dangerous characters and whitespace.

    Args:
        file_path: The file path to sanitize

    Returns:
        Sanitized file path

    Raises:
        ValueError: If path is empty after sanitization
    """
    # Strip whitespace and null bytes
    sanitized = file_path.strip().replace("\x00", "")

    if not sanitized:
        raise ValueError("File path cannot be empty")

    return sanitized


def validate_file_path(
    path: Path,
    original_path: str,
    *,
    check_traversal: bool = True,
    check_symlink: bool = True,
    check_size: bool = True,
    max_size_bytes: int = MAX_FILE_SIZE_BYTES,
    allow_empty: bool = False,
) -> dict | None:
    """
    Perform security validations on a file path.

    This function validates a resolved Path object against various security
    concerns including path traversal, symlink targets, and file size limits.

    Args:
        path: Resolved Path object
        original_path: Original path string provided by user (for error messages)
        check_traversal: Whether to check for path traversal in original input
        check_symlink: Whether to validate symlink targets
        check_size: Whether to enforce file size limits
        max_size_bytes: Maximum allowed file size in bytes
        allow_empty: Whether to allow empty files (default: False)

    Returns:
        Error dict if validation fails, None if valid

    Examples:
        >>> path = Path("/tmp/test.pdf").resolve()
        >>> error = validate_file_path(path, "../test.pdf")
        >>> if error:
        ...     print(error["error"])
    """
    # Check for path traversal in original input
    if check_traversal and is_path_traversal(original_path):
        return {"error": f"Invalid path: path traversal detected in '{original_path}'"}

    # Check if file is a symlink and validate target
    if check_symlink and path.is_symlink():
        try:
            real_path = path.resolve(strict=True)
            if not real_path.is_file():
                return {"error": f"Symlink does not point to a valid file: {original_path}"}
        except (OSError, RuntimeError):
            return {"error": f"Cannot resolve symlink: {original_path}"}

    # Check file size
    if check_size:
        try:
            file_size = path.stat().st_size
            if file_size > max_size_bytes:
                size_mb = file_size / (1024 * 1024)
                max_mb = max_size_bytes / (1024 * 1024)
                return {
                    "error": f"File too large: {size_mb:.1f}MB exceeds limit of {max_mb:.0f}MB"
                }
            if not allow_empty and file_size == 0:
                return {"error": f"File is empty: {original_path}"}
        except OSError as e:
            return {"error": f"Cannot access file: {str(e)}"}

    return None
