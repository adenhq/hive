import pytest
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

from framework.graph.node import NodeProtocol, NodeContext, NodeResult, NodeSpec
from framework.graph.edge import GraphSpec
from framework.graph.goal import Goal
from framework.runner.self_healing import SelfHealingRunner
from framework.llm.provider import LLMResponse

# 1. Define the buggy code content
BUGGY_CODE = """
from framework.graph.node import NodeProtocol, NodeContext, NodeResult

class BuggyNode(NodeProtocol):
    async def execute(self, ctx: NodeContext) -> NodeResult:
        # Deliberate bug: ZeroDivisionError
        val = 1 / 0
        return NodeResult(success=True, output={"val": val})
"""

# 2. Define the fixed code content
FIXED_CODE = """
from framework.graph.node import NodeProtocol, NodeContext, NodeResult

class BuggyNode(NodeProtocol):
    async def execute(self, ctx: NodeContext) -> NodeResult:
        # Fixed: return 1
        val = 1
        return NodeResult(success=True, output={"val": val})
"""

@pytest.fixture
def buggy_node_file(tmp_path):
    """Creates a temporary python file with buggy code."""
    # We need to put this in a place importable or just use the path for the runner 
    # The runner uses inspect.getsourcefile, so it must be a real file.
    # To load it as a class, we might need to manually register it.
    
    file_path = tmp_path / "buggy_node.py"
    file_path.write_text(BUGGY_CODE, encoding="utf-8")
    return file_path

@pytest.mark.skip(reason="Requires manual execution due to file system modification")
@pytest.mark.asyncio
async def test_self_healing_end_to_end(buggy_node_file, monkeypatch):
    """
    Test that the runner detects the ZeroDivisionError, asks LLM for fix,
    updates the file, and resumes execution.
    """
    
    # --- Setup Mocks ---
    
    # Mock LLM to return the fixed code
    mock_llm = MagicMock()
    # The runner calls complete() to get the patch
    mock_llm.complete.return_value = LLMResponse(
        content=f"```python\n{FIXED_CODE}\n```",
        model="mock-healer"
    )
    
    # Standard mocks for context
    mock_runtime = MagicMock()
    
    # --- Dynamic Module Loading ---
    # We need to load the buggy class from the file so the runner can use it
    import importlib.util
    spec = importlib.util.spec_from_file_location("BuggyNodeModule", buggy_node_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    BuggyNodeClass = module.BuggyNode
    
    # --- Build Graph ---
    node_spec = NodeSpec(id="buggy_node", name="Buggy Node", node_type="custom", input_keys=[], output_keys=["val"])
    graph = GraphSpec(
        id="test_graph",
        entry_node="buggy_node",
        nodes=[node_spec],
        edges=[],
        terminal_nodes=["buggy_node"]
    )
    goal = Goal(id="goal_1", name="Test Goal")
    
    # --- Initialize Runner ---
    # Use our mocked LLM
    runner = SelfHealingRunner(
        agent_path=buggy_node_file.parent,
        graph=graph,
        goal=goal,
        mock_mode=False, # We provide explicit llm
        model="mock-model"
    )
    # Inject mocked LLM
    runner._llm = mock_llm
    
    # Register the buggy instantiation
    # IMPORTANT: We register the *instance* of the buggy node. 
    # However, the SelfHealingNodeWrapper logic attempts to find the *class* source file.
    # `BuggyNodeClass` is defined in `buggy_node_file`, so `inspect.getsourcefile` should work.
    runner._setup() # Forces creation of executor
    runner._executor.register_node("buggy_node", BuggyNodeClass())
    
    # IMPORTANT: Enable evolution
    runner.evolve_on_failure = True
    
    # --- Execute ---
    print(f"Starting execution with buggy file at: {buggy_node_file}")
    print(f"Initial content:\n{buggy_node_file.read_text()}")
    
    result = await runner.run()
    
    # --- Verification ---
    
    # 1. Check execution success
    assert result.success, f"Execution failed: {result.error}"
    assert result.output.get("val") == 1, "Did not get fixed output"
    
    # 2. Check file was patched
    new_content = buggy_node_file.read_text()
    assert "val = 1" in new_content, "File was not patched on disk"
    assert "1 / 0" not in new_content, "Bug still present in file"
    
    # 3. Check LLM was called
    mock_llm.complete.assert_called()
    call_args = mock_llm.complete.call_args
    # Check prompt contained error
    assert "ZeroDivisionError" in call_args[1]["messages"][0]["content"]


if __name__ == "__main__":
    import tempfile
    import shutil
    
    async def run_manual_test():
        # Create temp dir
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            print(f"Created temp dir: {tmp_dir}")
            
            # Setup file
            file_path = tmp_dir / "buggy_node.py"
            file_path.write_text(BUGGY_CODE, encoding="utf-8")
            
            # Run test
            await test_self_healing_end_to_end(file_path, None)
            
            print("\n✅ TEST PASSED MANUALLY")
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            shutil.rmtree(tmp_dir)
            
    asyncio.run(run_manual_test())

