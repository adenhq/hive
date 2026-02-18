"""Utility functions for the Hive framework."""

from framework.utils.io import atomic_write


def validate_path_id(key: str, label: str = "key") -> None:
    """Validate an ID/key that will be used as a filename or path component.

    Prevents path traversal attacks by rejecting dangerous patterns.

    Args:
        key: The ID or key to validate.
        label: Human-readable label for error messages (e.g. "run_id").

    Raises:
        ValueError: If the key contains path traversal or dangerous patterns.
    """
    if not key or key.strip() == "":
        raise ValueError(f"{label} cannot be empty")

    if "/" in key or "\\" in key:
        raise ValueError(f"Invalid {label}: path separators not allowed in '{key}'")

    if ".." in key or key.startswith("."):
        raise ValueError(f"Invalid {label}: path traversal detected in '{key}'")

    if key.startswith("/") or (len(key) > 1 and key[1] == ":"):
        raise ValueError(f"Invalid {label}: absolute paths not allowed in '{key}'")

    if "\x00" in key:
        raise ValueError(f"Invalid {label}: null bytes not allowed")

    dangerous_chars = {"<", ">", "|", "&", "$", "`", "'", '"'}
    if any(char in key for char in dangerous_chars):
        raise ValueError(f"Invalid {label}: contains dangerous characters in '{key}'")


__all__ = ["atomic_write", "validate_path_id"]
