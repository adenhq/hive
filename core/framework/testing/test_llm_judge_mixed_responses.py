import pytest
from framework.llm.provider import LLMProvider, LLMResponse
from framework.testing.llm_judge import LLMJudge


class MockLLMProvider(LLMProvider):
    def __init__(self, response_content: str):
        self.response_content = response_content

    def complete(self, messages, system="", tools=None, max_tokens=1024, response_format=None, json_mode=False):
        return LLMResponse(content=self.response_content, model="mock", input_tokens=100, output_tokens=50)

    def complete_with_tools(self, messages, system, tools, tool_executor, max_iterations=10):
        raise NotImplementedError()


class TestLLMJudgeMixedResponses:
    def test_json_with_preamble_text(self):
        response = 'Sure, here is the evaluation: {"passes": true, "explanation": "Good"}'
        provider = MockLLMProvider(response_content=response)
        judge = LLMJudge(llm_provider=provider)
        result = judge.evaluate("test", "doc", "sum", "crit")
        assert result["passes"] is True
        assert result["explanation"] == "Good"

    def test_json_with_postamble_text(self):
        response = '{"passes": false, "explanation": "Bad"} Let me know if you need help!'
        provider = MockLLMProvider(response_content=response)
        judge = LLMJudge(llm_provider=provider)
        result = judge.evaluate("test", "doc", "sum", "crit")
        assert result["passes"] is False
        assert result["explanation"] == "Bad"

    def test_json_with_both_preamble_and_postamble(self):
        response = 'Analysis complete: {"passes": true, "explanation": "Nice"} Thanks!'
        provider = MockLLMProvider(response_content=response)
        judge = LLMJudge(llm_provider=provider)
        result = judge.evaluate("test", "doc", "sum", "crit")
        assert result["passes"] is True
        assert result["explanation"] == "Nice"

    def test_json_with_multiline_preamble(self):
        response = '''Line 1
Line 2
{"passes": true, "explanation": "Multi"}'''
        provider = MockLLMProvider(response_content=response)
        judge = LLMJudge(llm_provider=provider)
        result = judge.evaluate("test", "doc", "sum", "crit")
        assert result["passes"] is True

    def test_markdown_json_with_preamble(self):
        response = 'Result:\n```json\n{"passes": true, "explanation": "OK"}\n```'
        provider = MockLLMProvider(response_content=response)
        judge = LLMJudge(llm_provider=provider)
        result = judge.evaluate("test", "doc", "sum", "crit")
        assert result["passes"] is True

    def test_markdown_json_with_postamble(self):
        response = '```json\n{"passes": false, "explanation": "No"}\n```\nEnd'
        provider = MockLLMProvider(response_content=response)
        judge = LLMJudge(llm_provider=provider)
        result = judge.evaluate("test", "doc", "sum", "crit")
        assert result["passes"] is False

    def test_plain_json_backward_compat(self):
        response = '{"passes": true, "explanation": "Simple"}'
        provider = MockLLMProvider(response_content=response)
        judge = LLMJudge(llm_provider=provider)
        result = judge.evaluate("test", "doc", "sum", "crit")
        assert result["passes"] is True
