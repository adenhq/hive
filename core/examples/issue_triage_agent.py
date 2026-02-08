"""
Issue Triage Agent (Zero-API)
-----------------------------
A fully-instrumented Hive agent that classifies and prioritizes
GitHub issues using pure Python logic.

Run with:
    PYTHONPATH=core python core/examples/issue_triage_agent.py
"""

import asyncio
from pathlib import Path

from framework.graph import (
    Goal,
    NodeSpec,
    EdgeSpec,
    GraphSpec,
    EdgeCondition,
)
from framework.graph.executor import GraphExecutor
from framework.runtime.core import Runtime


# =========================
# Node Implementations
# =========================


def ingest_issue(title: str, body: str, labels: list[str]):
    runtime = RUNTIME
    runtime.set_node("ingest_issue")

    runtime.quick_decision(
        intent="Validate and ingest issue data",
        action="Normalize issue fields",
        reasoning="Issue title, body, and labels are required for triage",
    )

    return {
        "text": f"{title}\n{body}".lower(),
        "labels": [l.lower() for l in labels],
    }


def classify_issue(issue: dict):
    runtime = RUNTIME
    runtime.set_node("classify_issue")

    text = issue.get("text", "")
    labels = issue.get("labels", [])

    options = [
        {"id": "bug", "description": "A defect or error"},
        {"id": "feature", "description": "A feature request"},
        {"id": "question", "description": "A usage or support question"},
        {"id": "docs", "description": "Documentation-related"},
    ]

    if "bug" in labels or "error" in text or "crash" in text:
        chosen = "bug"
        reasoning = "Error-related keywords detected"
    elif "feature" in labels or "request" in text:
        chosen = "feature"
        reasoning = "Feature request indicators found"
    elif "doc" in labels or "documentation" in text:
        chosen = "docs"
        reasoning = "Documentation-related language detected"
    else:
        chosen = "question"
        reasoning = "No strong indicators; defaulting to question"

    decision_id = runtime.decide(
        intent="Classify the type of issue",
        options=options,
        chosen=chosen,
        reasoning=reasoning,
    )

    runtime.record_outcome(
        decision_id=decision_id,
        success=True,
        result={"category": chosen},
        summary=f"Issue classified as {chosen}",
    )

    return {
        "category": chosen,
        "issue": issue,
    }


def assign_priority(classification: dict):
    runtime = RUNTIME
    runtime.set_node("assign_priority")
    
    category = classification.get("category", "")
    issue = classification.get("issue", {})
    text = issue.get("text", "")
    
    options = [
        {"id": "P0", "description": "Critical"},
        {"id": "P1", "description": "High"},
        {"id": "P2", "description": "Medium"},
        {"id": "P3", "description": "Low"},
    ]

    if category == "bug" and ("crash" in text or "data loss" in text):
        chosen = "P0"
        reasoning = "Critical bug indicators present"
    elif category == "bug":
        chosen = "P1"
        reasoning = "Bug but not catastrophic"
    elif category == "feature":
        chosen = "P2"
        reasoning = "Feature requests are medium priority"
    else:
        chosen = "P3"
        reasoning = "Low urgency issue"

    decision_id = runtime.decide(
        intent="Assign issue priority",
        options=options,
        chosen=chosen,
        reasoning=reasoning,
    )

    runtime.record_outcome(
        decision_id=decision_id,
        success=True,
        result={"priority": chosen},
        summary=f"Priority set to {chosen}",
    )

    return {
        "priority": chosen,
        "category": category,  # Pass through for next node
    }


def recommend_action(priority_info: dict):
    runtime = RUNTIME
    runtime.set_node("recommend_action")

    category = priority_info.get("category", "")
    priority = priority_info.get("priority", "")

    action = {
        "bug": "Assign to engineering and request reproduction steps",
        "feature": "Add to product backlog",
        "docs": "Assign to documentation team",
        "question": "Respond and close if resolved",
    }.get(category, "Manual review required")

    runtime.quick_decision(
        intent="Recommend next action",
        action=action,
        reasoning=f"Based on category={category} and priority={priority}",
    )

    return {"recommended_action": action}


# =========================
# Agent Setup
# =========================

async def main():
    goal = Goal(
        id="issue-triage",
        name="Issue Triage",
        description="Classify, prioritize, and route GitHub issues",
        success_criteria=[
            {
                "id": "categorized",
                "description": "Issue category is determined",
                "metric": "output_contains",
                "target": "category",
                "weight": 0.5,
            },
            {
                "id": "prioritized",
                "description": "Issue priority is assigned",
                "metric": "output_contains",
                "target": "priority",
                "weight": 0.5,
            },
        ],
    )

    nodes = [
        NodeSpec(
            id="ingest_issue",
            name="Ingest Issue",
            node_type="function",
            function="ingest_issue",
            description="Normalize raw issue input and extract core fields",
            input_keys=["title", "body", "labels"],
            output_keys=["issue"],
        ),
        NodeSpec(
            id="classify_issue",
            name="Classify Issue",
            node_type="function",
            function="classify_issue",
            description="Determine the category of the issue based on content",
            input_keys=["issue"],
            output_keys=["classification"],  # Single output containing category + issue
        ),
        NodeSpec(
            id="assign_priority",
            name="Assign Priority",
            node_type="function",
            function="assign_priority",
            description="Assign priority level to the issue based on category and content",
            input_keys=["classification"],  # Read the classification dict
            output_keys=["priority_info"],  
        ),
        NodeSpec(
            id="recommend_action",
            name="Recommend Action",
            node_type="function",
            function="recommend_action",
            description="Recommend next action based on issue category and priority",
            input_keys=["priority_info"],
            output_keys=["recommended_action"],
        ),
    ]

    edges = [
        EdgeSpec(id="e1", source="ingest_issue", target="classify_issue", condition=EdgeCondition.ON_SUCCESS),
        EdgeSpec(id="e2", source="classify_issue", target="assign_priority", condition=EdgeCondition.ON_SUCCESS),
        EdgeSpec(id="e3", source="assign_priority", target="recommend_action", condition=EdgeCondition.ON_SUCCESS),
    ]

    graph = GraphSpec(
        id="issue-triage-graph",
        goal_id=goal.id,
        entry_node="ingest_issue",
        terminal_nodes=["recommend_action"],
        nodes=nodes,
        edges=edges,
    )

    runtime = Runtime(Path("./agent_logs"))
    global RUNTIME
    RUNTIME = runtime

    executor = GraphExecutor(runtime=runtime)

    executor.register_function("ingest_issue", ingest_issue)
    executor.register_function("classify_issue", classify_issue)
    executor.register_function("assign_priority", assign_priority)
    executor.register_function("recommend_action", recommend_action)

    result = await executor.execute(
        graph=graph,
        goal=goal,
        input_data={
            "title": "App crashes on startup",
            "body": "The app crashes with a null pointer exception.",
            "labels": ["bug"],
        },
    )

    print("\nTRIAGE RESULT")
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())