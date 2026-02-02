import os
import json
import sys
from pathlib import Path
from unittest.mock import patch

# 1. Path Configuration: Add tools/src to system path for local import
# This ensures we can import the aden_tools package during development
sys.path.append(str(Path(__file__).parent / "tools/src"))

try:
    from aden_tools.tools.csv_tool.csv_tool import register_tools
    from fastmcp import FastMCP
except ImportError as e:
    print(f"Import Error: {e}. Please ensure you ran 'uv pip install fastmcp'.")
    sys.exit(1)

def run_integration_test():
    """
    Integration test to verify multi-file CSV SQL JOIN capabilities.
    Mocks the security layer to simulate a session sandbox environment.
    """
    # 2. Sandbox Directory Setup
    # Define the root directory where the security layer (get_secure_path) looks for files
    workspaces_root = str(Path("./agent_logs").absolute())
    
    # Patch the security layer WORKSPACES_DIR to use our local mock folder
    with patch("aden_tools.tools.file_system_toolkits.security.WORKSPACES_DIR", workspaces_root):
        print("🚀 Initializing Integration Test...")
        mcp = FastMCP("test_server")
        register_tools(mcp) #
        
        # Access the underlying function directly from the MCP tool manager
        csv_sql = mcp._tool_manager._tools["csv_sql"].fn

        # 3. Create Mock CSV Files in the Sandbox
        # Simulating a typical Aden workspace/agent/session path structure
        ws, ag, sess = "test_workspace", "test_agent", "test_session"
        secure_dir = Path(workspaces_root) / ws / ag / sess
        secure_dir.mkdir(parents=True, exist_ok=True)

        # Dataset 1: User records
        (secure_dir / "users.csv").write_text("id,name,city_id\n1,Mert,10\n2,Vincent,20")
        # Dataset 2: City mapping
        (secure_dir / "cities.csv").write_text("city_id,city_name\n10,Edirne\n20,SF")
        
        print(f"📂 Mock environment ready at: {secure_dir}")

        # 4. Multi-file SQL Query Execution
        # testing JOIN capability: data0 refers to users.csv, data1 refers to cities.csv
        query = "SELECT u.name, c.city_name FROM data0 u JOIN data1 c ON u.city_id = c.city_id"
        print(f"🔍 Executing JOIN query: {query}")
        
        try:
            result = csv_sql(
                paths=["users.csv", "cities.csv"],
                workspace_id=ws, 
                agent_id=ag, 
                session_id=sess,
                query=query
            )
            
            if result.get("success"):
                print("\n TEST SUCCESSFUL! Multi-file JOIN Result:")
                print(json.dumps(result["rows"], indent=2))
            else:
                print(f"\n TOOL ERROR: {result.get('error')}")
                
        except Exception as e:
            print(f" Execution failed unexpectedly: {e}")

if __name__ == "__main__":
    run_integration_test()
    # Prevent terminal from closing immediately (useful for IDE execution)
    input("\nPress Enter to exit...")