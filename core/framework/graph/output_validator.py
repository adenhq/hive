"""
Output Validator - Pydantic-based validation for LLM outputs.

This module provides:
1. Schema-based validation of LLM outputs
2. Type coercion for common mismatches
3. Detailed error messages for debugging
4. Integration with NodeSpec output definitions
"""

from typing import Any, Type, get_type_hints
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError, create_model


@dataclass
class ValidationResult:
    """Result of output validation."""
    valid: bool
    errors: list[str]
    warnings: list[str]
    coerced_output: dict[str, Any] | None = None


class OutputValidator:
    """
    Validate LLM outputs against Pydantic schemas.
    
    Usage:
        # Validate against required keys
        result = OutputValidator.validate_keys(
            output={"name": "Alice"},
            required_keys=["name", "age"]
        )
        # result.valid = False, result.errors = ["Missing required key: age"]
        
        # Validate against Pydantic model
        class UserOutput(BaseModel):
            name: str
            age: int
        
        result = OutputValidator.validate(
            output={"name": "Alice", "age": "25"},
            schema=UserOutput
        )
        # result.valid = True (age coerced to int)
        # result.coerced_output = {"name": "Alice", "age": 25}
    """
    
    @staticmethod
    def validate_keys(
        output: dict[str, Any],
        required_keys: list[str],
        optional_keys: list[str] | None = None,
    ) -> ValidationResult:
        """
        Validate that required keys exist in output.
        
        Args:
            output: The output dict to validate
            required_keys: Keys that must be present
            optional_keys: Keys that may be present (for warnings about extras)
            
        Returns:
            ValidationResult with errors for missing keys
        """
        errors = []
        warnings = []
        
        # Check required keys
        for key in required_keys:
            if key not in output:
                errors.append(f"Missing required key: {key}")
            elif output[key] is None:
                warnings.append(f"Key '{key}' is present but has null value")
        
        # Check for unexpected keys
        if optional_keys is not None:
            expected = set(required_keys) | set(optional_keys)
            for key in output:
                if key not in expected:
                    warnings.append(f"Unexpected key in output: {key}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            coerced_output=output if len(errors) == 0 else None,
        )
    
    @staticmethod
    def validate(
        output: dict[str, Any],
        schema: Type[BaseModel],
    ) -> ValidationResult:
        """
        Validate output against a Pydantic model.
        
        Args:
            output: The output dict to validate
            schema: Pydantic model class to validate against
            
        Returns:
            ValidationResult with validation errors or coerced output
        """
        errors = []
        warnings = []
        
        try:
            # Pydantic will attempt type coercion automatically
            validated = schema.model_validate(output)
            return ValidationResult(
                valid=True,
                errors=[],
                warnings=warnings,
                coerced_output=validated.model_dump(),
            )
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                msg = error["msg"]
                errors.append(f"Validation error for '{field}': {msg}")
            
            return ValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                coerced_output=None,
            )
    
    @staticmethod
    def validate_with_schema_dict(
        output: dict[str, Any],
        schema_dict: dict[str, dict[str, Any]],
    ) -> ValidationResult:
        """
        Validate output against a schema dictionary (NodeSpec.input_schema format).
        
        Args:
            output: The output dict to validate
            schema_dict: Schema dict like {"key": {"type": "str", "required": True}}
            
        Returns:
            ValidationResult with validation errors
        """
        errors = []
        warnings = []
        coerced = {}
        
        # Type mapping for schema dict
        type_map = {
            "str": str,
            "string": str,
            "int": int,
            "integer": int,
            "float": float,
            "number": float,
            "bool": bool,
            "boolean": bool,
            "list": list,
            "array": list,
            "dict": dict,
            "object": dict,
        }
        
        for key, spec in schema_dict.items():
            required = spec.get("required", False)
            expected_type = spec.get("type", "str")
            
            if key not in output:
                if required:
                    errors.append(f"Missing required key: {key}")
                continue
            
            value = output[key]
            
            # Handle null values
            if value is None:
                if required:
                    warnings.append(f"Required key '{key}' has null value")
                coerced[key] = None
                continue
            
            # Type validation and coercion
            target_type = type_map.get(expected_type.lower(), str)
            
            # Try to coerce
            try:
                if isinstance(value, target_type):
                    coerced[key] = value
                elif target_type == str:
                    coerced[key] = str(value)
                elif target_type == int:
                    coerced[key] = int(float(value))  # Handle "25.0" -> 25
                elif target_type == float:
                    coerced[key] = float(value)
                elif target_type == bool:
                    if isinstance(value, str):
                        coerced[key] = value.lower() in ("true", "yes", "1")
                    else:
                        coerced[key] = bool(value)
                elif target_type == list:
                    if isinstance(value, str):
                        import json
                        coerced[key] = json.loads(value)
                    else:
                        coerced[key] = list(value)
                elif target_type == dict:
                    if isinstance(value, str):
                        import json
                        coerced[key] = json.loads(value)
                    else:
                        coerced[key] = dict(value)
                else:
                    coerced[key] = value
            except (ValueError, TypeError, json.JSONDecodeError) as e:
                errors.append(
                    f"Cannot convert '{key}' to {expected_type}: "
                    f"got {type(value).__name__} value '{str(value)[:50]}'"
                )
                coerced[key] = value
        
        # Copy any keys not in schema
        for key in output:
            if key not in schema_dict:
                coerced[key] = output[key]
                warnings.append(f"Extra key not in schema: {key}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            coerced_output=coerced if len(errors) == 0 else None,
        )
    
    @staticmethod
    def coerce_types(
        output: dict[str, Any],
        type_hints: dict[str, type],
    ) -> dict[str, Any]:
        """
        Attempt to coerce output values to match expected types.
        
        Args:
            output: The output dict
            type_hints: Dict mapping keys to expected types
            
        Returns:
            Output dict with coerced values
        """
        result = {}
        
        for key, value in output.items():
            if key in type_hints:
                target_type = type_hints[key]
                try:
                    if target_type == str:
                        result[key] = str(value)
                    elif target_type == int:
                        result[key] = int(float(value))
                    elif target_type == float:
                        result[key] = float(value)
                    elif target_type == bool:
                        if isinstance(value, str):
                            result[key] = value.lower() in ("true", "yes", "1")
                        else:
                            result[key] = bool(value)
                    else:
                        result[key] = value
                except (ValueError, TypeError):
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def create_dynamic_schema(
        schema_dict: dict[str, dict[str, Any]],
        model_name: str = "DynamicOutput",
    ) -> Type[BaseModel]:
        """
        Create a Pydantic model from a schema dictionary.
        
        Args:
            schema_dict: Schema dict like {"key": {"type": "str", "required": True}}
            model_name: Name for the generated model
            
        Returns:
            A dynamically created Pydantic model class
        """
        type_map = {
            "str": str,
            "string": str,
            "int": int,
            "integer": int,
            "float": float,
            "number": float,
            "bool": bool,
            "boolean": bool,
            "list": list,
            "array": list,
            "dict": dict,
            "object": dict,
            "any": Any,
        }
        
        fields = {}
        for key, spec in schema_dict.items():
            field_type = type_map.get(spec.get("type", "str").lower(), Any)
            required = spec.get("required", False)
            description = spec.get("description", "")
            default = ... if required else None
            
            if required:
                fields[key] = (field_type, Field(description=description))
            else:
                fields[key] = (field_type | None, Field(default=None, description=description))
        
        return create_model(model_name, **fields)
