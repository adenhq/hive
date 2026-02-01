from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

TraceEventType = Literal["node_start", "node_success", "node_error"]
TraceStatus = Literal["running", "completed", "failed"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    return _utc_now().isoformat()


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


@dataclass(frozen=True)
class TraceEvent:
    event_type: TraceEventType
    node_id: str
    timestamp_utc: str
    payload: dict


class ExecutionTrace:
    def __init__(self, workflow_id: str, run_id: str):
        self.workflow_id = workflow_id
        self.run_id = run_id
        self.events: list[TraceEvent] = []
        self.started_at_utc = _utc_iso()
        self.finished_at_utc: str | None = None
        self.status: TraceStatus = "running"

    def record_node_start(self, node_id: str, inputs: dict) -> None:
        try:
            payload = {"inputs": _json_safe(inputs)}
            self._append_event("node_start", node_id, payload)
        except Exception:
            return

    def record_node_success(self, node_id: str, outputs: dict) -> None:
        try:
            payload = {"outputs": _json_safe(outputs)}
            self._append_event("node_success", node_id, payload)
        except Exception:
            return

    def record_node_error(self, node_id: str, error: Exception) -> None:
        try:
            payload = {"error": str(error)}
            self._append_event("node_error", node_id, payload)
        except Exception:
            return

    def finalize(self, status: TraceStatus) -> None:
        try:
            self.status = status
            self.finished_at_utc = _utc_iso()
        except Exception:
            return

    def summary(self) -> dict:
        try:
            total_nodes = sum(1 for e in self.events if e.event_type == "node_start")
            succeeded_nodes = sum(1 for e in self.events if e.event_type == "node_success")
            failed_nodes = sum(1 for e in self.events if e.event_type == "node_error")

            duration_seconds: float | None
            if self.finished_at_utc is None:
                duration_seconds = None
            else:
                started = datetime.fromisoformat(self.started_at_utc)
                finished = datetime.fromisoformat(self.finished_at_utc)
                duration_seconds = (finished - started).total_seconds()

            return {
                "total_nodes": total_nodes,
                "succeeded_nodes": succeeded_nodes,
                "failed_nodes": failed_nodes,
                "duration_seconds": duration_seconds,
            }
        except Exception:
            return {
                "total_nodes": 0,
                "succeeded_nodes": 0,
                "failed_nodes": 0,
                "duration_seconds": None,
            }

    def _append_event(self, event_type: TraceEventType, node_id: str, payload: dict) -> None:
        event = TraceEvent(
            event_type=event_type,
            node_id=node_id,
            timestamp_utc=_utc_iso(),
            payload=payload,
        )
        self.events.append(event)
