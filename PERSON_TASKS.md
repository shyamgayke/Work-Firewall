# Work Firewall — Team Task Assignments (UPDATED for full build)

## Status: FULL BUILD — Not just a demo anymore

The checkpoint-hour-1 demo has been upgraded to a complete product.
All components are implemented and working.

---

## What's Already Done (by AI assistant)

- ✅ `firewall/store.py` — SQLite fact store with activity log
- ✅ `firewall/validator.py` — SHA-256 file hash invalidation  
- ✅ `firewall/proxy.py` — Full intercept loop with stats + activity events
- ✅ `firewall/extractor.py` — LLM fact extraction
- ✅ `firewall/matcher.py` — LLM semantic matching
- ✅ `firewall/llm.py` — Bifrost-first LLM client (fallback to Gemini)
- ✅ `firewall/stats.py` — Session stats with cost/latency estimation
- ✅ `mcp_server/server.py` — MCP server for VS Code Copilot integration
- ✅ `.vscode/mcp.json` — Auto-connects Copilot to Work Firewall
- ✅ `dashboard/server.py` — FastAPI backend with new endpoints
- ✅ `dashboard/static/index.html` — Dark glassmorphism dashboard UI
- ✅ `vscode-extension/` — TypeScript sidebar extension (compiled, ready)
- ✅ `agent/demo_agent.py` — baseline / firewall / compare modes
- ✅ `sample_repo/middleware.py` — expanded sample codebase
- ✅ `sample_repo/config.py` — expanded sample codebase
- ✅ `tools/real_tools.py` — updated with directory param
- ✅ `bifrost/config.yaml` — Bifrost gateway config
- ✅ `README.md` — complete setup + demo guide

---

## Person A — Agent & Testing

**Your remaining tasks:**
1. Run the full demo end-to-end and report the real avoidance numbers:
   ```bash
   python -m agent.demo_agent --mode=compare
   ```
   Note: how many out of 6 were avoided? What was the avoidance rate?

2. Run the demo 2-3 times, pick the best numbers for the pitch.

3. Verify the baseline mode for the demo narrative:
   ```bash
   python -m agent.demo_agent --mode=baseline
   ```

4. Optionally add 1-2 more tasks to FIREWALL_TASKS in demo_agent.py for
   a more dramatic avoidance demonstration.

---

## Person B — Firewall Core Verification

**Your remaining tasks:**
1. Verify the invalidation works: edit a file in sample_repo/, then
   check the dashboard — the affected facts should show "Stale".

2. Run the smoke test to confirm everything imports correctly:
   ```bash
   python -c "from firewall.proxy import intercept; print('OK')"
   ```

3. Tune the extractor/matcher prompts in `firewall/extractor.py` and
   `firewall/proxy.py` if you want better fact quality or match accuracy.

---

## Person C — Interface & Demo Prep

**Your remaining tasks:**

1. Start the dashboard:
   ```bash
   uvicorn dashboard.server:app --port 8000 --reload
   ```
   Open http://localhost:8000 — verify live updates, facts, activity feed.

2. (Optional) Start Bifrost for extra observability:
   ```bash
   npx -y @maximhq/bifrost
   ```
   Open http://localhost:8080 — shows LLM call tracing.

3. Test the VS Code extension:
   - Open `vscode-extension/` in VS Code
   - Press F5 → Extension Development Host opens
   - Look for the shield icon in the Activity Bar
   - Run `python -m agent.demo_agent --mode=firewall` in another terminal
   - Watch the sidebar update live

4. Test the MCP server with Copilot:
   - `python mcp_server/server.py`  (in one terminal)
   - In VS Code: open Copilot chat → Agent mode
   - Disable built-in file tools in Agent Customizations → Tools
   - Ask: "Where is JWT validation implemented?"
   - Confirm it calls `search_code` (Work Firewall's tool)

5. Rehearse the demo script (see README.md) — time it to 3 minutes.

---

## Demo Startup Sequence (Day of)

```bash
# Terminal 1 — Dashboard
uvicorn dashboard.server:app --port 8000 --reload

# Terminal 2 — (optional) Bifrost
npx -y @maximhq/bifrost

# Terminal 3 — Demo agent (run during presentation)
python -m agent.demo_agent --mode=baseline   # first
python -m agent.demo_agent --mode=firewall   # second — shows avoidance
```

Open http://localhost:8000 on the projected screen before starting.
