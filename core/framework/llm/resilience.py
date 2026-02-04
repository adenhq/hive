import time
import asyncio
import random
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar("T")

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failure detected, requests blocked
    HALF_OPEN = "half_open" # Testing if service has recovered

@dataclass
class ResilienceConfig:
    """Configuration for LLM resilience features."""
    # Retry settings
    max_retries: int = 3
    initial_delay: float = 1.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    # Circuit Breaker settings
    failure_threshold: int = 5      # Failures before opening circuit
    recovery_timeout: float = 30.0  # Seconds to stay open before half-open
    min_requests: int = 10          # Min requests before breaker can trip

class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern to protect against provider outages.
    """
    def __init__(self, config: ResilienceConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.lock = asyncio.Lock()
        
    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function with circuit breaker protection."""
        async with self.lock:
            await self._before_call()
            
        try:
            result = await func(*args, **kwargs)
            async with self.lock:
                self._on_success()
            return result
        except Exception as e:
            async with self.lock:
                self._on_failure()
            raise e

    async def _before_call(self) -> None:
        """Check if call is allowed based on current state."""
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.config.recovery_timeout:
                logger.info("🔌 Circuit Breaker: Transitioning to HALF-OPEN")
                self.state = CircuitState.HALF_OPEN
            else:
                raise RuntimeError(
                    f"Circuit is OPEN. Requests blocked for another {self.config.recovery_timeout - elapsed:.1f}s"
                )

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("🔌 Circuit Breaker: Recovery detected! Transitioning to CLOSED")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            # Optionally reset failure count on success if we want "consecutive" failure logic
            # For now, let's keep it simple: success in closed state doesn't reset but stays closed.
            # actually resetting is better to prevent "leaky" failures over long time.
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                logger.warning(
                    f"🔌 Circuit Breaker: Failure threshold ({self.config.failure_threshold}) "
                    f"reached. Opening circuit for {self.config.recovery_timeout}s"
                )
                self.state = CircuitState.OPEN
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning("🔌 Circuit Breaker: Failed in HALF-OPEN state. Re-opening circuit.")
            self.state = CircuitState.OPEN

class RetryHandler:
    """
    Handles exponential backoff retry logic.
    """
    def __init__(self, config: ResilienceConfig):
        self.config = config

    async def execute_with_retry(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function with exponential backoff retries."""
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt == self.config.max_retries:
                    break
                
                # Calculate delay: base * (factor^attempt)
                delay = self.config.initial_delay * (self.config.exponential_base ** attempt)
                
                # Add jitter to prevent thundering herd
                if self.config.jitter:
                    delay *= (0.5 + random.random())
                
                logger.warning(
                    f"⚠️ Call failed: {str(e)}. "
                    f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{self.config.max_retries})..."
                )
                await asyncio.sleep(delay)
                
        raise last_error if last_error else RuntimeError("Retry loop exhausted without error recorded")
