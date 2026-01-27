import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from framework.graph.goal import Goal
from framework.graph.edge import GraphSpec
from framework.schemas.versioning import AgentVersion, VersionRegistry, VersionSummary

class AgentVersionManager:
    """Manages version snapshots and registry for an agent."""

    def __init__(self, agent_path: str | Path):
        self.agent_path = Path(agent_path)
        self.version_dir = self.agent_path / ".aden" / "versions"
        self.registry_path = self.version_dir / "registry.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure versioning directory exists."""
        self.version_dir.mkdir(parents=True, exist_ok=True)

    def _load_registry(self) -> VersionRegistry:
        """Load the version registry."""
        if not self.registry_path.exists():
            return VersionRegistry(agent_id=self.agent_path.name)
        
        with open(self.registry_path) as f:
            return VersionRegistry.model_validate_json(f.read())

    def _save_registry(self, registry: VersionRegistry) -> None:
        """Save the version registry."""
        with open(self.registry_path, "w") as f:
            f.write(registry.model_dump_json(indent=2))

    def save_version(self, version: str, message: str, meta: dict[str, Any] | None = None) -> AgentVersion:
        """
        Take a snapshot of the current agent state and save it as a new version.
        """
        # 1. Load current agent state
        agent_json_path = self.agent_path / "agent.json"
        if not agent_json_path.exists():
            raise FileNotFoundError(f"agent.json not found in {self.agent_path}")

        with open(agent_json_path) as f:
            data = json.load(f)
        
        # We need to import load_agent_export from runner to reconstruct models
        from framework.runner.runner import load_agent_export
        graph, goal = load_agent_export(data)

        # 2. Check for optional components
        tools_path = self.agent_path / "tools.py"
        tools_code = tools_path.read_text() if tools_path.exists() else None

        mcp_path = self.agent_path / "mcp_servers.json"
        mcp_config = json.loads(mcp_path.read_text()) if mcp_path.exists() else None

        # 3. Create snapshot
        snapshot = AgentVersion(
            version=version,
            agent_id=self.agent_path.name,
            message=message,
            timestamp=datetime.now(),
            graph=graph,
            goal=goal,
            tools_code=tools_code,
            mcp_config=mcp_config,
            metadata=meta or {}
        )

        # 4. Save snapshot file
        snapshot_path = self.version_dir / f"{version}.json"
        with open(snapshot_path, "w") as f:
            f.write(snapshot.model_dump_json(indent=2))

        # 5. Update registry
        registry = self._load_registry()
        
        # Check if version already exists
        registry.versions = [v for v in registry.versions if v.version != version]
        
        registry.versions.append(VersionSummary(
            version=version,
            timestamp=snapshot.timestamp,
            message=message
        ))
        
        registry.active_version = version
        self._save_registry(registry)
        
        return snapshot

    def list_versions(self) -> list[VersionSummary]:
        """List all saved versions."""
        registry = self._load_registry()
        return sorted(registry.versions, key=lambda v: v.timestamp, reverse=True)

    def get_version(self, version_or_tag: str) -> AgentVersion | None:
        """Load a specific version snapshot."""
        registry = self._load_registry()
        
        # Resolve tag if needed
        version = registry.tags.get(version_or_tag, version_or_tag)
        
        snapshot_path = self.version_dir / f"{version}.json"
        if not snapshot_path.exists():
            return None
        
        with open(snapshot_path) as f:
            return AgentVersion.model_validate_json(f.read())

    def tag_version(self, version: str, tag: str) -> None:
        """Assign a tag to a version."""
        registry = self._load_registry()
        
        # Verify version exists
        if not any(v.version == version for v in registry.versions):
            raise ValueError(f"Version {version} not found in registry")
        
        registry.tags[tag] = version
        
        # Update summaries list tags
        for summary in registry.versions:
            if summary.version == version:
                if tag not in summary.tags:
                    summary.tags.append(tag)
            elif tag in summary.tags:
                summary.tags.remove(tag)
                
        self._save_registry(registry)

    def delete_version(self, version: str) -> None:
        """Delete a version snapshot."""
        registry = self._load_registry()
        
        # 1. Update summaries
        registry.versions = [v for v in registry.versions if v.version != version]
        
        # 2. Update tags
        registry.tags = {t: v for t, v in registry.tags.items() if v != version}
        
        # 3. Update active version
        if registry.active_version == version:
            registry.active_version = None
            
        self._save_registry(registry)
        
        # 4. Delete file
        snapshot_path = self.version_dir / f"{version}.json"
        if snapshot_path.exists():
            snapshot_path.unlink()

    def diff(self, v1_str: str, v2_str: str) -> dict[str, Any]:
        """
        Compare two versions and return the differences.
        """
        v1 = self.get_version(v1_str)
        v2 = self.get_version(v2_str)
        
        if not v1 or not v2:
            raise ValueError(f"One or both versions not found: {v1_str}, {v2_str}")
            
        diff_result = {
            "v1": v1.version,
            "v2": v2.version,
            "changes": []
        }
        
        # Simplified structural diff
        # Compare Graph ID
        if v1.graph.id != v2.graph.id:
            diff_result["changes"].append(f"Graph ID: {v1.graph.id} -> {v2.graph.id}")
            
        # Compare Graph Version
        if v1.graph.version != v2.graph.version:
            diff_result["changes"].append(f"Graph Version: {v1.graph.version} -> {v2.graph.version}")

        # Compare Node counts
        if len(v1.graph.nodes) != len(v2.graph.nodes):
            diff_result["changes"].append(f"Nodes: {len(v1.graph.nodes)} -> {len(v2.graph.nodes)}")
            
        # Compare Edge counts
        if len(v1.graph.edges) != len(v2.graph.edges):
            diff_result["changes"].append(f"Edges: {len(v1.graph.edges)} -> {len(v2.graph.edges)}")

        # Compare Tools code length
        len1 = len(v1.tools_code) if v1.tools_code else 0
        len2 = len(v2.tools_code) if v2.tools_code else 0
        if len1 != len2:
            diff_result["changes"].append(f"tools.py size: {len1} -> {len2} chars")
            
        return diff_result

    def rollback(self, version_or_tag: str) -> AgentVersion:
        """
        Restore the agent to a previous version.
        WARNING: This overwrites current files.
        """
        snapshot = self.get_version(version_or_tag)
        if not snapshot:
            raise ValueError(f"Version or tag '{version_or_tag}' not found")

        # 1. Restore agent.json
        # We need to wrap it back into the format load_agent_export expects
        # which is usually {"graph": ..., "goal": ...}
        agent_data = {
            "graph": snapshot.graph.model_dump(mode="json"),
            "goal": snapshot.goal.model_dump(mode="json")
        }
        
        agent_json_path = self.agent_path / "agent.json"
        with open(agent_json_path, "w") as f:
            json.dump(agent_data, f, indent=2)

        # 2. Restore tools.py
        tools_path = self.agent_path / "tools.py"
        if snapshot.tools_code:
            tools_path.write_text(snapshot.tools_code)
        elif tools_path.exists():
            tools_path.unlink()

        # 3. Restore mcp_servers.json
        mcp_path = self.agent_path / "mcp_servers.json"
        if snapshot.mcp_config:
            with open(mcp_path, "w") as f:
                json.dump(snapshot.mcp_config, f, indent=2)
        elif mcp_path.exists():
            mcp_path.unlink()

        # 4. Update active version in registry
        registry = self._load_registry()
        registry.active_version = snapshot.version
        self._save_registry(registry)

        return snapshot
