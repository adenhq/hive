import sys
from unittest.mock import MagicMock

# Mock GEPA dependency before it's imported by framework
sys.modules["kiss"] = MagicMock()
sys.modules["kiss.agents"] = MagicMock()
sys.modules["kiss.agents.gepa"] = MagicMock()

import pytest
from unittest.mock import patch
from framework.builder.optimizer import GEPAAgentOptimizer
from framework.graph.node import NodeSpec
from framework.graph.goal import Goal
from framework.schemas.run import Run, RunStatus
from framework.schemas.decision import Decision, Outcome

@pytest.fixture
def mock_node_spec():
    return NodeSpec(
        id="test-node",
        name="Test Node",
        description="A node for testing GEPA",
        system_prompt="Initial prompt",
    )

@pytest.fixture
def mock_goal():
    return Goal(
        id="test-goal",
        name="Test Goal",
        description="Goal for testing",
        success_criteria=[{
            "id": "sc1", 
            "description": "Success",
            "metric": "accuracy",
            "target": 0.9
        }]
    )

class MockExecutor:
    async def execute(self, **kwargs):
        return MagicMock(run_id="run-123", output={"success": True})

def test_optimizer_initialization(mock_node_spec, mock_goal):
    optimizer = GEPAAgentOptimizer(
        node_spec=mock_node_spec,
        goal=mock_goal,
        storage_path="/tmp/hive",
        executor_factory=lambda: MockExecutor()
    )
    assert optimizer.node_spec.id == "test-node"
    assert optimizer.initial_prompt == "Initial prompt"

@patch("framework.builder.optimizer.GEPA")
def test_optimize_flow(mock_gepa_class, mock_node_spec, mock_goal):
    # Setup mock GEPA
    mock_gepa_instance = mock_gepa_class.return_value
    mock_result = MagicMock()
    mock_result.prompt_template = "Optimized prompt"
    mock_gepa_instance.optimize.return_value = mock_result
    
    optimizer = GEPAAgentOptimizer(
        node_spec=mock_node_spec,
        goal=mock_goal,
        storage_path="/tmp/hive",
        executor_factory=lambda: MockExecutor()
    )
    
    train_examples = [{"input": "test"}]
    optimized_node = optimizer.optimize(train_examples)
    
    assert optimized_node.system_prompt == "Optimized prompt"
    mock_gepa_class.assert_called_once()
    mock_gepa_instance.optimize.assert_called_with(train_examples)

def test_decision_to_trajectory_segment():
    decision = Decision(
        id="dec-1",
        node_id="test-node",
        intent="Testing trajectory",
        reasoning="Because I can",
        chosen_option_id="opt-1"
    )
    decision.outcome = Outcome(success=True, summary="It worked")
    
    segment = decision.to_trajectory_segment()
    assert segment["role"] == "assistant"
    assert "Intent: Testing trajectory" in segment["content"]
    assert "Outcome: Success" in segment["content"]
