"""
Test that the agent builder can work without LLM dependencies.
"""
import sys
import os
import json
import pytest
from pathlib import Path

# Add the core directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

# Sample test data
SAMPLE_GOAL_JSON = """
{
    "id": "test_goal",
    "name": "Test Goal",
    "description": "A test goal",
    "success_criteria": [
        {
            "id": "crit_1",
            "description": "Test criteria",
            "metric": "success",
            "target": "true",
            "weight": 1.0,
            "met": false
        }
    ],
    "constraints": [
        {
            "id": "const_1",
            "description": "Test constraint",
            "constraint_type": "hard",
            "category": "test",
            "check": "lambda x: True"
        }
    ]
}
"""

def test_import_agent_builder_no_llm():
    """Test that we can import agent_builder_server without LLM dependencies."""
    # Mock the LLM imports
    import builtins
    original_import = builtins.__import__
    
    def mock_import(name, *args, **kwargs):
        if 'anthropic' in name or 'openai' in name:
            raise ImportError(f"{name} not available")
        return original_import(name, *args, **kwargs)
    
    builtins.__import__ = mock_import
    
    try:
        # Try to import the module
        import core.framework.mcp.agent_builder_server as abs_mod
        assert hasattr(abs_mod, 'generate_constraint_tests')
        assert hasattr(abs_mod, 'generate_success_tests')
    finally:
        # Restore the original import
        builtins.__import__ = original_import

def test_generate_tests_without_llm():
    """Test that test generation works without LLM."""
    from core.framework.mcp.agent_builder_server import (
        generate_constraint_tests,
        generate_success_tests
    )
    
    # Test constraint test generation
    constraint_result = generate_constraint_tests(
        goal_id="test_goal",
        goal_json=SAMPLE_GOAL_JSON,
        agent_path="exports/test_agent"
    )
    constraint_data = json.loads(constraint_result)
    assert "test_guidelines" in constraint_data
    assert "test_template" in constraint_data
    
    # Test success test generation
    success_result = generate_success_tests(
        goal_id="test_goal",
        goal_json=SAMPLE_GOAL_JSON,
        node_names="test_node",
        tool_names="test_tool",
        agent_path="exports/test_agent"
    )
    success_data = json.loads(success_result)
    assert "test_guidelines" in success_data
    assert "test_template" in success_data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
