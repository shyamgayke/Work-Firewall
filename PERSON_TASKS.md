# Work Firewall — Team Task Guide

> **Read this first before touching any code.**
> This file tells you exactly what to work on based on your role (A, B, or C).

---

## Quick Setup (everyone does this once)

```bash
# 1. Clone / open the repo
# 2. Set your API key (Google Gemini or OpenAI)
cp .env.example .env
# Edit .env and paste your GOOGLE_API_KEY=AIzaSy... (or OPENAI_API_KEY)

# 3. Install deps (already done if packages are present)
pip install -r requirements.txt

# 4. Run the demo to verify everything works
python -m agent.demo_agent
```

---

## Person A — Agent & Tools

**Your files:**
- `tools/real_tools.py` — `grep_search`, `read_file`, `list_files`
- `agent/demo_agent.py` — the agent loop and demo scenarios

**Hour 0–1:**
- [ ] Verify `grep_search('jwt')` and `read_file('auth.py')` work against `sample_repo/`
- [ ] Run `python -m agent.demo_agent` and confirm tool calls print output
- [ ] The stubs in `real_tools.py` already work — just review and adjust paths if needed

**Hour 1–4:**
- [ ] Expand `demo_agent.py` with 2–3 more investigation questions
- [ ] Add a second question that is a *differently worded* version of the first
      (this is the key demo: it should be AVOIDED by the firewall)
- [ ] Add questions that span `db.py` and `routes.py` (not just `auth.py`)
- [ ] Log real numbers: how many calls avoided vs executed per run

**Where NOT to work:** `firewall/`, `dashboard/` — those are B and C.

---

## Person B — Firewall Core

**Your files:**
- `firewall/store.py` — fact storage (dict → SQLite in Hour 1-4)
- `firewall/extractor.py` — LLM: raw tool output → structured fact
- `firewall/validator.py` — hash-based fact invalidation
- `firewall/matcher.py` — LLM router (also Person C, coordinate)

**Hour 0–1:**
- [ ] Read `firewall/store.py` — understand the fact schema
- [ ] Read `firewall/extractor.py` — the LLM extraction prompt is already written
- [ ] Run one manual extraction test:
  ```python
  from firewall.extractor import extract_fact
  print(extract_fact("grep_search", {"pattern": "jwt"}, "auth.py:8: import jwt\nauth.py:21: token = jwt.encode(...)"))
  ```
- [ ] Confirm it returns a sensible one-sentence fact

**Hour 1–4:**
- [ ] Move `store.py` from plain dict to SQLite
  - Add `import sqlite3` and `DB_PATH = "firewall_facts.db"`
  - `store_fact()` → INSERT row; `get_all_facts()` → SELECT all
- [ ] Implement `validator.py` `is_fact_valid()` (whole-file SHA-256 only — no line ranges)
- [ ] Tune the extraction prompt in `extractor.py` against real outputs
- [ ] Test a fact being invalidated: edit `sample_repo/auth.py`, then check `is_fact_valid()`

**Where NOT to work:** `agent/`, `dashboard/` — those are A and C.

---

## Person C — Interface & Demo (you)

**Your files:**
- `firewall/proxy.py` — the intercept layer (DONE for Hour 0-1)
- `firewall/matcher.py` — tune the LLM matcher here (Hour 1-4)
- `dashboard/server.py` — FastAPI backend (Hour 4-7)
- `dashboard/static/index.html` — polling dashboard UI (Hour 4-7)

**Hour 0–1:**
- [x] `proxy.py` is complete — review it and understand the flow
- [ ] Run `python -m agent.demo_agent` and verify ✅/🔧 output
- [ ] Prepare your 60-second verbal explanation (see `Work_Firewall_Full_Context.md §4`)

**Hour 1–4:**
- [ ] Move matcher logic from `proxy.py` into `firewall/matcher.py`
- [ ] Test `find_matching_fact()` against 4–5 question pairs manually
- [ ] Confirm false-positive rate is low (NO_MATCH when it should be)

**Hour 4–7:**
- [ ] Stand up `dashboard/server.py` — run with:
      `uvicorn dashboard.server:app --reload --port 8000`
- [ ] Build out `dashboard/static/index.html` — stats bar + facts list + activity feed

---

## How to run the full stack

```bash
# Terminal 1 — run the demo agent
python -m agent.demo_agent

# Terminal 2 (Hour 4+) — run the dashboard
uvicorn dashboard.server:app --reload --port 8000
# Open http://localhost:8000
```

---

## Cut-scope reminders (do NOT build these)
- No VS Code extension
- No MCP server
- No embedding-based matching (LLM router only)
- No line-range hashing (whole-file SHA-256 only)
