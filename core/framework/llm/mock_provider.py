"""Mock LLM Provider for testing without API keys."""

from typing import Any, Dict, List, Optional
import json
from datetime import datetime


class MockLLMProvider:
    """
    Mock LLM provider that returns predefined responses without making API calls.
    Useful for testing agents without requiring API keys or credits.
    """
    
    def __init__(self, model: str = "mock-model", **kwargs) -> None:
        """
        Initialize mock provider.
        
        Args:
            model: Model name (ignored in mock mode)
            **kwargs: Additional arguments (ignored)
        """
        self.model = model
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a mock response.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Temperature setting (logged but not used)
            max_tokens: Max tokens (logged but not used)
            **kwargs: Additional arguments
            
        Returns:
            Mock response dictionary matching real LLM provider format
        """
        self.call_count += 1
        
        # Extract the last user message for context
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # Create mock response based on message content
        mock_content = self._generate_mock_content(user_message)
        
        # Record this call
        call_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "call_number": self.call_count,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response": mock_content
        }
        self.call_history.append(call_record)
        
        # Return in the same format as real providers
        return {
            "content": mock_content,
            "role": "assistant",
            "model": self.model,
            "usage": {
                "prompt_tokens": len(str(messages)) // 4,  # Rough estimate
                "completion_tokens": len(mock_content) // 4,
                "total_tokens": (len(str(messages)) + len(mock_content)) // 4
            },
            "finish_reason": "stop",
            "mock": True  # Flag to indicate this is a mock response
        }
    
    def _generate_mock_content(self, user_message: str) -> str:
        """
        Generate contextual mock content based on the user message.
        
        Args:
            user_message: The user's input message
            
        Returns:
            Contextual mock response string
        """
        user_lower = user_message.lower()
        
        # Contextual responses based on keywords
        if "search" in user_lower or "research" in user_lower:
            return json.dumps({
                "search_results": [
                    {"title": "Mock Result 1", "url": "https://example.com/1", "snippet": "This is a mock search result."},
                    {"title": "Mock Result 2", "url": "https://example.com/2", "snippet": "Another mock result for testing."}
                ],
                "query": user_message[:100]
            })
        
        elif "analyze" in user_lower or "analysis" in user_lower:
            return json.dumps({
                "analysis": "This is a mock analysis response. The data shows positive trends.",
                "confidence": 0.85,
                "key_findings": ["Finding 1", "Finding 2", "Finding 3"]
            })
        
        elif "summarize" in user_lower or "summary" in user_lower:
            return "Mock Summary: This is a brief summary of the content. Key points include important information and relevant details for testing purposes."
        
        elif "question" in user_lower or "?" in user_message:
            return "Mock Answer: Based on the available information, the answer is affirmative. This response is generated for testing purposes."
        
        elif "generate" in user_lower or "create" in user_lower:
            return json.dumps({
                "generated_content": "This is mock generated content for testing.",
                "metadata": {"type": "mock", "version": "1.0"}
            })
        
        else:
            # Generic response
            return f"Mock LLM Response (call #{self.call_count}): Acknowledged. This is a simulated response for testing purposes without making actual API calls."
    
    async def agenerate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async version of generate (delegates to sync version).
        
        Args:
            messages: List of message dictionaries
            temperature: Temperature setting
            max_tokens: Max tokens
            **kwargs: Additional arguments
            
        Returns:
            Mock response dictionary
        """
        return self.generate(messages, temperature, max_tokens, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about mock provider usage.
        
        Returns:
            Dictionary with call count and history
        """
        return {
            "total_calls": self.call_count,
            "model": self.model,
            "call_history": self.call_history
        }
    
    def reset(self) -> None:
        """Reset call counter and history."""
        self.call_count = 0
        self.call_history = []


# Convenience function for creating mock provider
def create_mock_provider(model: str = "mock-gpt-4", **kwargs) -> MockLLMProvider:
    """
    Create a mock LLM provider instance.
    
    Args:
        model: Mock model name
        **kwargs: Additional arguments
        
    Returns:
        MockLLMProvider instance
    """
    return MockLLMProvider(model=model, **kwargs)