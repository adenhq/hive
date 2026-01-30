"""Tests for EventBus."""

import asyncio

import pytest

from framework.runtime.event_bus import AgentEvent, EventBus, EventType


@pytest.mark.asyncio
async def test_wait_for_timeout_returns_none():
    """Test that wait_for returns None on timeout instead of raising."""
    bus = EventBus()

    # wait_for should return None when timeout expires, not raise an exception
    result = await bus.wait_for(
        event_type=EventType.EXECUTION_COMPLETED,
        timeout=0.1,
    )

    assert result is None


@pytest.mark.asyncio
async def test_wait_for_receives_event():
    """Test that wait_for correctly receives an event before timeout."""
    bus = EventBus()

    async def publish_after_delay():
        await asyncio.sleep(0.05)
        await bus.publish(
            AgentEvent(
                type=EventType.EXECUTION_COMPLETED,
                stream_id="test-stream",
                execution_id="exec-123",
                data={"result": "success"},
            )
        )

    # Start publisher in background
    task = asyncio.create_task(publish_after_delay())

    # Wait for the event
    result = await bus.wait_for(
        event_type=EventType.EXECUTION_COMPLETED,
        timeout=1.0,
    )

    await task

    assert result is not None
    assert result.type == EventType.EXECUTION_COMPLETED
    assert result.stream_id == "test-stream"
    assert result.execution_id == "exec-123"


@pytest.mark.asyncio
async def test_wait_for_with_stream_filter():
    """Test that wait_for correctly filters by stream_id."""
    bus = EventBus()

    async def publish_events():
        await asyncio.sleep(0.02)
        # Publish event for wrong stream first
        await bus.publish(
            AgentEvent(
                type=EventType.EXECUTION_COMPLETED,
                stream_id="other-stream",
                execution_id="exec-1",
            )
        )
        await asyncio.sleep(0.02)
        # Then publish for correct stream
        await bus.publish(
            AgentEvent(
                type=EventType.EXECUTION_COMPLETED,
                stream_id="target-stream",
                execution_id="exec-2",
            )
        )

    task = asyncio.create_task(publish_events())

    result = await bus.wait_for(
        event_type=EventType.EXECUTION_COMPLETED,
        stream_id="target-stream",
        timeout=1.0,
    )

    await task

    assert result is not None
    assert result.stream_id == "target-stream"
    assert result.execution_id == "exec-2"


@pytest.mark.asyncio
async def test_wait_for_without_timeout():
    """Test that wait_for works without a timeout when event arrives."""
    bus = EventBus()

    async def publish_soon():
        await asyncio.sleep(0.05)
        await bus.publish(
            AgentEvent(
                type=EventType.STREAM_STARTED,
                stream_id="test",
            )
        )

    task = asyncio.create_task(publish_soon())

    result = await bus.wait_for(event_type=EventType.STREAM_STARTED)

    await task

    assert result is not None
    assert result.type == EventType.STREAM_STARTED