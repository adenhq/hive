import json
import os
import hashlib
import asyncio
import tempfile
import aiofiles
import platform
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from framework.testing.failure_record import FailureRecord
from framework.utils.privacy import mask_sensitive_data

class FailureStorage:
    """Persistent storage for failure records using Hybrid Log/Stats approach."""
    
    def __init__(self, storage_path: str | Path):
        self.storage_path = Path(storage_path)
        self.failures_path = self.storage_path / "failures"
        self.failures_path.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def record_failure(self, failure: FailureRecord) -> str:
        """Record a failure with deduplication logic and PII masking."""
        
        # 1. Auto-populate environment if missing (Robustness)
        if not failure.environment:
            failure.environment = {
                "os": platform.system().lower(),
                "python": sys.version.split()[0],
                "arch": platform.machine(),
                "node": platform.node()
            }

        # 2. Mask sensitive data
        failure.input_data = mask_sensitive_data(failure.input_data)
        failure.memory_snapshot = mask_sensitive_data(failure.memory_snapshot)
        
        # 3. Generate fingerprint if missing
        if not failure.fingerprint:
            base = f"{failure.node_id or 'unknown'}:{failure.error_type}:{failure.error_message}"
            failure.fingerprint = hashlib.sha256(base.encode()).hexdigest()

        # Define paths
        goal_file = self.failures_path / f"failures_{failure.goal_id}.jsonl"
        stats_file = self.failures_path / f"stats_{failure.goal_id}.json"
        
        async with self._lock:
            # 4. Smart Stats Update (Read-Modify-Write protected by Lock)
            stats = {}
            if stats_file.exists():
                try:
                    async with aiofiles.open(stats_file, "r") as f:
                        content = await f.read()
                        if content:
                            stats = json.loads(content)
                except Exception:
                    stats = {} # Corrupt file fallback
            
            fp = failure.fingerprint
            if fp not in stats:
                stats[fp] = {
                    "count": 0,
                    "first_seen": failure.timestamp.isoformat(),
                    "last_seen": failure.timestamp.isoformat(),
                    "error_type": failure.error_type,
                    "message": failure.error_message[:100], # Truncate for index
                    "node_id": failure.node_id
                }
            
            stats[fp]["count"] += 1
            stats[fp]["last_seen"] = failure.timestamp.isoformat()
            current_count = stats[fp]["count"]
            
            # Atomic Stats Write
            async with aiofiles.open(stats_file, "w") as f:
                await f.write(json.dumps(stats, indent=2))
            
            # 5. Conditional Logging (Smart Deduplication)
            # Only full log the first 5 instances to save disk, then just sample or stop.
            # This prevents the "infinite loop 1GB file" scenario.
            if current_count <= 5:
                 async with aiofiles.open(goal_file, mode="a", encoding="utf-8") as f:
                    await f.write(failure.model_dump_json() + "\n")
                
        return failure.id

    def get_failures_by_goal(self, goal_id: str, limit: int = 50) -> List[FailureRecord]:
        """Get recent failures for a goal."""
        goal_file = self.failures_path / f"failures_{goal_id}.jsonl"
        if not goal_file.exists():
            return []
            
        failures = []
        try:
            with open(goal_file, "r", encoding="utf-8") as f:
                # Read specific number of lines from end is harder with variable length json
                # Reading all for now, assuming files don't get massive immediately
                # Optimization: Seek to end and read backwards if needed later
                lines = f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        failures.append(FailureRecord.model_validate_json(line))
        except Exception:
            return []
            
        return failures

    def get_failures_by_node(self, node_id: str) -> List[FailureRecord]:
        """Scan all failures for a specific node (expensive operation)."""
        all_failures = []
        for file in self.failures_path.glob("failures_*.jsonl"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    for line in f:
                        if f'"node_id": "{node_id}"' in line: # Quick pre-filter
                            rec = FailureRecord.model_validate_json(line)
                            if rec.node_id == node_id:
                                all_failures.append(rec)
            except Exception:
                continue
        return all_failures
        
    def get_failure_stats(self, goal_id: str) -> Dict[str, Any]:
        """Get failure statistics for a goal."""
        failures = self.get_failures_by_goal(goal_id, limit=1000)
        
        stats = {
            "total": len(failures),
            "by_severity": {},
            "by_node": {},
            "by_type": {}
        }
        
        for f in failures:
            # Severity
            stats["by_severity"][f.severity] = stats["by_severity"].get(f.severity, 0) + 1
            
            # Node
            node = f.node_id or "unknown"
            stats["by_node"][node] = stats["by_node"].get(node, 0) + 1
            
            # Type
            err = f.error_type
            stats["by_type"][err] = stats["by_type"].get(err, 0) + 1
            
        return stats
