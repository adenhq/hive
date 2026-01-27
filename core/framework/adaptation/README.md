# ADAPT Pillar - Agent Self-Improvement System

Complete implementation of Aden's ADAPT pillar: "Continuous evaluation, supervision, and adaptation ensure agents improve over time"

## Overview

The ADAPT pillar enables agents to:
- 📊 **Evaluate** their own performance systematically
- 🔍 **Analyze** failure patterns automatically  
- 🤖 **Decide** when improvement is needed
- 🔧 **Repair** themselves without human intervention
- 📈 **Improve** continuously over time

## Architecture

```
┌─────────────────────────────────────────┐
│ 1. Agent Evaluator                      │
│    Measures: Accuracy, Success Rate,    │
│    Latency, Cost, Quality Score         │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│ 2. Failure Analyzer                     │
│    Categorizes: Logic errors, API fails,│
│    Timeouts, Validation errors, etc.    │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│ 3. Improvement Trigger                  │
│    Decides: When to improve, Priority,  │
│    What actions to take                 │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│ 4. Self-Repair Engine                   │
│    Generates: Code fixes, Applies them, │
│    Re-tests, Verifies improvement       │
└─────────────────────────────────────────┘
```

## Components

### 1. Agent Evaluator (`evaluator.py`)

Tracks agent performance over time.

**Key Features:**
- Multi-metric evaluation (accuracy, success rate, latency, cost)
- Performance trend analysis (improving/stable/degrading)
- Version comparison (A vs B testing)
- Overall quality scoring (0-100)
- Historical tracking

**Usage:**
```python
from framework.adaptation import AgentEvaluator

evaluator = AgentEvaluator(agent_id="support-agent")

# Evaluate against test suite
metrics = evaluator.evaluate(
    test_cases=[
        {"input": {"ticket": "..."}, "expected": {"category": "billing"}},
        # ... more test cases
    ],
    agent_runner=agent.run,
    version="v2.0"
)

# View report
print(evaluator.generate_report())

# Check trend
trend = evaluator.get_trend()  # IMPROVING, STABLE, or DEGRADING

# Compare versions
comparison = evaluator.compare_versions("v1.0", "v2.0")
print(f"Accuracy change: {comparison['accuracy_change']}%")
```

### 2. Failure Analyzer (`failure_analyzer.py`)

Categorizes failures and identifies patterns.

**Failure Categories:**
- `INPUT_VALIDATION` - Bad input data
- `LOGIC_ERROR` - Bugs in code
- `EXTERNAL_API` - Third-party API failures
- `TIMEOUT` - Performance issues
- `RESOURCE_EXHAUSTION` - Memory/compute limits
- `CONSTRAINT_VIOLATION` - Business rule violations

**Usage:**
```python
from framework.adaptation import FailureAnalyzer

analyzer = FailureAnalyzer(agent_id="support-agent")

# Record failure
analyzer.record_failure(
    node_id="validator",
    error=ValueError("Missing email field"),
    input_data={"name": "John"}
)

# Get top patterns
patterns = analyzer.get_top_patterns(limit=5)

# Get suggestions
suggestions = analyzer.generate_improvement_suggestions()

# View report
analyzer.print_failure_report()
```

### 3. Improvement Trigger (`improvement_trigger.py`)

Decides when agents need improvement.

**Trigger Conditions:**
- Accuracy below threshold (default 80%)
- Success rate too low (default 85%)
- Performance degrading over time
- Cost explosion (2x increase)
- Repeated failure patterns (5+ times)

**Priority Levels:**
- **CRITICAL** - Multiple triggers or accuracy < 60%
- **HIGH** - Accuracy/success rate issues
- **MEDIUM** - Cost/performance issues
- **LOW** - Isolated patterns

**Usage:**
```python
from framework.adaptation import ImprovementTrigger, PerformanceTrend

trigger = ImprovementTrigger(
    accuracy_threshold=0.80,
    success_threshold=0.85
)

decision = trigger.decide(
    current_metrics=current_metrics,
    previous_metrics=previous_metrics,
    trend=PerformanceTrend.DEGRADING,
    failure_analyzer=failure_analyzer
)

if decision.should_improve:
    print(f"Priority: {decision.priority}")
    print(f"Reasons: {decision.reasons}")
    print(f"Actions: {decision.suggested_actions}")
```

### 4. Self-Repair Engine (`self_repair.py`)

Automated diagnostic and repair system.

**Features:**
- Complete diagnostic cycle
- Automated code fix generation
- Continuous monitoring mode
- Repair history tracking

**Usage:**
```python
from framework.adaptation import SelfRepairEngine

engine = SelfRepairEngine(
    agent_id="support-agent",
    agent_path="exports/support_agent"
)

# Run full diagnostic and repair
report = engine.diagnose_and_repair(
    test_cases=test_suite,
    agent_runner=agent.run,
    current_version="v2.0"
)

# Continuous monitoring
monitoring_report = engine.continuous_monitoring_cycle(
    test_cases=test_suite,
    agent_runner=agent.run,
    max_repair_attempts=3
)
```

## Integration with GraphExecutor

Automatic evaluation during execution:

```python
from framework.graph.executor import GraphExecutor
from framework.adaptation.integration import AdaptiveExecutionWrapper

# Create executor
executor = GraphExecutor(runtime=runtime)

# Wrap with ADAPT capabilities
adaptive_executor = AdaptiveExecutionWrapper(
    executor=executor,
    agent_id="my-agent"
)

# Execute normally - metrics tracked automatically
result = await adaptive_executor.execute(graph, goal, input_data)

# Check health
health = adaptive_executor.get_health_status()
print(f"Agent health: {health['status']}")
print(f"Accuracy: {health['accuracy']:.1%}")
print(f"Needs improvement: {health['needs_improvement']}")
```

## MCP Tools

Access ADAPT features via MCP:

```bash
# Run MCP server
python -m framework.adaptation.mcp_adapt_server
```

**Available Tools:**
- `create_evaluator` - Initialize evaluator for an agent
- `get_agent_metrics` - Get performance metrics
- `compare_agent_versions` - A/B testing
- `analyze_failures` - Get failure analysis
- `get_improvement_decision` - Automated decision
- `trigger_self_repair` - Initiate repair cycle
- `export_metrics_to_json` - Export data for analysis
- `get_performance_trend` - Trend analysis

## Examples

### Basic Evaluation:
```bash
PYTHONPATH=core python core/examples/self_improvement_demo.py
```

### Complete Self-Repair:
```bash
PYTHONPATH=core python core/examples/complete_adapt_demo.py
```

## Testing

```bash
cd core
python -m pytest framework/adaptation/tests/ -v
```

## Files

```
core/framework/adaptation/
├── __init__.py                  # Package exports
├── evaluator.py                 # Performance evaluation (270 lines)
├── failure_analyzer.py          # Failure categorization (240 lines)
├── improvement_trigger.py       # Improvement decisions (180 lines)
├── self_repair.py              # Automated repair (280 lines)
├── integration.py              # GraphExecutor integration (150 lines)
├── mcp_adapt_server.py         # MCP tools (200 lines)
└── tests/
    ├── __init__.py
    └── test_evaluator.py       # Unit tests (80 lines)
```

## Production Benefits

✅ **Reduced Maintenance** - Agents fix themselves
✅ **Higher Quality** - Continuous optimization
✅ **Lower Costs** - Identify expensive operations
✅ **Enterprise-Ready** - Systematic quality assurance
✅ **Competitive Edge** - Only framework with complete self-improvement

## Business Impact

**Enables:**
- Enterprise sales (proof of continuous improvement)
- Compliance (audit trail of quality)
- Cost predictability (track and optimize)
- Reliability guarantees (automated quality control)

**Differentiates from:**
- LangChain (no self-improvement)
- CrewAI (no evaluation system)
- AutoGen (no failure analysis)
- All competitors (no complete ADAPT pillar)

---

**This completes Aden's vision of truly autonomous, self-improving AI agents.**
