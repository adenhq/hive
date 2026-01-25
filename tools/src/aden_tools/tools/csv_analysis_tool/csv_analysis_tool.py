import pandas as pd
from fastmcp import FastMCP
import os
from typing import Optional, Dict, Any

def register_tools(mcp: FastMCP) -> None:
    """Register CSV analysis tools with the MCP server."""

    @mcp.tool()
    def inspect_csv(file_path: str) -> Dict[str, Any]:
        """
        Inspect a CSV file to understand its structure (columns, types, sample data).
        
        Use this before trying to manipulate or query data to understand the schema.
        
        Args:
            file_path: Absolute path to the CSV file.
            
        Returns:
            Dict containing 'columns', 'dtypes', 'shape', and 'sample' data.
        """
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
            
        try:
            df = pd.read_csv(file_path)
            
            sample = df.head(5).fillna("").to_dict(orient="records")
            
            return {
                "file": os.path.basename(file_path),
                "rows": df.shape[0],
                "columns": list(df.columns),
                "dtypes": {k: str(v) for k, v in df.dtypes.items()},
                "sample_data": sample,
                "summary": df.describe().fillna("").to_dict()
            }
        except Exception as e:
            return {"error": f"Failed to read CSV: {str(e)}"}