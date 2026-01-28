"""
Output Cleaner - Framework-level I/O validation and cleaning.

Validates node outputs match expected schemas and uses fast LLM
to clean malformed outputs before they flow to the next node.

This prevents cascading failures and dramatically improves execution success rates.
"""

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CleansingConfig:
    """Configuration for output cleansing."""

    enabled: bool = True
    fast_model: str = "cerebras/llama-3.3-70b"  # Fast, cheap model for cleaning
    max_retries: int = 2
    cache_successful_patterns: bool = True
    cache_max_size: int = 100  # Maximum number of cached patterns
    cache_ttl_seconds: int = 3600  # Cache entries expire after 1 hour
    fallback_to_raw: bool = True  # If cleaning fails, pass raw output
    log_cleanings: bool = True  # Log when cleansing happens


@dataclass
class CachedPattern:
    """A cached successful cleansing pattern."""

    source_node_id: str
    target_node_id: str
    error_signature: str  # Hash of validation errors
    original_output: dict[str, Any]  # The raw output that was cleaned
    cleaned_output: dict[str, Any]  # The successful cleaned result
    created_at: float  # Timestamp for TTL tracking
    hit_count: int = 0  # Number of times this pattern was reused


@dataclass
class ValidationResult:
    """Result of output validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cleaned_output: dict[str, Any] | None = None


class OutputCleaner:
    """
    Framework-level output validation and cleaning.

    Uses fast LLM (llama-3.3-70b) to clean malformed outputs
    before they flow to the next node.

    Example:
        cleaner = OutputCleaner(
            config=CleansingConfig(enabled=True),
            llm_provider=llm,
        )

        # Validate output
        validation = cleaner.validate_output(
            output=node_output,
            source_node_id="analyze",
            target_node_spec=next_node_spec,
        )

        if not validation.valid:
            # Clean the output
            cleaned = cleaner.clean_output(
                output=node_output,
                source_node_id="analyze",
                target_node_spec=next_node_spec,
                validation_errors=validation.errors,
            )
    """

    def __init__(self, config: CleansingConfig, llm_provider=None):
        """
        Initialize the output cleaner.

        Args:
            config: Cleansing configuration
            llm_provider: Optional LLM provider. If None and cleaning is enabled,
                         will create a LiteLLMProvider with the configured fast_model.
        """
        self.config = config
        self.success_cache: dict[str, CachedPattern] = {}  # Cache successful patterns
        self.failure_count: dict[str, int] = {}  # Track edge failures
        self.cleansing_count = 0  # Track total cleanings performed
        self.cache_hits = 0  # Track cache hits
        self.cache_misses = 0  # Track cache misses

        # Initialize LLM provider for cleaning
        if llm_provider:
            self.llm = llm_provider
        elif config.enabled:
            # Create dedicated fast LLM provider for cleaning
            try:
                from framework.llm.litellm import LiteLLMProvider
                import os

                api_key = os.environ.get("CEREBRAS_API_KEY")
                if api_key:
                    self.llm = LiteLLMProvider(
                        api_key=api_key,
                        model=config.fast_model,
                        temperature=0.0,  # Deterministic cleaning
                    )
                    logger.info(
                        f"✓ Initialized OutputCleaner with {config.fast_model}"
                    )
                else:
                    logger.warning(
                        "⚠ CEREBRAS_API_KEY not found, output cleaning will be disabled"
                    )
                    self.llm = None
            except ImportError:
                logger.warning("⚠ LiteLLMProvider not available, output cleaning disabled")
                self.llm = None
        else:
            self.llm = None

    def _make_cache_key(
        self,
        source_node_id: str,
        target_node_id: str,
        validation_errors: list[str],
    ) -> str:
        """
        Create a cache key from the node transition and error signature.

        The key combines:
        - Source node ID
        - Target node ID
        - Hash of sorted validation errors (for pattern matching)
        """
        # Create a stable hash of the errors
        error_str = "|".join(sorted(validation_errors))
        error_hash = hashlib.md5(error_str.encode()).hexdigest()[:8]
        return f"{source_node_id}→{target_node_id}:{error_hash}"

    def _get_cached_pattern(
        self,
        source_node_id: str,
        target_node_id: str,
        validation_errors: list[str],
        output: dict[str, Any],
    ) -> CachedPattern | None:
        """
        Check if we have a cached pattern for this transition and errors.

        Returns the cached pattern if found and not expired, otherwise None.
        """
        if not self.config.cache_successful_patterns:
            return None

        cache_key = self._make_cache_key(source_node_id, target_node_id, validation_errors)

        if cache_key not in self.success_cache:
            return None

        pattern = self.success_cache[cache_key]

        # Check TTL expiration
        if time.time() - pattern.created_at > self.config.cache_ttl_seconds:
            del self.success_cache[cache_key]
            logger.debug(f"Cache entry expired: {cache_key}")
            return None

        # Check if output structure is similar enough to apply cached pattern
        if self._outputs_similar(output, pattern.original_output):
            return pattern

        return None

    def _outputs_similar(
        self,
        output1: dict[str, Any],
        output2: dict[str, Any],
    ) -> bool:
        """
        Check if two outputs have similar structure (same keys, similar types).

        This determines if a cached cleaning pattern can be reused.
        """
        # Same keys check
        if set(output1.keys()) != set(output2.keys()):
            return False

        # Check value types match
        for key in output1.keys():
            type1 = type(output1[key]).__name__
            type2 = type(output2[key]).__name__
            if type1 != type2:
                return False

        return True

    def _cache_pattern(
        self,
        source_node_id: str,
        target_node_id: str,
        validation_errors: list[str],
        original_output: dict[str, Any],
        cleaned_output: dict[str, Any],
    ) -> None:
        """
        Cache a successful cleansing pattern for future reuse.
        """
        if not self.config.cache_successful_patterns:
            return

        cache_key = self._make_cache_key(source_node_id, target_node_id, validation_errors)

        # Enforce max cache size (LRU-style: remove oldest entries)
        if len(self.success_cache) >= self.config.cache_max_size:
            # Remove the oldest entry by created_at
            oldest_key = min(
                self.success_cache.keys(),
                key=lambda k: self.success_cache[k].created_at
            )
            del self.success_cache[oldest_key]
            logger.debug(f"Cache full, evicted oldest entry: {oldest_key}")

        self.success_cache[cache_key] = CachedPattern(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            error_signature=cache_key.split(":")[-1],
            original_output=original_output.copy(),
            cleaned_output=cleaned_output.copy(),
            created_at=time.time(),
            hit_count=0,
        )

        logger.debug(f"Cached cleansing pattern: {cache_key}")

    def _apply_cached_pattern(
        self,
        output: dict[str, Any],
        pattern: CachedPattern,
    ) -> dict[str, Any]:
        """
        Apply a cached cleansing pattern to a new similar output.

        This is a smart mapping: if the cached pattern shows how to transform
        certain fields, we apply the same transformation logic.
        """
        # Update hit count
        pattern.hit_count += 1
        self.cache_hits += 1

        # For simple cases, if the structure matches, we can apply the same field mappings
        # This works well for common cases like nested JSON string extraction

        cleaned = {}

        for key in pattern.cleaned_output.keys():
            if key in output:
                original_val = pattern.original_output.get(key)
                cleaned_val = pattern.cleaned_output.get(key)
                current_val = output.get(key)

                # Case 1: Original was a JSON string containing the key, cleaned extracted it
                # e.g., original: '{"data": "value"}' -> cleaned: "value" (for key "data")
                if isinstance(original_val, str) and isinstance(current_val, str):
                    try:
                        original_parsed = json.loads(original_val)
                        current_parsed = json.loads(current_val)

                        # Check if we extracted a nested field in the original cleaning
                        if isinstance(original_parsed, dict) and key in original_parsed:
                            if isinstance(current_parsed, dict) and key in current_parsed:
                                # Same pattern: extract the nested key
                                cleaned[key] = current_parsed[key]
                                continue
                    except json.JSONDecodeError:
                        pass

                # Case 2: Original was a JSON string and cleaned was a dict (parsed JSON)
                if isinstance(original_val, str) and isinstance(cleaned_val, dict):
                    if isinstance(current_val, str):
                        try:
                            parsed = json.loads(current_val)
                            if isinstance(parsed, dict) and key in parsed:
                                cleaned[key] = parsed[key]
                            else:
                                cleaned[key] = parsed
                            continue
                        except json.JSONDecodeError:
                            pass

                # Case 3: Same types - just use the current value
                if type(original_val) == type(cleaned_val):
                    cleaned[key] = current_val
                else:
                    # Type transformation happened, try to replicate
                    cleaned[key] = current_val
            else:
                # Key not in current output but was in pattern - use pattern value as template
                cleaned[key] = pattern.cleaned_output[key]

        if self.config.log_cleanings:
            logger.info(
                f"⚡ Cache hit! Applied cached pattern (hit #{pattern.hit_count})"
            )

        return cleaned

    def validate_output(
        self,
        output: dict[str, Any],
        source_node_id: str,
        target_node_spec: Any,  # NodeSpec
    ) -> ValidationResult:
        """
        Validate output matches target node's expected input schema.

        Args:
            output: Output from source node
            source_node_id: ID of source node
            target_node_spec: Spec of target node (for input_keys)

        Returns:
            ValidationResult with errors and optionally cleaned output
        """
        errors = []
        warnings = []

        # Check 1: Required input keys present
        for key in target_node_spec.input_keys:
            if key not in output:
                errors.append(f"Missing required key: '{key}'")
                continue

            value = output[key]

            # Check 2: Detect if value is JSON string (the JSON parsing trap!)
            if isinstance(value, str):
                # Try parsing as JSON to detect the trap
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, dict):
                        if key in parsed:
                            # Key exists in parsed JSON - classic parsing failure!
                            errors.append(
                                f"Key '{key}' contains JSON string with nested '{key}' field - "
                                f"likely parsing failure from LLM node"
                            )
                        elif len(value) > 100:
                            # Large JSON string, but doesn't contain the key
                            warnings.append(
                                f"Key '{key}' contains JSON string ({len(value)} chars)"
                            )
                except json.JSONDecodeError:
                    # Not JSON, check if suspiciously large
                    if len(value) > 500:
                        warnings.append(
                            f"Key '{key}' contains large string ({len(value)} chars), "
                            f"possibly entire LLM response"
                        )

            # Check 3: Type validation (if schema provided)
            if hasattr(target_node_spec, "input_schema") and target_node_spec.input_schema:
                expected_schema = target_node_spec.input_schema.get(key)
                if expected_schema:
                    expected_type = expected_schema.get("type")
                    if expected_type and not self._type_matches(value, expected_type):
                        actual_type = type(value).__name__
                        errors.append(
                            f"Key '{key}': expected type '{expected_type}', got '{actual_type}'"
                        )

        # Warnings don't make validation fail, but errors do
        is_valid = len(errors) == 0

        if not is_valid and self.config.log_cleanings:
            logger.warning(
                f"⚠ Output validation failed for {source_node_id} → {target_node_spec.id}: "
                f"{len(errors)} error(s), {len(warnings)} warning(s)"
            )

        return ValidationResult(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
        )

    def clean_output(
        self,
        output: dict[str, Any],
        source_node_id: str,
        target_node_spec: Any,  # NodeSpec
        validation_errors: list[str],
    ) -> dict[str, Any]:
        """
        Use fast LLM to clean malformed output.

        First checks for a cached pattern from a previous similar cleaning.
        If no cache hit, uses the LLM and caches the successful result.

        Args:
            output: Raw output from source node
            source_node_id: ID of source node
            target_node_spec: Target node spec (for schema)
            validation_errors: Errors from validation

        Returns:
            Cleaned output matching target schema

        Raises:
            Exception: If cleaning fails and fallback_to_raw is False
        """
        if not self.config.enabled:
            logger.warning("⚠ Output cleansing disabled in config")
            return output

        # Check cache first - avoid LLM call if we've seen this pattern before
        cached_pattern = self._get_cached_pattern(
            source_node_id=source_node_id,
            target_node_id=target_node_spec.id,
            validation_errors=validation_errors,
            output=output,
        )

        if cached_pattern is not None:
            # Cache hit! Apply the cached transformation
            return self._apply_cached_pattern(output, cached_pattern)

        # Cache miss - need to use LLM
        self.cache_misses += 1

        if not self.llm:
            logger.warning("⚠ No LLM provider available for cleansing")
            return output

        # Build schema description for target node
        schema_desc = self._build_schema_description(target_node_spec)

        # Create cleansing prompt
        prompt = f"""Clean this malformed agent output to match the expected schema.

VALIDATION ERRORS:
{chr(10).join(f"- {e}" for e in validation_errors)}

EXPECTED SCHEMA for node '{target_node_spec.id}':
{schema_desc}

RAW OUTPUT from node '{source_node_id}':
{json.dumps(output, indent=2, default=str)}

INSTRUCTIONS:
1. Extract values that match the expected schema keys
2. If a value is a JSON string, parse it and extract the correct field
3. Convert types to match the schema (string, dict, list, number, boolean)
4. Remove extra fields not in the expected schema
5. Ensure all required keys are present

Return ONLY valid JSON matching the expected schema. No explanations, no markdown."""

        try:
            if self.config.log_cleanings:
                logger.info(
                    f"🧹 Cleaning output from '{source_node_id}' using {self.config.fast_model}"
                )

            response = self.llm.complete(
                messages=[{"role": "user", "content": prompt}],
                system="You clean malformed agent outputs. Return only valid JSON matching the schema.",
                max_tokens=2048,  # Sufficient for cleaning most outputs
            )

            # Parse cleaned output
            cleaned_text = response.content.strip()

            # Remove markdown if present
            if cleaned_text.startswith("```"):
                match = re.search(
                    r"```(?:json)?\s*\n?(.*?)\n?```", cleaned_text, re.DOTALL
                )
                if match:
                    cleaned_text = match.group(1).strip()

            cleaned = json.loads(cleaned_text)

            if isinstance(cleaned, dict):
                self.cleansing_count += 1

                # Cache this successful pattern for future reuse
                self._cache_pattern(
                    source_node_id=source_node_id,
                    target_node_id=target_node_spec.id,
                    validation_errors=validation_errors,
                    original_output=output,
                    cleaned_output=cleaned,
                )

                if self.config.log_cleanings:
                    logger.info(
                        f"✓ Output cleaned successfully (total cleanings: {self.cleansing_count})"
                    )
                return cleaned
            else:
                logger.warning(
                    f"⚠ Cleaned output is not a dict: {type(cleaned)}"
                )
                if self.config.fallback_to_raw:
                    return output
                else:
                    raise ValueError(
                        f"Cleaning produced {type(cleaned)}, expected dict"
                    )

        except json.JSONDecodeError as e:
            logger.error(f"✗ Failed to parse cleaned JSON: {e}")
            if self.config.fallback_to_raw:
                logger.info("↩ Falling back to raw output")
                return output
            else:
                raise

        except Exception as e:
            logger.error(f"✗ Output cleaning failed: {e}")
            if self.config.fallback_to_raw:
                logger.info("↩ Falling back to raw output")
                return output
            else:
                raise

    def _build_schema_description(self, node_spec: Any) -> str:
        """Build human-readable schema description from NodeSpec."""
        lines = ["{"]

        for key in node_spec.input_keys:
            # Get type hint and description if available
            if hasattr(node_spec, "input_schema") and node_spec.input_schema:
                schema = node_spec.input_schema.get(key, {})
                type_hint = schema.get("type", "any")
                description = schema.get("description", "")
                required = schema.get("required", True)

                line = f'  "{key}": {type_hint}'
                if description:
                    line += f'  // {description}'
                if required:
                    line += " (required)"
                lines.append(line + ",")
            else:
                # No schema, just show the key
                lines.append(f'  "{key}": any  // (required)')

        lines.append("}")
        return "\n".join(lines)

    def _type_matches(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "str": str,
            "int": int,
            "integer": int,
            "float": float,
            "number": (int, float),
            "bool": bool,
            "boolean": bool,
            "dict": dict,
            "object": dict,
            "list": list,
            "array": list,
            "any": object,  # Matches everything
        }

        expected_class = type_map.get(expected_type.lower())
        if expected_class:
            return isinstance(value, expected_class)

        # Unknown type, allow it
        return True

    def get_stats(self) -> dict[str, Any]:
        """Get cleansing statistics including cache performance."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "total_cleanings": self.cleansing_count,
            "failure_count": dict(self.failure_count),
            "cache_size": len(self.success_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{hit_rate:.1f}%",
            "llm_calls_saved": self.cache_hits,  # Each cache hit saves an LLM call
        }

    def clear_cache(self) -> None:
        """Clear the pattern cache."""
        self.success_cache.clear()
        logger.info("🗑️ Output cleaner cache cleared")
