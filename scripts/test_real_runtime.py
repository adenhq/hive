import asyncio
import sys
import shutil
from pathlib import Path

# Bootstrap path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "core"))

from framework.runtime.core import Runtime
from framework.schemas.run import Run
# from framework.schemas.agent import Agent # Not needed for this test
from framework.testing.failure_storage import FailureStorage

async def main():
    print("🧪 Starting Real Runtime Integration Test...")
    
    # Setup Paths
    agent_export_path = project_root / "exports" / "real_agent"
    if agent_export_path.exists():
        try:
            shutil.rmtree(agent_export_path)
        except:
            pass # might be locked
            
    storage_path = agent_export_path / ".hive" / "storage"
    
    # Mocking a minimal Runtime structure since we can't spin up full graph
    # We just want to test `record_failure`
    
    class MockStorage:
        base_path = storage_path
        
    class MockRuntime(Runtime):
        def __init__(self):
            self.storage = MockStorage()
            self._current_run = Run(
                id="real_run_123",
                goal_id="real_goal_X",
                agent_id="agent_007",
                status="running"
            )
            # We don't call super().__init__ to avoid heavy loading, just testing record_failure
            # But record_failure relies on self.storage and imports
            
    runtime = MockRuntime()
    
    print("💥 Triggering a REAL failure...")
    try:
        # Simulate an error
        raise ConnectionTimeoutError("Connection to OpenAI timed out after 60000ms")
    except Exception as e:
        # This calls the ACTUAL record_failure method we implemented
        # It should capture sys.platform, python version etc automatically
        fail_id = runtime.record_failure(
            node_id="llm_node_real",
            error=e,
            input_data={"test": "data"},
            severity="error"
        )
        print(f"✅ Failure recorded with ID: {fail_id}")
        
    # Now verify the file content has REAL env data
    goal_file = storage_path / "failures" / "failures_real_goal_X.jsonl"
    
    # Wait a bit for async write (fire and forget task)
    await asyncio.sleep(1)
    
    if goal_file.exists():
        print(f"📂 Log file found: {goal_file}")
        content = goal_file.read_text("utf-8")
        print("🔍 Content Preview:")
        print(content)
        
        if "windows" in content.lower() or "linux" in content.lower():
            print("✅ Real OS detected!")
        if "3.1" in content:
             print("✅ Real Python version detected!")
    else:
        print("❌ Log file NOT found! Async write failed?")

# Helper exception
class ConnectionTimeoutError(Exception):
    pass

if __name__ == "__main__":
    asyncio.run(main())
