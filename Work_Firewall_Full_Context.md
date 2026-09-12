# Work Firewall — Full Project Context

> This document is meant to be handed to another AI agent or teammate cold, so they
> have complete context on what this project is, every decision made so far, the
> current build plan, and how work is split. Read top to bottom before doing anything.

---

## 1. What This Project Is

**Work Firewall** is an intelligent middleware layer that sits between an AI coding
agent and the tools it uses to explore a codebase (grep, file read, search, etc.).
Its purpose is to prevent agents from repeatedly performing the same searches, file
reads, and investigations when the required information has already been discovered
earlier in the same session.

**The problem:** AI coding agents doing complex tasks (security audits, bug
investigations, refactors) often re-run the same searches and re-read the same files
multiple times through different phrasings of the same underlying question. This
wastes tool calls, latency, and API cost.

**The mechanism:** Work Firewall intercepts tool calls, converts their outputs into
structured, reusable **facts** (not raw cached responses), stores them with
provenance (which files/lines they depend on), and reuses them when a later —
possibly differently worded — question can be answered from existing facts. Facts
are automatically invalidated when the underlying code changes.

**One-line pitch:** *"Work Firewall gives AI coding agents institutional memory by
converting discoveries into reusable evidence, preventing redundant investigations
and dramatically reducing unnecessary tool execution."*

**Hackathon track fit:** Track 3 (Developer Tooling) — specifically "Codebase
Intelligence & Navigation." Also touches Track 1 (AI & Automation) framing if
relevant.

---

## 2. Key Design Decisions Made So Far (and why)

### 2.1 Facts, not raw caching
We store structured facts with file/line provenance, not raw tool-output caching.
This is the core differentiator from "just a cache" — it allows differently-worded
questions to hit the same underlying knowledge, and it allows precise invalidation
tied to actual code changes.

### 2.2 Interception = function-level, not network-level
"Middleware" here means intercepting at the point where an agent's tool-calling loop
dispatches a tool call — a Python function sitting between the agent and the real
tool functions — **not** a literal network proxy/firewall appliance. This is
intentional: it's simpler to build, and it's actually how most real agent
guardrail/observability tools work. Be upfront about this distinction if asked; it's
a legitimate, defensible design, not a shortcut to hide.

### 2.3 Matching approach: LLM-as-router (not embeddings, for now)
To decide if a new tool-call request can be answered from existing facts, we send
the candidate facts + the new request to an LLM and ask it to judge if there's a
match. This was chosen over embedding-based similarity search because it's simpler
to build and debug under time pressure. Embeddings are a valid stretch-goal upgrade
(cheaper/faster at scale) but not required for the demo to work.

### 2.4 Invalidation approach: whole-file hashing (MVP), not line-range hashing
We hash the entire file a fact depends on and compare hashes to detect changes. This
is the deliberate **first corner to cut** if time-constrained — line-range-level
hashing (more precise) was considered but is a stretch goal, not required.

### 2.5 VS Code / real-agent integration — investigated, then cut for time
We explored making Work Firewall work with a **real** agent (GitHub Copilot in VS
Code) rather than only a custom demo agent. Findings, in case this is revisited with
more time:

- VS Code has a real, current **Language Model Tools API** and **MCP server**
  support — extensions/MCP servers can register tools (e.g., `search_code`,
  `read_file`) that Copilot's agent mode can call.
- Copilot's agent **chooses** which available tool to use; you cannot force
  interception of every built-in tool call automatically.
- **The actual working mechanism:** disable VS Code's built-in file-search/read
  tools in the **Agent Customizations → Tools** panel (a persistent, not per-message,
  setting), leaving only your MCP-provided tools available. With built-ins disabled,
  Copilot has no choice but to route those actions through your tools. This is
  verified, current VS Code behavior (confirmed via VS Code's own docs), not a
  guess.
- Practical requirement: MCP tools must be marked with `readOnlyHint: true` in their
  definitions, or VS Code will show a confirmation dialog before every single tool
  call — which would break a live demo's flow.
- **UI decision:** if built, the VS Code-side UI should be a **sidebar panel**
  (like GitLens/Docker's views) — a passive dashboard (facts, stats, activity feed),
  **not** a new chat window and **not** a chat participant. It sits in VS Code's
  Activity Bar, separate from and next to the existing Copilot Chat panel. A "chat
  participant" (`@workfirewall`) option was considered and rejected: it would
  require building an entire second agent from scratch just to have something to
  wrap, which undermines the "sits in front of *any* agent" pitch and is much higher
  effort.
- **Given the current 10-hour time budget, this entire VS Code/MCP integration is
  CUT, not deferred-with-intent.** The deliverable is a standalone Python
  demonstration (custom demo agent + firewall core + a plain web dashboard). If a
  judge asks whether this integrates with real tools like Copilot, the honest answer
  is: "we scoped that out given the time budget; here's the verified mechanism for
  how it would work" (see above) — not a claim that it's built.

### 2.6 Known objections / honest answers to have ready
- **"Isn't this just caching?"** → Traditional caching is exact-match on requests;
  we reuse facts across differently-worded questions and auto-invalidate on real
  code changes — plain caching does neither.
- **"What if the LLM extracts a wrong fact?"** → Every reused fact is re-validated
  against current file content before being trusted. A wrong fact tied to unchanged
  code is a real residual risk; we keep extraction conservative and show provenance
  in the dashboard so it's inspectable, not hidden.
- **"Your checker/matcher LLM can also be wrong."** → True; it's a second,
  independent check, not a guarantee. We test it against at least one failure case
  we didn't specifically design around, and report the honest result rather than
  claiming perfection.
- **"Does the LLM overhead outweigh the tool-call savings?"** → Cite real measured
  numbers from your own testing (calls avoided vs. calls executed, rough
  latency/cost saved) — have actual figures ready, not a hand-wave.
- **"Who is the user, and what do they actually click?"** → The primary "user" of
  the core mechanism is the AI agent, not a human — the system works automatically,
  with zero human interaction needed for the core value. The dashboard/UI exists for
  two reasons only: (1) trust/auditability (a human can inspect what the system
  believes and manually invalidate a wrong fact) and (2) making an otherwise
  invisible efficiency gain demonstrable. It is not the main interaction surface —
  be upfront about this if asked "what does the user do with this," since claiming
  otherwise overstates the product.

---

## 3. Architecture

```
AI Agent (Claude/GPT with tool-calling)
        ↓
Work Firewall (proxy/middleware layer)
   ├── Intercept layer      → catches every tool call before it executes
   ├── Fact extraction      → turns raw tool output into structured facts
   ├── Knowledge store      → repo-aware fact database + provenance
   ├── Validity checker     → detects if underlying code changed
   └── Dashboard            → shows calls avoided, cost/latency saved
        ↓
Real Tools (grep, file read, search, static analysis, tests)
```

### Fact schema
```
{
  "statement": "JWT validation occurs in auth.py, lines 40-65",
  "files": ["auth.py"],
  "line_ranges": {"auth.py": [40, 65]},
  "content_hash": "<sha256 of referenced file content at extraction time>",
  "source_tool_call": "grep_search('jwt')",
  "created_at": <timestamp>
}
```

### Tech stack
- **Language:** Python 3.11+
- **Web framework:** FastAPI (dashboard API)
- **Database:** SQLite (zero setup, sufficient for repo-scale demo)
- **LLM:** Claude or GPT-4-class model with tool-use/function-calling
- **Frontend:** Plain HTML/JS dashboard (polling, not real-time infra)
- **Repo tooling:** `hashlib` for content hashing (git-based diffing considered but
  not required for MVP)

### Core files
```
work-firewall/
├── agent/demo_agent.py       # the demo coding agent doing an investigation
├── firewall/
│   ├── proxy.py              # intercepts tool calls, ties everything together
│   ├── extractor.py          # LLM call: tool output -> structured facts
│   ├── store.py              # SQLite fact storage
│   ├── matcher.py            # LLM-as-router: can a new request be answered from facts?
│   └── validator.py          # file-hash based invalidation check
├── tools/real_tools.py       # grep, file read, list files (real tool implementations)
├── dashboard/
│   ├── server.py             # FastAPI app: /api/stats, /api/facts
│   └── static/index.html     # polling dashboard UI
├── sample_repo/              # seeded codebase for the demo (small auth-system example)
└── README.md
```

Full working code for every component above (extraction prompt, matcher prompt,
validator logic, proxy wiring, dashboard) exists in the earlier, fuller build guide
document (`Work_Firewall_Build_Guide.md`) — that document has copy-pasteable code
for the 36-hour version. This document's job is context and current plan, not
re-deriving that code; consult the build guide for exact implementations, adjusting
scope per the timeline below.

---

## 4. CURRENT CONSTRAINT: 10 Hours Total, Review at Hour 1

Given the compressed timeline, the VS Code/MCP integration described in §2.5 is
**cut entirely** for this build. Deliverable = standalone Python demo: custom demo
agent + firewall core + plain web dashboard. No VS Code extension, no MCP server, no
real-Copilot integration in this version.

### Team roles (fixed ownership throughout)
- **Person A — Agent & Tools:** demo agent loop, real tool functions, sample repo
  content, running/logging test scenarios
- **Person B — Firewall Core:** extraction, storage, matching, validation logic —
  the actual technical claim of the project
- **Person C — Interface & Demo:** dashboard (backend + frontend), demo narrative,
  rehearsal, judge Q&A prep

### Phase-by-phase plan

**Hour 0–1: Review-ready slice**
Goal: something visibly running for the 1-hour review, even if rough — no polished
UI required yet.
- A: 2–3 real tool functions (`grep_search`, `read_file`) against one small
  hardcoded sample file (~30 lines, auth-style code). Baseline agent loop with
  tool-use working.
- B: Minimal fact store (plain Python dict is fine at this stage). One extraction
  prompt, tested once against real tool output.
- C: Proxy function tying A + B together — check dict for a match → LLM router call
  → print "✅ avoided call, used fact: ..." or run real tool + store new fact.
  Prepare 60-second verbal architecture explanation for the reviewer.
- **What to say at review:** be explicit this is the working core loop; UI and
  full storage are next. Reviewers respond better to "the hard part works, polish is
  next" than to something that looks finished but is faked underneath.

**Hour 1–4: Harden the core loop**
- A: Expand sample content to 2–3 files (a few real facts to extract, not just
  one). Add a second, differently-worded follow-up question to demonstrate semantic
  reuse (not just exact repeats).
- B: Move storage from dict → SQLite (`store.py`). Add whole-file-hash validity
  check (`validator.py`) — skip line-range precision entirely.
- C: Tune the matcher (`matcher.py`) against 4–5 test questions — this is the
  highest false-positive risk area, so it gets real time here.

**Hour 4–7: Dashboard**
- A: Run the full agent+firewall loop against 2–3 scripted scenarios repeatedly;
  log real numbers (calls avoided vs. executed) for later use in the pitch.
- B: Stand up minimal FastAPI server (`/api/stats`, `/api/facts`).
- C: Build plain HTML dashboard (stats bar, facts list, activity feed) polling
  those endpoints. No fancy styling needed.

**Hour 7–9: Test, measure, cut scope as needed**
All three: run the full stack end-to-end 3–4 times, fix flaky parts. Cut order if
behind schedule: (1) drop manual invalidate button, (2) drop on/off toggle, (3) drop
any second demo scenario beyond one reliable one. Record final honest numbers
(calls avoided/executed, rough time/cost saved) — need at least one real statistic
to say out loud.

**Hour 9–10: Demo prep**
All three: run the final demo script twice, timed. Assign roles — one drives the
keyboard, one narrates, one is on standby for technical Q&A. Prepare a fallback
(screen recording of a working run) in case live demo breaks.

### Cut-scope reminders
- No VS Code extension, no MCP server, no real Copilot integration in this version.
- No line-range hashing — whole file only.
- No embedding-based matching — LLM-as-router only.
- If asked about future integration, answer from §2.5 (it's a verified, real plan,
  just not built yet) rather than implying it already works.

---

## 5. Demo Script (for whatever time slot is available)

1. **Hook (short):** "AI coding agents re-investigate the same facts about a
   codebase over and over. We built a firewall that gives them memory."
2. **Live run 1 — baseline:** Run the agent without Work Firewall on a task (e.g.,
   "explain the authentication flow"). Note the tool-call count.
3. **Live run 2 — with firewall:** Run a related, differently-worded follow-up with
   Work Firewall on. Dashboard shows facts already known, calls avoided in real
   time.
4. **The numbers:** State your real measured savings (calls avoided vs. executed).
5. **How it works, briefly:** One sentence on fact extraction, one sentence on
   invalidation (the "not just caching" point).
6. **Honest limitation:** "Fact quality depends on extraction quality — our
   validity check ties every reused fact back to unchanged code, so we're never
   confidently wrong on stale code, just occasionally redoing work we didn't need
   to."

---

## 6. What a Future Session Should Know

If you're picking this up mid-build or after a gap:
- Check which phase (per §4) was last completed and what's in the actual codebase
  vs. what's still just planned here.
- Don't reintroduce VS Code/MCP work unless the time budget has genuinely expanded
  — it was cut deliberately for the 10-hour version, not forgotten.
- The full, uncompressed 36-hour version of this plan (with VS Code integration
  included) exists in earlier project history if the timeline changes — ask for it
  to be reconstituted if more time becomes available.
- Preserve the honest-answers list in §2.6 — these are pre-thought responses to the
  most likely tough questions and shouldn't be improvised from scratch under
  pressure.
