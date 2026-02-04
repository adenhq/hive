import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from framework.llm.resilience import ResilienceConfig, CircuitBreaker, RetryHandler, CircuitState

@pytest.mark.asyncio
async def test_retry_handler_success():
    config = ResilienceConfig(max_retries=3, initial_delay=0.01)
    handler = RetryHandler(config)
    
    func = AsyncMock(return_value="success")
    result = await handler.execute_with_retry(func)
    
    assert result == "success"
    assert func.call_count == 1

@pytest.mark.asyncio
async def test_retry_handler_fail_then_success():
    config = ResilienceConfig(max_retries=3, initial_delay=0.01)
    handler = RetryHandler(config)
    
    func = AsyncMock()
    func.side_effect = [ValueError("fail1"), ValueError("fail2"), "success"]
    
    result = await handler.execute_with_retry(func)
    
    assert result == "success"
    assert func.call_count == 3

@pytest.mark.asyncio
async def test_retry_handler_exhaust_retries():
    config = ResilienceConfig(max_retries=2, initial_delay=0.01)
    handler = RetryHandler(config)
    
    func = AsyncMock(side_effect=ValueError("constant fail"))
    
    with pytest.raises(ValueError, match="constant fail"):
        await handler.execute_with_retry(func)
    
    assert func.call_count == 3  # Initial + 2 retries

@pytest.mark.asyncio
async def test_circuit_breaker_tripping():
    config = ResilienceConfig(failure_threshold=2, recovery_timeout=0.1)
    breaker = CircuitBreaker(config)
    
    func = AsyncMock(side_effect=ValueError("fail"))
    
    # First failure
    with pytest.raises(ValueError):
        await breaker.call(func)
    assert breaker.state == CircuitState.CLOSED
    
    # Second failure - should trip
    with pytest.raises(ValueError):
        await breaker.call(func)
    assert breaker.state == CircuitState.OPEN
    
    # Third call - should fail immediately without calling func
    with pytest.raises(RuntimeError, match="Circuit is OPEN"):
        await breaker.call(func)
    assert func.call_count == 2

@pytest.mark.asyncio
async def test_circuit_breaker_recovery():
    config = ResilienceConfig(failure_threshold=1, recovery_timeout=0.05)
    breaker = CircuitBreaker(config)
    
    func = AsyncMock(side_effect=ValueError("fail"))
    
    # Trip the circuit
    with pytest.raises(ValueError):
        await breaker.call(func)
    assert breaker.state == CircuitState.OPEN
    
    # Wait for recovery timeout
    await asyncio.sleep(0.1)
    
    # Next call should be HALF-OPEN
    func.side_effect = None
    func.return_value = "recovered"
    
    result = await breaker.call(func)
    assert result == "recovered"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure():
    config = ResilienceConfig(failure_threshold=1, recovery_timeout=0.05)
    breaker = CircuitBreaker(config)
    
    # Trip it
    try:
        await breaker.call(AsyncMock(side_effect=ValueError("fail")))
    except ValueError:
        pass
    assert breaker.state == CircuitState.OPEN
    
    await asyncio.sleep(0.1)
    
    # Call fails in HALF-OPEN
    func = AsyncMock(side_effect=ValueError("still failing"))
    with pytest.raises(ValueError):
        await breaker.call(func)
    
    assert breaker.state == CircuitState.OPEN
    assert func.call_count == 1
