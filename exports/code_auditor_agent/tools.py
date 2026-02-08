
import os
from core.framework.runner.tool_registry import tool

@tool(description="Reads the content of a local code file for auditing.")
def read_code_file(file_path: str) -> str:
    """
    Reads a file from the filesystem.
    
    Args:
        file_path: Absolute or relative path to the code file.
        
    Returns:
        The content of the file or an error message.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool(description="Formats a bug list into a professional markdown report.")
def format_audit_report(bugs: list, file_name: str) -> str:
    """
    Creates a formatted markdown report.
    """
    report = f"# Code Audit Report: {file_name}\n\n"
    if not bugs:
        report += "✅ No critical bugs identified.\n"
    else:
        for i, bug in enumerate(bugs, 1):
            report += f"### {i}. {bug.get('title', 'Unknown Issue')}\n"
            report += f"- **Severity**: {bug.get('severity', 'Medium')}\n"
            report += f"- **Description**: {bug.get('description', 'N/A')}\n\n"
    return report
