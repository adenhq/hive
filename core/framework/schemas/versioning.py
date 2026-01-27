from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any

from framework.graph.edge import GraphSpec
from framework.graph.goal import Goal

class AgentVersion(BaseModel):
    """A full snapshot of an agent at a specific point in time."""
    version: str = Field(description="Semantic version string (e.g., 1.0.0)")
    agent_id: str = Field(description="Unique ID of the agent")
    message: str = Field(description="Description of what changed in this version")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Core components
    graph: GraphSpec = Field(description="Complete graph definition (nodes and edges)")
    goal: Goal = Field(description="Complete goal definition (success criteria and constraints)")
    
    # Optional components
    tools_code: str | None = Field(default=None, description="Content of tools.py if it exists")
    mcp_config: dict[str, Any] | None = Field(default=None, description="MCP server configurations")
    
    # Metadata for tracking evolution
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata (parent, reason, etc.)")

class VersionSummary(BaseModel):
    """Lightweight summary of a version for listing."""
    version: str
    timestamp: datetime
    message: str
    tags: list[str] = Field(default_factory=list)

class VersionRegistry(BaseModel):
    """Registry tracking all versions and tags for an agent."""
    agent_id: str
    versions: list[VersionSummary] = Field(default_factory=list)
    active_version: str | None = None
    tags: dict[str, str] = Field(default_factory=dict, description="Tag name to version mapping")
