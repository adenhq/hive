import asyncio
import json
import hashlib
import re
import os
import shutil
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# === COPY OF privacy.py ===
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

# === COPY OF failure_record.py ===
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

# === COPY OF failure_storage.py ===
class FailureStorage:
    def __init__(self, storage_path: str | Path):
        self.storage_path = Path(storage_path)
        self.failures_path = self.storage_path / "failures"
        self.failures_path.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def record_failure(self, failure: FailureRecord) -> str:
        failure.input_data = mask_sensitive_data(failure.input_data)
        failure.memory_snapshot = mask_sensitive_data(failure.memory_snapshot)
        
        if not failure.fingerprint:
            base = f"{failure.node_id or 'unknown'}:{failure.error_type}:{failure.error_message}"
            failure.fingerprint = hashlib.sha256(base.encode()).hexdigest()

        goal_file = self.failures_path / f"failures_{failure.goal_id}.jsonl"
        record_json = failure.model_dump_json()
        
        async with self._lock:
            with open(goal_file, "a", encoding="utf-8") as f:
                f.write(record_json + "\n")
                
        return failure.id

# === STRESS TEST LOGIC ===
async def run_load_test(num_failures=1000):
    test_dir = Path("stress_test_standalone")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    
    storage = FailureStorage(test_dir)
    latencies = []
    
    print(f"🚀 [Standalone] Iniciando Stress Test com {num_failures} falhas...")
    start_total = time.perf_counter()
    
    async def record_task(i):
        rec = FailureRecord(
            id=f"test_{i}",
            run_id=f"run_{i}", 
            goal_id="stress_goal", 
            node_id="node_chaos",
            severity=FailureSeverity.ERROR, 
            error_type="ChaosError",
            error_message=f"Error message number {i % 10}",
            input_data={"api_key": "sk-123", "data": "val"}
        )
        t_start = time.perf_counter()
        await storage.record_failure(rec)
        latencies.append(time.perf_counter() - t_start)

    await asyncio.gather(*(record_task(i) for i in range(num_failures)))
    total_time = time.perf_counter() - start_total
    
    # Validation
    goal_file = test_dir / "failures" / "failures_stress_goal.jsonl"
    with open(goal_file, "r") as f:
        count = len(f.readlines())
        
    print(f"✅ Records written: {count}/{num_failures}")
    print(f"✅ Concluído em {total_time:.2f}s")
    print(f"   Throughput: {num_failures/total_time:.2f} writes/sec")
    
    # Check Privacy
    with open(goal_file, "r") as f:
        first = json.loads(f.readline())
        if first["input_data"]["api_key"] == "********":
            print("✅ Privacy Masking Verified!")
        else:
            print("❌ Privacy Masking Failed!")
            
    return latencies

def plot_results(latencies):
    try:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 5))
        plt.plot(latencies, color='magenta', alpha=0.6, linewidth=1)
        plt.title("Latência de Gravação de Falhas (1000 Requests Async)")
        plt.xlabel("Requisição (#)")
        plt.ylabel("Tempo (segundos)")
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Add P95 line
        p95 = sorted(latencies)[int(len(latencies)*0.95)]
        plt.axhline(y=p95, color='r', linestyle=':', label=f'P95: {p95*1000:.2f}ms')
        plt.legend()
        
        output_file = Path("stress_test_performance.png")
        plt.savefig(output_file)
        print(f"\n📊 Gráfico gerado com sucesso: {output_file.absolute()}")
    except ImportError:
        print("\n⚠️ Matplotlib não instalado. Gráfico ignorado.")
    except Exception as e:
        print(f"\n❌ Erro ao gerar gráfico: {e}")

if __name__ == "__main__":
    latencies = asyncio.run(run_load_test(1000))
    plot_results(latencies)
