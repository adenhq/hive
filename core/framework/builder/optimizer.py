"""
GEPA Agent Optimizer - Bridges Hive Runtime with GEPA algorithm.
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from framework.graph.goal import Goal
from framework.graph.node import NodeSpec
from framework.runtime.core import Runtime
from framework.schemas.run import RunStatus
from kiss.agents.gepa import GEPA, PromptCandidate

logger = logging.getLogger(__name__)

class GEPAAgentOptimizer:
    """
    Optimizes Hive agent nodes using GEPA (Genetic-Pareto Prompt Evolution).
    """

    def __init__(
        self,
        node_spec: NodeSpec,
        goal: Goal,
        storage_path: str,
        executor_factory: Callable,
    ):
        self.node_spec = node_spec
        self.goal = goal
        self.storage_path = storage_path
        self.executor_factory = executor_factory
        self.initial_prompt = node_spec.system_prompt or ""

    def _agent_wrapper(self, prompt_template: str, arguments: dict[str, str]) -> tuple[str, list[Any]]:
        """
        Runs the Hive agent with a mutated prompt and returns results/trajectories.
        """
        # Create a mutated copy of the node spec
        mutated_spec = self.node_spec.model_copy(update={"system_prompt": prompt_template})
        
        # We need a way to run just this node or a graph containing it.
        # For simplicity in this integration, we assume we are optimizing a node within its graph context.
        # The executor_factory should return a GraphExecutor that can run the relevant graph.
        
        runtime = Runtime(self.storage_path)
        executor = self.executor_factory()
        
        # In a real implementation, we would need to ensure the graph uses the mutated_spec.
        # This might require passing the mutated node to the executor or patching the graph.
        
        import asyncio
        run_result = asyncio.run(
            executor.execute(
                goal=self.goal,
                input_data=arguments,
                # Injected mutated node spec would go here if supported by executor
            )
        )
        
        # Extract "trajectory" from the run
        run_data = runtime.storage.load_run(run_result.run_id)
        trajectory = []
        if run_data:
            for decision in run_data.decisions:
                if decision.node_id == self.node_spec.id:
                    trajectory.append(decision.to_trajectory_segment())
        
        result_str = json.dumps(run_result.output, default=str)
        return result_str, trajectory

    def _evaluation_fn(self, result_str: str) -> dict[str, float]:
        """
        Evaluates the agent result.
        """
        try:
            result = json.loads(result_str)
            # Default success metric. Can be customized.
            success = 1.0 if result.get("success") or result.get("result") else 0.0
            return {"success": success}
        except Exception:
            return {"success": 0.0}

    def optimize(self, train_examples: list[dict[str, str]], **gepa_kwargs) -> NodeSpec:
        """
        Runs the GEPA optimization loop.
        """
        gepa = GEPA(
            agent_wrapper=self._agent_wrapper,
            initial_prompt_template=self.initial_prompt,
            evaluation_fn=self._evaluation_fn,
            **gepa_kwargs
        )
        
        best_candidate: PromptCandidate = gepa.optimize(train_examples)
        
        # Update the node spec with the best prompt
        optimized_node = self.node_spec.model_copy(
            update={"system_prompt": best_candidate.prompt_template}
        )
        return optimized_node
