# Hive Agent Builder UI

A visual drag-and-drop interface for building AI agents without code. Design complex multi-step workflows, test nodes individually, and export production-ready Python agents.

![Agent Builder](https://img.shields.io/badge/Status-Beta-blue)
![React](https://img.shields.io/badge/React-18-61dafb)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178c6)
![React Flow](https://img.shields.io/badge/React_Flow-12.10-ff0072)

---

## How This Fits Into Hive

The [Hive Framework](https://github.com/adenhq/hive) offers **two ways** to build AI agents:

| Approach | Method | Best For |
|----------|--------|----------|
| **Goal-Driven** (Auto) | Describe goals in natural language → Coding agent generates the agent graph | Rapid prototyping, complex agents, users who prefer AI assistance |
| **Visual Builder** (Manual) | Drag-and-drop nodes → Configure manually → Export code | Learning, precise control, visual thinkers, custom workflows |

### This UI Builder = Manual Mode

```
┌─────────────────────────────────────────────────────────────────┐
│                        HIVE FRAMEWORK                           │
│                                                                 │
│   ┌─────────────────────┐       ┌─────────────────────┐        │
│   │   GOAL-DRIVEN       │       │   VISUAL BUILDER    │        │
│   │   (Auto Mode)       │       │   (Manual Mode)     │        │
│   │                     │       │                     │        │
│   │  "Build me an       │       │   [Node] → [Node]   │        │
│   │   agent that..."    │       │      ↓        ↓     │        │
│   │        ↓            │       │   Drag & Drop UI    │        │
│   │  Coding Agent       │       │                     │        │
│   │   generates graph   │       │   ← YOU ARE HERE    │        │
│   └──────────┬──────────┘       └──────────┬──────────┘        │
│              │                             │                    │
│              └──────────┬──────────────────┘                    │
│                         ↓                                       │
│              ┌─────────────────────┐                           │
│              │   Hive Runtime      │                           │
│              │   (Execute Agent)   │                           │
│              └─────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

### When to Use Each

**Use Goal-Driven (Claude Code)** when you:
- Want AI to design the agent architecture
- Need rapid iteration on complex workflows
- Prefer describing outcomes over implementation

```bash
claude> /building-agents
# "Build me an agent that researches a topic and writes a summary"
```

**Use Visual Builder (This UI)** when you:
- Want to see and control every node
- Are learning how agents work
- Need precise control over data flow
- Prefer visual design over text descriptions

Both approaches produce the same output: **production-ready Python agents** that run on the Hive runtime.

---

## Features

### Core Capabilities
- **Visual Node Editor** - Intuitive drag-and-drop canvas powered by React Flow
- **4 Node Types** - LLM Generate, Tool Use, Router, Function nodes
- **Pre-built Templates** - Research Agent, Support Agent, Profile Scraper, and more
- **Live Testing** - Test individual nodes before running the full agent
- **Code Export** - Generate production-ready Python agents

### Data Flow Visualization (New!)
- **Edge Labels** - See which keys flow between connected nodes
- **Key Matching** - Green chips show matching input/output keys
- **Warning Indicators** - Amber dashed edges when keys don't match
- **Node Warnings** - Visual badge on nodes missing required inputs

### Smart Key Suggestions (New!)
- **Auto-suggestions** - See available keys from connected source nodes
- **One-click Add** - Click suggested keys to add them instantly
- **Missing Key Alerts** - Highlights input keys not provided by source nodes

### Reorganized Configuration Panel (New!)
- **Data Flow Section** - Prominent section for input/output key management
- **Grouped Test Section** - Test input, button, and results in one place
- **Behavior Section** - System prompts and tool configuration
- **Execution Settings** - Start/End node toggles

---

## Quick Start

```bash
cd agent-builder-ui
npm install
npm run dev
# Open http://localhost:5173
```

---

## Usage

### Building Your First Agent

1. **Select a Template** - Choose from pre-built workflows or start blank
2. **Add Nodes** - Drag nodes from the left sidebar onto the canvas
3. **Connect Nodes** - Draw edges between nodes to define the flow
4. **Configure Data Flow** - Set input/output keys (watch for green edge labels!)
5. **Write Prompts** - Tell each node what to do
6. **Test Individual Nodes** - Use the Test section to verify each step
7. **Run Full Agent** - Click "Execute Agent" to run the complete workflow
8. **Export Code** - Download as a Python package

### Understanding Data Flow

```
┌─────────────────┐       url        ┌─────────────────┐
│  Scrape Page    │  ─────────────▶  │  Extract Links  │
│                 │  profile_summary │                 │
│  in:  url       │  ─────────────▶  │  in:  url       │
│  out: profile   │                  │       profile   │
│       url ←─────│──────────────────│  out: links     │
└─────────────────┘                  └─────────────────┘
```

**Key Concept:** Output keys from Node A must match input keys on Node B for data to flow.

---

## Node Types

| Type | Use Case | Has Tools |
|------|----------|-----------|
| **LLM Generate** | Reasoning, analysis, text generation | No |
| **Tool Use** | Web scraping, file operations, API calls | Yes |
| **Router** | Conditional branching (if/else logic) | No |
| **Function** | Custom Python code execution | No |

---

## Templates

| Template | Description | Nodes |
|----------|-------------|-------|
| **Research Agent** | Analyzes query → Scrapes web → Summarizes findings | 3 |
| **Support Agent** | Classifies ticket → Generates response | 2 |
| **Profile Scraper** | Scrapes profile → Extracts blog links | 2 |
| **Document Processor** | Extracts content → Analyzes → Reports | 3 |
| **Data Enrichment** | Validates → Enriches → Formats | 3 |

---

## Running Exported Agents

### Quick Start

```bash
# 1. Navigate to hive project
cd /path/to/hive

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Set your API key (Gemini, OpenAI, or Anthropic)
export GEMINI_API_KEY="your-key"

# 4. Run the agent (note: JSON must be on same line!)
PYTHONPATH=core python my_agent.py run '{"url":"https://example.com"}'
```

### Tool Configuration (Required for Tool Nodes)

If your agent uses tools (web_scrape, pdf_read, etc.), create an `mcp_servers.json` file **in the same folder** as your agent:

```json
{
  "hive-tools": {
    "transport": "stdio",
    "command": "python",
    "args": ["mcp_server.py", "--stdio"],
    "cwd": "/absolute/path/to/hive/tools",
    "description": "Hive tools MCP server"
  }
}
```

### Available Commands

```bash
# Run with input
PYTHONPATH=core python my_agent.py run '{"query":"your input"}'

# Show agent info (nodes, entry point)
PYTHONPATH=core python my_agent.py info

# Validate structure (check edges reference valid nodes)
PYTHONPATH=core python my_agent.py validate
```

### Troubleshooting

| Error | Solution |
|-------|----------|
| `Tool validation failed: web_scrape not registered` | Create `mcp_servers.json` next to your agent |
| `Missing required input: url` | Check JSON is on same line as `run` command |
| `zsh: no such file or directory` | Quote the JSON properly: `'{"key":"value"}'` |
| `ModuleNotFoundError: framework` | Add `PYTHONPATH=core` before python command |

### Example Output

```json
{
  "success": true,
  "output": {
    "profile_summary": "Senior Software Engineer at Reclaim Protocol...",
    "links": [
      "https://example.com/blog/post-1",
      "https://example.com/blog/post-2"
    ],
    "summary": "This blog post explores..."
  }
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Node Canvas  │ │ Config Panel │ │ Templates & Export   │ │
│  │ (React Flow) │ │ (Data Flow)  │ │ (Code Generation)    │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
└─────────────────────────────┬───────────────────────────────┘
                              │ API Calls
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│  POST /api/test-node  - Test individual nodes               │
│  POST /api/run        - Execute full agent                  │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Hive Framework                           │
│  - Dynamic GraphSpec construction                           │
│  - AgentRuntime execution with LiteLLM                      │
│  - MCP tool integration (web_scrape, pdf_read, etc.)        │
└─────────────────────────────────────────────────────────────┘
```

---

## Recent Updates

### v0.2.0 - UX Improvements
- **Data Flow Visualization** - Edge labels showing key flow between nodes
- **Key Validation** - Warning indicators for mismatched keys
- **Smart Suggestions** - Auto-suggest available keys from connected nodes
- **Reorganized Panel** - Logical grouping of configuration options
- **New Template** - Profile Scraper workflow

### v0.1.0 - Initial Release
- Visual node editor with React Flow
- 4 node types (LLM, Tool, Router, Function)
- Code export to Python
- Real-time agent execution

---

## Roadmap

### Short Term
- [ ] **Undo/Redo** - Track and revert changes
- [ ] **Copy/Paste Nodes** - Duplicate node configurations
- [ ] **Import Agents** - Load previously exported Python agents
- [ ] **Dark Mode** - Because developers love dark mode

### Medium Term
- [ ] **Live Execution View** - Watch nodes light up during execution
- [ ] **Execution History** - View past runs and their outputs
- [ ] **Node Library** - Save and reuse custom node configurations
- [ ] **Branching Flows** - Visual support for router node paths

### Long Term
- [ ] **Collaboration** - Share agents via URL
- [ ] **Version Control** - Track changes to agent definitions
- [ ] **Marketplace** - Community templates and nodes
- [ ] **Visual Debugger** - Step-through execution with context inspection
- [ ] **Auto-optimization** - AI suggestions for improving prompts

### Proposed Features

#### Self-Improving Agents (Closes the Gap with Goal-Driven Mode)

The holy grail: agents that learn from failures and improve themselves.

```
┌─────────────────────────────────────────────────────────────┐
│                  SELF-IMPROVING LOOP                        │
│                                                             │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│   │  Run    │───▶│ Failure │───▶│ Analyze │               │
│   │  Agent  │    │ Captured│    │  with AI│               │
│   └─────────┘    └─────────┘    └────┬────┘               │
│        ▲                             │                     │
│        │                             ▼                     │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│   │Redeploy │◀───│ Update  │◀───│Suggest  │               │
│   │         │    │  Graph  │    │  Fixes  │               │
│   └─────────┘    └─────────┘    └─────────┘               │
└─────────────────────────────────────────────────────────────┘
```

**Required Components:**

| Component | Description | Status |
|-----------|-------------|--------|
| Execution History DB | Store all runs, inputs, outputs, failures | Not started |
| Failure Analysis API | AI endpoint that analyzes what went wrong | Not started |
| Graph Modification API | Programmatically add/update/remove nodes & edges | Not started |
| Import from Python | Load exported agents back into UI for editing | Not started |
| "Fix This" Button | One-click to apply AI-suggested improvements | Not started |
| Auto-Evolution Toggle | Enable automatic improvement cycle for deployed agents | Not started |

**Example Flow:**
```
1. Agent runs: Scrape Profile → Get Blog Links
2. Fails: "No blog links found"
3. AI Analysis: "The page uses JavaScript rendering, web_scrape got empty content"
4. AI Suggestion: "Add a wait/render step, or use a headless browser tool"
5. User clicks "Apply Fix" → New node added automatically
6. Agent re-runs successfully
```

This would make the Visual Builder equivalent to Goal-Driven mode in terms of adaptability.

#### Multi-Model Support
```
Node A (GPT-4) → Node B (Claude) → Node C (Gemini)
```
Different nodes using different LLM providers based on task requirements.

#### Conditional Branching UI
```
           ┌─▶ [Handle Billing] ─┐
[Router] ──┼─▶ [Handle Tech]    ─┼─▶ [Send Response]
           └─▶ [Handle General] ─┘
```
Visual paths for router node conditions.

#### Parallel Execution
```
         ┌─▶ [Scrape Site A] ─┐
[Start] ─┤                    ├─▶ [Merge Results]
         └─▶ [Scrape Site B] ─┘
```
Run multiple nodes simultaneously and merge results.

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| React 18 | UI Framework |
| TypeScript | Type Safety |
| React Flow 12 | Node Editor |
| Lucide React | Icons |
| Prism.js | Code Highlighting |
| Vite | Build Tool |

---

## Project Structure

```
agent-builder-ui/
├── src/
│   ├── App.tsx          # Main application (nodes, edges, panels)
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── public/
├── package.json
└── vite.config.ts
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Related Projects

- **[Hive Framework](../core/)** - The underlying agent execution framework
- **[Hive Tools](../tools/)** - MCP tool implementations

---

## License

MIT

---

<p align="center">
  Built with React Flow + Hive Framework
</p>
