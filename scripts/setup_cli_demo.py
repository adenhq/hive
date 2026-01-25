import asyncio
import sys
import random
import re
import hashlib
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# === COPY OF CLASSES to bypass import hell in this demo script ===

SENSITIVE_PATTERNS = {
    "api_key": re.compile(r"(sk-[a-zA-Z0-9]{32,}|AIza[a-zA-Z0-9_-]{35})"),
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "generic_secret": re.compile(r"(password|secret|token|auth|key)[\s:\"]+([a-zA-Z0-9_-]{8,})", re.IGNORECASE)
}

def mask_sensitive_data(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: mask_sensitive_data(v) if k not in ["api_key", "password", "token", "secret"] 
            else "********" 
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    elif isinstance(data, str):
        masked_str = data
        for label, pattern in SENSITIVE_PATTERNS.items():
            masked_str = pattern.sub(f"[MASKED_{label.upper()}]", masked_str)
        return masked_str
    return data

class FailureSeverity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"

class FailureRecord(BaseModel):
    id: str
    run_id: str
    goal_id: str
    node_id: Optional[str] = None
    severity: FailureSeverity
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    fingerprint: Optional[str] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    memory_snapshot: Dict[str, Any] = Field(default_factory=dict)
    execution_path: List[str] = Field(default_factory=list)
    decisions_before_failure: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    environment: Dict[str, str] = Field(default_factory=dict)

class FailureStorage:
    def __init__(self, storage_path: str | Path):
        self.storage_path = Path(storage_path)
        self.failures_path = self.storage_path / "failures"
        self.failures_path.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def record_failure(self, failure: FailureRecord) -> str:
        # Mocking import logic since this is a standalone script
        import aiofiles 
        
        failure.input_data = mask_sensitive_data(failure.input_data)
        failure.memory_snapshot = mask_sensitive_data(failure.memory_snapshot)
        if not failure.fingerprint:
            base = f"{failure.node_id or 'unknown'}:{failure.error_type}:{failure.error_message}"
            failure.fingerprint = hashlib.sha256(base.encode()).hexdigest()
        goal_file = self.failures_path / f"failures_{failure.goal_id}.jsonl"
        record_json = failure.model_dump_json()
        
        async with self._lock:
            async with aiofiles.open(goal_file, mode="a", encoding="utf-8") as f:
                await f.write(record_json + "\n")
        return failure.id

# === END COPY ===

async def create_demo_data():
    # Define standard storage path used by CLI (updated to .hive/storage inside agent path)
    agent_name = "demo_agent"
    agent_path = Path("exports") / agent_name
    storage_path = agent_path / ".hive" / "storage"
    
    print(f"📂 Criando dados de demonstração em: {storage_path}")
    if storage_path.exists():
        import shutil
        shutil.rmtree(storage_path)
    
    storage = FailureStorage(storage_path)
    
    errors = [
        ("TimeoutError", "LLM failed to respond within 30s"),
        ("ValueError", "Invalid output format from tool"),
        ("ConnectionError", "Could not connect to MCP server 'filesystem'"),
        ("RuntimeError", "Max retries exceeded for node 'search_web'")
    ]
    
    goal_id = "demo_goal_1"
    
    print(f"📝 Gerando 15 falhas simuladas para o objetivo '{goal_id}'...")
    
    # Create a set of recurring errors to test aggregation
    recurring_errors = [
        # (ID, Type, Message) - ID derived from fingerprint concept (stable)
        ("fail_timeout_01", "TimeoutError", "LLM failed to respond within 30s"),
        ("fail_timeout_01", "TimeoutError", "LLM failed to respond within 30s"), # Duplicate
        ("fail_timeout_01", "TimeoutError", "LLM failed to respond within 30s"), # Duplicate
        ("fail_val_02", "ValueError", "Invalid output format from tool"),
        ("fail_val_02", "ValueError", "Invalid output format from tool"), # Duplicate
        ("fail_conn_03", "ConnectionError", "Could not connect to MCP server 'filesystem'"),
        ("fail_crit_04", "RuntimeError", "Max retries exceeded for node 'search_web'")
    ]
    
    # Add some random ones too
    for i in range(8):
         recurring_errors.append((f"fail_rand_{i}", "RandomError", f"Random glitch {i}"))

    for err_id, err_type, err_msg in recurring_errors:
        severity = FailureSeverity.CRITICAL if "RuntimeError" in err_type else FailureSeverity.ERROR
        
        rec = FailureRecord(
            id=err_id,
            run_id=f"run_demo_{random.randint(100, 999)}",
            goal_id=goal_id,
            node_id=random.choice(["planner", "executor", "reviewer", "tool_use"]),
            severity=severity,
            error_type=err_type,
            error_message=err_msg,
            input_data={"user_query": "Build a rocket", "step": 1},
            environment={"os": "demo_os", "python": "3.12"} 
        )
        
        await storage.record_failure(rec)
        
    print("✅ Dados criados com sucesso!")
    print("\nAgora você pode rodar os comandos do CLI:")
    print(f"   python cli.py failures list exports/{agent_name} --goal {goal_id}")
    print(f"   python cli.py failures stats exports/{agent_name} --goal {goal_id}")
    print(f"   python cli.py failures show exports/{agent_name} fail_timeout_01")

if __name__ == "__main__":
    asyncio.run(create_demo_data())
