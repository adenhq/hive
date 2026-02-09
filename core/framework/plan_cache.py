"""
Episodic Plan Cache implementation for Hive.
Part of issue #3749: Episodic Plan Cache for Deterministic Orchestration.
"""

from typing import Dict, Any, Optional
from datetime import datetime


class PlanCache:
    """
    Cache for successful agent plans to avoid re-planning.
    
    Features:
    - Store successful plans with intent as key
    - Retrieve similar plans using intent matching
    - Simple in-memory storage (can be extended to vector DB)
    """
    
    def __init__(self):
        """Initialize empty cache."""
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    def store(self, intent: str, plan: dict, result: dict) -> None:
        """
        Store a successful plan in cache.
        
        Args:
            intent: The user intent/query string
            plan: The successful execution plan (DAG/JSON)
            result: The execution result and metadata
        """
        self.cache[intent] = {
            'plan': plan,
            'result': result,
            'timestamp': datetime.now().isoformat(),
            'usage_count': 0
        }
        print(f"[PlanCache] Stored plan for intent: {intent[:50]}...")
    
    def get_similar(self, intent: str, threshold: float = 0.95) -> Optional[dict]:
        """
        Get similar cached plan based on intent.
        
        Args:
            intent: User intent to match
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            Cached plan if found, None otherwise
        """
        # TODO: Implement vector similarity search
        # For now, exact string match
        cached = self.cache.get(intent)
        
        if cached:
            cached['usage_count'] += 1
            print(f"[PlanCache] Using cached plan for: {intent[:50]}...")
            return cached
        
        print(f"[PlanCache] No cache hit for: {intent[:50]}...")
        return None
    
    def get_usage_stats(self) -> dict:
        """Get cache usage statistics."""
        total = len(self.cache)
        used = sum(1 for item in self.cache.values() if item['usage_count'] > 0)
        
        return {
            'total_plans': total,
            'plans_used': used,
            'hit_rate': (used / total * 100) if total > 0 else 0
        }
    
    def clear(self) -> None:
        """Clear all cached plans."""
        self.cache.clear()
        print("[PlanCache] Cache cleared")
    
    def __len__(self) -> int:
        """Return number of cached plans."""
        return len(self.cache)


# Example usage
if __name__ == "__main__":
    # Quick test
    cache = PlanCache()
    
    # Store a plan
    test_plan = {"nodes": ["start", "process", "end"]}
    test_result = {"success": True, "cost": 0.05}
    
    cache.store("Create monthly budget report", test_plan, test_result)
    
    # Retrieve it
    cached = cache.get_similar("Create monthly budget report")
    if cached:
        print(f"Retrieved plan: {cached['plan']}")
    
    print(f"Stats: {cache.get_usage_stats()}")
