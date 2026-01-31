"""
MCP Server for Agent Building Tools

Exposes tools for building goal-driven agents via the Model Context Protocol.
Fixed: Anthropic provider integration and credential enforcement.

Usage:
    python -m framework.mcp.agent_builder_server
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Annotated

from mcp.server import FastMCP

from framework.graph import Constraint, EdgeCondition, EdgeSpec, Goal, NodeSpec, SuccessCriterion
from framework.graph.plan import Plan

# Testing framework imports
from framework.testing.prompts import (
    PYTEST_TEST_FILE_HEADER,
)
from framework.utils.io import atomic_write

# Initialize MCP server
mcp = FastMCP("agent-builder")


# Session persistence directory
SESSIONS_DIR = Path(".agent-builder-sessions")
ACTIVE_SESSION_FILE = SESSIONS_DIR / ".active"


# Session storage
class BuildSession:
    """Build session with persistence support."""

    def __init__(self, name: str, session_id: str | None = None):
        self.id = session_id or f"build_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.name = name
        self.goal: Goal | None = None
        self.nodes: list[NodeSpec] = []
        self.edges: list[EdgeSpec] = []
        self.mcp_servers: list[dict] = []  # MCP server configurations
        self.created_at = datetime.now().isoformat()
        self.last_modified = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Serialize session to dictionary."""
        return {
            "session_id": self.id,
            "name": self.name,
            "goal": self.goal.model_dump() if self.goal else None,
            "nodes": [n.model_dump() for n in self.nodes],
            "edges": [e.model_dump() for e in self.edges],
            "mcp_servers": self.mcp_servers,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BuildSession":
        """Deserialize session from dictionary."""
        session = cls(name=data["name"], session_id=data["session_id"])
        session.created_at = data.get("created_at", session.created_at)
        session.last_modified = data.get("last_modified", session.last_modified)

        # Restore goal
        if data.get("goal"):
            goal_data = data["goal"]
            session.goal = Goal(
                id=goal_data["id"],
                name=goal_data["name"],
                description=goal_data["description"],
                success_criteria=[
                    SuccessCriterion(**sc) for sc in goal_data.get("success_criteria", [])
                ],
                constraints=[Constraint(**c) for c in goal_data.get("constraints", [])],
            )

        # Restore nodes
        session.nodes = [NodeSpec(**n) for n in data.get("nodes", [])]

        # Restore edges
        edges_data = data.get("edges", [])
        for e in edges_data:
            # Convert condition string back to enum
            condition_str = e.get("condition")
            if isinstance(condition_str, str):
                condition_map = {
                    "always": EdgeCondition.ALWAYS,
                    "on_success": EdgeCondition.ON_SUCCESS,
                    "on_failure": EdgeCondition.ON_FAILURE,
                    "conditional": EdgeCondition.CONDITIONAL,
                    "llm_decide": EdgeCondition.LLM_DECIDE,
                }
                e["condition"] = condition_map.get(condition_str, EdgeCondition.ON_SUCCESS)
            session.edges.append(EdgeSpec(**e))

        # Restore MCP servers
        session.mcp_servers = data.get("mcp_servers", [])

        return session


# Global session
_session: BuildSession | None = None


def _ensure_sessions_dir():
    """Ensure sessions directory exists."""
    SESSIONS_DIR.mkdir(exist_ok=True)


def _save_session(session: BuildSession):
    """Save session to disk."""
    _ensure_sessions_dir()

    # Update last modified
    session.last_modified = datetime.now().isoformat()

    # Save session file
    session_file = SESSIONS_DIR / f"{session.id}.json"
    with atomic_write(session_file) as f:
        json.dump(session.to_dict(), f, indent=2, default=str)

    # Update active session pointer
    with atomic_write(ACTIVE_SESSION_FILE) as f:
        f.write(session.id)


def _load_session(session_id: str) -> BuildSession:
    """Load session from disk."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        raise ValueError(f"Session '{session_id}' not found")

    with open(session_file) as f:
        data = json.load(f)

    return BuildSession.from_dict(data)


def _load_active_session() -> BuildSession | None:
    """Load the active session if one exists."""
    if not ACTIVE_SESSION_FILE.exists():
        return None

    try:
        with open(ACTIVE_SESSION_FILE) as f:
            session_id = f.read().strip()

        if session_id:
            return _load_session(session_id)
    except Exception:
        pass

    return None


def get_session() -> BuildSession:
    global _session

    # Try to load active session if no session in memory
    if _session is None:
        _session = _load_active_session()

    if _session is None:
        raise ValueError("No active session. Call create_session first.")

    return _session


# =============================================================================
# MCP TOOLS
# =============================================================================


@mcp.tool()
def create_session(name: Annotated[str, "Name for the agent being built"]) -> str:
    """Create a new agent building session. Call this first before building an agent."""
    global _session
    _session = BuildSession(name)
    _save_session(_session)  # Auto-save

    return json.dumps(
        {
            "session_id": _session.id,
            "name": name,
            "status": "created",
            "persisted": True,
        }
    )


@mcp.tool()
def list_sessions() -> str:
    """List all saved agent building sessions."""
    _ensure_sessions_dir()
    sessions = []
    if SESSIONS_DIR.exists():
        for session_file in SESSIONS_DIR.glob("*.json"):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                    sessions.append(
                        {
                            "session_id": data["session_id"],
                            "name": data["name"],
                            "last_modified": data["last_modified"],
                        }
                    )
            except Exception:
                pass

    return json.dumps(sorted(sessions, key=lambda x: x["last_modified"], reverse=True), indent=2)


@mcp.tool()
def resume_session(session_id: Annotated[str, "The ID of the session to resume"]) -> str:
    """Resume a previous building session by ID."""
    global _session
    try:
        _session = _load_session(session_id)
        # Update active session pointer
        with atomic_write(ACTIVE_SESSION_FILE) as f:
            f.write(_session.id)

        return json.dumps(
            {
                "session_id": _session.id,
                "name": _session.name,
                "status": "resumed",
                "goal_defined": _session.goal is not None,
                "node_count": len(_session.nodes),
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def set_goal(
    name: Annotated[str, "Goal name"],
    description: Annotated[str, "High-level goal description"],
    success_criteria: Annotated[
        str,
        "JSON array of success criteria objects: [{'id': '...', 'description': '...', 'target': '...'}]",
    ],
    constraints: Annotated[
        str, "JSON array of constraint objects: [{'id': '...', 'description': '...'}]"
    ] = "[]",
) -> str:
    """
    Step 1: Define the agent's goal.
    This creates the high-level objective, criteria for success, and operational constraints.
    """
    try:
        session = get_session()

        sc_list = [SuccessCriterion(**sc) for sc in json.loads(success_criteria)]
        c_list = [Constraint(**c) for c in json.loads(constraints)]

        session.goal = Goal(
            id=session.name.lower().replace(" ", "-"),
            name=name,
            description=description,
            success_criteria=sc_list,
            constraints=c_list,
        )

        _save_session(session)

        return json.dumps(
            {"status": "goal_set", "goal_id": session.goal.id, "session_id": session.id}
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def add_mcp_server(
    name: Annotated[str, "Unique name for the MCP server"],
    command: Annotated[str, "Command to run the server (e.g., 'npx', 'python')"],
    args: Annotated[str, "JSON array of command arguments"],
    env: Annotated[str, "JSON dictionary of environment variables"] = "{}",
) -> str:
    """
    Register an MCP server that the agent can use.
    Tools from this server will be available to include in nodes.
    """
    try:
        session = get_session()

        server_config = {
            "name": name,
            "command": command,
            "args": json.loads(args),
            "env": json.loads(env),
        }

        # Check for duplicates
        session.mcp_servers = [s for s in session.mcp_servers if s["name"] != name]
        session.mcp_servers.append(server_config)

        _save_session(session)

        return json.dumps(
            {"status": "mcp_server_added", "server": name, "total_servers": len(session.mcp_servers)}
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def add_node(
    id: Annotated[str, "Unique node ID"],
    description: Annotated[str, "What this node does"],
    prompt_template: Annotated[str, "Prompt template for the LLM"],
    output_schema: Annotated[str, "JSON schema for the node's output"],
    tools: Annotated[str, "JSON array of tool names to make available to this node"] = "[]",
) -> str:
    """
    Step 2: Add an execution node to the agent's workflow.
    Nodes are the individual steps the agent takes to reach its goal.
    """
    try:
        session = get_session()

        node = NodeSpec(
            id=id,
            description=description,
            prompt_template=prompt_template,
            output_schema=json.loads(output_schema),
            tools=json.loads(tools),
        )

        # Check for duplicates
        session.nodes = [n for n in session.nodes if n.id != id]
        session.nodes.append(node)

        _save_session(session)

        return json.dumps({"status": "node_added", "node_id": id, "total_nodes": len(session.nodes)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def add_edge(
    source: Annotated[str, "Source node ID"],
    target: Annotated[str, "Target node ID"],
    condition: Annotated[
        str,
        "Transition condition: 'always', 'on_success', 'on_failure', 'conditional', or 'llm_decide'",
    ] = "on_success",
    condition_value: Annotated[str, "Value for 'conditional' transitions"] = None,
) -> str:
    """
    Step 3: Connect two nodes with a transition edge.
    This defines the workflow logic and path the agent follows.
    """
    try:
        session = get_session()

        # Validate nodes exist
        node_ids = {n.id for n in session.nodes}
        if source not in node_ids:
            return json.dumps({"error": f"Source node '{source}' not found"})
        if target not in node_ids:
            return json.dumps({"error": f"Target node '{target}' not found"})

        # Map condition string to enum
        condition_map = {
            "always": EdgeCondition.ALWAYS,
            "on_success": EdgeCondition.ON_SUCCESS,
            "on_failure": EdgeCondition.ON_FAILURE,
            "conditional": EdgeCondition.CONDITIONAL,
            "llm_decide": EdgeCondition.LLM_DECIDE,
        }

        edge = EdgeSpec(
            source=source,
            target=target,
            condition=condition_map.get(condition, EdgeCondition.ON_SUCCESS),
            condition_value=condition_value,
        )

        session.edges.append(edge)
        _save_session(session)

        return json.dumps({"status": "edge_added", "from": source, "to": target})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def export_agent(
    target_path: Annotated[str, "Directory where the agent should be created"] = None,
) -> str:
    """
    Step 4: Finalize the agent and export it as a runnable Python package.
    The agent will be saved to the specified target_path (default is exports/[session_name]).
    """
    try:
        session = get_session()
        if not session.goal:
            return json.dumps({"error": "Goal must be set before export"})
        if not session.nodes:
            return json.dumps({"error": "At least one node is required"})

        # Setup paths
        if not target_path:
            clean_name = session.name.lower().replace(" ", "_")
            target_path = f"exports/{clean_name}"

        export_dir = Path(target_path)
        export_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write agent.py (The brain)
        agent_py = [
            '"""',
            f"Agent: {session.name}",
            "Generated by Agent Builder",
            '"""',
            "from framework.runner import AgentRunner",
            "from framework.graph import Goal, SuccessCriterion, Constraint, NodeSpec, EdgeSpec, EdgeCondition",
            "",
            "# Goal Definition",
            f"goal = {session.goal.model_dump_json(indent=2)}",
            "",
            "# Node Definitions",
            f"nodes = {json.dumps([n.model_dump() for n in session.nodes], indent=2)}",
            "",
            "# Edge Definitions",
            f"edges = {json.dumps([e.model_dump() for e in session.edges], indent=2, default=str)}",
            "",
            "# MCP Servers",
            f"mcp_servers = {json.dumps(session.mcp_servers, indent=2)}",
            "",
            "# Initialize default agent instance",
            "default_agent = AgentRunner(",
            "    name=goal['name'],",
            "    goal=Goal(**goal),",
            "    nodes=[NodeSpec(**n) for n in nodes],",
            "    edges=[EdgeSpec(**e) for e in edges],",
            "    mcp_servers=mcp_servers",
            ")",
        ]

        atomic_write(export_dir / "agent.py", "\n".join(agent_py))

        # 2. Write __init__.py
        init_py = [
            "from .agent import default_agent",
            "",
            '__all__ = ["default_agent"]',
        ]
        atomic_write(export_dir / "__init__.py", "\n".join(init_py))

        # 3. Write metadata (agent.json)
        agent_metadata = {
            "id": session.goal.id,
            "name": session.name,
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "nodes": [n.id for n in session.nodes],
            "edges": len(session.edges),
            "mcp_servers": [s["name"] for s in session.mcp_servers],
        }
        with open(export_dir / "agent.json", "w") as f:
            json.dump(agent_metadata, f, indent=2)

        # 4. Create tests directory
        tests_dir = export_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        atomic_write(tests_dir / "__init__.py", "")

        return json.dumps(
            {
                "status": "exported",
                "path": str(export_dir.absolute()),
                "files": ["agent.py", "__init__.py", "agent.json", "tests/"],
            },
            indent=2,
        )
    except Exception as e:
        import traceback

        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
def generate_constraint_tests(
    goal_id: Annotated[str, "The goal ID"],
    goal_json: Annotated[str, "The full Goal JSON object"],
    agent_path: Annotated[str, "Path to the agent export directory"],
) -> str:
    """
    Generate test guidelines and templates for validating agent constraints.
    Returns a file_header and test_template to be used with the Write tool.
    """
    try:
        goal_data = json.loads(goal_json)
        constraints = goal_data.get("constraints", [])
        agent_name = Path(agent_path).name

        formatted_constraints = []
        for c in constraints:
            formatted_constraints.append(f"- {c['id']}: {c['description']}")

        output_file = f"{agent_path}/tests/test_constraints.py"

        response = {
            "output_file": output_file,
            "file_header": PYTEST_TEST_FILE_HEADER.format(
                agent_name=agent_name,
                test_type="Constraint",
                description="validating agent constraints",
            ),
            "test_template": "async def test_constraint_{id}(mock_mode):\n    # Test {description}",
            "constraints_formatted": "\n".join(formatted_constraints),
            "test_guidelines": [
                "1. Each constraint should have at least one dedicated test function.",
                "2. Use the 'mock_mode' fixture to validate structure without spending tokens.",
                "3. Assert that the agent's behavior or output respects the constraint boundaries.",
                "4. Include an API key check at the top of the file using the provided header.",
            ],
            "instruction": f"Use the Write tool to create '{output_file}' using the 'file_header' and the constraints listed.",
        }

        return json.dumps(response, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def generate_success_tests(
    goal_id: Annotated[str, "The goal ID"],
    goal_json: Annotated[str, "The full Goal JSON object"],
    node_names: Annotated[str, "Comma-separated list of node names"],
    tool_names: Annotated[str, "Comma-separated list of tool names"],
    agent_path: Annotated[str, "Path to the agent export directory"],
) -> str:
    """
    Generate test guidelines and templates for validating agent success criteria.
    Returns a file_header and test_template to be used with the Write tool.
    """
    try:
        goal_data = json.loads(goal_json)
        criteria = goal_data.get("success_criteria", [])
        agent_name = Path(agent_path).name

        formatted_criteria = []
        for c in criteria:
            formatted_criteria.append(f"- {c['id']}: {c['description']} (Target: {c['target']})")

        output_file = f"{agent_path}/tests/test_success_criteria.py"

        response = {
            "output_file": output_file,
            "file_header": PYTEST_TEST_FILE_HEADER.format(
                agent_name=agent_name,
                test_type="Success Criteria",
                description="validating agent goals",
            ),
            "test_template": "async def test_success_{id}(mock_mode):\n    # Test {description}",
            "success_criteria_formatted": "\n".join(formatted_criteria),
            "test_guidelines": [
                "1. Create comprehensive tests for each success criterion.",
                "2. Real success validation requires LLM output (cannot be fully validated in mock mode).",
                "3. Tests should verify both the result data and the target metrics (e.g., counts, quality).",
                "4. Use default_agent.run() to execute the agent in the test environment.",
            ],
            "instruction": f"Use the Write tool to create '{output_file}' using the 'file_header' and the criteria listed.",
        }

        return json.dumps(response, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def run_tests(
    goal_id: Annotated[str, "The goal ID"],
    agent_path: Annotated[str, "Path to the agent export directory"],
    test_types: Annotated[str, "JSON array of test types: ['constraint', 'success']"] = "[]",
    parallel: Annotated[int, "Number of parallel workers"] = 1,
    fail_fast: Annotated[bool, "Stop on first failure"] = False,
    mock_mode: Annotated[bool, "Run in mock mode (bypass LLM/API)"] = False,
) -> str:
    """
    Execute agent tests using pytest.
    Fixed: Injects current process environment (for credentials) into test execution.
    """
    try:
        test_dir = Path(agent_path) / "tests"
        if not test_dir.exists():
            return json.dumps({"error": f"Test directory not found: {test_dir}"})

        # Build pytest command
        cmd = ["pytest", str(test_dir), "-v"]

        types = json.loads(test_types)
        if "constraint" in types:
            cmd.extend(["-k", "constraint"])
        elif "success" in types:
            cmd.extend(["-k", "success"])

        if fail_fast:
            cmd.append("-x")

        # Inject existing credentials into subprocess environment
        test_env = os.environ.copy()
        if mock_mode:
            test_env["MOCK_MODE"] = "1"

        # Run pytest
        result = subprocess.run(cmd, capture_output=True, text=True, env=test_env)

        return json.dumps(
            {
                "goal_id": goal_id,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "status": "passed" if result.returncode == 0 else "failed",
                "mock_mode": mock_mode
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def debug_test(
    goal_id: Annotated[str, "The goal ID"],
    test_name: Annotated[str, "The full name of the test to debug"],
    agent_path: Annotated[str, "Path to the agent export directory"],
) -> str:
    """
    Debug a single failed test with verbose output and injected credentials.
    """
    try:
        cmd = ["pytest", f"{agent_path}/tests/", "-k", test_name, "-vvs"]
        result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())

        return json.dumps(
            {
                "test_name": test_name,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "instruction": "Analyze the stack trace and logs above to identify the failure cause.",
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_tests(
    goal_id: Annotated[str, "The goal ID"],
    agent_path: Annotated[str, "Path to the agent export directory"],
) -> str:
    """
    List all available test files and functions for an agent.
    """
    try:
        test_dir = Path(agent_path) / "tests"
        if not test_dir.exists():
            return json.dumps({"files": [], "total": 0})

        test_files = []
        for p in test_dir.glob("test_*.py"):
            with open(p) as f:
                content = f.read()
                functions = [
                    line.split("def ")[1].split("(")[0]
                    for line in content.splitlines()
                    if line.startswith("async def test_") or line.startswith("def test_")
                ]
                test_files.append({"file": p.name, "tests": functions})

        return json.dumps({"files": test_files, "total_files": len(test_files)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# CREDENTIAL MANAGEMENT TOOLS (Fixed for Anthropic Provider)
# =============================================================================


@mcp.tool()
def store_credential(
    credential_name: Annotated[str, "Name (e.g., 'anthropic', 'hubspot')"],
    api_key: Annotated[str, "The API key or token value"],
    description: Annotated[str, "Brief description"] = None,
) -> str:
    """
    Securely store a credential. Explicitly ensures ANTHROPIC_API_KEY is synced to the session environment.
    """
    try:
        from framework.credentials import CredentialManager

        manager = CredentialManager()
        manager.store(credential_name, api_key, description)
        
        # Explicit Fix: Sync to the running process so subsequent tools (like run_tests) see it
        if credential_name.lower() == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key

        return json.dumps(
            {
                "success": True,
                "credential": credential_name,
                "message": f"Credential '{credential_name}' stored and session environment updated.",
            }
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def delete_credential(
    credential_name: Annotated[str, "Name of the credential to remove"],
) -> str:
    """
    Remove a stored credential and clear it from the session environment.
    """
    try:
        from framework.credentials import CredentialManager

        manager = CredentialManager()
        deleted = manager.delete(credential_name)
        
        if deleted and credential_name.lower() == "anthropic":
            os.environ.pop("ANTHROPIC_API_KEY", None)

        return json.dumps(
            {
                "success": deleted,
                "credential": credential_name,
                "message": f"Credential '{credential_name}' deleted"
                if deleted
                else f"Credential '{credential_name}' not found",
            }
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def verify_credentials(
    agent_path: Annotated[str, "Path to the exported agent directory"],
) -> str:
    """
    Verify configuration. Ensures Anthropic provider is specifically validated.
    """
    try:
        from framework.runner import AgentRunner
        from framework.credentials import CredentialManager

        # Check raw environment first (fast check)
        anthropic_ready = "ANTHROPIC_API_KEY" in os.environ
        
        runner = AgentRunner.load(agent_path)
        validation = runner.validate()

        return json.dumps(
            {
                "agent": agent_path,
                "anthropic_provider_ready": anthropic_ready,
                "framework_ready": not validation.missing_credentials,
                "missing_credentials": validation.missing_credentials,
                "warnings": validation.warnings,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")
