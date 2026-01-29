"""Node definitions for README Improver Agent."""

from framework.graph import NodeSpec

# Node 1: Read File
read_file_node = NodeSpec(
    id="read-file",
    name="Read File",
    description="Read the content of the input file using the view_file tool",
    node_type="llm_tool_use",
    input_keys=["file_path"],
    output_keys=["raw_content", "file_info"],
    output_schema={
        "raw_content": {
            "type": "string",
            "required": True,
            "description": "The raw content read from the file",
        },
        "file_info": {
            "type": "object",
            "required": True,
            "description": "Information about the file (path, size, etc.)",
        },
    },
    system_prompt="""\
You are a file reader assistant. Your task is to read a file and return its content.

Steps:
1. Use the view_file tool to read the file at the given file_path
2. Return the content and basic file information

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks.

Return this JSON structure:
{
  "raw_content": "The full content of the file...",
  "file_info": {
    "path": "the/file/path.md",
    "read_successfully": true
  }
}

If the file cannot be read, return:
{
  "raw_content": "",
  "file_info": {
    "path": "the/file/path.md",
    "read_successfully": false,
    "error": "Error message"
  }
}
""",
    tools=["view_file"],
    max_retries=3,
)

# Node 2: Improve Content
improve_content_node = NodeSpec(
    id="improve-content",
    name="Improve Content",
    description="Fix spelling errors and improve formatting to professional Markdown",
    node_type="llm_generate",
    input_keys=["raw_content"],
    output_keys=["polished_content", "improvements_made"],
    output_schema={
        "polished_content": {
            "type": "string",
            "required": True,
            "description": "The improved, polished README content in Markdown format",
        },
        "improvements_made": {
            "type": "array",
            "required": True,
            "description": "List of improvements made to the content",
        },
    },
    system_prompt="""\
You are a professional technical writer specializing in README files and documentation.

Your task is to improve the given raw content by:

1. **Spelling & Grammar**: Fix all spelling errors, typos, and grammatical issues
2. **Markdown Formatting**: Apply professional Markdown formatting:
   - Add appropriate headers (# ## ###) for sections
   - Use bullet points (-) or numbered lists where appropriate
   - Format code snippets with proper code blocks (```)
   - Add emphasis (*italic*, **bold**) where it improves readability
   - Ensure proper spacing between sections
3. **Structure**: Organize content logically with clear sections
4. **Readability**: Improve sentence flow and clarity without changing meaning

IMPORTANT RULES:
- Preserve ALL original information - do not remove or add facts
- Keep technical terms and code exactly as they are
- Maintain the author's voice and intent
- Only improve formatting and fix errors

CRITICAL: Return ONLY raw JSON. NO markdown code blocks around the JSON.

Return this JSON structure:
{
  "polished_content": "# Title\\n\\nThe improved markdown content...\\n\\n## Section\\n\\n- Bullet point\\n- Another point",
  "improvements_made": [
    "Fixed 3 spelling errors",
    "Added section headers",
    "Converted text lists to bullet points",
    "Added code formatting for commands"
  ]
}
""",
    tools=[],
    max_retries=3,
)

__all__ = [
    "read_file_node",
    "improve_content_node",
]
