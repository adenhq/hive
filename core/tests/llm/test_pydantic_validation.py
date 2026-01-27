import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel
from framework.llm.litellm import LiteLLMProvider
from framework.llm.provider import LLMResponse

class UserInfo(BaseModel):
    name: str
    age: int
    email: str

class TestPydanticValidation:
    @patch("framework.llm.litellm.litellm.completion")
    def test_complete_structure_success(self, mock_completion):
        # Setup mock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # Mock returning a JSON string
        mock_response.choices[0].message.content = '{"name": "Alice", "age": 30, "email": "alice@example.com"}'
        mock_response.model = "gpt-4o"
        mock_completion.return_value = mock_response

        # Init provider
        provider = LiteLLMProvider(model="gpt-4o")

        # Call complete_structure
        result = provider.complete_structure(
            messages=[{"role": "user", "content": "Extract info"}],
            schema=UserInfo
        )

        # Verify result
        assert isinstance(result, UserInfo)
        assert result.name == "Alice"
        assert result.age == 30
        assert result.email == "alice@example.com"

        # Verify mock call
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["response_format"] == UserInfo

    @patch("framework.llm.litellm.litellm.completion")
    def test_complete_structure_direct_object_return(self, mock_completion):
        # Test case where litellm returns the object directly (some versions/providers)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        expected_obj = UserInfo(name="Bob", age=25, email="bob@example.com")
        mock_response.choices[0].message.content = expected_obj
        mock_completion.return_value = mock_response

        provider = LiteLLMProvider(model="gpt-4o")

        result = provider.complete_structure(
            messages=[{"role": "user", "content": "Extract info"}],
            schema=UserInfo
        )

        assert result == expected_obj
