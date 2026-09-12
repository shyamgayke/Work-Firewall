# ============================================================
# firewall/proxy.py — Work Firewall intercept layer
#
# Flow for every tool call:
#   1. Filter facts by validity (SHA-256 hash check)
#   2. Ask LLM matcher if any fact answers the request
#   3a. HIT  → return fact, log "avoided"
#   3b. MISS → run real tool → extract fact → store → log "executed"
# ============================================================

import os
import sys
import time
import re
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from firewall.llm import llm_chat
from firewall.store import store_fact, get_all_facts, push_avoided, push_executed
from firewall.validator import filter_valid_facts
from firewall.extractor import extract_fact
from tools.real_tools import TOOL_REGISTRY
import firewall.stats as stats

# ---------------------------------------------------------------------------
# Matcher
# ---------------------------------------------------------------------------

MATCHER_PROMPT = """You are a router for a code-investigation firewall.
Decide if any stored fact already answers the incoming tool call.

Stored facts:
{facts_block}

Incoming request:
  Tool : {tool_name}
  Args : {tool_args}
  Question: {question}

Reply in EXACTLY one of these two formats, no other text:
  MATCH: <fact_id>
  NO_MATCH

Rules:
- MATCH only if the fact clearly contains the answer the tool call would produce.
- Prefer NO_MATCH if unsure — a false negative just costs one extra tool call.
- Do NOT match on superficial word overlap; match on actual knowledge coverage."""


def _format_facts(facts: list[dict]) -> str:
    if not facts:
        return "(none)"
    return "\n".join(
        f"[{f['id']}] {f['statement']}  (from: {f['source_tool_call']})"
        for f in facts
    )


def _llm_match(tool_name: str, tool_args: dict, question: str, valid_facts: list[dict]) -> dict | None:
    """Run the LLM matcher. Returns matched fact dict or None."""
    if not valid_facts:
        return None

    prompt = MATCHER_PROMPT.format(
        facts_block=_format_facts(valid_facts),
        tool_name=tool_name,
        tool_args=tool_args,
        question=question or "(not specified)",
    )

    result = llm_chat(prompt, max_tokens=200)
    if not result:
        return None

    m = re.search(r"MATCH:\s*(\d+)", result)
    if m:
        fact_id = int(m.group(1))
        return next((f for f in valid_facts if f["id"] == fact_id), None)
    return None


def _keyword_match(tool_args: dict, question: str, valid_facts: list[dict]) -> dict | None:
    """Offline keyword-based fallback matcher."""
    q_lower = (question or "").lower()
    pattern = str(tool_args.get("pattern", "")).lower()
    filepath = str(tool_args.get("filepath", "")).lower()

    for f in valid_facts:
        stmt = f["statement"].lower()
        if pattern and pattern in stmt:
            return f
        if filepath and filepath in stmt:
            return f
        # Topic-level keyword matching
        for kw in ["jwt", "token", "auth", "database", "sqlite", "password", "hash"]:
            if kw in q_lower and kw in stmt:
                return f
    return None


# ---------------------------------------------------------------------------
# Core intercept function
# ---------------------------------------------------------------------------

def intercept(
    tool_name: str,
    tool_args: dict[str, Any],
    question: str = "",
    sample_repo_dir: str = None,
    firewall_enabled: bool = True,
) -> str:
    """
    Main Work Firewall entry point.

    Args:
        tool_name:        tool to call (e.g. "grep_search")
        tool_args:        kwargs for the tool
        question:         agent's natural-language question (helps matcher)
        sample_repo_dir:  absolute path to repo root (for file hashing)
        firewall_enabled: set False to bypass firewall (baseline mode)

    Returns:
        Tool output string (from fact store or real tool)
    """
    call_label = f"{tool_name}({tool_args})"

    # ── BYPASS MODE (baseline demo) ─────────────────────────────────────────
    if not firewall_enabled:
        if tool_name not in TOOL_REGISTRY:
            return f"[ERROR] Unknown tool: '{tool_name}'"
        t0 = time.time()
        output = TOOL_REGISTRY[tool_name](**tool_args)
        stats.record_executed(call_label, None, time.time() - t0)
        return output

    # ── 1. Get valid (non-stale) facts ──────────────────────────────────────
    all_facts = get_all_facts()
    valid_facts = filter_valid_facts(all_facts)

    # ── 2. Match ─────────────────────────────────────────────────────────────
    matched_fact = _llm_match(tool_name, tool_args, question, valid_facts)

    # Offline keyword fallback if LLM didn't match (also catches rate limits)
    if not matched_fact:
        matched_fact = _keyword_match(tool_args, question, valid_facts)

    # ── 3a. HIT ──────────────────────────────────────────────────────────────
    if matched_fact:
        print(
            f"\n✅  AVOIDED  [{call_label}]\n"
            f"    Reusing fact #{matched_fact['id']}: {matched_fact['statement']}\n"
        )
        stats.record_avoided(call_label, matched_fact)
        push_avoided(call_label, matched_fact)
        return f"[FIREWALL — FACT REUSED]\n{matched_fact['statement']}"

    # ── 3b. MISS: run real tool ───────────────────────────────────────────────
    if tool_name not in TOOL_REGISTRY:
        return f"[FIREWALL ERROR] Unknown tool: '{tool_name}'"

    print(f"\n🔧  EXECUTING  [{call_label}]")
    t0 = time.time()
    raw_output = TOOL_REGISTRY[tool_name](**tool_args)
    tool_latency = time.time() - t0
    print(f"    → returned in {tool_latency:.2f}s")

    # ── 4. Extract + store ───────────────────────────────────────────────────
    fact_statement = extract_fact(tool_name, tool_args, raw_output)

    new_fact = None
    if fact_statement:
        files_to_hash = []
        if sample_repo_dir:
            mentioned = re.findall(r"[\w/\\]+\.py", raw_output)
            for rel in mentioned:
                abs_path = os.path.join(sample_repo_dir, os.path.basename(rel))
                if os.path.exists(abs_path):
                    files_to_hash.append(abs_path)

        new_fact = store_fact(
            statement=fact_statement,
            files=files_to_hash,
            source_tool_call=call_label,
            raw_output=raw_output,
        )
        print(f"    → Stored fact #{new_fact['id']}: {fact_statement}\n")

    stats.record_executed(call_label, new_fact, tool_latency)
    push_executed(call_label, new_fact)
    return raw_output


def query_firewall(prompt: str, repo_dir: str = None) -> dict:
    """
    High-level natural language query entry point.
    Checks similarity against all valid facts. If matched, reuses fact (AVOIDED).
    If not, executes tool, extracts fact, stores it, and returns result (EXECUTED).
    """
    if not repo_dir:
        repo_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_repo")

    all_facts = get_all_facts()
    valid_facts = filter_valid_facts(all_facts)

    # Check similarity against stored facts
    matched = _llm_match(
        tool_name="natural_query",
        tool_args={"prompt": prompt},
        question=prompt,
        valid_facts=valid_facts,
    )
    if not matched:
        matched = _keyword_match(tool_args={"pattern": prompt}, question=prompt, valid_facts=valid_facts)

    if matched:
        call_label = f"query('{prompt[:40]}...')"
        stats.record_avoided(call_label, matched)
        push_avoided(call_label, matched)
        return {
            "status": "avoided",
            "matched": True,
            "fact": matched,
            "statement": matched["statement"],
            "files": matched.get("files", []),
            "source": matched.get("source_tool_call", ""),
            "message": f"⚡ Work Firewall memory hit! Reused Fact #{matched['id']}: {matched['statement']}"
        }

    # If not matched, deduce tool to run based on prompt keywords
    p_lower = prompt.lower()
    if "jwt" in p_lower or "token" in p_lower:
        tool_name = "grep_search"
        tool_args = {"pattern": "jwt", "directory": repo_dir}
    elif "password" in p_lower or "hash" in p_lower or "bcrypt" in p_lower:
        tool_name = "grep_search"
        tool_args = {"pattern": "bcrypt|hash_password|hashpw", "directory": repo_dir}
    elif "db" in p_lower or "database" in p_lower or "sql" in p_lower:
        tool_name = "grep_search"
        tool_args = {"pattern": "sqlite|database|db", "directory": repo_dir}
    elif "list" in p_lower or ("file" in p_lower and "structure" in p_lower):
        tool_name = "list_files"
        tool_args = {"directory": repo_dir}
    elif "auth" in p_lower:
        tool_name = "read_file"
        tool_args = {"filepath": os.path.join(repo_dir, "auth.py")}
    else:
        words = [w for w in re.findall(r"\w+", p_lower) if len(w) > 3]
        term = words[0] if words else "def"
        tool_name = "grep_search"
        tool_args = {"pattern": term, "directory": repo_dir}

    raw_output = intercept(
        tool_name=tool_name,
        tool_args=tool_args,
        question=prompt,
        sample_repo_dir=repo_dir,
        firewall_enabled=True,
    )

    latest_facts = get_all_facts()
    latest = latest_facts[0] if latest_facts else None

    return {
        "status": "executed",
        "matched": False,
        "fact": latest,
        "statement": latest["statement"] if latest else f"Investigated with {tool_name}",
        "files": latest.get("files", []) if latest else [],
        "source": f"{tool_name}({tool_args})",
        "raw_output": raw_output[:300],
        "message": f"🔧 Executed {tool_name} and discovered new institutional fact: {latest['statement'] if latest else raw_output[:100]}"
    }

