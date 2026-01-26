"""
Security validation for MCP server configuration.

This module provides validation functions to prevent RCE vulnerabilities
when registering MCP servers with STDIO transport.

All sanitization and validation logic is centralized here for:
- Easy maintenance
- Future extensions
- Consistent security checks
"""

import os
from pathlib import Path
from typing import Tuple


# Whitelist of allowed commands for STDIO transport
ALLOWED_COMMANDS = {
    "python",
    "python3",
    "node",
    "npx",
}

# Dangerous characters that could be used for shell injection
DANGEROUS_CHARS = [
    ';',  # Command separator
    '&',  # Background process
    '|',  # Pipe
    '`',  # Command substitution
    '$',  # Variable expansion
    '(',  # Command grouping
    ')',  # Command grouping
    '<',  # Input redirection
    '>',  # Output redirection
    '\n', # Newline (command chaining)
    '\r', # Carriage return
]

# Dangerous environment variables that should not be overridden
DANGEROUS_ENV_VARS = [
    'LD_PRELOAD',      # Library hijacking (Linux)
    'LD_LIBRARY_PATH', # Library path manipulation (Linux)
    'PATH',            # Command path manipulation
    'PYTHONPATH',      # Python module hijacking
    'DYLD_INSERT_LIBRARIES',  # Library hijacking (macOS)
    'DYLD_LIBRARY_PATH',     # Library path manipulation (macOS)
]


def validate_mcp_stdio_config(
    command: str,
    args: list[str],
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> Tuple[bool, str]:
    """
    Validate MCP STDIO configuration for security.
    
    This function performs comprehensive validation to prevent RCE vulnerabilities:
    - Checks if STDIO transport is allowed (via environment variable)
    - Validates command is in whitelist
    - Validates args don't contain shell injection characters
    - Validates cwd is within safe directories
    - Validates env doesn't contain dangerous variables
    
    Args:
        command: Command to execute (e.g., "python")
        args: List of command arguments
        cwd: Working directory (optional)
        env: Environment variables (optional)
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if configuration is safe, False otherwise
        - error_message: Empty string if valid, error description if invalid
    """
    # 1. Check if STDIO transport is allowed
    if not is_stdio_transport_allowed():
        return False, (
            "STDIO transport requires ADEN_ALLOW_UNSAFE_MCP_STDIO=true. "
            "Set this environment variable to enable STDIO transport (use with caution)."
        )
    
    # 2. Validate command is in whitelist
    validation_result = validate_command(command)
    if not validation_result[0]:
        return validation_result
    
    # 3. Validate args don't contain shell injection characters
    validation_result = validate_args(args)
    if not validation_result[0]:
        return validation_result
    
    # 4. Validate cwd is within safe directories
    if cwd:
        validation_result = validate_cwd(cwd)
        if not validation_result[0]:
            return validation_result
    
    # 5. Validate env doesn't contain dangerous variables
    if env:
        validation_result = validate_env(env)
        if not validation_result[0]:
            return validation_result
    
    # All validations passed
    return True, ""


def is_stdio_transport_allowed() -> bool:
    """
    Check if STDIO transport is allowed via environment variable.
    
    Returns:
        True if ADEN_ALLOW_UNSAFE_MCP_STDIO=true, False otherwise
    """
    return os.getenv("ADEN_ALLOW_UNSAFE_MCP_STDIO", "false").lower() == "true"


def validate_command(command: str) -> Tuple[bool, str]:
    """
    Validate that the command is in the allowed whitelist.
    
    Args:
        command: Command to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not command:
        return False, "Command is required for STDIO transport"
    
    # Extract just the executable name (handle paths like "/usr/bin/python")
    command_base = Path(command).name
    
    if command_base not in ALLOWED_COMMANDS:
        return False, (
            f"Command '{command_base}' is not in the allowed whitelist. "
            f"Allowed commands: {sorted(ALLOWED_COMMANDS)}"
        )
    
    return True, ""


def validate_args(args: list[str]) -> Tuple[bool, str]:
    """
    Validate that args don't contain shell injection characters.
    
    Args:
        args: List of command arguments to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(args, list):
        return False, "Args must be a list"
    
    for i, arg in enumerate(args):
        if not isinstance(arg, str):
            return False, f"Args[{i}] must be a string, got {type(arg).__name__}"
        
        # Check for dangerous characters
        found_chars = [char for char in DANGEROUS_CHARS if char in arg]
        if found_chars:
            return False, (
                f"Potentially dangerous character(s) in args[{i}]: {found_chars}. "
                f"This could be used for shell injection attacks."
            )
    
    return True, ""


def validate_cwd(cwd: str) -> Tuple[bool, str]:
    """
    Validate that the working directory is within safe base directories.
    
    Args:
        cwd: Working directory path to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        cwd_path = Path(cwd).resolve()
    except (OSError, ValueError) as e:
        return False, f"Invalid working directory path '{cwd}': {e}"
    
    # Define safe base directories
    # Get the project root (assuming this file is in core/framework/mcp/)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent.resolve()
    
    SAFE_BASE_DIRS = [
        Path.cwd().resolve(),  # Current working directory
        project_root,          # Project root
    ]
    
    # Check if cwd is within any safe directory
    is_safe = any(
        str(cwd_path).startswith(str(base)) 
        for base in SAFE_BASE_DIRS
    )
    
    if not is_safe:
        return False, (
            f"Working directory '{cwd}' (resolved to '{cwd_path}') is outside safe base directories. "
            f"Safe directories: {[str(d) for d in SAFE_BASE_DIRS]}"
        )
    
    return True, ""


def validate_env(env: dict[str, str]) -> Tuple[bool, str]:
    """
    Validate that environment variables don't include dangerous ones.
    
    Args:
        env: Dictionary of environment variables to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(env, dict):
        return False, "Env must be a dictionary"
    
    for key in env.keys():
        if not isinstance(key, str):
            return False, f"Env keys must be strings, got {type(key).__name__}"
        
        if key in DANGEROUS_ENV_VARS:
            return False, (
                f"Environment variable '{key}' cannot be overridden for security reasons. "
                f"This variable could be used to hijack execution or manipulate system behavior."
            )
    
    return True, ""


# Future extension point: Add more validation functions here as needed
# Example:
# def validate_additional_security_check(...) -> Tuple[bool, str]:
#     """Add new security checks here"""
#     pass
