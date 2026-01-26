"""
Tests for Audit Trail.
"""

import pytest
from datetime import datetime
from pathlib import Path

from framework.runtime.core import Runtime
from framework.runtime.audit_trail import AuditTrail, AuditEntry, AuditEntryType


class TestAuditTrail:
    """Tests for AuditTrail class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.storage_path = Path("./test_audit_logs")
        self.runtime = Runtime(storage_path=self.storage_path)
    
    def test_empty_trail(self):
        """Test audit trail with no run."""
        trail = AuditTrail(self.runtime)
        entries = trail.get_timeline()
        
        assert entries == []
    
    def test_trail_with_run(self):
        """Test audit trail with a run."""
        # Start a run
        run_id = self.runtime.start_run(
            goal_id="test-goal",
            goal_description="Test the audit trail",
            input_data={"input": "test"}
        )
        
        # Make some decisions
        decision_id = self.runtime.decide(
            intent="Process the input",
            options=[
                {"id": "opt1", "description": "Option 1", "action_type": "test"},
                {"id": "opt2", "description": "Option 2", "action_type": "test"},
            ],
            chosen="opt1",
            reasoning="Option 1 is better for testing",
            node_id="test-node",
        )
        
        self.runtime.record_outcome(
            decision_id=decision_id,
            success=True,
            result="Test completed",
        )
        
        # End the run
        self.runtime.end_run(
            success=True,
            narrative="Test run completed successfully",
        )
        
        # Get audit trail
        trail = AuditTrail(self.runtime)
        entries = trail.get_timeline()
        
        # Should have run_start, decision, run_end
        assert len(entries) >= 3
        
        # Check entry types
        types = [e.entry_type for e in entries]
        assert AuditEntryType.RUN_START in types
        assert AuditEntryType.DECISION in types
        assert AuditEntryType.RUN_END in types
    
    def test_filter_by_node(self):
        """Test filtering by node ID."""
        self.runtime.start_run("test", "Test")
        
        # Decision for node1
        d1 = self.runtime.decide(
            intent="Test 1",
            options=[{"id": "a", "description": "A", "action_type": "test"}],
            chosen="a",
            reasoning="Test",
            node_id="node1",
        )
        self.runtime.record_outcome(d1, True)
        
        # Decision for node2
        d2 = self.runtime.decide(
            intent="Test 2",
            options=[{"id": "b", "description": "B", "action_type": "test"}],
            chosen="b",
            reasoning="Test",
            node_id="node2",
        )
        self.runtime.record_outcome(d2, True)
        
        trail = AuditTrail(self.runtime)
        
        node1_entries = trail.filter_by_node("node1")
        assert len(node1_entries) == 1
        assert node1_entries[0].node_id == "node1"
        
        node2_entries = trail.filter_by_node("node2")
        assert len(node2_entries) == 1
        assert node2_entries[0].node_id == "node2"
    
    def test_filter_by_outcome(self):
        """Test filtering by success/failure."""
        self.runtime.start_run("test", "Test")
        
        # Successful decision
        d1 = self.runtime.decide(
            intent="Success",
            options=[{"id": "a", "description": "A", "action_type": "test"}],
            chosen="a",
            reasoning="Test",
            node_id="node1",
        )
        self.runtime.record_outcome(d1, success=True)
        
        # Failed decision
        d2 = self.runtime.decide(
            intent="Failure",
            options=[{"id": "b", "description": "B", "action_type": "test"}],
            chosen="b",
            reasoning="Test",
            node_id="node2",
        )
        self.runtime.record_outcome(d2, success=False, error="Test error")
        
        trail = AuditTrail(self.runtime)
        
        successes = trail.filter_by_outcome(success=True)
        assert len(successes) == 1
        assert successes[0].success is True
        
        failures = trail.filter_by_outcome(success=False)
        assert len(failures) == 1
        assert failures[0].success is False
    
    def test_export_json(self):
        """Test JSON export."""
        self.runtime.start_run("test", "Test")
        d1 = self.runtime.decide(
            intent="Test",
            options=[{"id": "a", "description": "A", "action_type": "test"}],
            chosen="a",
            reasoning="Test",
        )
        self.runtime.record_outcome(d1, True)
        
        trail = AuditTrail(self.runtime)
        json_output = trail.export_json()
        
        assert isinstance(json_output, str)
        assert "entries" in json_output
        assert "summary" in json_output
        
        import json
        data = json.loads(json_output)
        assert "entries" in data
        assert "summary" in data
    
    def test_export_markdown(self):
        """Test Markdown export."""
        self.runtime.start_run("test", "Test")
        d1 = self.runtime.decide(
            intent="Test decision",
            options=[{"id": "a", "description": "Action A", "action_type": "test"}],
            chosen="a",
            reasoning="Good choice",
        )
        self.runtime.record_outcome(d1, True)
        self.runtime.end_run(True, "Done")
        
        trail = AuditTrail(self.runtime)
        md_output = trail.export_markdown()
        
        assert isinstance(md_output, str)
        assert "# Audit Trail" in md_output
        assert "## Summary" in md_output
        assert "## Timeline" in md_output
        assert "Test decision" in md_output
    
    def test_summary_stats(self):
        """Test summary statistics."""
        self.runtime.start_run("test", "Test")
        
        # 2 successes
        for i in range(2):
            d = self.runtime.decide(
                intent=f"Success {i}",
                options=[{"id": "a", "description": "A", "action_type": "test"}],
                chosen="a",
                reasoning="Test",
                node_id="nodeA",
            )
            self.runtime.record_outcome(d, True, tokens_used=100, latency_ms=50)
        
        # 1 failure
        d = self.runtime.decide(
            intent="Failure",
            options=[{"id": "b", "description": "B", "action_type": "test"}],
            chosen="b",
            reasoning="Test",
            node_id="nodeB",
        )
        self.runtime.record_outcome(d, False, error="Error")
        
        trail = AuditTrail(self.runtime)
        stats = trail.get_summary_stats()
        
        assert stats["total_decisions"] == 3
        assert stats["successful_decisions"] == 2
        assert stats["failed_decisions"] == 1
        assert stats["success_rate"] == 2/3
        assert stats["total_tokens"] == 200
        assert "nodeA" in stats["nodes_involved"]
        assert "nodeB" in stats["nodes_involved"]
