"""
Tests for durable wait / signal / timer runtime substrate (TDD coverage of current_issue.md).

Required surface area (issue):
- Models: WaitRequest, SignalEnvelope (frozen), ExecutionPaused, WaitResumed
- Store: add (idempotent), get_pending, match_signal (type + filter), mark_resumed, get_expired
- Runtime: wait() -> ExecutionPaused, signal() -> WaitResumed | None, tick(now) -> list[WaitResumed]
- Semantics: run isolation, exactly-once resume, deterministic FIFO, timers as synthetic signals
- Lifecycle events: WAIT_CREATED, WAIT_MATCHED, WAIT_TIMED_OUT, WAIT_RESUMED
- Opt-in: runtime works without event_bus
"""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any

import pytest

from framework.runtime.durable_wait import (
    WAIT_TIMEOUT_SIGNAL_TYPE,
    DurableWaitRuntime,
    ExecutionPaused,
    InMemoryWaitStore,
    SignalEnvelope,
    WaitRequest,
    WaitResumed,
    WaitStoreIfce,
)
from framework.runtime.event_bus import AgentEvent, EventBus, EventType

# === Fixtures ===


@pytest.fixture
def run_id() -> str:
    return "run_001"


@pytest.fixture
def wait_request(run_id: str) -> WaitRequest:
    return WaitRequest(
        wait_id="wait_1",
        run_id=run_id,
        node_id="node_a",
        attempt=1,
        signal_type="email.reply",
        match={"thread_id": "t1"},
        timeout_at=datetime(2025, 3, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def signal_envelope() -> SignalEnvelope:
    return SignalEnvelope(
        signal_type="email.reply",
        payload={"thread_id": "t1", "body": "Got it"},
        correlation_id="c1",
        causation_id=None,
        received_at=datetime.now(UTC),
    )


@pytest.fixture
def wait_store() -> WaitStoreIfce:
    return InMemoryWaitStore()


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus(max_history=100)


@pytest.fixture
def durable_runtime(wait_store: WaitStoreIfce, event_bus: EventBus) -> DurableWaitRuntime:
    return DurableWaitRuntime(wait_store=wait_store, event_bus=event_bus)


# === Model tests ===


def test_wait_request_creation(wait_request: WaitRequest, run_id: str) -> None:
    assert wait_request.wait_id == "wait_1"
    assert wait_request.run_id == run_id
    assert wait_request.node_id == "node_a"
    assert wait_request.attempt == 1
    assert wait_request.signal_type == "email.reply"
    assert wait_request.match == {"thread_id": "t1"}
    assert wait_request.timeout_at is not None


def test_wait_request_frozen(wait_request: WaitRequest) -> None:
    with pytest.raises(FrozenInstanceError):
        wait_request.wait_id = "other"  # type: ignore[misc]


def test_signal_envelope_creation(signal_envelope: SignalEnvelope) -> None:
    assert signal_envelope.signal_type == "email.reply"
    assert signal_envelope.payload["thread_id"] == "t1"
    assert signal_envelope.correlation_id == "c1"


def test_signal_envelope_frozen(signal_envelope: SignalEnvelope) -> None:
    """SignalEnvelope is immutable (required by issue: frozen dataclass)."""
    with pytest.raises(FrozenInstanceError):
        signal_envelope.signal_type = "other"  # type: ignore[misc]


def test_execution_paused_creation(wait_request: WaitRequest) -> None:
    session_state: dict[str, Any] = {"paused_at": "node_a", "memory": {}}
    paused = ExecutionPaused(
        wait_id=wait_request.wait_id,
        run_id=wait_request.run_id,
        node_id=wait_request.node_id,
        attempt=wait_request.attempt,
        session_state=session_state,
        wait_request=wait_request,
    )
    assert paused.wait_id == "wait_1"
    assert paused.run_id == wait_request.run_id
    assert paused.session_state == session_state
    assert paused.wait_request == wait_request


# === WaitStore tests (run isolation, exactly-once, deterministic) ===


@pytest.mark.asyncio
async def test_wait_store_add_and_get_pending(
    wait_store: WaitStoreIfce,
    wait_request: WaitRequest,
    run_id: str,
) -> None:
    await wait_store.add(wait_request)
    pending = await wait_store.get_pending(run_id)
    assert len(pending) == 1
    assert pending[0].wait_id == wait_request.wait_id

    other_run = "run_002"
    pending_other = await wait_store.get_pending(other_run)
    assert len(pending_other) == 0


@pytest.mark.asyncio
async def test_wait_store_add_idempotent_for_same_wait_id(
    wait_store: WaitStoreIfce,
    wait_request: WaitRequest,
    run_id: str,
) -> None:
    """Store.add is idempotent for same wait_id within run (required by WaitStoreIfce)."""
    await wait_store.add(wait_request)
    await wait_store.add(wait_request)
    pending = await wait_store.get_pending(run_id)
    assert len(pending) == 1
    assert pending[0].wait_id == wait_request.wait_id


@pytest.mark.asyncio
async def test_wait_store_mark_resumed_removes_wait(
    wait_store: WaitStoreIfce,
    wait_request: WaitRequest,
    run_id: str,
) -> None:
    """mark_resumed removes the wait from pending (exactly-once resume)."""
    await wait_store.add(wait_request)
    await wait_store.mark_resumed(run_id, wait_request.wait_id)
    pending = await wait_store.get_pending(run_id)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_wait_store_run_isolation(
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    """Events for one run must not match waits for another run."""
    req_a = WaitRequest(
        wait_id="w_a",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="approval",
        match=None,
        timeout_at=None,
    )
    await wait_store.add(req_a)

    envelope = SignalEnvelope(
        signal_type="approval",
        payload={},
        correlation_id=None,
        causation_id=None,
        received_at=datetime.now(UTC),
    )
    # Signal for different run must not match
    matched = await wait_store.match_signal("run_other", envelope)
    assert matched is None

    pending = await wait_store.get_pending(run_id)
    assert len(pending) == 1


@pytest.mark.asyncio
async def test_wait_store_match_signal_deterministic_fifo(
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    """If multiple waits match, selection is deterministic (FIFO by creation order)."""
    for i in range(3):
        req = WaitRequest(
            wait_id=f"w_{i}",
            run_id=run_id,
            node_id="n",
            attempt=1,
            signal_type="same",
            match=None,
            timeout_at=None,
        )
        await wait_store.add(req)

    envelope = SignalEnvelope(
        signal_type="same",
        payload={},
        correlation_id=None,
        causation_id=None,
        received_at=datetime.now(UTC),
    )
    matched = await wait_store.match_signal(run_id, envelope)
    assert matched == "w_0"
    # Second match returns next
    matched2 = await wait_store.match_signal(run_id, envelope)
    assert matched2 == "w_1"
    matched3 = await wait_store.match_signal(run_id, envelope)
    assert matched3 == "w_2"
    matched_none = await wait_store.match_signal(run_id, envelope)
    assert matched_none is None


@pytest.mark.asyncio
async def test_wait_store_match_signal_type_and_match_filter(
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    """Match requires signal_type equality and optional match dict filter."""
    req1 = WaitRequest(
        wait_id="w1",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="email.reply",
        match={"thread_id": "t1"},
        timeout_at=None,
    )
    req2 = WaitRequest(
        wait_id="w2",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="approval",
        match=None,
        timeout_at=None,
    )
    await wait_store.add(req1)
    await wait_store.add(req2)

    # Signal approval: only w2 matches; w1 remains pending
    envelope_approval = SignalEnvelope(
        signal_type="approval",
        payload={"thread_id": "t1"},
        correlation_id=None,
        causation_id=None,
        received_at=datetime.now(UTC),
    )
    matched = await wait_store.match_signal(run_id, envelope_approval)
    assert matched == "w2"
    pending = await wait_store.get_pending(run_id)
    assert len(pending) == 1 and pending[0].wait_id == "w1"

    # Signal email.reply with matching payload: w1 matches
    envelope_reply = SignalEnvelope(
        signal_type="email.reply",
        payload={"thread_id": "t1"},
        correlation_id=None,
        causation_id=None,
        received_at=datetime.now(UTC),
    )
    assert await wait_store.match_signal(run_id, envelope_reply) == "w1"
    pending2 = await wait_store.get_pending(run_id)
    assert len(pending2) == 0


@pytest.mark.asyncio
async def test_wait_store_match_signal_rejects_payload_missing_match_key(
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    """Match filter: payload missing key from wait.match does not match."""
    req = WaitRequest(
        wait_id="w1",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="email.reply",
        match={"thread_id": "t1"},
        timeout_at=None,
    )
    await wait_store.add(req)
    envelope = SignalEnvelope(
        signal_type="email.reply",
        payload={},  # missing thread_id
        correlation_id=None,
        causation_id=None,
        received_at=datetime.now(UTC),
    )
    assert await wait_store.match_signal(run_id, envelope) is None
    pending = await wait_store.get_pending(run_id)
    assert len(pending) == 1


@pytest.mark.asyncio
async def test_wait_store_match_signal_rejects_payload_wrong_value(
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    """Match filter: payload with wrong value for wait.match key does not match."""
    req = WaitRequest(
        wait_id="w1",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="email.reply",
        match={"thread_id": "t1"},
        timeout_at=None,
    )
    await wait_store.add(req)
    envelope = SignalEnvelope(
        signal_type="email.reply",
        payload={"thread_id": "t2"},
        correlation_id=None,
        causation_id=None,
        received_at=datetime.now(UTC),
    )
    assert await wait_store.match_signal(run_id, envelope) is None
    pending = await wait_store.get_pending(run_id)
    assert len(pending) == 1


@pytest.mark.asyncio
async def test_wait_store_match_signal_empty_match_matches_any_payload(
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    """match={} means no filter: any payload with same signal_type matches (optional filter)."""
    req = WaitRequest(
        wait_id="w1",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="approval",
        match={},
        timeout_at=None,
    )
    await wait_store.add(req)
    envelope = SignalEnvelope(
        signal_type="approval",
        payload={"any": "keys"},
        correlation_id=None,
        causation_id=None,
        received_at=datetime.now(UTC),
    )
    assert await wait_store.match_signal(run_id, envelope) == "w1"
    pending = await wait_store.get_pending(run_id)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_wait_store_exactly_once_resume(
    wait_store: WaitStoreIfce,
    wait_request: WaitRequest,
    run_id: str,
    signal_envelope: SignalEnvelope,
) -> None:
    """For a given (run_id, wait_id), at most one resume (match removes wait)."""
    await wait_store.add(wait_request)
    first = await wait_store.match_signal(run_id, signal_envelope)
    assert first == wait_request.wait_id
    second = await wait_store.match_signal(run_id, signal_envelope)
    assert second is None
    pending = await wait_store.get_pending(run_id)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_wait_store_get_expired(
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    past = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    future = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    req_past = WaitRequest(
        wait_id="expired",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="x",
        match=None,
        timeout_at=past,
    )
    req_future = WaitRequest(
        wait_id="not_expired",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="x",
        match=None,
        timeout_at=future,
    )
    await wait_store.add(req_past)
    await wait_store.add(req_future)

    now = datetime(2025, 2, 1, 0, 0, 0, tzinfo=UTC)
    expired = await wait_store.get_expired(now)
    assert len(expired) == 1
    assert expired[0][0] == run_id and expired[0][1] == "expired"

    # get_expired removes expired waits from store; second call returns nothing
    expired2 = await wait_store.get_expired(now)
    assert len(expired2) == 0


@pytest.mark.asyncio
async def test_wait_store_get_expired_none_timeout(
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    req = WaitRequest(
        wait_id="no_timeout",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="x",
        match=None,
        timeout_at=None,
    )
    await wait_store.add(req)
    expired = await wait_store.get_expired(datetime.now(UTC))
    assert len(expired) == 0


# === DurableWaitRuntime tests ===


@pytest.mark.asyncio
async def test_runtime_wait_returns_execution_paused(
    durable_runtime: DurableWaitRuntime,
    wait_request: WaitRequest,
    run_id: str,
) -> None:
    session_state: dict[str, Any] = {"memory": {}}
    paused = await durable_runtime.wait(wait_request, session_state=session_state)
    assert isinstance(paused, ExecutionPaused)
    assert paused.wait_id == wait_request.wait_id
    assert paused.run_id == run_id
    assert paused.session_state == session_state


@pytest.mark.asyncio
async def test_runtime_wait_without_event_bus_returns_execution_paused(
    wait_store: WaitStoreIfce,
    wait_request: WaitRequest,
    run_id: str,
) -> None:
    """Runtime works without event_bus (additive/opt-in; required by issue)."""
    runtime = DurableWaitRuntime(wait_store=wait_store, event_bus=None)
    paused = await runtime.wait(wait_request, session_state={})
    assert isinstance(paused, ExecutionPaused)
    assert paused.wait_id == wait_request.wait_id
    assert paused.run_id == run_id


@pytest.mark.asyncio
async def test_runtime_wait_emits_wait_created(
    durable_runtime: DurableWaitRuntime,
    wait_request: WaitRequest,
    event_bus: EventBus,
) -> None:
    received: list[AgentEvent] = []

    async def handler(event: AgentEvent) -> None:
        received.append(event)

    sub_id = event_bus.subscribe(
        event_types=[EventType.WAIT_CREATED],
        handler=handler,
    )
    await durable_runtime.wait(wait_request, session_state={})
    await asyncio.sleep(0.05)
    event_bus.unsubscribe(sub_id)

    assert len(received) == 1
    assert received[0].type == EventType.WAIT_CREATED
    assert received[0].data.get("wait_id") == wait_request.wait_id
    assert received[0].data.get("run_id") == wait_request.run_id


@pytest.mark.asyncio
async def test_runtime_signal_matches_and_returns_wait_resumed(
    durable_runtime: DurableWaitRuntime,
    wait_request: WaitRequest,
    signal_envelope: SignalEnvelope,
    run_id: str,
) -> None:
    """signal() returns WaitResumed with all required fields (issue: runtime.signal)."""
    await durable_runtime.wait(wait_request, session_state={})
    result = await durable_runtime.signal(run_id, signal_envelope)
    assert result is not None
    assert isinstance(result, WaitResumed)
    assert result.run_id == run_id
    assert result.wait_id == wait_request.wait_id
    assert result.timed_out is False
    assert result.matched_signal_type == signal_envelope.signal_type


@pytest.mark.asyncio
async def test_runtime_workflow_reply_or_timeout_branch_deterministically(
    durable_runtime: DurableWaitRuntime,
    wait_store: WaitStoreIfce,
    wait_request: WaitRequest,
    signal_envelope: SignalEnvelope,
    run_id: str,
) -> None:
    """Workflow: wait for reply OR timeout → branch deterministically (issue motivation).

    One wait with signal_type=email.reply + timeout_at can be satisfied by signal or tick.
    WaitResumed.timed_out and matched_signal_type let the node branch (reply vs timeout).
    """
    # Branch A: reply arrives → resume with timed_out=False, matched_signal_type="email.reply"
    await durable_runtime.wait(wait_request, session_state={})
    reply_resumed = await durable_runtime.signal(run_id, signal_envelope)
    assert reply_resumed is not None
    assert reply_resumed.timed_out is False
    assert reply_resumed.matched_signal_type == "email.reply"
    # Node can branch: if not reply_resumed.timed_out: handle_reply(reply_resumed)

    # Branch B: timeout fires → resume with timed_out=True, matched_signal_type=wait.timeout
    run_b = "run_b"
    past = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    wait_timeout = WaitRequest(
        wait_id="wait_reply_or_timeout",
        run_id=run_b,
        node_id="node_a",
        attempt=1,
        signal_type="email.reply",
        match={"thread_id": "t1"},
        timeout_at=past,
    )
    await wait_store.add(wait_timeout)
    now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)
    timeout_resumed_list = await durable_runtime.tick(now)
    assert len(timeout_resumed_list) == 1
    timeout_resumed = timeout_resumed_list[0]
    assert timeout_resumed.timed_out is True
    assert timeout_resumed.matched_signal_type == WAIT_TIMEOUT_SIGNAL_TYPE
    # Node can branch: if timeout_resumed.timed_out: handle_timeout(timeout_resumed)

    # Outcomes are distinct and sufficient for deterministic branching
    assert reply_resumed.timed_out is not timeout_resumed.timed_out
    assert reply_resumed.matched_signal_type != timeout_resumed.matched_signal_type


@pytest.mark.asyncio
async def test_runtime_signal_no_match_returns_none(
    durable_runtime: DurableWaitRuntime,
    run_id: str,
    signal_envelope: SignalEnvelope,
) -> None:
    result = await durable_runtime.signal(run_id, signal_envelope)
    assert result is None


@pytest.mark.asyncio
async def test_runtime_run_isolation_signal_for_other_run_does_not_match(
    durable_runtime: DurableWaitRuntime,
    wait_store: WaitStoreIfce,
    wait_request: WaitRequest,
    signal_envelope: SignalEnvelope,
    run_id: str,
) -> None:
    """Run isolation: signal for run B must not match wait for run A (issue: run-scoped)."""
    await durable_runtime.wait(wait_request, session_state={})
    other_run = "run_other"
    result = await durable_runtime.signal(other_run, signal_envelope)
    assert result is None
    # Wait for run_id still pending (store is run-scoped)
    pending = await wait_store.get_pending(run_id)
    assert len(pending) == 1
    assert pending[0].wait_id == wait_request.wait_id


@pytest.mark.asyncio
async def test_runtime_signal_emits_wait_matched(
    durable_runtime: DurableWaitRuntime,
    wait_request: WaitRequest,
    signal_envelope: SignalEnvelope,
    event_bus: EventBus,
) -> None:
    received: list[AgentEvent] = []

    async def handler(event: AgentEvent) -> None:
        received.append(event)

    await durable_runtime.wait(wait_request, session_state={})
    sub_id = event_bus.subscribe(
        event_types=[EventType.WAIT_MATCHED],
        handler=handler,
    )
    await durable_runtime.signal(wait_request.run_id, signal_envelope)
    await asyncio.sleep(0.05)
    event_bus.unsubscribe(sub_id)

    assert len(received) == 1
    assert received[0].type == EventType.WAIT_MATCHED
    assert received[0].data.get("wait_id") == wait_request.wait_id


@pytest.mark.asyncio
async def test_runtime_signal_emits_wait_resumed(
    durable_runtime: DurableWaitRuntime,
    wait_request: WaitRequest,
    signal_envelope: SignalEnvelope,
    event_bus: EventBus,
) -> None:
    """Lifecycle: signal match emits WAIT_RESUMED (issue: auditable wait.resumed)."""
    received: list[AgentEvent] = []

    async def handler(event: AgentEvent) -> None:
        received.append(event)

    await durable_runtime.wait(wait_request, session_state={})
    sub_id = event_bus.subscribe(
        event_types=[EventType.WAIT_RESUMED],
        handler=handler,
    )
    await durable_runtime.signal(wait_request.run_id, signal_envelope)
    await asyncio.sleep(0.05)
    event_bus.unsubscribe(sub_id)

    assert len(received) == 1
    assert received[0].type == EventType.WAIT_RESUMED
    assert received[0].data.get("wait_id") == wait_request.wait_id
    assert received[0].data.get("timed_out") is False
    assert received[0].data.get("matched_signal_type") == signal_envelope.signal_type


@pytest.mark.asyncio
async def test_runtime_tick_returns_expired_waits_as_wait_resumed(
    durable_runtime: DurableWaitRuntime,
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    """tick() returns WaitResumed with timed_out=True and synthetic wait.timeout."""
    past = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    req = WaitRequest(
        wait_id="timed_out",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="x",
        match=None,
        timeout_at=past,
    )
    await wait_store.add(req)
    now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)
    resumed = await durable_runtime.tick(now)
    assert len(resumed) == 1
    assert isinstance(resumed[0], WaitResumed)
    assert resumed[0].run_id == run_id
    assert resumed[0].wait_id == "timed_out"
    assert resumed[0].timed_out is True
    assert resumed[0].matched_signal_type == WAIT_TIMEOUT_SIGNAL_TYPE


@pytest.mark.asyncio
async def test_runtime_tick_emits_wait_timed_out(
    durable_runtime: DurableWaitRuntime,
    wait_store: WaitStoreIfce,
    event_bus: EventBus,
    run_id: str,
) -> None:
    past = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    req = WaitRequest(
        wait_id="timed_out",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="x",
        match=None,
        timeout_at=past,
    )
    await wait_store.add(req)

    received: list[AgentEvent] = []

    async def handler(event: AgentEvent) -> None:
        received.append(event)

    sub_id = event_bus.subscribe(
        event_types=[EventType.WAIT_TIMED_OUT],
        handler=handler,
    )
    now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)
    await durable_runtime.tick(now)
    await asyncio.sleep(0.05)
    event_bus.unsubscribe(sub_id)

    assert len(received) == 1
    assert received[0].type == EventType.WAIT_TIMED_OUT
    assert received[0].data.get("wait_id") == "timed_out"


@pytest.mark.asyncio
async def test_runtime_tick_emits_wait_resumed(
    durable_runtime: DurableWaitRuntime,
    wait_store: WaitStoreIfce,
    event_bus: EventBus,
    run_id: str,
) -> None:
    """Lifecycle: tick timeout emits WAIT_RESUMED (issue: auditable wait.resumed)."""
    past = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    req = WaitRequest(
        wait_id="timed_out",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="x",
        match=None,
        timeout_at=past,
    )
    await wait_store.add(req)

    received: list[AgentEvent] = []

    async def handler(event: AgentEvent) -> None:
        received.append(event)

    sub_id = event_bus.subscribe(
        event_types=[EventType.WAIT_RESUMED],
        handler=handler,
    )
    now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)
    await durable_runtime.tick(now)
    await asyncio.sleep(0.05)
    event_bus.unsubscribe(sub_id)

    assert len(received) == 1
    assert received[0].type == EventType.WAIT_RESUMED
    assert received[0].data.get("wait_id") == "timed_out"
    assert received[0].data.get("timed_out") is True
    assert received[0].data.get("matched_signal_type") == WAIT_TIMEOUT_SIGNAL_TYPE


@pytest.mark.asyncio
async def test_runtime_tick_exactly_once_per_wait(
    durable_runtime: DurableWaitRuntime,
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    past = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    req = WaitRequest(
        wait_id="once",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="x",
        match=None,
        timeout_at=past,
    )
    await wait_store.add(req)
    now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)
    first = await durable_runtime.tick(now)
    assert len(first) == 1
    second = await durable_runtime.tick(now)
    assert len(second) == 0


@pytest.mark.asyncio
async def test_runtime_signal_then_tick_exactly_once_no_double_resume(
    durable_runtime: DurableWaitRuntime,
    wait_request: WaitRequest,
    signal_envelope: SignalEnvelope,
    run_id: str,
) -> None:
    """Exactly-once: if signal matches first, tick must not resume same wait."""
    # Wait has timeout in past so it would be expired by tick
    past = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    req = WaitRequest(
        wait_id=wait_request.wait_id,
        run_id=run_id,
        node_id=wait_request.node_id,
        attempt=wait_request.attempt,
        signal_type=wait_request.signal_type,
        match=wait_request.match,
        timeout_at=past,
    )
    await durable_runtime.wait(req, session_state={})
    now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)
    signal_result = await durable_runtime.signal(run_id, signal_envelope)
    assert signal_result is not None
    assert signal_result.wait_id == req.wait_id
    # Tick should not return this wait (already removed by signal)
    tick_resumed = await durable_runtime.tick(now)
    assert len(tick_resumed) == 0


@pytest.mark.asyncio
async def test_runtime_concurrent_signal_and_tick_exactly_one_resume(
    durable_runtime: DurableWaitRuntime,
    wait_request: WaitRequest,
    signal_envelope: SignalEnvelope,
    run_id: str,
) -> None:
    """Exactly-once under race: concurrent signal and tick for same wait → one resume."""
    past = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    req = WaitRequest(
        wait_id=wait_request.wait_id,
        run_id=run_id,
        node_id=wait_request.node_id,
        attempt=wait_request.attempt,
        signal_type=wait_request.signal_type,
        match=wait_request.match,
        timeout_at=past,
    )
    await durable_runtime.wait(req, session_state={})
    now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)

    signal_result, tick_result = await asyncio.gather(
        durable_runtime.signal(run_id, signal_envelope),
        durable_runtime.tick(now),
    )
    # One path wins: either signal matched (WaitResumed, []) or tick fired ([WaitResumed], None)
    resumed_count = (1 if signal_result is not None else 0) + len(tick_result)
    assert resumed_count == 1
    if signal_result is not None:
        assert signal_result.wait_id == req.wait_id
        assert len(tick_result) == 0
    else:
        assert len(tick_result) == 1
        assert tick_result[0].wait_id == req.wait_id


@pytest.mark.asyncio
async def test_runtime_tick_multi_run_returns_correct_run_wait_ids(
    durable_runtime: DurableWaitRuntime,
    wait_store: WaitStoreIfce,
) -> None:
    """tick(now) with expired waits in multiple runs returns correct (run_id, wait_id) per run."""
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
    past = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    for run_id_val, wait_id_val in [("run_a", "wait_a"), ("run_b", "wait_b")]:
        req = WaitRequest(
            wait_id=wait_id_val,
            run_id=run_id_val,
            node_id="n",
            attempt=1,
            signal_type="x",
            match=None,
            timeout_at=past,
        )
        await wait_store.add(req)

    resumed = await durable_runtime.tick(now)
    assert len(resumed) == 2
    run_wait_ids = {(r.run_id, r.wait_id) for r in resumed}
    assert run_wait_ids == {("run_a", "wait_a"), ("run_b", "wait_b")}


@pytest.mark.asyncio
async def test_runtime_tick_returns_empty_when_no_expired(
    durable_runtime: DurableWaitRuntime,
    run_id: str,
) -> None:
    """tick(now) with no pending waits or no expired waits returns [] (issue: runtime.tick)."""
    now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)
    resumed = await durable_runtime.tick(now)
    assert resumed == []


@pytest.mark.asyncio
async def test_runtime_tick_with_none_uses_current_time(
    durable_runtime: DurableWaitRuntime,
    wait_store: WaitStoreIfce,
    run_id: str,
) -> None:
    """tick(now=None) uses current time and does not crash."""
    future_dt = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)
    req = WaitRequest(
        wait_id="future",
        run_id=run_id,
        node_id="n",
        attempt=1,
        signal_type="x",
        match=None,
        timeout_at=future_dt,
    )
    await wait_store.add(req)
    resumed = await durable_runtime.tick(now=None)
    # No expired (future_dt is in future relative to "now")
    assert len(resumed) == 0
