# Work Firewall 🛡️

> **"Institutional memory for AI coding agents — converting discoveries into reusable facts to eliminate redundant investigations."**

[![Maxim AI Bifrost](https://img.shields.io/badge/AI%20Gateway-Maxim%20AI%20Bifrost-6366f1)](https://github.com/maximhq/bifrost)
[![VS Code Extension](https://img.shields.io/badge/VS%20Code-Extension%20Available-007acc)](./vscode-extension)
[![MCP Compliant](https://img.shields.io/badge/MCP-2.x%20Standard-22c55e)](./mcp_server)
[![Avoidance Rate](https://img.shields.io/badge/Tool%20Call%20Avoidance-83.3%25-brightgreen)](#benchmarks)

---

## 📌 The Problem
When AI coding agents (GitHub Copilot, Claude Desktop, Cursor, custom agents) tackle complex tasks like debugging, refactoring, or security auditing, **they suffer from severe session amnesia**:
- They re-grep the same terms (`jwt`, `password`, `authenticate`) across multiple steps.
- They repeatedly re-read the exact same source files under slightly different prompts.
- They blow through API rate limits, bloat context windows with duplicate code, and waste seconds of latency on every turn.

---

## 💡 The Solution: Work Firewall
**Work Firewall** is an intelligent middleware layer sitting between AI coding agents and developer tools (`grep`, `read_file`, `list_files`).
1. **Interception:** Catches tool calls before execution.
2. **Semantic Matching:** Checks if an incoming request can be answered by previously discovered knowledge—even if worded completely differently.
3. **Structured Fact Extraction:** Turns raw tool outputs into concise, self-contained facts with file and line provenance.
4. **Cryptographic Invalidation:** Hashes referenced files using SHA-256. If code changes, any dependent facts are marked stale and automatically re-executed.
5. **Maxim AI Bifrost Integration:** Uses Maxim AI Bifrost as the resilient, high-speed AI Gateway for LLM calls with automatic fallback and observability.
6. **VS Code & MCP Native:** Ships with a ready-to-install VS Code Extension and an MCP 2.x server.

---

## 🏛️ Architecture

```
                    AI Coding Agent (VS Code Copilot / Claude Desktop)
                                            │
                                            ▼
                        ┌───────────────────────────────────────┐
                        │   Work Firewall Middleware (proxy.py) │
                        └───────┬───────────────────────┬───────┘
                                │                       │
                  Semantic Check│                       │ Metrics & Resilience
                                ▼                       ▼
                   ┌────────────────────────┐  ┌─────────────────────────┐
                   │ Valid Facts Store      │  │ Maxim AI Bifrost        │
                   │ (SQLite + SHA-256 Hash)│  │ Gateway (Port 8080)     │
                   └────────────────────────┘  └─────────────────────────┘
                                │
                 [Miss: Execute Real Tool]
                                ▼
                   ┌────────────────────────┐
                   │ Developer Tools        │
                   │ (grep, read, list)     │
                   └────────────────────────┘
```

---

## ⚡ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Ensure `.env` contains your Google API key (or OpenAI key):
```env
GOOGLE_API_KEY=your_key_here
BIFROST_URL=http://localhost:8080/v1
BIFROST_MODEL=gemini/gemini-flash-latest
```

### 3. Run Everything (1-Click Master Launcher)
```bash
# Starts Bifrost + Dashboard + runs Comparison Demo:
python run_all.py
```

### 4. Interactive Endpoints
- **Agent Intelligence Web Dashboard:** [`http://localhost:8000`](http://localhost:8000)
- **Maxim AI Bifrost Gateway:** [`http://localhost:8080`](http://localhost:8080)
- **MCP Server (stdio):** `python mcp_server/server.py`

---

## 📊 Live Measured Benchmarks

Running the comparative test (`python -m agent.demo_agent --mode=compare`):

| Metric | Baseline (No Firewall) | With Work Firewall | Savings / Gain |
| :--- | :---: | :---: | :---: |
| **Total Tool Calls** | 6 | 6 | — |
| **Executed Tool Calls** | 6 | **1** | **-83.3%** |
| **Avoided Tool Calls** | 0 | **5** | **+5 calls avoided** |
| **Avoidance Rate** | 0.0% | **83.3%** | **83.3% efficiency** |
| **Latency Saved** | 0.0s | **6.0s+** | **Instant fact return** |
| **Token Bloat** | High | Minimal | Context preserved |

---

## 🧩 VS Code Extension & MCP Integration

### 1. Install VS Code Extension (`.vsix`)
The extension package has been compiled and bundled into:
```bash
code --install-extension vscode-extension/work-firewall-1.0.0.vsix
```
*Features:*
- **Activity Bar Shield Icon:** Live agent metrics inside VS Code.
- **Real-Time Feed:** See tool calls being intercepted and avoided live.
- **Knowledge Store Inspector:** Browse active facts, file provenance, and manually invalidate facts.

### 2. Connect GitHub Copilot via MCP
Work Firewall includes `.vscode/mcp.json` pre-configured to launch `mcp_server/server.py`:
```json
{
  "mcpServers": {
    "work-firewall": {
      "command": "python",
      "args": ["mcp_server/server.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```
In VS Code Copilot Agent mode, tool calls like `search_code` and `read_file` are intercepted through Work Firewall automatically.

---

## 📁 Repository Structure

```
Work-Firewall/
├── run_all.py                 # Master launcher (Bifrost + Dashboard + Demo)
├── PITCH.md                   # Complete judge pitch guide & objection responses
├── firewall/
│   ├── proxy.py               # Core interception layer
│   ├── extractor.py           # Tool output -> structured fact
│   ├── matcher.py             # Semantic LLM router for fact reuse
│   ├── store.py               # SQLite database & provenance store
│   ├── validator.py           # SHA-256 file content hashing & invalidation
│   ├── llm.py                 # Resilient multi-tier LLM client (Bifrost/Gemini/OpenAI)
│   └── stats.py               # Session metrics, cost & latency tracker
├── bifrost/
│   └── config.yaml            # Maxim AI Bifrost provider & guardrails configuration
├── dashboard/
│   ├── server.py              # FastAPI backend (/api/stats, /api/facts, /api/activity)
│   └── static/index.html      # Premium dark-mode dashboard UI
├── vscode-extension/
│   ├── src/extension.ts       # TypeScript extension source
│   ├── package.json           # VS Code extension manifest
│   └── work-firewall-1.0.0.vsix # Packaged installable extension
├── mcp_server/
│   └── server.py              # MCP 2.x standard tool-calling server
├── agent/
│   └── demo_agent.py          # Benchmark runner (baseline vs firewall modes)
└── sample_repo/               # Test codebase for live demonstration
```

---

## 🏆 Presentation & Pitch
Refer to [**`PITCH.md`**](file:///c:/Users/abhij/Documents/Mine/Abhijeeth%27s/2025%20VIT%20college%20work/Others/Competition/HackBattle/Work-Firewall/PITCH.md) for the 60-second hook, demonstration sequence, and answers to tough technical questions.
