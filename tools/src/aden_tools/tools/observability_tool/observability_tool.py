"""
Observability Tool - Analyze agent runs and metrics.
"""
import json
import os
from typing import Dict, Any, List
from pathlib import Path
from fastmcp import FastMCP

def register_tools(mcp: FastMCP, credentials=None) -> None:
    """Register observability tools."""

    # Helper to find storage path
    def _get_storage_path() -> Path:
        # Default to ~/.hive/storage
        return Path.home() / ".hive" / "storage"

    @mcp.tool()
    def list_recent_runs(limit: int = 10) -> List[Dict[str, Any]]:
        """
        List the most recent agent runs.
        
        Args:
            limit: Number of runs to return (default 10)
        """
        storage_path = _get_storage_path()
        runs_dir = storage_path / "runs"
        
        if not runs_dir.exists():
            # Try to find agent-specific storage
            # This is a simplification - in reality we might need to search recursively
            return [{"error": f"No runs found in {storage_path}"}]
            
        runs = []
        # Walk through all agent directories
        for agent_dir in storage_path.iterdir():
            if not agent_dir.is_dir():
                continue
                
            agent_runs_dir = agent_dir / "runs"
            if not agent_runs_dir.exists():
                continue
                
            for run_file in agent_runs_dir.glob("*.json"):
                try:
                    # Get modification time
                    mtime = run_file.stat().st_mtime
                    
                    # Read basic info (avoid reading full file if possible, but here we need status)
                    with open(run_file, 'r') as f:
                        data = json.load(f)
                        
                    runs.append({
                        "id": data.get("id"),
                        "agent": agent_dir.name,
                        "goal": data.get("goal_description"),
                        "status": data.get("status"),
                        "timestamp": mtime,
                        "metrics": data.get("output_data", {}).get("metrics", {})
                    })
                except Exception:
                    continue
                    
        # Sort by timestamp descending
        runs.sort(key=lambda x: x["timestamp"], reverse=True)
        return runs[:limit]

    @mcp.tool()
    def get_run_details(run_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific run.
        
        Args:
            run_id: The ID of the run to retrieve
        """
        storage_path = _get_storage_path()
        
        # Search for the run file across all agent directories
        for agent_dir in storage_path.iterdir():
            if not agent_dir.is_dir():
                continue
                
            run_file = agent_dir / "runs" / f"{run_id}.json"
            if run_file.exists():
                try:
                    with open(run_file, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    return {"error": str(e)}
                    
        return {"error": f"Run {run_id} not found"}

    @mcp.tool()
    def analyze_run_metrics(run_id: str) -> Dict[str, Any]:
        """
        Analyze performance metrics for a run.
        
        Args:
            run_id: The ID of the run to analyze
        """
        data = get_run_details(run_id)
        if "error" in data:
            return data
            
        metrics = data.get("output_data", {}).get("metrics", {})
        decisions = data.get("decisions", [])
        
        # Calculate additional metrics
        total_decisions = len(decisions)
        tool_calls = sum(1 for d in decisions if d.get("options", [{}])[0].get("action_type") == "tool_call")
        
        return {
            "run_id": run_id,
            "status": data.get("status"),
            "metrics": metrics,
            "derived_metrics": {
                "total_decisions": total_decisions,
                "tool_call_count": tool_calls,
                "avg_latency_per_step": metrics.get("total_latency_ms", 0) / max(1, total_decisions) if metrics else 0
            }
        }
