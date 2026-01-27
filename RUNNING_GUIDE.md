# Complete Step-by-Step Guide: Running Aden Hive Framework

This guide walks you through the complete flow from initial setup to running agents.

---

## **PHASE 1: Initial Setup (One-Time)**

### **Step 1: Prerequisites Check**

```bash
# Check Python version (must be 3.11+)
python --version
# or
python3 --version

# If Python < 3.11, upgrade first
```

**Requirements:**
- Python 3.11 or higher
- pip (usually comes with Python)
- Git (to clone the repository)

---

### **Step 2: Navigate to Project Root**

```bash
# If you haven't cloned yet:
git clone https://github.com/adenhq/hive.git
cd hive

# If already cloned:
cd d:\hive  # or your project path
```

---

### **Step 3: Run Complete Setup Script**

**Option A: Automated Setup (Recommended)**

```bash
# Run the complete setup script
./quickstart.sh

# This script will:
# ✓ Check Python version
# ✓ Install framework package
# ✓ Install aden_tools package
# ✓ Install MCP dependencies
# ✓ Fix package compatibility
# ✓ Install Claude Code skills
# ✓ Verify everything works
```

**Option B: Python Setup Only**

```bash
# If you only need Python packages (no Claude skills):
./scripts/setup-python.sh
```

**What gets installed:**
- `framework` - Core agent runtime
- `aden_tools` - 19 MCP tools for agent capabilities
- `mcp`, `fastmcp` - MCP server dependencies
- `litellm` - LLM provider abstraction
- All required dependencies

---

### **Step 4: Set API Key (For Real LLM Usage)**

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Or for Windows PowerShell:
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Or add to your .env file (if using one)
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env
```

**Note:** For mock mode (testing without LLM), you can skip this step.

---

### **Step 5: Verify Installation**

```bash
# Test framework import
python -c "import framework; print('✓ framework OK')"

# Test aden_tools import
python -c "import aden_tools; print('✓ aden_tools OK')"

# Test litellm import
python -c "import litellm; print('✓ litellm OK')"
```

All should print "✓ ... OK" without errors.

---

## **PHASE 2: Building Your First Agent**

### **Step 6: Open Claude Code**

```bash
# Navigate to project root
cd d:\hive

# Open Claude Code (or your IDE)
# Make sure you're in the project directory
```

---

### **Step 7: Build Agent Using Claude Skills**

In Claude Code, use the building skills:

```
# Option 1: Complete workflow (recommended for first time)
/building-agents

# Option 2: Step-by-step construction
/building-agents-construction

# Option 3: Just understand concepts first
/building-agents-core
```

**The building process:**
1. **Define Goal** - Describe what your agent should achieve
2. **Add Nodes** - Create LLM, Router, or Function nodes
3. **Connect Edges** - Link nodes with routing logic
4. **Test** - Validate the agent works
5. **Approve** - Human approval at each step
6. **Export** - Generate `agent.json` and `tools.py`

**Example Goal:**
```
Goal: Process customer support tickets
- Success Criteria: Correctly categorize priority
- Constraints: Respond within 5 minutes
```

---

### **Step 8: Agent Export Structure**

After building, your agent will be in `exports/your_agent_name/`:

```
exports/
└── your_agent_name/
    ├── agent.json          # Graph structure (nodes, edges, goal)
    ├── tools.py            # Tool implementations
    ├── mcp_servers.json     # MCP server configs (optional)
    └── README.md           # Agent documentation
```

---

## **PHASE 3: Running Your Agent**

### **Step 9: Validate Agent Structure**

```bash
# From project root (d:\hive)
PYTHONPATH=core:exports python -m your_agent_name validate

# Example with a real agent:
PYTHONPATH=core:exports python -m support_ticket_agent validate
```

**What this checks:**
- ✓ Graph structure is valid
- ✓ All nodes are reachable
- ✓ Required tools are registered
- ✓ Credentials are available

**Expected output:**
```
✓ Graph validation passed
✓ All tools available
⚠ Missing ANTHROPIC_API_KEY (set for LLM nodes)
```

---

### **Step 10: View Agent Information**

```bash
# Get agent metadata
PYTHONPATH=core:exports python -m your_agent_name info

# Shows:
# - Agent name and description
# - Goal details
# - Node count and types
# - Edge count
# - Required tools
# - Entry points
```

---

### **Step 11: Run Agent (Single Execution)**

**Basic Run:**

```bash
# Run with input data
PYTHONPATH=core:exports python -m your_agent_name run --input '{"key": "value"}'

# Example: Support ticket agent
PYTHONPATH=core:exports python -m support_ticket_agent run --input '{
  "ticket_content": "My login is broken. Error 401.",
  "customer_id": "CUST-123",
  "ticket_id": "TKT-456"
}'
```

**Mock Mode (No LLM Calls):**

```bash
# Run in mock mode for testing
PYTHONPATH=core:exports python -m your_agent_name run --mock --input '{"key": "value"}'
```

**With Custom Model:**

```bash
# Use a specific LLM model
PYTHONPATH=core:exports python -m your_agent_name run \
  --model "claude-sonnet-4-20250514" \
  --input '{"key": "value"}'
```

**Available Models:**
- `claude-sonnet-4-20250514` (Anthropic)
- `gpt-4o-mini` (OpenAI)
- `gemini/gemini-pro` (Google)
- `cerebras/zai-glm-4.7` (Cerebras)
- Any LiteLLM-compatible model

---

### **Step 12: Run Agent (Multi-Entry-Point)**

For agents with multiple entry points (webhook + API):

```bash
# Start the agent runtime
PYTHONPATH=core:exports python -m your_agent_name start

# In another terminal, trigger execution
PYTHONPATH=core:exports python -m your_agent_name trigger \
  --entry-point webhook \
  --input '{"ticket_id": "123"}'

# Check goal progress
PYTHONPATH=core:exports python -m your_agent_name progress

# Stop the runtime
PYTHONPATH=core:exports python -m your_agent_name stop
```

---

## **PHASE 4: Testing Your Agent**

### **Step 13: Generate Tests**

Use Claude Code testing skill:

```
/testing-agent
```

This will:
1. Generate test cases from goal success criteria
2. Require your approval before storing
3. Create test files in `exports/your_agent_name/tests/`

---

### **Step 14: Run Tests**

```bash
# Run all tests
PYTHONPATH=core:exports python -m framework.testing.cli test-run \
  exports/your_agent_name \
  --goal your_goal_id \
  --parallel 4

# Debug a specific test
PYTHONPATH=core:exports python -m framework.testing.cli test-debug \
  exports/your_agent_name \
  test_name
```

---

## **PHASE 5: Monitoring and Analysis**

### **Step 15: View Execution History**

Agent runs are stored in `~/.hive/storage/your_agent_name/`:

```bash
# List recent runs
ls ~/.hive/storage/your_agent_name/runs/

# View a specific run
cat ~/.hive/storage/your_agent_name/runs/run_20250127_123456.json
```

**Run data includes:**
- All decisions made
- Options considered
- Outcomes recorded
- Token usage
- Latency metrics

---

### **Step 16: Analyze with Builder Query**

```python
# Python script to analyze runs
from framework import BuilderQuery

query = BuilderQuery("~/.hive/storage/your_agent_name")

# Find patterns
patterns = query.find_patterns("your_goal_id")
print(f"Success rate: {patterns.success_rate:.1%}")

# Analyze failures
analysis = query.analyze_failure("run_123")
print(f"Root cause: {analysis.root_cause}")

# Get improvements
suggestions = query.suggest_improvements("your_goal_id")
for s in suggestions:
    print(f"[{s['priority']}] {s['recommendation']}")
```

---

## **PHASE 6: Advanced Usage**

### **Step 17: Custom Tools**

Add custom tools to your agent:

```python
# exports/your_agent_name/tools.py
from framework.llm.provider import Tool

def my_custom_tool(param1: str, param2: int) -> dict:
    """Custom tool description."""
    return {"result": f"Processed {param1} with {param2}"}

# Tool is auto-discovered by AgentRunner
```

---

### **Step 18: MCP Server Integration**

Configure MCP servers in `mcp_servers.json`:

```json
{
  "servers": [
    {
      "name": "tools",
      "transport": "stdio",
      "command": "python",
      "args": ["-m", "aden_tools.mcp_server", "--stdio"],
      "cwd": "/path/to/tools"
    }
  ]
}
```

---

### **Step 19: Human-in-the-Loop (HITL)**

Add pause nodes to your agent graph:

```python
# In your agent.json or builder
{
  "nodes": [
    {
      "id": "approval-check",
      "node_type": "human_input",
      "name": "Human Approval",
      "description": "Pause for human approval"
    }
  ],
  "pause_nodes": ["approval-check"]
}
```

When execution reaches a pause node:
- Execution pauses
- Session state is saved
- Resume with the same input to continue

---

### **Step 20: Resume Paused Execution**

```bash
# Resume from a pause
PYTHONPATH=core:exports python -m your_agent_name run \
  --input '{"key": "value"}' \
  --session-state '{
    "paused_at": "approval-check",
    "resume_from": "approval-check_resume",
    "memory": {"previous_data": "value"}
  }'
```

---

## **TROUBLESHOOTING**

### **Common Issues:**

**1. "ModuleNotFoundError: No module named 'framework'"**
```bash
# Solution: Reinstall framework
cd core && pip install -e . && cd ..
```

**2. "ModuleNotFoundError: No module named 'aden_tools'"**
```bash
# Solution: Reinstall tools
cd tools && pip install -e . && cd ..
```

**3. "No module named 'your_agent_name'"**
```bash
# Solution: Make sure PYTHONPATH is set correctly
# Always run from project root with:
PYTHONPATH=core:exports python -m your_agent_name ...
```

**4. "Missing tools"**
```bash
# Solution: Check tools.py exists and tools are registered
# Validate agent:
PYTHONPATH=core:exports python -m your_agent_name validate
```

**5. "ANTHROPIC_API_KEY not set"**
```bash
# Solution: Set the API key
export ANTHROPIC_API_KEY="sk-ant-your-key"

# Or use mock mode:
PYTHONPATH=core:exports python -m your_agent_name run --mock --input '{}'
```

**6. "Output validation failed"**
```bash
# Solution: Check node output_keys match what's being written
# Review agent.json node definitions
```

---

## **QUICK REFERENCE**

### **Essential Commands:**

```bash
# Setup (one-time)
./quickstart.sh

# Validate agent
PYTHONPATH=core:exports python -m agent_name validate

# View info
PYTHONPATH=core:exports python -m agent_name info

# Run agent
PYTHONPATH=core:exports python -m agent_name run --input '{"key": "value"}'

# Run in mock mode
PYTHONPATH=core:exports python -m agent_name run --mock --input '{}'

# With custom model
PYTHONPATH=core:exports python -m agent_name run --model "gpt-4o-mini" --input '{}'
```

### **Claude Code Skills:**

```
/building-agents          # Complete workflow
/building-agents-core     # Understand concepts
/building-agents-construction  # Step-by-step build
/testing-agent            # Test your agent
/agent-workflow           # End-to-end guide
```

---

## **NEXT STEPS**

1. **Build your first agent** using `/building-agents`
2. **Test it** with `/testing-agent`
3. **Run it** with real data
4. **Analyze results** and iterate
5. **Deploy** to production

For more details, see:
- [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) - Detailed setup
- [README.md](README.md) - Framework overview
- [DEVELOPER.md](DEVELOPER.md) - Developer guide

---

**Happy Building! 🚀**
