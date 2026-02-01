import framework.trace.execution_trace as trace_module
from framework.trace import ExecutionTrace


def test_node_start_success_events_order(monkeypatch):
    timestamps = iter(
        [
            "2026-02-01T00:00:00+00:00",
            "2026-02-01T00:00:01+00:00",
            "2026-02-01T00:00:02+00:00",
        ]
    )
    monkeypatch.setattr(trace_module, "_utc_iso", lambda: next(timestamps))

    trace = ExecutionTrace(workflow_id="wf-1", run_id="run-1")
    trace.record_node_start("node-1", {"a": 1})
    trace.record_node_success("node-1", {"b": 2})

    assert len(trace.events) == 2
    assert trace.events[0].event_type == "node_start"
    assert trace.events[1].event_type == "node_success"
    assert trace.events[0].node_id == "node-1"
    assert trace.events[1].node_id == "node-1"


def test_error_records_node_error_and_final_status_failed(monkeypatch):
    timestamps = iter(
        [
            "2026-02-01T00:00:00+00:00",
            "2026-02-01T00:00:01+00:00",
            "2026-02-01T00:00:02+00:00",
            "2026-02-01T00:00:03+00:00",
        ]
    )
    monkeypatch.setattr(trace_module, "_utc_iso", lambda: next(timestamps))

    trace = ExecutionTrace(workflow_id="wf-1", run_id="run-1")
    trace.record_node_start("node-1", {"a": 1})
    trace.record_node_error("node-1", ValueError("boom"))
    trace.finalize(status="failed")

    assert trace.events[-1].event_type == "node_error"
    assert trace.status == "failed"


def test_summary_counts_and_duration(monkeypatch):
    timestamps = iter(
        [
            "2026-02-01T00:00:00+00:00",
            "2026-02-01T00:00:01+00:00",
            "2026-02-01T00:00:02+00:00",
            "2026-02-01T00:00:10+00:00",
        ]
    )
    monkeypatch.setattr(trace_module, "_utc_iso", lambda: next(timestamps))

    trace = ExecutionTrace(workflow_id="wf-1", run_id="run-1")
    trace.record_node_start("node-1", {"a": 1})
    trace.record_node_success("node-1", {"b": 2})
    trace.finalize(status="completed")

    summary = trace.summary()

    assert summary["total_nodes"] == 1
    assert summary["succeeded_nodes"] == 1
    assert summary["failed_nodes"] == 0
    assert summary["duration_seconds"] == 10.0
