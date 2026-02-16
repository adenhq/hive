
"""
Agent Execution Logger
----------------------

Lightweight logging utility to track agent reasoning steps.
This module does NOT modify planner behavior.
It only records execution events to help analyze reasoning continuity
and support future memory improvements.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class AgentExecutionLogger:
    def __init__(self, log_dir: str = "agent_logs", session_id: Optional[str] = None):
        self.log_dir = log_dir
        self.session_id = session_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        os.makedirs(self.log_dir, exist_ok=True)

        self.log_file = os.path.join(self.log_dir, f"session_{self.session_id}.jsonl")

    def _write(self, data: Dict[str, Any]) -> None:
        """Write a single log entry"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def log_step(
        self,
        step_number: int,
        instruction: str,
        action: str,
        tool: Optional[str],
        result: Any,
        status: str = "success",
    ) -> None:
        """Log a reasoning step"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "step": step_number,
            "instruction": instruction,
            "action": action,
            "tool": tool,
            "status": status,
            "result_preview": str(result)[:300],
        }
        self._write(entry)

    def log_error(
        self,
        step_number: int,
        instruction: str,
        action: str,
        error: Exception,
    ) -> None:
        """Log an execution error"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "step": step_number,
            "instruction": instruction,
            "action": action,
            "status": "error",
            "error": str(error),
        }
        self._write(entry)

    def log_session_summary(self, total_steps: int, success: bool) -> None:
        """Log end of session summary"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "session_summary",
            "total_steps": total_steps,
            "success": success,
        }
        self._write(entry)
