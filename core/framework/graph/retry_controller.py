"""
Run-level retry controller.

Provides:
- A global retry budget across an entire agent run
- Exponential backoff with optional jitter
- Centralized accounting for retries across nodes
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class RunRetryConfig:
    """
    Configuration for run-level retry behavior.

    All values are in seconds where applicable.
    """

    max_total_retries: int = 20
    base_delay_seconds: float = 0.5
    multiplier: float = 2.0
    max_delay_seconds: float = 10.0
    jitter_ratio: float = 0.1  # +/- 10% jitter by default


@dataclass
class RunRetryDecision:
    """Result of a retry budget check."""

    allow: bool
    delay_seconds: float = 0.0
    retry_index: int = 0  # Global retry index (1-based) when allowed
    reason: str | None = None
    node_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RunRetryController:
    """
    Central controller for run-level retries.

    This class is safe to use from concurrent tasks within a single event loop.
    """

    def __init__(
        self,
        config: RunRetryConfig | None = None,
        logger_: logging.Logger | None = None,
    ) -> None:
        self.config = config or RunRetryConfig()
        self.total_retries: int = 0
        self._lock = asyncio.Lock()
        # Allow caller to pass executor logger for consistent tagging
        self._logger = logger_ or logger

    @property
    def max_total_retries(self) -> int:
        return self.config.max_total_retries

    async def request_retry(
        self,
        node_id: str | None = None,
        last_error: str | None = None,
    ) -> RunRetryDecision:
        """
        Request permission to perform a retry.

        Returns:
            RunRetryDecision indicating whether retry is allowed and the
            backoff delay to apply before retrying.
        """
        async with self._lock:
            if self.total_retries >= self.config.max_total_retries:
                reason = (
                    "Global retry budget exhausted: "
                    f"{self.total_retries}/{self.config.max_total_retries}"
                )
                self._logger.error(
                    "❌ Global retry denied for node %s: %s (last_error=%s)",
                    node_id,
                    reason,
                    last_error,
                )
                return RunRetryDecision(
                    allow=False,
                    delay_seconds=0.0,
                    retry_index=self.total_retries,
                    reason=reason,
                    node_id=node_id,
                )

            # Count this retry attempt
            self.total_retries += 1
            retry_index = self.total_retries

            delay = self._calculate_backoff(retry_index)

            self._logger.info(
                "↻ Global retry %s/%s for node %s, delay=%.2fs (last_error=%s)",
                retry_index,
                self.config.max_total_retries,
                node_id,
                delay,
                last_error,
            )

            return RunRetryDecision(
                allow=True,
                delay_seconds=delay,
                retry_index=retry_index,
                node_id=node_id,
            )

    def _calculate_backoff(self, retry_index: int) -> float:
        """
        Compute exponential backoff with jitter for the given retry index.

        retry_index is 1-based and corresponds to the global retry count.
        """
        # Base exponential backoff: base * multiplier^(retry_index - 1)
        base_delay = self.config.base_delay_seconds * (
            self.config.multiplier ** max(retry_index - 1, 0)
        )

        delay = min(base_delay, self.config.max_delay_seconds)

        # Apply jitter in range [(1-jitter_ratio), (1+jitter_ratio)]
        if self.config.jitter_ratio > 0:
            jitter_factor = random.uniform(
                1.0 - self.config.jitter_ratio,
                1.0 + self.config.jitter_ratio,
            )
            delay *= jitter_factor

        # Never return negative delay
        return max(0.0, delay)

