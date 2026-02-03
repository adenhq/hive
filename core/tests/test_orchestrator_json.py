"""Tests for Orchestrator JSON routing."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from collections import namedtuple
from framework.runner.orchestrator import AgentOrchestrator, RoutingDecision, CapabilityResponse, CapabilityLevel
from framework.llm.provider import LLMResponse

# Helper to create capable agents list that works with string formatting
def create_capable_agent(name, reasoning="test"):
    return (name, CapabilityResponse(
        agent_name=name,
        level=CapabilityLevel.BEST_FIT,
        confidence=0.9,
        reasoning=reasoning
    ))

@pytest.mark.asyncio
async def test_llm_route_with_clean_json():
    """Test routing with clean JSON response."""
    mock_llm = MagicMock()
    mock_llm.complete.return_value = LLMResponse(
        content='{"selected": ["agent1"], "reasoning": "test", "parallel": false}',
        model="test-model"
    )
    
    orchestrator = AgentOrchestrator(llm=mock_llm)
    # Register mock agent
    orchestrator._agents["agent1"] = MagicMock()
    
    capable = [
        create_capable_agent("agent1"),
        create_capable_agent("agent2")
    ]
    
    decision = await orchestrator._llm_route({"task": "test"}, "intent", capable)
    
    assert decision.selected_agents == ["agent1"]
    assert decision.reasoning == "test"
    assert decision.should_parallelize is False

@pytest.mark.asyncio
async def test_llm_route_with_markdown_json():
    """Test routing with markdown code block JSON response."""
    mock_llm = MagicMock()
    mock_llm.complete.return_value = LLMResponse(
        content='```json\n{"selected": ["agent1"], "reasoning": "test", "parallel": true}\n```',
        model="test-model"
    )
    
    orchestrator = AgentOrchestrator(llm=mock_llm)
    orchestrator._agents["agent1"] = MagicMock()
    
    capable = [create_capable_agent("agent1")]
    
    decision = await orchestrator._llm_route({"task": "test"}, "intent", capable)
    
    assert decision.selected_agents == ["agent1"]
    assert decision.should_parallelize is True
    
@pytest.mark.asyncio
async def test_llm_route_with_text_before_json():
    """Test routing with text before JSON."""
    mock_llm = MagicMock()
    mock_llm.complete.return_value = LLMResponse(
        content='Here is the routing:\n{"selected": ["agent1"], "reasoning": "test"}',
        model="test-model"
    )
    
    orchestrator = AgentOrchestrator(llm=mock_llm)
    orchestrator._agents["agent1"] = MagicMock()
    
    capable = [create_capable_agent("agent1")]
    
    decision = await orchestrator._llm_route({"task": "test"}, "intent", capable)
    
    assert decision.selected_agents == ["agent1"]
