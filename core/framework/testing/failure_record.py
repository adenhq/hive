from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class FailureSeverity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"

class FailureRecord(BaseModel):
    """Record of a single failure for analysis."""
    id: str
    run_id: str
    goal_id: str
    node_id: Optional[str] = None
    
    # Failure details
    severity: FailureSeverity
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    fingerprint: Optional[str] = None
    
    # Context
    input_data: Dict[str, Any] = Field(default_factory=dict)
    memory_snapshot: Dict[str, Any] = Field(default_factory=dict)
    
    # Debugging info
    execution_path: List[str] = Field(default_factory=list)
    decisions_before_failure: List[str] = Field(default_factory=list)
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    environment: Dict[str, str] = Field(default_factory=dict)
