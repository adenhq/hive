import asyncio
import pytest
import shutil
from pathlib import Path
from framework.graph.edge import GraphSpec
from framework.graph.goal import Goal
from framework.graph.node import NodeSpec, NodeProtocol, NodeContext, NodeResult
from framework.graph.executor import GraphExecutor
from framework.runtime.event_bus import EventBus, EventType
from framework.runtime.core import Runtime

class SimpleNode(NodeProtocol):
    """A simple node for testing monitoring."""
    async def execute(self, ctx: NodeContext) -> NodeResult:
        # Simulate some work
        await asyncio.sleep(0.1)
        return NodeResult(
            success=True, 
            output={"result": "ok"},
            tokens_used=100,
            latency_ms=100
        )

@pytest.mark.asyncio
async def test_graph_executor_monitoring_events():
    storage_path = Path("./test_storage_executor_monitoring")
    if storage_path.exists():
        shutil.rmtree(storage_path)
    storage_path.mkdir()

    try:
        # 1. Setup
        node_spec = NodeSpec(
            id="test_node",
            name="Test Node",
            description="Testing monitoring hooks",
            node_type="function"
        )
        graph = GraphSpec(
            id="monitoring_graph",
            goal_id="monitoring_goal",
            entry_node="test_node",
            nodes=[node_spec],
            terminal_nodes=["test_node"]
        )
        goal = Goal(id="monitoring_goal", name="Monitoring Goal", description="Verify events")
        
        runtime = Runtime(storage_path)
        event_bus = EventBus()
        
        executor = GraphExecutor(
            runtime=runtime,
            event_bus=event_bus,
            stream_id="test_stream",
            execution_id="test_exec"
        )
        
        # Register the node implementation
        executor.register_node("test_node", SimpleNode())
        
        # Subscribe to events
        captured_events = []
        async def event_handler(event):
            captured_events.append(event)
            
        event_bus.subscribe(
            event_types=[EventType.NODE_STARTED, EventType.NODE_COMPLETED],
            handler=event_handler
        )
        
        # 2. Execute
        result = await executor.execute(graph, goal)
        
        # Give a micro-moment for background tasks to finish if any
        await asyncio.sleep(0.1)
        
        # 3. Verify
        assert result.success
        
        started = [e for e in captured_events if e.type == EventType.NODE_STARTED]
        completed = [e for e in captured_events if e.type == EventType.NODE_COMPLETED]
        
        assert len(started) == 1
        assert started[0].data["node_id"] == "test_node"
        assert started[0].stream_id == "test_stream"
        assert started[0].execution_id == "test_exec"
        
        assert len(completed) == 1
        assert completed[0].data["node_id"] == "test_node"
        assert completed[0].data["success"] is True
        assert completed[0].data["tokens_used"] == 100
        assert completed[0].data["latency_ms"] == 100
        
    finally:
        if storage_path.exists():
            shutil.rmtree(storage_path)
