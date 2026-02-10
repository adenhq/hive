import pytest
from framework.graph.hitl import HITLQuestion, HITLInputType

def test_valid_free_text():
    """Test creating a valid free text question."""
    q = HITLQuestion(id="q1", question="What is your name?", input_type=HITLInputType.FREE_TEXT)
    assert q.id == "q1"
    assert q.question == "What is your name?"

def test_valid_selection():
    """Test creating a valid selection question."""
    q = HITLQuestion(
        id="q2",
        question="Select a color",
        input_type=HITLInputType.SELECTION,
        options=["Red", "Blue"]
    )
    assert q.options == ["Red", "Blue"]

def test_invalid_selection():
    """Test creating a selection question without options raises ValueError."""
    with pytest.raises(ValueError, match="The 'options' field must be provided for SELECTION input types."):
        HITLQuestion(
            id="q3",
            question="Select a color",
            input_type=HITLInputType.SELECTION
        )
    # Also test empty list
    with pytest.raises(ValueError, match="The 'options' field must be provided for SELECTION input types."):
        HITLQuestion(
            id="q3b",
            question="Select a color",
            input_type=HITLInputType.SELECTION,
            options=[]
        )

def test_valid_structured():
    """Test creating a valid structured question."""
    q = HITLQuestion(
        id="q4",
        question="Provide details",
        input_type=HITLInputType.STRUCTURED,
        fields={"name": "Your name", "age": "Your age"}
    )
    assert q.fields == {"name": "Your name", "age": "Your age"}

def test_invalid_structured():
    """Test creating a structured question without fields raises ValueError."""
    with pytest.raises(ValueError, match="The 'fields' field must be provided for STRUCTURED input types."):
        HITLQuestion(
            id="q5",
            question="Provide details",
            input_type=HITLInputType.STRUCTURED
        )
    # Also test empty dict
    with pytest.raises(ValueError, match="The 'fields' field must be provided for STRUCTURED input types."):
        HITLQuestion(
            id="q5b",
            question="Provide details",
            input_type=HITLInputType.STRUCTURED,
            fields={}
        )
