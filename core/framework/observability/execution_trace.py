from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
import json

TraceStatus = Literal["running", "completed", "failed"]


@dataclass
class NodeExecutionRecord:
	node_id: str
	started_at: datetime
	finished_at: Optional[datetime]
	status: TraceStatus
	inputs: Dict[str, Any]
	outputs: Dict[str, Any]
	error: Optional[str]

	def to_dict(self) -> Dict[str, Any]:
		return {
			"node_id": self.node_id,
			"started_at": self.started_at.isoformat(),
			"finished_at": self.finished_at.isoformat() if self.finished_at else None,
			"status": self.status,
			"inputs": self.inputs,
			"outputs": self.outputs,
			"error": self.error,
		}


@dataclass
class ExecutionTrace:
	workflow_id: str
	run_id: str
	started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
	finished_at: Optional[datetime] = None
	status: TraceStatus = "running"
	nodes: List[NodeExecutionRecord] = field(default_factory=list)

	def record_node_start(self, node_id: str, inputs: Dict[str, Any]) -> None:
		now = datetime.now(timezone.utc)
		record = NodeExecutionRecord(
			node_id=node_id,
			started_at=now,
			finished_at=None,
			status="running",
			inputs=dict(inputs),
			outputs={},
			error=None,
		)
		self.nodes.append(record)

	def record_node_success(self, node_id: str, outputs: Dict[str, Any]) -> None:
		record = self._get_latest_running_node()
		if record.node_id != node_id:
			raise ValueError("Most recent node does not match node_id")
		record.finished_at = datetime.now(timezone.utc)
		record.status = "completed"
		record.outputs = dict(outputs)
		record.error = None

	def record_node_error(self, node_id: str, error: Exception) -> None:
		record = self._get_latest_running_node()
		if record.node_id != node_id:
			raise ValueError("Most recent node does not match node_id")
		record.finished_at = datetime.now(timezone.utc)
		record.status = "failed"
		record.outputs = {}
		record.error = str(error)

	def finalize(self, status: TraceStatus) -> None:
		if status not in ("completed", "failed"):
			raise ValueError("Finalize status must be 'completed' or 'failed'")
		self.status = status
		self.finished_at = datetime.now(timezone.utc)

	def to_dict(self) -> Dict[str, Any]:
		return {
			"workflow_id": self.workflow_id,
			"run_id": self.run_id,
			"started_at": self.started_at.isoformat(),
			"finished_at": self.finished_at.isoformat() if self.finished_at else None,
			"status": self.status,
			"nodes": [node.to_dict() for node in self.nodes],
		}

	def to_json(self) -> str:
		return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

	def summary(self) -> Dict[str, Any]:
		completed = sum(1 for node in self.nodes if node.status == "completed")
		failed = sum(1 for node in self.nodes if node.status == "failed")
		running = sum(1 for node in self.nodes if node.status == "running")
		failed_node_id = next((n.node_id for n in self.nodes if n.status == "failed"), None)

		duration_seconds: Optional[float]
		if self.finished_at is None:
			duration_seconds = None
		else:
			duration_seconds = (self.finished_at - self.started_at).total_seconds()

		return {
			"total_nodes": len(self.nodes),
			"completed_nodes": completed,
			"failed_nodes": failed,
			"running_nodes": running,
			"duration_seconds": duration_seconds,
			"failed_node_id": failed_node_id,
			"status": self.status,
		}

	def _get_latest_running_node(self) -> NodeExecutionRecord:
		if not self.nodes:
			raise ValueError("No nodes have been started")
		latest = self.nodes[-1]
		if latest.status != "running":
			raise ValueError("Most recent node is not running")
		return latest
