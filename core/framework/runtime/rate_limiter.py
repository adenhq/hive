"""Rate limiter for tool execution in Hive."""

from collections import defaultdict
from time import time
from typing import Dict, Tuple, List, Optional
import threading
import logging

logger = logging.getLogger(__name__)


class ToolRateLimiter:
    """Thread-safe rate limiter for tool execution."""
    
    def __init__(self, config: Optional[Dict[str, Dict]] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Optional dict mapping tool names to their limits.
                   Example: {'web_search': {'max_per_minute': 60}}
        """
        self.config = config or {}
        self.calls: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        self.lock = threading.Lock()
        
        # Default limits if not configured
        self.defaults = {
            'max_per_minute': 100,
            'max_per_hour': 1000,
            'max_cost_per_hour': 50.0
        }
        
        logger.info("ToolRateLimiter initialized with config: %s", config or "defaults")
    
    def check_limit(
        self, 
        tool_name: str, 
        estimated_cost: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Check if tool execution is allowed within rate limits.
        
        Args:
            tool_name: Name of the tool being executed
            estimated_cost: Estimated cost in USD
        
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        with self.lock:
            now = time()
            
            # Get limits for this tool (use defaults if not configured)
            limits = self.config.get(tool_name, self.defaults)
            
            # Clean up old call records
            self._cleanup_old_calls(tool_name, now)
            
            # Get calls within time windows
            minute_calls = [
                (t, c) for t, c in self.calls[tool_name]
                if now - t < 60
            ]
            hour_calls = [
                (t, c) for t, c in self.calls[tool_name]
                if now - t < 3600
            ]
            
            # Check per-minute limit
            max_per_min = limits.get('max_per_minute', self.defaults['max_per_minute'])
            if len(minute_calls) >= max_per_min:
                reason = (
                    f"Rate limit exceeded for {tool_name}: "
                    f"{len(minute_calls)}/{max_per_min} calls per minute"
                )
                logger.warning(reason)
                return False, reason
            
            # Check per-hour limit
            max_per_hour = limits.get('max_per_hour', self.defaults['max_per_hour'])
            if len(hour_calls) >= max_per_hour:
                reason = (
                    f"Rate limit exceeded for {tool_name}: "
                    f"{len(hour_calls)}/{max_per_hour} calls per hour"
                )
                logger.warning(reason)
                return False, reason
            
            # Check cost limit
            max_cost = limits.get('max_cost_per_hour', self.defaults['max_cost_per_hour'])
            hour_cost = sum(cost for _, cost in hour_calls)
            if hour_cost + estimated_cost > max_cost:
                reason = (
                    f"Cost limit exceeded for {tool_name}: "
                    f"${hour_cost + estimated_cost:.2f}/${max_cost:.2f} per hour"
                )
                logger.warning(reason)
                return False, reason
            
            # All checks passed - record the call
            self.calls[tool_name].append((now, estimated_cost))
            
            logger.debug(
                f"Rate limit check passed for {tool_name}: "
                f"{len(minute_calls)+1}/min, {len(hour_calls)+1}/hour, "
                f"${hour_cost + estimated_cost:.2f}/hour"
            )
            
            return True, "OK"
    
    def _cleanup_old_calls(self, tool_name: str, current_time: float) -> None:
        """Remove call records older than 1 hour."""
        self.calls[tool_name] = [
            (t, c) for t, c in self.calls[tool_name]
            if current_time - t < 3600
        ]
    
    def get_stats(self, tool_name: str) -> Dict:
        """
        Get current usage statistics for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dict with stats about calls and costs
        """
        with self.lock:
            now = time()
            self._cleanup_old_calls(tool_name, now)
            
            minute_calls = [
                (t, c) for t, c in self.calls[tool_name]
                if now - t < 60
            ]
            hour_calls = [
                (t, c) for t, c in self.calls[tool_name]
                if now - t < 3600
            ]
            
            return {
                'calls_last_minute': len(minute_calls),
                'calls_last_hour': len(hour_calls),
                'cost_last_hour': sum(c for _, c in hour_calls),
                'total_calls': len(self.calls[tool_name])
            }
    
    def reset(self, tool_name: Optional[str] = None) -> None:
        """
        Reset rate limits.
        
        Args:
            tool_name: If provided, reset only this tool. Otherwise reset all.
        """
        with self.lock:
            if tool_name:
                self.calls[tool_name] = []
                logger.info(f"Reset rate limits for {tool_name}")
            else:
                self.calls.clear()
                logger.info("Reset all rate limits")


class RateLimitExceeded(Exception):
    """Exception raised when a rate limit is exceeded."""
    pass
