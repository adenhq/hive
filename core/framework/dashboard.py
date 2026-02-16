
import functools
import http.server
import json
import logging
import os
import socketserver
import threading
import webbrowser
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# --- EMBEDDED FRONTEND (Single File Vue3 + Tailwind) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hive Studio</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <style>
        body { background-color: #09090b; color: #e4e4e7; font-family: 'Inter', sans-serif; }
        .glass { background: rgba(39, 39, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .card:hover { transform: translateY(-2px); transition: all 0.2s; border-color: #8b5cf6; }
        .status-success { color: #4ade80; }
        .status-failed { color: #f87171; }
        .status-running { color: #fbbf24; }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #18181b; }
        ::-webkit-scrollbar-thumb { background: #3f3f46; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #52525b; }
    </style>
    <script>
        tailwind.config = { darkMode: 'class', theme: { extend: { colors: { gray: { 900: '#09090b', 800: '#18181b', 700: '#27272a' } } } } }
    </script>
</head>
<body class="h-screen flex overflow-hidden">
    <div id="app" class="flex w-full h-full">
        <!-- Sidebar -->
        <aside class="w-64 glass border-r border-gray-700 flex flex-col">
            <div class="p-6 border-b border-gray-700">
                <h1 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">Hive Studio</h1>
                <p class="text-xs text-gray-400 mt-1">Control Center</p>
            </div>
            <nav class="flex-1 overflow-y-auto p-4 space-y-2">
                <div v-if="loading" class="text-center text-gray-500 mt-4">Loading agents...</div>
                <div v-for="agent in agents" :key="agent.name" 
                     @click="selectAgent(agent.name)"
                     :class="{'bg-purple-900/30 border-purple-500/50 text-white': selectedAgent === agent.name, 'hover:bg-gray-800 text-gray-400': selectedAgent !== agent.name}"
                     class="p-3 rounded-lg cursor-pointer border border-transparent transition-all flex items-center gap-3">
                    <div class="w-2 h-2 rounded-full" :class="agent.has_sessions ? 'bg-green-500' : 'bg-gray-600'"></div>
                    <span class="font-medium">{{ agent.name }}</span>
                </div>
            </nav>
            <div class="p-4 border-t border-gray-700 text-xs text-gray-500 text-center">
                v1.0.0 &bull; Localhost
            </div>
        </aside>

        <!-- Main Content -->
        <main class="flex-1 flex flex-col overflow-hidden relative"> 
            <!-- Header -->
            <header class="h-16 glass border-b border-gray-700 flex items-center justify-between px-8 z-10">
                <div>
                     <h2 class="text-lg font-semibold text-white">{{ selectedAgent ? selectedAgent : 'Select an Agent' }}</h2>
                     <p class="text-xs text-gray-400" v-if="selectedAgent">Viewing execution history</p>
                </div>
                <!-- Controls -->
                <div class="flex gap-3" v-if="selectedAgent">
                    <button class="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm border border-gray-600 flex items-center gap-2" @click="fetchSessions(selectedAgent)">
                        🔄 Refresh
                    </button>
                    <button class="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-md text-sm font-medium shadow-lg shadow-purple-900/20 flex items-center gap-2 hover:scale-105 transition-transform" @click="triggerRun">
                        ▶ Run Agent
                    </button>
                </div>
            </header>

            <!-- Dashboard Content -->
            <div class="flex-1 overflow-y-auto p-8 relative">
                <!-- Welcome State -->
                <div v-if="!selectedAgent" class="flex flex-col items-center justify-center h-full text-gray-500">
                    <div class="text-6xl mb-4">🛸</div>
                    <p class="text-xl font-medium">Select an agent to begin</p>
                    <p class="text-sm mt-2">View history, inspect logic, and monitor runs.</p>
                </div>

                <!-- Session List -->
                <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
                    <div v-for="session in sessions" :key="session.id" 
                         @click="viewSession(session)"
                         class="glass rounded-xl p-5 border border-gray-700 hover:border-purple-500/50 cursor-pointer group relative overflow-hidden">
                        
                        <div class="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity">
                            <span class="text-lg text-gray-500 group-hover:text-purple-400">↗</span>
                        </div>

                        <div class="flex items-center justify-between mb-4">
                            <span class="text-xs font-mono text-gray-500 bg-gray-800/50 px-2 py-1 rounded">{{ session.id.substring(0, 8) }}</span>
                            <span class="text-xs px-2 py-0.5 rounded-full border" 
                                  :class="statusClass(session.status)">
                                {{ session.status ? session.status.toUpperCase() : 'UNKNOWN' }}
                            </span>
                        </div>

                        <div class="space-y-3">
                            <div class="flex justify-between items-end">
                                <div class="text-2xl font-bold text-white">{{ session.steps }}</div>
                                <div class="text-xs text-gray-500 mb-1">STEPS</div>
                            </div>
                             <div class="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                                <div class="bg-purple-500 h-full rounded-full" :style="{ width: Math.min(session.steps, 100) + '%' }"></div>
                            </div>
                        </div>

                        <div class="mt-4 pt-4 border-t border-gray-700/50 flex justify-between text-xs text-gray-400">
                             <span>{{ formatDate(session.updated_at) }}</span>
                             <span>{{ session.memory_keys || 0 }} memory keys</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Details Drawer (Simplified) -->
            <div v-if="activeSession" class="absolute inset-y-0 right-0 w-1/2 glass border-l border-gray-700 shadow-2xl p-6 overflow-y-auto transform transition-transform" style="background: rgba(24, 24, 27, 0.95);">
                 <div class="flex justify-between items-start mb-6">
                    <div>
                        <h3 class="text-xl font-bold text-white">Session Details</h3>
                        <p class="text-sm text-gray-400 mt-1 font-mono">{{ activeSession.id }}</p>
                    </div>
                    <button @click="activeSession = null" class="text-gray-400 hover:text-white text-2xl">&times;</button>
                </div>
                
                <div class="space-y-6">
                    <div class="bg-gray-900 rounded-lg p-4 border border-gray-800">
                        <h4 class="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Metrics</h4>
                         <div class="grid grid-cols-2 gap-4">
                            <div><p class="text-xs text-gray-500">Duration</p><p class="text-lg text-white">--</p></div>
                            <div><p class="text-xs text-gray-500">Steps</p><p class="text-lg text-white">{{ activeSession.steps }}</p></div>
                            <div><p class="text-xs text-gray-500">Final Node</p><p class="text-lg text-purple-400 truncate">{{ activeSession.current_node }}</p></div>
                            <div><p class="text-xs text-gray-500">Memory</p><p class="text-lg text-white">{{ activeSession.memory_keys }} keys</p></div>
                        </div>
                    </div>

                    <div class="bg-gray-900 rounded-lg p-4 border border-gray-800">
                        <h4 class="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">State Preview</h4>
                         <pre class="text-xs text-green-400 bg-black p-4 rounded overflow-x-auto border border-gray-800 font-mono">{{ JSON.stringify(activeSession, null, 2) }}</pre>
                    </div>
                </div>
            </div>

        </main>
    </div>

    <script>
        const { createApp, ref, onMounted } = Vue

        createApp({
            setup() {
                const agents = ref([])
                const selectedAgent = ref(null)
                const sessions = ref([])
                const loading = ref(true)
                const activeSession = ref(null)

                const fetchAgents = async () => {
                    const res = await fetch('/api/agents')
                    agents.value = await res.json()
                    loading.value = false
                }

                const selectAgent = (name) => {
                    selectedAgent.value = name
                    fetchSessions(name)
                    activeSession.value = null
                }

                const fetchSessions = async (name) => {
                    const res = await fetch(`/api/sessions/${name}`)
                    sessions.value = await res.json()
                }
                
                const viewSession = (session) => {
                    activeSession.value = session
                }

                const triggerRun = () => {
                    alert('Run Triggered! (Check your terminal)')
                    // In a real implementation this would POST /api/run
                }

                // Utilities
                const statusClass = (status) => {
                    if (!status) return 'border-gray-600 text-gray-400'
                    if (status.includes('fail')) return 'border-red-500/50 text-red-500 bg-red-500/10'
                    if (status.includes('completed')) return 'border-green-500/50 text-green-500 bg-green-500/10'
                    return 'border-yellow-500/50 text-yellow-500 bg-yellow-500/10'
                }
                
                const formatDate = (iso) => {
                    if (!iso) return ''
                    return new Date(iso).toLocaleString()
                }

                onMounted(() => {
                    fetchAgents()
                })

                return { agents, selectedAgent, sessions, loading, selectAgent, fetchSessions, viewSession, activeSession, triggerRun, statusClass, formatDate }
            }
        }).mount('#app')
    </script>
</body>
</html>
"""

class APIHandler(http.server.SimpleHTTPRequestHandler):
    """Handles API requests and serves the SPA."""
    
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.strip().encode("utf-8"))
            return

        if self.path == "/api/agents":
            self._handle_agents()
            return

        if self.path.startswith("/api/sessions/"):
            agent_name = self.path.split("/")[-1]
            self._handle_sessions(agent_name)
            return

        # Fallback
        self.send_response(404)
        self.end_headers()

    def _handle_agents(self):
        """List all agents in ~/.hive/agents."""
        agents = []
        home = Path.home()
        agents_dir = home / ".hive" / "agents"
        
        if agents_dir.exists():
            for d in agents_dir.iterdir():
                if d.is_dir():
                    has_sessions = (d / "sessions").exists()
                    agents.append({"name": d.name, "path": str(d), "has_sessions": has_sessions})
        
        self._send_json(agents)

    def _handle_sessions(self, agent_name):
        """List sessions for an agent."""
        home = Path.home()
        sessions_dir = home / ".hive" / "agents" / agent_name / "sessions"
        data = []

        if sessions_dir.exists():
            # Get latest 20 sessions
            paths = sorted(sessions_dir.iterdir(), key=os.path.getmtime, reverse=True)[:20]
            for p in paths:
                state_file = p / "state.json"
                if state_file.exists():
                    try:
                        with open(state_file) as f:
                            state = json.load(f)
                            progress = state.get("progress", {})
                            timestamps = state.get("timestamps", {})
                            
                            status = "completed"
                            if progress.get("paused_at"): status = "paused"
                            
                            data.append({
                                "id": p.name,
                                "status": status,
                                "steps": progress.get("steps_executed", 0),
                                "current_node": progress.get("current_node", "?"),
                                "updated_at": timestamps.get("updated_at"),
                                "memory_keys": len(state.get("memory", {}))
                            })
                    except:
                        pass
        
        self._send_json(data)

    def _send_json(self, data: Any):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Silence logs

def start_dashboard(port: int = 8000):
    """Start the Hive Studio dashboard."""
    # Ensure port is available (simple check)
    server = socketserver.ThreadingTCPServer(("127.0.0.1", port), APIHandler)
    
    url = f"http://127.0.0.1:{port}"
    print(f"\n🚀 Hive Studio is running at: {url}")
    print("   Press Ctrl+C to stop.")
    
    # Auto-open browser
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
        server.shutdown()
