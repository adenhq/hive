"""
Integration between Experience Bus and Plan Cache.
Bridges real-time coordination with historical learning.
"""

from typing import Optional, Dict, Any


class ExperienceBusWithCache:
    """
    Combines Experience Bus coordination with Plan Cache memory.
    
    This class demonstrates how:
    1. Experience Bus can populate the cache with successful plans
    2. Cache can provide plans for Experience Bus to coordinate
    3. Real-time learning updates historical memory
    """
    
    def __init__(self, plan_cache=None):
        """
        Initialize with optional PlanCache instance.
        
        Args:
            plan_cache: Existing PlanCache instance, or create new
        """
        if plan_cache is None:
            from .plan_cache import PlanCache
            plan_cache = PlanCache()
        
        self.plan_cache = plan_cache
        self.execution_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'plans_stored': 0
        }
    
    def on_successful_execution(self, intent: str, plan: dict, 
                                result: dict, agent_id: str) -> None:
        """
        Callback when agent successfully executes a plan.
        
        Args:
            intent: User intent that triggered execution
            plan: The plan that was executed
            result: Execution result with metadata
            agent_id: ID of agent that executed
        """
        # Store successful plan in cache
        self.plan_cache.store(intent, plan, result)
        self.execution_stats['plans_stored'] += 1
        
        # TODO: Broadcast to Experience Bus for real-time sharing
        print(f"[ExpBusWithCache] Agent {agent_id} succeeded: {intent[:50]}...")
        print(f"[ExpBusWithCache] Plan cached for future use")
    
    def on_execution_failure(self, intent: str, error: str, 
                            agent_id: str) -> None:
        """
        Callback when agent execution fails.
        
        Args:
            intent: User intent that failed
            error: Error message/details
            agent_id: ID of agent that failed
        """
        # TODO: Experience Bus would broadcast this to prevent repeats
        print(f"[ExpBusWithCache] Agent {agent_id} failed: {intent[:50]}...")
        print(f"[ExpBusWithCache] Error: {error}")
        
        # TODO: Remove or mark problematic cached plans
        print(f"[ExpBusWithCache] Alert: Cached plan may need review")
    
    def get_or_create_plan(self, intent: str) -> Dict[str, Any]:
        """
        Main entry point: Get cached plan or indicate need for new one.
        
        Args:
            intent: User intent/query
            
        Returns:
            Dictionary with plan and metadata
        """
        # 1. Check cache first
        cached = self.plan_cache.get_similar(intent)
        
        if cached:
            self.execution_stats['cache_hits'] += 1
            return {
                'source': 'cache',
                'plan': cached['plan'],
                'metadata': {
                    'original_intent': intent,
                    'cache_hit': True,
                    'previous_success': True,
                    'usage_count': cached['usage_count']
                }
            }
        
        # 2. Cache miss - need new plan
        self.execution_stats['cache_misses'] += 1
        return {
            'source': 'llm',
            'plan': None,  # LLM needs to generate
            'metadata': {
                'original_intent': intent,
                'cache_hit': False,
                'message': 'No cached plan found, LLM generation required'
            }
        }
    
    def coordinate_cached_plan(self, intent: str, agents: list) -> Dict[str, Any]:
        """
        Coordinate execution of a cached plan across agents.
        
        Args:
            intent: User intent
            agents: List of agent IDs to coordinate
            
        Returns:
            Coordination plan
        """
        cached = self.plan_cache.get_similar(intent)
        
        if not cached:
            return {'error': 'No cached plan found'}
        
        # TODO: Experience Bus would handle actual coordination
        coordination_plan = {
            'intent': intent,
            'cached_plan': cached['plan'],
            'agents': agents,
            'steps': [
                f"1. Load cached plan for: {intent[:50]}...",
                f"2. Distribute tasks to {len(agents)} agents",
                "3. Coordinate via Experience Bus events",
                "4. Collect and merge results"
            ],
            'expected_benefits': {
                'time_saved': '15-30s LLM generation',
                'cost_saved': 'Token usage avoided',
                'determinism': 'Repeatable execution path'
            }
        }
        
        return coordination_plan
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        cache_stats = self.plan_cache.get_usage_stats()
        
        return {
            **cache_stats,
            **self.execution_stats,
            'total_executions': (
                self.execution_stats['cache_hits'] + 
                self.execution_stats['cache_misses']
            )
        }


# Example integration test
if __name__ == "__main__":
    print("=== Experience Bus + Plan Cache Integration Test ===")
    
    # Create integrated system
    system = ExperienceBusWithCache()
    
    # Simulate successful execution
    test_intent = "Generate monthly financial report"
    test_plan = {
        "graph": {
            "nodes": ["collect_data", "analyze", "generate_report"],
            "edges": [["collect_data", "analyze"], ["analyze", "generate_report"]]
        }
    }
    test_result = {"success": True, "duration": 45.2, "cost": 0.12}
    
    system.on_successful_execution(
        test_intent, test_plan, test_result, "agent_001"
    )
    
    # Test retrieval
    result = system.get_or_create_plan(test_intent)
    print(f"\nGet or create result: {result['source']}")
    print(f"Metadata: {result['metadata']}")
    
    # Test coordination
    coord = system.coordinate_cached_plan(
        test_intent, ["agent_001", "agent_002"]
    )
    print(f"\nCoordination plan steps: {coord['steps']}")
    
    # Show stats
    print(f"\nSystem stats: {system.get_stats()}")
