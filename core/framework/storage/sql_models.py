"""
SQLAlchemy models for SQL storage backend.

Defines the database schema for storing runs and related data.
Uses SQLAlchemy 2.0+ async patterns.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON, TypeDecorator


class JSONType(TypeDecorator):
    """
    Platform-agnostic JSON type.
    
    Uses JSONB on PostgreSQL for better performance,
    falls back to standard JSON on other databases.
    """
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class RunModel(Base):
    """
    SQLAlchemy model for Run objects.
    
    Stores the complete run data with JSON columns for
    complex nested structures (decisions, problems, metrics).
    """
    __tablename__ = "runs"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    
    # Core fields (indexed for queries)
    goal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Text fields
    narrative: Mapped[str] = mapped_column(Text, default="")
    goal_description: Mapped[str] = mapped_column(Text, default="")
    
    # JSON fields (complex nested data)
    input_data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    output_data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    decisions: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list)
    problems: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_runs_goal_status", "goal_id", "status"),
        Index("ix_runs_started_at", "started_at"),
    )
    
    def __repr__(self) -> str:
        return f"<RunModel(id={self.id}, goal_id={self.goal_id}, status={self.status})>"


class RunNodeIndex(Base):
    """
    Index table for node-to-run relationships.
    
    Enables efficient querying of "which runs executed node X?"
    without scanning all runs' JSON data.
    """
    __tablename__ = "run_node_index"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64), 
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Composite index for the most common query pattern
    __table_args__ = (
        Index("ix_run_node_index_node_run", "node_id", "run_id"),
    )
    
    def __repr__(self) -> str:
        return f"<RunNodeIndex(run_id={self.run_id}, node_id={self.node_id})>"


class RunSummaryModel(Base):
    """
    Cached run summaries for fast loading.
    
    Stores pre-computed RunSummary data to avoid
    full run deserialization for list/scan operations.
    """
    __tablename__ = "run_summaries"
    
    # Primary key (matches run_id)
    run_id: Mapped[str] = mapped_column(
        String(64), 
        ForeignKey("runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    
    # Core summary fields
    goal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    
    # Stats
    decision_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(default=0.0)
    problem_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Text
    narrative: Mapped[str] = mapped_column(Text, default="")
    
    # JSON fields for lists
    key_decisions: Mapped[list[str]] = mapped_column(JSONType, default=list)
    critical_problems: Mapped[list[str]] = mapped_column(JSONType, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONType, default=list)
    successes: Mapped[list[str]] = mapped_column(JSONType, default=list)
    
    def __repr__(self) -> str:
        return f"<RunSummaryModel(run_id={self.run_id}, status={self.status})>"
