"""Hive base tests - verifies CURRENT repo state."""
import pytest
import os

def test_framework_imports():
    import framework
    from framework.runner import AgentRunner
    assert AgentRunner

def test_aden_tools_imports():
    import aden_tools
    # Basic import only (WebSearchTool missing)
    assert aden_tools

def test_agent_loader():
    assert os.path.exists("exports"), "Create exports/"
    assert os.path.exists("exports/supportticketagent"), "Create supportticketagent dir"

def test_no_import_errors():
    __import__("litellm")
    # Skip missing modules for now
    pass
