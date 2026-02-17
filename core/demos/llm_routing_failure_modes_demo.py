"""
Demo script showing all three LLM routing failure modes.

This demonstrates the fix for the fail-open vulnerability in LLM routing.
"""

from unittest.mock import Mock

from framework.graph.edge import EdgeCondition, EdgeSpec, LLMFailureMode


def demo_failure_modes():
    """Demonstrate all three failure modes with simulated LLM failures."""

    # Setup
    mock_goal = Mock()
    mock_goal.name = "Demo Goal"
    mock_goal.description = "Demonstrating LLM routing failure modes"

    source_output = {"result": "success"}
    memory = {"context": "demo"}

    print("=" * 80)
    print("LLM ROUTING FAILURE MODES DEMO")
    print("=" * 80)
    print()

    # -------------------------------------------------------------------
    # Mode 1: PROCEED (Fail-open, backward compatible)
    # -------------------------------------------------------------------
    print("MODE 1: PROCEED (Fail-Open)")
    print("-" * 80)

    edge_proceed = EdgeSpec(
        id="proceed-edge",
        source="source",
        target="target",
        condition=EdgeCondition.LLM_DECIDE,
        on_llm_failure=LLMFailureMode.PROCEED,  # Default
        description="Non-critical routing with high availability requirement",
    )

    # Test with missing LLM
    result = edge_proceed.should_traverse(
        source_success=True,
        source_output=source_output,
        memory=memory,
        llm=None,  # LLM unavailable
        goal=mock_goal,
    )

    print(f"Result when LLM unavailable (source succeeded): {result}")
    print("Behavior: Proceeds because source_success=True (fail-open)")
    print()

    # -------------------------------------------------------------------
    # Mode 2: SKIP (Fail-closed, security-critical)
    # -------------------------------------------------------------------
    print("MODE 2: SKIP (Fail-Closed)")
    print("-" * 80)

    edge_skip = EdgeSpec(
        id="auth-check",
        source="validate_token",
        target="protected_resource",
        condition=EdgeCondition.LLM_DECIDE,
        on_llm_failure=LLMFailureMode.SKIP,  # Fail-closed
        description="Authorization check - must not proceed on failures",
    )

    # Test with missing LLM (simulates LLM service outage)
    result = edge_skip.should_traverse(
        source_success=True,
        source_output={"token": "valid"},
        memory=memory,
        llm=None,  # LLM unavailable
        goal=mock_goal,
    )

    print(f"Result when LLM unavailable (source succeeded): {result}")
    print("  Behavior: Does NOT proceed even though source succeeded (fail-closed)")
    print("  Use case: Security gates, authorization checks, sensitive data access")
    print()

    # -------------------------------------------------------------------
    # Mode 3: RAISE (Escalate to executor)
    # -------------------------------------------------------------------
    print("MODE 3: RAISE (Escalate)")
    print("-" * 80)

    edge_raise = EdgeSpec(
        id="critical-decision",
        source="analysis",
        target="action",
        condition=EdgeCondition.LLM_DECIDE,
        on_llm_failure=LLMFailureMode.RAISE,  # Escalate
        description="Critical decision that requires LLM - halt if unavailable",
    )

    # Test with missing LLM
    try:
        result = edge_raise.should_traverse(
            source_success=True,
            source_output=source_output,
            memory=memory,
            llm=None,  # LLM unavailable
            goal=mock_goal,
        )
        print(f"Should have raised exception but got: {result}")
    except RuntimeError as e:
        print("Raised RuntimeError as expected:")
        print(f"  {e}")
        print("Use case: Critical workflows where LLM decision is mandatory")
    print()

    # -------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Before this fix:")
    print("All LLM routing failures defaulted to PROCEED (fail-open)")
    print("Security vulnerability: bypassed authorization checks on failures")
    print("Silent failures: only warnings logged")
    print()
    print("After this fix:")
    print("Three configurable modes: PROCEED, SKIP, RAISE")
    print("Default is PROCEED (backward compatible)")
    print("Security-critical edges can use SKIP (fail-closed)")
    print("Critical workflows can use RAISE (halt execution)")
    print("Clear error logging with edge context")
    print()
    print("Migration for security-critical edges:")
    print("on_llm_failure=LLMFailureMode.SKIP  # Explicitly fail-closed")
    print("=" * 80)


if __name__ == "__main__":
    demo_failure_modes()
