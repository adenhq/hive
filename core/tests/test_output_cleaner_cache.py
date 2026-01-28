"""
Tests for OutputCleaner pattern caching functionality.

These tests verify that the caching mechanism works correctly
to avoid unnecessary LLM calls for repeated similar cleaning tasks.
"""

import time
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from framework.graph.output_cleaner import (
    OutputCleaner,
    CleansingConfig,
    CachedPattern,
    ValidationResult,
)


@dataclass
class MockNodeSpec:
    """Mock node spec for testing."""
    id: str
    input_keys: list
    input_schema: dict = None


class MockLLMResponse:
    """Mock LLM response."""
    def __init__(self, content: str):
        self.content = content


class TestOutputCleanerCache:
    """Tests for the output cleaner caching functionality."""

    def test_cache_key_generation(self):
        """Test that cache keys are generated consistently."""
        config = CleansingConfig(enabled=True, cache_successful_patterns=True)
        cleaner = OutputCleaner(config=config, llm_provider=None)

        # Same inputs should produce same key
        key1 = cleaner._make_cache_key("node_a", "node_b", ["error1", "error2"])
        key2 = cleaner._make_cache_key("node_a", "node_b", ["error1", "error2"])
        assert key1 == key2

        # Order of errors shouldn't matter (they're sorted)
        key3 = cleaner._make_cache_key("node_a", "node_b", ["error2", "error1"])
        assert key1 == key3

        # Different errors should produce different key
        key4 = cleaner._make_cache_key("node_a", "node_b", ["error1", "error3"])
        assert key1 != key4

        # Different nodes should produce different key
        key5 = cleaner._make_cache_key("node_a", "node_c", ["error1", "error2"])
        assert key1 != key5

    def test_outputs_similar(self):
        """Test that output similarity detection works correctly."""
        config = CleansingConfig(enabled=True)
        cleaner = OutputCleaner(config=config, llm_provider=None)

        # Same keys and types should be similar
        output1 = {"key1": "value1", "key2": 123}
        output2 = {"key1": "different_value", "key2": 456}
        assert cleaner._outputs_similar(output1, output2) is True

        # Different keys should not be similar
        output3 = {"key1": "value1", "key3": 123}
        assert cleaner._outputs_similar(output1, output3) is False

        # Different types should not be similar
        output4 = {"key1": "value1", "key2": "not_an_int"}
        assert cleaner._outputs_similar(output1, output4) is False

    def test_cache_pattern_stored_after_successful_clean(self):
        """Test that successful cleanings are cached."""
        config = CleansingConfig(enabled=True, cache_successful_patterns=True)

        # Mock LLM that returns cleaned output
        mock_llm = MagicMock()
        mock_llm.complete.return_value = MockLLMResponse('{"key1": "cleaned_value"}')

        cleaner = OutputCleaner(config=config, llm_provider=mock_llm)

        target_spec = MockNodeSpec(id="target_node", input_keys=["key1"])

        # First call - should use LLM
        output = {"key1": '{"key1": "nested_value"}'}
        errors = ["Key 'key1' contains JSON string with nested 'key1' field"]

        result = cleaner.clean_output(
            output=output,
            source_node_id="source_node",
            target_node_spec=target_spec,
            validation_errors=errors,
        )

        # Verify LLM was called
        assert mock_llm.complete.called
        assert result == {"key1": "cleaned_value"}

        # Verify pattern was cached
        assert len(cleaner.success_cache) == 1
        assert cleaner.cache_misses == 1
        assert cleaner.cache_hits == 0

    def test_cache_hit_avoids_llm_call(self):
        """Test that cache hits avoid calling the LLM."""
        config = CleansingConfig(enabled=True, cache_successful_patterns=True)

        # Mock LLM that returns cleaned output
        mock_llm = MagicMock()
        mock_llm.complete.return_value = MockLLMResponse('{"key1": "cleaned_value"}')

        cleaner = OutputCleaner(config=config, llm_provider=mock_llm)

        target_spec = MockNodeSpec(id="target_node", input_keys=["key1"])

        # First call - should use LLM
        output1 = {"key1": '{"key1": "nested_value_1"}'}
        errors = ["Key 'key1' contains JSON string with nested 'key1' field"]

        cleaner.clean_output(
            output=output1,
            source_node_id="source_node",
            target_node_spec=target_spec,
            validation_errors=errors,
        )

        # Reset mock to track second call
        mock_llm.reset_mock()

        # Second call with similar output - should hit cache
        output2 = {"key1": '{"key1": "nested_value_2"}'}  # Same structure, different value

        result = cleaner.clean_output(
            output=output2,
            source_node_id="source_node",
            target_node_spec=target_spec,
            validation_errors=errors,
        )

        # Verify LLM was NOT called (cache hit)
        assert not mock_llm.complete.called
        assert cleaner.cache_hits == 1
        assert cleaner.cache_misses == 1

    def test_cache_ttl_expiration(self):
        """Test that cached patterns expire after TTL."""
        # Use very short TTL for testing
        config = CleansingConfig(
            enabled=True,
            cache_successful_patterns=True,
            cache_ttl_seconds=1,  # 1 second TTL
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MockLLMResponse('{"key1": "cleaned"}')

        cleaner = OutputCleaner(config=config, llm_provider=mock_llm)

        target_spec = MockNodeSpec(id="target_node", input_keys=["key1"])
        output = {"key1": "malformed"}
        errors = ["error1"]

        # First call - caches the pattern
        cleaner.clean_output(
            output=output,
            source_node_id="source",
            target_node_spec=target_spec,
            validation_errors=errors,
        )

        assert len(cleaner.success_cache) == 1

        # Wait for TTL to expire
        time.sleep(1.1)

        # Reset mock
        mock_llm.reset_mock()

        # Second call - should NOT hit cache (expired)
        cleaner.clean_output(
            output=output,
            source_node_id="source",
            target_node_spec=target_spec,
            validation_errors=errors,
        )

        # LLM should be called again because cache expired
        assert mock_llm.complete.called

    def test_cache_max_size_eviction(self):
        """Test that cache evicts oldest entries when full."""
        config = CleansingConfig(
            enabled=True,
            cache_successful_patterns=True,
            cache_max_size=2,  # Small cache for testing
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MockLLMResponse('{"key1": "cleaned"}')

        cleaner = OutputCleaner(config=config, llm_provider=mock_llm)

        target_spec = MockNodeSpec(id="target_node", input_keys=["key1"])

        # Add 3 patterns (cache size is 2)
        for i in range(3):
            output = {"key1": f"malformed_{i}"}
            errors = [f"error_{i}"]

            cleaner.clean_output(
                output=output,
                source_node_id=f"source_{i}",
                target_node_spec=target_spec,
                validation_errors=errors,
            )
            # Small delay to ensure different timestamps
            time.sleep(0.01)

        # Cache should only have 2 entries (max size)
        assert len(cleaner.success_cache) == 2

        # The first entry (source_0) should have been evicted
        # The last two entries should remain
        keys = list(cleaner.success_cache.keys())
        assert all("source_0" not in k for k in keys)

    def test_get_stats_includes_cache_info(self):
        """Test that get_stats returns cache statistics."""
        config = CleansingConfig(enabled=True, cache_successful_patterns=True)

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MockLLMResponse('{"key1": "cleaned"}')

        cleaner = OutputCleaner(config=config, llm_provider=mock_llm)

        target_spec = MockNodeSpec(id="target_node", input_keys=["key1"])
        output = {"key1": "malformed"}
        errors = ["error1"]

        # First call - cache miss
        cleaner.clean_output(
            output=output,
            source_node_id="source",
            target_node_spec=target_spec,
            validation_errors=errors,
        )

        # Second call - cache hit
        cleaner.clean_output(
            output=output,
            source_node_id="source",
            target_node_spec=target_spec,
            validation_errors=errors,
        )

        stats = cleaner.get_stats()

        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["cache_size"] == 1
        assert stats["cache_hit_rate"] == "50.0%"
        assert stats["llm_calls_saved"] == 1

    def test_clear_cache(self):
        """Test that clear_cache empties the cache."""
        config = CleansingConfig(enabled=True, cache_successful_patterns=True)

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MockLLMResponse('{"key1": "cleaned"}')

        cleaner = OutputCleaner(config=config, llm_provider=mock_llm)

        target_spec = MockNodeSpec(id="target_node", input_keys=["key1"])

        # Add a pattern to cache
        cleaner.clean_output(
            output={"key1": "malformed"},
            source_node_id="source",
            target_node_spec=target_spec,
            validation_errors=["error"],
        )

        assert len(cleaner.success_cache) == 1

        # Clear the cache
        cleaner.clear_cache()

        assert len(cleaner.success_cache) == 0

    def test_apply_cached_pattern_json_extraction(self):
        """Test that cached patterns correctly extract nested JSON."""
        config = CleansingConfig(enabled=True, cache_successful_patterns=True)
        cleaner = OutputCleaner(config=config, llm_provider=None)

        # Manually create a cached pattern for JSON extraction
        pattern = CachedPattern(
            source_node_id="source",
            target_node_id="target",
            error_signature="abc123",
            original_output={"data": '{"data": "original_value"}'},
            cleaned_output={"data": "original_value"},
            created_at=time.time(),
            hit_count=0,
        )

        # Apply pattern to new similar output
        new_output = {"data": '{"data": "new_value"}'}
        result = cleaner._apply_cached_pattern(new_output, pattern)

        assert result["data"] == "new_value"
        assert pattern.hit_count == 1
        assert cleaner.cache_hits == 1

    def test_cache_disabled(self):
        """Test that caching can be disabled via config."""
        config = CleansingConfig(enabled=True, cache_successful_patterns=False)

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MockLLMResponse('{"key1": "cleaned"}')

        cleaner = OutputCleaner(config=config, llm_provider=mock_llm)

        target_spec = MockNodeSpec(id="target_node", input_keys=["key1"])
        output = {"key1": "malformed"}
        errors = ["error1"]

        # First call
        cleaner.clean_output(
            output=output,
            source_node_id="source",
            target_node_spec=target_spec,
            validation_errors=errors,
        )

        # Cache should be empty when disabled
        assert len(cleaner.success_cache) == 0

        # Reset mock
        mock_llm.reset_mock()

        # Second call should still use LLM
        cleaner.clean_output(
            output=output,
            source_node_id="source",
            target_node_spec=target_spec,
            validation_errors=errors,
        )

        # LLM should be called because caching is disabled
        assert mock_llm.complete.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
