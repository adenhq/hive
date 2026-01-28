import asyncio
import pytest
import shutil
from pathlib import Path
from framework.graph.edge import GraphSpec
from framework.graph.goal import Goal
from framework.graph.node import NodeSpec, NodeProtocol, NodeContext, NodeResult, SharedMemory
from framework.runtime.agent_runtime import AgentRuntime, EntryPointSpec
from framework.runtime.shared_state import StateScope

class GlobalCounterNode(NodeProtocol):
    """A node that increments a global counter."""
    async def execute(self, ctx: NodeContext) -> NodeResult:
        # Read from global scope
        count = ctx.memory.read("global_counter", scope=StateScope.GLOBAL) or 0
        count += 1
        # Write back to global scope
        ctx.memory.write("global_counter", count, scope=StateScope.GLOBAL)
        return NodeResult(success=True, output={"count": count})

@pytest.mark.asyncio
async def test_global_memory_persistence():
    storage_path = Path("./test_storage_shared_memory")
    if storage_path.exists():
        shutil.rmtree(storage_path)
    storage_path.mkdir()

    try:
        # 1. Define a simple graph
        node_spec = NodeSpec(
            id="counter_node",
            name="Counter",
            description="Increments global counter",
            node_type="function"
        )
        graph = GraphSpec(
            id="test_graph",
            goal_id="test_goal",
            entry_node="counter_node",
            nodes=[node_spec],
            terminal_nodes=["counter_node"]
        )
        goal = Goal(id="test_goal", name="Test Goal", description="Verify persistence")
        
        # 2. Setup first runtime session
        runtime1 = AgentRuntime(
            graph=graph,
            goal=goal,
            storage_path=storage_path,
        )
        # Register the node implementation
        runtime1._streams = {} # Placeholder to avoid trigger issues before start
        
        # Create a custom node registry
        node_impl = GlobalCounterNode()
        
        # We'll use trigger_and_wait which creates the executor
        # But we need to make sure the executor uses our node_impl
        # For simplicity in testing, we can mock the executor or register node
        
        # Let's simplify and test the AgentRuntime's state saving directly first
        await runtime1.start()
        
        # Write directly to global state for testing
        await runtime1.state_manager.write(
            "global_counter", 10, 
            execution_id="test", 
            stream_id="test", 
            isolation="shared", 
            scope=StateScope.GLOBAL
        )
        
        # Stop runtime (saves state)
        await runtime1.stop()
        
        assert (storage_path / "shared_state.json").exists()
        
        # 3. Setup second runtime session (RESTORE)
        runtime2 = AgentRuntime(
            graph=graph,
            goal=goal,
            storage_path=storage_path,
        )
        await runtime2.start()
        
        # Read from restored global state
        val = await runtime2.state_manager.read(
            "global_counter", 
            execution_id="test2", 
            stream_id="test2", 
            isolation="shared"
        )
        
        assert val == 10
        await runtime2.stop()

    finally:
        if storage_path.exists():
            shutil.rmtree(storage_path)

@pytest.mark.asyncio
async def test_node_scoped_write():
    """Verify that nodes can correctly write to global scope via context.memory."""
    # This test is more of a unit test for the SharedMemory wrapper
    from framework.runtime.shared_state import SharedStateManager, IsolationLevel
    
    manager = SharedStateManager()
    memory = SharedMemory(
        _manager=manager,
        _execution_id="exec1",
        _stream_id="stream1",
        _isolation=IsolationLevel.SHARED
    )
    
    # Write to global scope
    memory.write("key1", "val1", scope=StateScope.GLOBAL)
    
    # Verify it is in manager's global state
    assert manager._global_state["key1"] == "val1"
    
    # Verify it is visible via read(scope=GLOBAL)
    assert memory.read("key1", scope=StateScope.GLOBAL) == "val1"
    
    # Verify it is NOT in manager's execution state (as it was global)
    assert manager._execution_state.get("exec1", {}).get("key1") is None
