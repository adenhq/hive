"""Benchmark import times for the framework."""

import time
import sys

def measure_import(module_name: str) -> float:
    """Measure time to import a module."""
    # Clear from cache if exists
    modules_to_clear = [k for k in sys.modules if k.startswith(module_name.split('.')[0])]
    for mod in modules_to_clear:
        del sys.modules[mod]

    start = time.perf_counter()
    __import__(module_name)
    elapsed = time.perf_counter() - start
    return elapsed

def main():
    print("=" * 60)
    print("IMPORT TIME BENCHMARK")
    print("=" * 60)

    # Test 1: Base framework (should be fast now)
    print("\n1. Importing framework (base)...")
    t1 = measure_import("framework")
    print(f"   Time: {t1:.3f}s")

    # Test 2: LLM module without provider
    print("\n2. Importing framework.llm (no providers)...")
    # Clear cache
    for mod in list(sys.modules.keys()):
        if mod.startswith("framework"):
            del sys.modules[mod]
    t2 = measure_import("framework.llm")
    print(f"   Time: {t2:.3f}s")

    # Test 3: Accessing LiteLLMProvider (triggers lazy load)
    print("\n3. Accessing LiteLLMProvider (lazy load)...")
    for mod in list(sys.modules.keys()):
        if mod.startswith("framework") or mod.startswith("litellm"):
            del sys.modules[mod]

    start = time.perf_counter()
    from framework.llm import LiteLLMProvider
    t3 = time.perf_counter() - start
    print(f"   Time: {t3:.3f}s")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Base framework import: {t1:.3f}s")
    print(f"LLM module (lazy):     {t2:.3f}s")
    print(f"LiteLLM (on access):   {t3:.3f}s")
    print(f"\nTotal if using LLM:    {t1 + t3:.3f}s")
    print(f"Savings when not using LLM: ~{t3:.1f}s")

if __name__ == "__main__":
    main()
