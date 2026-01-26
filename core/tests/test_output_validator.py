"""
Tests for Output Validator.
"""

import pytest
from pydantic import BaseModel

from framework.graph.output_validator import OutputValidator, ValidationResult


class TestValidateKeys:
    """Tests for validate_keys method."""
    
    def test_all_required_present(self):
        """Test when all required keys are present."""
        output = {"name": "Alice", "age": 25}
        result = OutputValidator.validate_keys(output, ["name", "age"])
        
        assert result.valid is True
        assert result.errors == []
        assert result.coerced_output == output
    
    def test_missing_required_key(self):
        """Test when required key is missing."""
        output = {"name": "Alice"}
        result = OutputValidator.validate_keys(output, ["name", "age"])
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert "age" in result.errors[0]
    
    def test_null_value_warning(self):
        """Test warning when value is null."""
        output = {"name": None}
        result = OutputValidator.validate_keys(output, ["name"])
        
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "null" in result.warnings[0]
    
    def test_unexpected_key_warning(self):
        """Test warning for unexpected keys."""
        output = {"name": "Alice", "extra": "value"}
        result = OutputValidator.validate_keys(
            output, 
            required_keys=["name"],
            optional_keys=[]
        )
        
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "extra" in result.warnings[0]


class TestValidatePydantic:
    """Tests for validate method with Pydantic models."""
    
    def test_valid_output(self):
        """Test validation of valid output."""
        class UserOutput(BaseModel):
            name: str
            age: int
        
        output = {"name": "Alice", "age": 25}
        result = OutputValidator.validate(output, UserOutput)
        
        assert result.valid is True
        assert result.coerced_output == {"name": "Alice", "age": 25}
    
    def test_type_coercion(self):
        """Test automatic type coercion."""
        class UserOutput(BaseModel):
            name: str
            age: int
        
        # age is string, should be coerced to int
        output = {"name": "Alice", "age": "25"}
        result = OutputValidator.validate(output, UserOutput)
        
        assert result.valid is True
        assert result.coerced_output["age"] == 25
        assert isinstance(result.coerced_output["age"], int)
    
    def test_invalid_type(self):
        """Test validation failure for invalid type."""
        class UserOutput(BaseModel):
            name: str
            age: int
        
        output = {"name": "Alice", "age": "not-a-number"}
        result = OutputValidator.validate(output, UserOutput)
        
        assert result.valid is False
        assert len(result.errors) >= 1
    
    def test_missing_field(self):
        """Test validation failure for missing field."""
        class UserOutput(BaseModel):
            name: str
            age: int
        
        output = {"name": "Alice"}
        result = OutputValidator.validate(output, UserOutput)
        
        assert result.valid is False


class TestValidateWithSchemaDict:
    """Tests for validate_with_schema_dict method."""
    
    def test_valid_schema(self):
        """Test validation with schema dict."""
        schema = {
            "name": {"type": "str", "required": True},
            "age": {"type": "int", "required": True},
        }
        output = {"name": "Alice", "age": 25}
        
        result = OutputValidator.validate_with_schema_dict(output, schema)
        
        assert result.valid is True
        assert result.coerced_output["name"] == "Alice"
        assert result.coerced_output["age"] == 25
    
    def test_type_coercion_str_to_int(self):
        """Test coercion from string to int."""
        schema = {"age": {"type": "int", "required": True}}
        output = {"age": "25"}
        
        result = OutputValidator.validate_with_schema_dict(output, schema)
        
        assert result.valid is True
        assert result.coerced_output["age"] == 25
    
    def test_type_coercion_str_to_float(self):
        """Test coercion from string to float."""
        schema = {"price": {"type": "float", "required": True}}
        output = {"price": "19.99"}
        
        result = OutputValidator.validate_with_schema_dict(output, schema)
        
        assert result.valid is True
        assert result.coerced_output["price"] == 19.99
    
    def test_type_coercion_str_to_bool(self):
        """Test coercion from string to bool."""
        schema = {"active": {"type": "bool", "required": True}}
        
        result1 = OutputValidator.validate_with_schema_dict({"active": "true"}, schema)
        assert result1.coerced_output["active"] is True
        
        result2 = OutputValidator.validate_with_schema_dict({"active": "false"}, schema)
        assert result2.coerced_output["active"] is False
    
    def test_missing_required(self):
        """Test error for missing required field."""
        schema = {"name": {"type": "str", "required": True}}
        output = {}
        
        result = OutputValidator.validate_with_schema_dict(output, schema)
        
        assert result.valid is False
        assert "name" in result.errors[0]
    
    def test_optional_field(self):
        """Test optional field handling."""
        schema = {
            "name": {"type": "str", "required": True},
            "nickname": {"type": "str", "required": False},
        }
        output = {"name": "Alice"}
        
        result = OutputValidator.validate_with_schema_dict(output, schema)
        
        assert result.valid is True
    
    def test_extra_fields_warning(self):
        """Test warning for extra fields not in schema."""
        schema = {"name": {"type": "str", "required": True}}
        output = {"name": "Alice", "extra": "value"}
        
        result = OutputValidator.validate_with_schema_dict(output, schema)
        
        assert result.valid is True
        assert any("extra" in w for w in result.warnings)


class TestCoerceTypes:
    """Tests for coerce_types method."""
    
    def test_coerce_to_int(self):
        """Test coercion to int."""
        output = {"count": "10"}
        type_hints = {"count": int}
        
        result = OutputValidator.coerce_types(output, type_hints)
        
        assert result["count"] == 10
        assert isinstance(result["count"], int)
    
    def test_coerce_to_float(self):
        """Test coercion to float."""
        output = {"price": "19.99"}
        type_hints = {"price": float}
        
        result = OutputValidator.coerce_types(output, type_hints)
        
        assert result["price"] == 19.99
    
    def test_coerce_preserves_unknown_keys(self):
        """Test that unknown keys are preserved."""
        output = {"name": "Alice", "unknown": "value"}
        type_hints = {"name": str}
        
        result = OutputValidator.coerce_types(output, type_hints)
        
        assert result["unknown"] == "value"


class TestCreateDynamicSchema:
    """Tests for create_dynamic_schema method."""
    
    def test_create_simple_schema(self):
        """Test creating a simple dynamic schema."""
        schema_dict = {
            "name": {"type": "str", "required": True, "description": "User name"},
            "age": {"type": "int", "required": False, "description": "User age"},
        }
        
        Model = OutputValidator.create_dynamic_schema(schema_dict, "UserModel")
        
        # Validate with the dynamic model
        instance = Model(name="Alice", age=25)
        assert instance.name == "Alice"
        assert instance.age == 25
    
    def test_dynamic_schema_optional_fields(self):
        """Test optional fields in dynamic schema."""
        schema_dict = {
            "required_field": {"type": "str", "required": True},
            "optional_field": {"type": "str", "required": False},
        }
        
        Model = OutputValidator.create_dynamic_schema(schema_dict)
        
        # Should work without optional field
        instance = Model(required_field="value")
        assert instance.required_field == "value"
        assert instance.optional_field is None
