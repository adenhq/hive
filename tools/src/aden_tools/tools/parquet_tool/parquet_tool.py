import importlib.util
from fasmcp import FastMCP
from ..file_system_toolkits.security import get_secure_path

def register_tools(mcp: FastMCP):
    """Register Parquet Tool with the MCP server."""

    @mcp.tool()
    def secure_parquet_path(file_path: str) -> str:
        """ Get the secure path for the parquet file."""
        return get_secure_path(file_path, allowed_extensions=[".parquet"])

    def _connect_to_duckdb(file_path: str):
        import duckdb
        conn = duckdb.connect(database=':memory:')
        conn.execute("SET enable_progress_bar=false;")
        conn.execute("SET memory_limit='1GB';")
        conn.execute("SET threads=2;")
        return conn

    @mcp.tool()
    def parquet_read(file_path: str, workspace_id: str, agent_id: str, session_id: str):
        """ The function to read the the parquet file and return its content as a string or JSON."""
        if importlib.util.find_spec("duckdb") is None:
            return {"error": "duckdb is not installed. Please install it to use this tool."
                    "pip install duckdb  or  pip install tools[sql]"}
        if not file_path.endswith(".parquet"):
            return {"error": "The file is not a parquet file."}


        return {"error": "Not implemented yet."}

    @mcp.tool()
    def describe_parquet(file_path: str, workspace_id: str, agent_id: str, session_id: str):
        """ The function to describe the parquet file schema."""
        return {"error": "Not implemented yet."}

    @mcp.tool()
    def sample_parquet(file_path: str, n: int = 5, workspace_id: str = "", agent_id: str = "", session_id: str = ""):
        """ The function to return n sample rows from the parquet file."""
        return {"error": "Not implemented yet."}

    @mcp.tool()
    def run_sql_on_parquet(file_path: str, query: str, workspace_id: str, agent_id: str, session_id: str):
        """ The function to run SQL query on the parquet file."""
        return {"error": "Not implemented yet."}


