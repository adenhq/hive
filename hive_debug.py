
import asyncio
import sys
import argparse
from pathlib import Path

# Add core to path
sys.path.append("core")

from framework.runtime.agent_runtime import AgentRuntime, EntryPointSpec
from framework.graph.edge import GraphSpec # Or edge?
from framework.graph.executor import ExecutionResult

async def debug_session(runtime: AgentRuntime, input_data: dict, entry_point: str = "default"):
    """Run an interactive debug session."""
    print(f"\n--- Hive Debugger ({entry_point}) ---")
    print("Commands: break <node_id>, run, resume <exec_id>, status, exit")
    
    stream = runtime.get_stream(entry_point)
    active_execution_id = None
    
    while True:
        cmd = input("(debug) ").strip().split()
        if not cmd:
            continue
            
        op = cmd[0]
        
        if op == "exit":
            break
            
        if op == "break":
            if len(cmd) < 2:
                print("Usage: break <node_id>")
                continue
            node_id = cmd[1]
            runtime.set_breakpoint(node_id)
            print(f"Breakpoint set at {node_id}")
            
        elif op == "unbreak":
            if len(cmd) < 2:
                print("Usage: unbreak <node_id>")
                continue
            node_id = cmd[1]
            runtime.remove_breakpoint(node_id)
            print(f"Breakpoint removed from {node_id}")

        elif op == "run":
            print("Starting execution...")
            active_execution_id = await stream.execute(input_data)
            print(f"Started execution: {active_execution_id}")
            # Wait for update
            result = await stream.wait_for_completion(active_execution_id)
            if result and result.paused_at:
                print(f"PAUSED at {result.paused_at}")
                print(f"State: {result.session_state}")
            else:
                print("Execution completed.")
                if result:
                    print("Output:", result.output)
                else:
                    print("Wait timed out or failed.")
                    
        elif op == "resume":
            eid = cmd[1] if len(cmd) > 1 else active_execution_id
            if not eid:
                print("No active execution ID")
                continue
            print(f"Resuming {eid}...")
            active_execution_id = await runtime.resume_execution(entry_point, eid, {})
            print(f"Resumed as {active_execution_id}")
            result = await stream.wait_for_completion(active_execution_id)
            if result and result.paused_at:
                print(f"PAUSED at {result.paused_at}")
            else:
                print("Execution completed.")
                if result:
                    print("Output:", result.output)
                    
        elif op == "status":
            print(stream.get_stats())
            
        else:
            print("Unknown command")

if __name__ == "__main__":
    print("Hive Debugger Tool")
    print("This tool is designed to wrap an existing agent script.")
    print("Usage: Import debug_session and await it with your initialized runtime.")
