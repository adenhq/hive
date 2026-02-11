"""Tests for rate limiter."""

import pytest
import time
from framework.runtime.rate_limiter import ToolRateLimiter, RateLimitExceeded


class TestToolRateLimiter:
    """Test rate limiter functionality."""
    
    def test_initialization(self):
        """Test that rate limiter initializes correctly."""
        limiter = ToolRateLimiter()
        assert limiter is not None
        assert limiter.defaults['max_per_minute'] == 100
    
    def test_allows_calls_within_limit(self):
        """Test that calls within limit are allowed."""
        limiter = ToolRateLimiter({
            'test_tool': {
                'max_per_minute': 5,
                'max_per_hour': 100,
                'max_cost_per_hour': 10.0
            }
        })
        
        # First call should succeed
        allowed, reason = limiter.check_limit('test_tool', 0.01)
        assert allowed is True
        assert reason == "OK"
        
        # Second call should succeed
        allowed, reason = limiter.check_limit('test_tool', 0.01)
        assert allowed is True
    
    def test_blocks_when_per_minute_exceeded(self):
        """Test that calls are blocked when per-minute limit exceeded."""
        limiter = ToolRateLimiter({
            'test_tool': {
                'max_per_minute': 3,
                'max_per_hour': 100,
                'max_cost_per_hour': 10.0
            }
        })
        
        # Make 3 calls (should all succeed)
        for i in range(3):
            allowed, _ = limiter.check_limit('test_tool', 0.01)
            assert allowed is True, f"Call {i+1} should be allowed"
        
        # 4th call should fail
        allowed, reason = limiter.check_limit('test_tool', 0.01)
        assert allowed is False
        assert 'calls per minute' in reason
    
    def test_blocks_when_cost_exceeded(self):
        """Test that calls are blocked when cost limit exceeded."""
        limiter = ToolRateLimiter({
            'test_tool': {
                'max_per_minute': 100,
                'max_per_hour': 100,
                'max_cost_per_hour': 1.0
            }
        })
        
        # Make expensive call (within limit)
        allowed, _ = limiter.check_limit('test_tool', 0.5)
        assert allowed is True
        
        # Another expensive call should exceed cost limit
        allowed, reason = limiter.check_limit('test_tool', 0.6)
        assert allowed is False
        assert 'Cost limit' in reason
    
    def test_get_stats(self):
        """Test that stats are accurate."""
        limiter = ToolRateLimiter()
        
        # Make some calls
        limiter.check_limit('test_tool', 0.05)
        limiter.check_limit('test_tool', 0.03)
        
        # Get stats
        stats = limiter.get_stats('test_tool')
        
        assert stats['calls_last_minute'] == 2
        assert stats['calls_last_hour'] == 2
        assert stats['cost_last_hour'] == 0.08
    
    def test_reset_single_tool(self):
        """Test resetting a single tool."""
        limiter = ToolRateLimiter()
        
        # Make calls to two tools
        limiter.check_limit('tool1', 0.01)
        limiter.check_limit('tool2', 0.01)
        
        # Reset tool1
        limiter.reset('tool1')
        
        # tool1 should be reset, tool2 should not
        assert limiter.get_stats('tool1')['total_calls'] == 0
        assert limiter.get_stats('tool2')['total_calls'] == 1
    
    def test_reset_all_tools(self):
        """Test resetting all tools."""
        limiter = ToolRateLimiter()
        
        # Make calls to multiple tools
        limiter.check_limit('tool1', 0.01)
        limiter.check_limit('tool2', 0.01)
        
        # Reset all
        limiter.reset()
        
        # Both should be reset
        assert limiter.get_stats('tool1')['total_calls'] == 0
        assert limiter.get_stats('tool2')['total_calls'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
