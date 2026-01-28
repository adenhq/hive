"""
LLM JSON Cleaner Tool - A deterministic JSON cleaning tool for FastMCP.

Extracts, normalizes, and validates JSON from raw LLM output against a schema.
Supports strict, coerce, and force modes for different levels of correction.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field


# ============================================================================
# SCHEMA MODELS
# ============================================================================

class CleanerError(BaseModel):
    """Structured error from the cleaning process."""
    stage: Literal["extraction", "syntax", "schema"]
    path: Optional[str] = None
    message: str


class CleanerMetadata(BaseModel):
    """Metadata about the cleaning operation."""
    success: bool
    errors: Optional[list[CleanerError]] = None
    forced_fixes: Optional[list[str]] = None


class CleanerResult(BaseModel):
    """Complete result from the JSON cleaner."""
    data: Optional[dict[str, Any] | list[Any]] = None
    metadata: CleanerMetadata


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _extract_json_block(raw: str) -> tuple[str | None, CleanerError | None]:
    """Phase 1: Extract JSON block from raw LLM output."""
    text = raw.strip()
    
    # Try to find JSON in markdown fences first
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(fence_pattern, text)
    if matches:
        text = matches[0].strip()
    
    # Find first { or [
    start_idx = -1
    for i, ch in enumerate(text):
        if ch in "{[":
            start_idx = i
            break
    
    if start_idx == -1:
        return None, CleanerError(stage="extraction", message="No JSON object or array found")
    
    open_char = text[start_idx]
    close_char = "}" if open_char == "{" else "]"
    
    # Find matching closing brace/bracket
    depth = 0
    in_string = False
    escape_next = False
    end_idx = -1
    
    for i in range(start_idx, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                end_idx = i
                break
    
    if end_idx == -1:
        return None, CleanerError(stage="extraction", message="Unbalanced braces/brackets")
    
    return text[start_idx:end_idx + 1], None


def _normalize_syntax(json_str: str) -> tuple[Any | None, CleanerError | None]:
    """Phase 2: Parse JSON with limited safe fixes."""
    # Try direct parse
    try:
        return json.loads(json_str), None
    except json.JSONDecodeError:
        pass
    
    # Fix trailing commas
    try:
        fixed = re.sub(r",(\s*[}\]])", r"\1", json_str)
        return json.loads(fixed), None
    except json.JSONDecodeError:
        pass
    
    # Fix single quotes + trailing commas
    try:
        fixed = re.sub(r"(?<!\\)'", '"', json_str)
        fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)
        return json.loads(fixed), None
    except json.JSONDecodeError:
        pass
    
    return None, CleanerError(stage="syntax", message="Invalid JSON syntax after normalization attempts")


def _get_type_default(schema_type: str | list[str] | None) -> Any:
    """Get deterministic default value for a schema type."""
    if schema_type is None:
        return None
    
    types = [schema_type] if isinstance(schema_type, str) else schema_type
    primary_type = types[0] if types else None
    
    defaults = {
        "string": "",
        "integer": 0,
        "number": 0,
        "boolean": False,
        "array": [],
        "object": {},
        "null": None
    }
    return defaults.get(primary_type)


def _coerce_value(value: Any, expected_type: str | list[str], force: bool = False) -> tuple[Any, bool]:
    """Coerce a value to match expected schema type. Returns (coerced_value, was_forced)."""
    types = [expected_type] if isinstance(expected_type, str) else expected_type
    
    # Check if already correct type
    for t in types:
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return value, False
        if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return value, False
        if t == "boolean" and isinstance(value, bool):
            return value, False
        if t == "string" and isinstance(value, str):
            return value.strip(), False
        if t == "null" and value is None:
            return value, False
        if t == "array" and isinstance(value, list):
            return value, False
        if t == "object" and isinstance(value, dict):
            return value, False
    
    # Safe coercions (coerce mode)
    for t in types:
        if t == "integer" and isinstance(value, str):
            stripped = value.strip()
            if stripped.lstrip("-").isdigit():
                return int(stripped), False
        elif t == "integer" and isinstance(value, float):
            if value.is_integer():
                return int(value), False
        elif t == "number" and isinstance(value, str):
            stripped = value.strip()
            try:
                result = float(stripped)
                if result.is_integer() and "." not in stripped:
                    return int(result), False
                return result, False
            except ValueError:
                pass
        elif t == "boolean" and isinstance(value, str):
            stripped = value.strip().lower()
            if stripped == "true":
                return True, False
            if stripped == "false":
                return False, False
        elif t == "string" and isinstance(value, str):
            return value.strip(), False
    
    # Aggressive coercions (force mode only)
    if force:
        for t in types:
            if t == "string":
                if value is None:
                    return "", True
                return str(value).strip(), True
            elif t == "integer":
                if isinstance(value, bool):
                    return 1 if value else 0, True
                if isinstance(value, float):
                    return int(value), True
                if isinstance(value, str):
                    match = re.search(r"-?\d+", value)
                    if match:
                        return int(match.group()), True
                return 0, True
            elif t == "number":
                if isinstance(value, bool):
                    return 1.0 if value else 0.0, True
                if isinstance(value, str):
                    match = re.search(r"-?\d+\.?\d*", value)
                    if match:
                        num_str = match.group()
                        return float(num_str) if "." in num_str else int(num_str), True
                return 0, True
            elif t == "boolean":
                if value is None or value == "" or value == 0 or value == []:
                    return False, True
                if isinstance(value, str):
                    stripped = value.strip().lower()
                    if stripped in ("0", "no", "n", "false", "off", ""):
                        return False, True
                    if stripped in ("1", "yes", "y", "true", "on"):
                        return True, True
                return bool(value), True
            elif t == "array":
                if value is None:
                    return [], True
                if not isinstance(value, list):
                    return [value], True
            elif t == "object":
                if value is None:
                    return {}, True
            elif t == "null":
                return None, True
    
    return value, False


def _apply_coercions(data: Any, schema: dict[str, Any], force: bool = False, 
                     path: str = "", fixes: list[str] | None = None) -> Any:
    """Recursively apply safe coercions based on schema."""
    if fixes is None:
        fixes = []
    
    if schema is None:
        return data
    
    schema_type = schema.get("type")
    
    if schema_type and data is not None and not isinstance(data, (dict, list)):
        coerced, was_forced = _coerce_value(data, schema_type, force)
        if was_forced:
            fixes.append(f"Forced coercion at '{path or 'root'}': {type(data).__name__} -> {type(coerced).__name__}")
        data = coerced
    
    if isinstance(data, dict):
        properties = schema.get("properties", {})
        result = {}
        for key, val in data.items():
            prop_schema = properties.get(key, {})
            result[key] = _apply_coercions(val, prop_schema, force, f"{path}.{key}" if path else key, fixes)
        return result
    
    if isinstance(data, list):
        items_schema = schema.get("items", {})
        return [_apply_coercions(item, items_schema, force, f"{path}[{i}]", fixes) for i, item in enumerate(data)]
    
    return data


def _apply_defaults(data: Any, schema: dict[str, Any]) -> Any:
    """Apply schema defaults to missing fields."""
    if not isinstance(data, dict):
        return data
    
    properties = schema.get("properties", {})
    result = dict(data)
    
    for key, prop_schema in properties.items():
        if key not in result and "default" in prop_schema:
            result[key] = prop_schema["default"]
        elif key in result and isinstance(result[key], dict) and isinstance(prop_schema.get("properties"), dict):
            result[key] = _apply_defaults(result[key], prop_schema)
    
    return result


def _remove_extra_properties(data: Any, schema: dict[str, Any], path: str = "", 
                             fixes: list[str] | None = None) -> Any:
    """Remove properties not defined in schema (force mode always removes extras)."""
    if fixes is None:
        fixes = []
    
    if not isinstance(data, dict):
        return data
    
    properties = schema.get("properties", {})
    
    result = {}
    for key, val in data.items():
        if key in properties:
            prop_schema = properties[key]
            result[key] = _remove_extra_properties(val, prop_schema, f"{path}.{key}" if path else key, fixes)
        else:
            fixes.append(f"Removed extra property '{(path + '.' + key) if path else key}'")
    
    return result


def _fill_missing_required(data: Any, schema: dict[str, Any], path: str = "", 
                           fixes: list[str] | None = None) -> Any:
    """Fill missing required fields with type-appropriate defaults (force mode)."""
    if fixes is None:
        fixes = []
    
    if not isinstance(data, dict):
        return data
    
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    result = dict(data)
    
    for key in required:
        if key not in result:
            prop_schema = properties.get(key, {})
            if "default" in prop_schema:
                result[key] = prop_schema["default"]
                fixes.append(f"Applied schema default at '{(path + '.' + key) if path else key}'")
            else:
                prop_type = prop_schema.get("type")
                default_val = _get_type_default(prop_type)
                result[key] = default_val
                fixes.append(f"Filled missing required '{(path + '.' + key) if path else key}' with {repr(default_val)}")
    
    for key, prop_schema in properties.items():
        if key in result and isinstance(result[key], dict) and prop_schema.get("type") == "object":
            result[key] = _fill_missing_required(result[key], prop_schema, f"{path}.{key}" if path else key, fixes)
    
    return result


def _apply_constraints(data: Any, schema: dict[str, Any], path: str = "", 
                       fixes: list[str] | None = None) -> Any:
    """Apply schema constraints like min/max, minLength/maxLength (force mode)."""
    if fixes is None:
        fixes = []
    
    if schema is None:
        return data
    
    # String constraints
    if isinstance(data, str):
        min_len = schema.get("minLength")
        max_len = schema.get("maxLength")
        if max_len is not None and len(data) > max_len:
            fixes.append(f"Truncated string at '{path or 'root'}' to maxLength {max_len}")
            data = data[:max_len]
        if min_len is not None and len(data) < min_len:
            fixes.append(f"Padded string at '{path or 'root'}' to minLength {min_len}")
            data = data.ljust(min_len)
    
    # Numeric constraints
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        exclusive_min = schema.get("exclusiveMinimum")
        exclusive_max = schema.get("exclusiveMaximum")
        
        if minimum is not None and data < minimum:
            fixes.append(f"Clamped '{path or 'root'}' to minimum {minimum}")
            data = minimum
        if maximum is not None and data > maximum:
            fixes.append(f"Clamped '{path or 'root'}' to maximum {maximum}")
            data = maximum
        if exclusive_min is not None and data <= exclusive_min:
            fixes.append(f"Clamped '{path or 'root'}' above exclusiveMinimum {exclusive_min}")
            data = exclusive_min + (1 if isinstance(data, int) else 0.001)
        if exclusive_max is not None and data >= exclusive_max:
            fixes.append(f"Clamped '{path or 'root'}' below exclusiveMaximum {exclusive_max}")
            data = exclusive_max - (1 if isinstance(data, int) else 0.001)
    
    # Array constraints
    if isinstance(data, list):
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        items_schema = schema.get("items", {})
        
        if max_items is not None and len(data) > max_items:
            fixes.append(f"Truncated array at '{path or 'root'}' to maxItems {max_items}")
            data = data[:max_items]
        if min_items is not None and len(data) < min_items:
            item_default = _get_type_default(items_schema.get("type"))
            while len(data) < min_items:
                data.append(item_default)
            fixes.append(f"Padded array at '{path or 'root'}' to minItems {min_items}")
        
        data = [_apply_constraints(item, items_schema, f"{path}[{i}]", fixes) for i, item in enumerate(data)]
    
    # Recurse into objects
    if isinstance(data, dict):
        properties = schema.get("properties", {})
        result = {}
        for key, val in data.items():
            prop_schema = properties.get(key, {})
            result[key] = _apply_constraints(val, prop_schema, f"{path}.{key}" if path else key, fixes)
        return result
    
    return data


def _filter_invalid_array_items(data: Any, schema: dict[str, Any], path: str = "", 
                                fixes: list[str] | None = None) -> Any:
    """Filter out array items that can't be coerced to the correct type (force mode)."""
    if fixes is None:
        fixes = []
    
    if isinstance(data, list) and "items" in schema:
        items_schema = schema["items"]
        item_type = items_schema.get("type")
        
        if item_type:
            valid_items = []
            for i, item in enumerate(data):
                coerced, _ = _coerce_value(item, item_type, force=True)
                is_valid = False
                
                if item_type == "integer" and isinstance(coerced, int) and not isinstance(coerced, bool):
                    is_valid = True
                elif item_type == "number" and isinstance(coerced, (int, float)) and not isinstance(coerced, bool):
                    is_valid = True
                elif item_type == "string" and isinstance(coerced, str):
                    is_valid = True
                elif item_type == "boolean" and isinstance(coerced, bool):
                    is_valid = True
                elif item_type == "object" and isinstance(coerced, dict):
                    coerced = _filter_invalid_array_items(coerced, items_schema, f"{path}[{i}]", fixes)
                    is_valid = True
                elif item_type == "array" and isinstance(coerced, list):
                    coerced = _filter_invalid_array_items(coerced, items_schema, f"{path}[{i}]", fixes)
                    is_valid = True
                
                if is_valid:
                    valid_items.append(coerced)
                else:
                    fixes.append(f"Filtered out invalid item at '{path}[{i}]'")
            
            return valid_items
    
    if isinstance(data, dict):
        properties = schema.get("properties", {})
        return {k: _filter_invalid_array_items(v, properties.get(k, {}), f"{path}.{k}" if path else k, fixes) 
                for k, v in data.items()}
    
    return data


def _validate_against_schema(data: Any, schema: dict[str, Any]) -> list[CleanerError]:
    """Validate data against JSON schema and return errors."""
    try:
        from jsonschema.validators import validator_for
        validator_cls = validator_for(schema)
        validator = validator_cls(schema)
        
        errors = []
        for err in validator.iter_errors(data):
            errors.append(CleanerError(
                stage="schema",
                path=".".join(str(p) for p in err.absolute_path) if err.absolute_path else None,
                message=err.message
            ))
        return errors
    except ImportError:
        return [CleanerError(stage="schema", message="jsonschema package not installed")]


def _process_json(data: Any, schema: dict[str, Any], mode: str) -> tuple[Any | None, list[CleanerError] | None, list[str]]:
    """Phase 3: Validate against schema with optional coercion."""
    working_data = data
    forced_fixes: list[str] = []
    
    is_coerce = mode in ("coerce", "force")
    is_force = mode == "force"
    
    # Apply coercions
    if is_coerce:
        working_data = _apply_coercions(working_data, schema, force=is_force, fixes=forced_fixes)
    
    # Force mode: aggressive fixes
    if is_force:
        working_data = _remove_extra_properties(working_data, schema, fixes=forced_fixes)
        working_data = _fill_missing_required(working_data, schema, fixes=forced_fixes)
        working_data = _apply_constraints(working_data, schema, fixes=forced_fixes)
        working_data = _filter_invalid_array_items(working_data, schema, fixes=forced_fixes)
    
    # Apply defaults
    working_data = _apply_defaults(working_data, schema)
    
    # Validate
    errors = _validate_against_schema(working_data, schema)
    
    if errors:
        return None, errors, forced_fixes
    
    return working_data, None, forced_fixes


def _clean_llm_json(llm_output: str, schema: dict[str, Any], mode: str) -> CleanerResult:
    """Core cleaning logic."""
    # Phase 1: Extract JSON block
    json_str, extract_err = _extract_json_block(llm_output)
    if extract_err:
        return CleanerResult(
            data=None,
            metadata=CleanerMetadata(success=False, errors=[extract_err])
        )
    
    # Phase 2: Normalize syntax
    parsed, syntax_err = _normalize_syntax(json_str)
    if syntax_err:
        return CleanerResult(
            data=None,
            metadata=CleanerMetadata(success=False, errors=[syntax_err])
        )
    
    # Phase 3: Validate and coerce
    cleaned, schema_errs, forced_fixes = _process_json(parsed, schema, mode)
    if schema_errs:
        return CleanerResult(
            data=None,
            metadata=CleanerMetadata(
                success=False, 
                errors=schema_errs, 
                forced_fixes=forced_fixes if forced_fixes else None
            )
        )
    
    return CleanerResult(
        data=cleaned,
        metadata=CleanerMetadata(
            success=True, 
            errors=None, 
            forced_fixes=forced_fixes if forced_fixes else None
        )
    )


# FASTMCP TOOL REGISTRATION

def register_tools(mcp: FastMCP) -> None:
    """Register LLM JSON cleaner tools with the MCP server."""

    @mcp.tool()
    def llm_json_cleaner(
        llm_output: str,
        schema: dict[str, Any],
        mode: str = "coerce",
    ) -> dict[str, Any]:
        """
        Clean and validate JSON from raw LLM output against a JSON Schema.
        
        Extracts JSON from markdown fences or surrounding text, fixes common
        syntax errors, and validates/coerces values to match the schema.
        
        Use this tool when you need to:
        - Extract JSON from LLM responses with markdown or chatter
        - Fix trailing commas, single quotes, or other syntax issues
        - Coerce string values like "42" to integers
        - Force schema compliance by filling defaults and removing extras

        Args:
            llm_output: Raw LLM response string that may contain JSON
            schema: JSON Schema (draft-07 compatible) to validate against
            mode: Validation mode - one of:
                  - "strict": No coercion, exact type matching required
                  - "coerce": Safe coercions (e.g., "42" -> 42, "true" -> True)
                  - "force": Aggressive fixes (fill missing required, remove extras,
                            clamp to min/max, coerce any value)

        Returns:
            Dict with:
            - data: The cleaned JSON object/array (null if failed)
            - metadata: {
                success: bool,
                errors: [{stage, path, message}, ...] or null,
                forced_fixes: ["description of fix", ...] or null
              }
        
        Examples:
            # Extract and coerce from markdown
            llm_json_cleaner(
                '```json\\n{"count": "42"}\\n```',
                {"type": "object", "properties": {"count": {"type": "integer"}}},
                "coerce"
            )
            # Returns: {"data": {"count": 42}, "metadata": {"success": true, ...}}
            
            # Force mode fills missing required fields
            llm_json_cleaner(
                '{"name": "test"}',
                {"type": "object", "properties": {"name": {"type": "string"}, 
                 "count": {"type": "integer"}}, "required": ["name", "count"]},
                "force"
            )
            # Returns: {"data": {"name": "test", "count": 0}, "metadata": {...}}
        """
        # Validate mode
        if mode not in ("strict", "coerce", "force"):
            return {
                "data": None,
                "metadata": {
                    "success": False,
                    "errors": [{
                        "stage": "schema",
                        "path": None,
                        "message": f"Invalid mode '{mode}'. Must be 'strict', 'coerce', or 'force'"
                    }],
                    "forced_fixes": None
                }
            }
        
        # Validate schema is a dict
        if not isinstance(schema, dict):
            return {
                "data": None,
                "metadata": {
                    "success": False,
                    "errors": [{
                        "stage": "schema",
                        "path": None,
                        "message": "Schema must be a JSON object"
                    }],
                    "forced_fixes": None
                }
            }
        
        # Run the cleaner
        result = _clean_llm_json(llm_output, schema, mode)
        return result.model_dump()


# STANDALONE USAGE (for testing without FastMCP)

def run(llm_output: str, schema: dict[str, Any], mode: str = "coerce") -> tuple[Any, dict[str, Any]]:
    """
    Standalone entry point. Returns (data, metadata) tuple.
    
    Args:
        llm_output: Raw LLM response string
        schema: JSON Schema (draft-07)
        mode: "strict" | "coerce" | "force"
    
    Returns:
        Tuple of (cleaned_data, metadata_dict)
    """
    result = _clean_llm_json(llm_output, schema, mode)
    return (result.data, result.metadata.model_dump())


