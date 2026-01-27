import pytest
from pydantic import BaseModel, Field
from typing import Optional, List
from framework.graph.node import _clean_schema_for_llm

class DemoModel(BaseModel):
    title_field: str = Field(title="Custom Title", description="A field with a title")
    default_field: int = Field(default=42, description="A field with a default")
    optional_field: Optional[str] = Field(default=None)
    nested_list: List[str] = Field(default_factory=list)

class NestedModel(BaseModel):
    inner: DemoModel

def test_clean_schema_basic():
    """Test that unsupported fields are removed from the schema."""
    schema = DemoModel.model_json_schema()
    cleaned = _clean_schema_for_llm(schema)
    
    # Root level cleaning
    assert "title" not in cleaned
    assert "additionalProperties" in cleaned
    assert cleaned["additionalProperties"] is False
    
    # Properties cleaning
    props = cleaned["properties"]
    
    # title_field should not have 'title'
    assert "title" not in props["title_field"]
    
    # default_field should not have 'default'
    assert "default" not in props["default_field"]
    
    # Nested fields check
    assert "additionalProperties" in cleaned
    
def test_clean_schema_nested():
    """Test cleaning of nested schemas."""
    schema = NestedModel.model_json_schema()
    cleaned = _clean_schema_for_llm(schema)
    
    # Find the nested DemoModel (Pydantic usually puts it in $defs)
    # But for a direct nested model in a simple case it might be inline or in definitions
    
    # Let's check the refined structure if it was inlined or referenced
    # If using $defs, we need to ensure $defs is also cleaned if our function handles it
    # Current implementation handles 'properties', 'items', 'allOf', 'anyOf', 'oneOf'
    
    if "$defs" in cleaned:
        for def_name, def_schema in cleaned["$defs"].items():
            cleaned["$defs"][def_name] = _clean_schema_for_llm(def_schema)
            # Verify fixed
            assert "title" not in cleaned["$defs"][def_name]
            if "properties" in cleaned["$defs"][def_name]:
                for p in cleaned["$defs"][def_name]["properties"].values():
                    assert "default" not in p

def test_clean_schema_recursive():
    """Verify recursive cleaning logic."""
    raw_schema = {
        "title": "Main",
        "type": "object",
        "properties": {
            "sub": {
                "title": "Sub",
                "default": "val",
                "type": "object",
                "properties": {
                    "leaf": {"default": 1}
                }
            }
        }
    }
    
    cleaned = _clean_schema_for_llm(raw_schema)
    
    assert "title" not in cleaned
    assert cleaned["additionalProperties"] is False
    assert "title" not in cleaned["properties"]["sub"]
    assert "default" not in cleaned["properties"]["sub"]
    assert cleaned["properties"]["sub"]["additionalProperties"] is False
    assert "default" not in cleaned["properties"]["sub"]["properties"]["leaf"]

if __name__ == "__main__":
    # If run directly, use pytest
    import sys
    sys.exit(pytest.main([__file__]))
