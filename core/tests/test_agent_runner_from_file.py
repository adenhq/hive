import codecs
import inspect
import json
from pathlib import Path

from framework.runner import AgentRunner


def _minimal_export() -> dict:
    return {
        "agent": {
            "id": "test-agent",
            "name": "Test Agent",
            "version": "1.0.0",
            "description": "Minimal export for from_file() tests",
        },
        "graph": {
            "id": "test-graph",
            "goal_id": "test-goal",
            "version": "1.0.0",
            "entry_node": "hello",
            "entry_points": {"start": "hello"},
            "terminal_nodes": ["hello"],
            "pause_nodes": [],
            "nodes": [
                {
                    "id": "hello",
                    "name": "Hello",
                    "description": "Return a result",
                    "node_type": "llm_generate",
                    "input_keys": [],
                    "output_keys": ["result"],
                }
            ],
            "edges": [],
            "max_steps": 5,
            "max_retries_per_node": 1,
            "description": "",
        },
        "goal": {
            "id": "test-goal",
            "name": "Test Goal",
            "description": "Test goal description",
            "success_criteria": [],
            "constraints": [],
        },
        "required_tools": [],
        "metadata": {"created_at": "2026-02-10T00:00:00", "node_count": 1, "edge_count": 0},
    }


def test_from_file_loads_export_from_directory(tmp_path: Path) -> None:
    export = _minimal_export()
    agent_dir = tmp_path / "my_agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.json").write_text(json.dumps(export), encoding="utf-8")

    runner = AgentRunner.from_file(
        agent_dir,
        mock_mode=True,
        storage_path=(tmp_path / "storage"),
    )

    assert runner.agent_path == agent_dir
    assert runner.goal.id == "test-goal"
    assert runner.graph.entry_node == "hello"
    assert inspect.iscoroutinefunction(runner.run)


def test_from_file_handles_utf8_bom(tmp_path: Path) -> None:
    export = _minimal_export()
    agent_dir = tmp_path / "my_agent"
    agent_dir.mkdir(parents=True)
    agent_json_path = agent_dir / "agent.json"

    raw = json.dumps(export).encode("utf-8")
    agent_json_path.write_bytes(codecs.BOM_UTF8 + raw)

    runner = AgentRunner.from_file(
        agent_json_path,
        mock_mode=True,
        storage_path=(tmp_path / "storage"),
    )

    assert runner.agent_path == agent_dir
    assert runner.goal.id == "test-goal"
