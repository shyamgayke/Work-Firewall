# ============================================================
# firewall/proxy.py  — Person C's file
#
# The Work Firewall intercept layer.
# Sits between the agent and the real tools.
# On every tool call:
#   1. Ask the LLM matcher if any stored fact already answers it.
#   2. YES → return the fact, print "✅ avoided"
#   3. NO  → run the real tool, extract a new fact, store it, print "🔧 executed"
# ============================================================

import os
import time
from typing import Any

from openai import OpenAI

# -- Person B's modules (imported once they exist) --
from firewall.store import store_fact, get_all_facts, hash_file
from firewall.extractor import extract_fact

# -- Person A's tool registry --
from tools.real_tools import TOOL_REGISTRY

# -- Dashboard stats (written here so the dashboard can read them) --
import firewall.stats as stats

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------------------------------------------------------------------------
# LLM Matcher prompt
# ---------------------------------------------------------------------------
MATCHER_PROMPT = """You are a router for an AI tool-call firewall.
Your job: decide if any of the stored facts below already answers the incoming tool request,
so we can skip re-running the tool.

Stored facts:
{facts_block}

Incoming tool call:
  Tool: {tool_name}
  Args: {tool_args}
  Question being investigated: {question}

Reply in EXACTLY this format — no other text:
MATCH: <fact_id>
or
NO_MATCH

If any fact clearly covers what this tool call would discover, output MATCH with its id.
If there is any doubt, output NO_MATCH. Prefer false negatives over false positives."""


def _format_facts(facts: list[dict]) -> str:
    if not facts:
        return "(none)"
    lines = []
    for f in facts:
        lines.append(f"[{f['id']}] {f['statement']}  (source: {f['source_tool_call']})")
    return "\n".join(lines)


def _check_validity(fact: dict) -> bool:
    """
    Return True if every file the fact depends on is unchanged (hash still matches).
    If a file is missing or changed → fact is stale → don't reuse it.
    """
    for filepath, stored_hash in fact.get("content_hashes", {}).items():
        current_hash = hash_file(filepath)
        if current_hash != stored_hash:
            return False
    return True


# ---------------------------------------------------------------------------
# Core intercept function — this is what the agent calls instead of tools
# ---------------------------------------------------------------------------
def intercept(
    tool_name: str,
    tool_args: dict[str, Any],
    question: str = "",          # optional: the agent's natural-language question
    sample_repo_dir: str = None, # used to resolve relative file paths for hashing
) -> str:
    """
    Main entry point for the Work Firewall.

    Args:
        tool_name:       name of the tool the agent wants to call (e.g. "grep_search")
        tool_args:       kwargs dict for that tool (e.g. {"pattern": "jwt"})
        question:        the agent's current investigation question (helps the matcher)
        sample_repo_dir: absolute path to the sample repo root (for file hashing)

    Returns:
        The tool output (either from the fact store or from running the real tool).
    """

    call_label = f"{tool_name}({tool_args})"

    # ── 1. Get valid facts ──────────────────────────────────────────────────
    all_facts = get_all_facts()
    valid_facts = [f for f in all_facts if _check_validity(f)]

    # ── 2. Ask the LLM matcher ──────────────────────────────────────────────
    matched_fact = None

    if valid_facts:
        facts_block = _format_facts(valid_facts)
        prompt = MATCHER_PROMPT.format(
            facts_block=facts_block,
            tool_name=tool_name,
            tool_args=tool_args,
            question=question or "(not specified)",
        )

        t0 = time.time()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=30,
        )
        matcher_latency = time.time() - t0

        decision = response.choices[0].message.content.strip()

        if decision.startswith("MATCH:"):
            try:
                fact_id = int(decision.split(":")[1].strip())
                matched_fact = next((f for f in valid_facts if f["id"] == fact_id), None)
            except (ValueError, IndexError):
                matched_fact = None

    # ── 3a. HIT — return from fact store ────────────────────────────────────
    if matched_fact:
        print(
            f"\n✅  AVOIDED  [{call_label}]\n"
            f"    Reusing fact #{matched_fact['id']}: {matched_fact['statement']}\n"
        )
        stats.record_avoided(call_label, matched_fact)
        return f"[FIREWALL - FACT REUSED]\n{matched_fact['statement']}"

    # ── 3b. MISS — run the real tool ─────────────────────────────────────────
    if tool_name not in TOOL_REGISTRY:
        error_msg = f"[FIREWALL ERROR] Unknown tool: '{tool_name}'"
        print(f"\n❌  {error_msg}\n")
        return error_msg

    print(f"\n🔧  EXECUTING  [{call_label}]  (no matching fact found)\n")
    t0 = time.time()
    raw_output = TOOL_REGISTRY[tool_name](**tool_args)
    tool_latency = time.time() - t0

    print(f"    → Tool returned in {tool_latency:.2f}s")

    # ── 4. Extract a fact from the output ────────────────────────────────────
    fact_statement = extract_fact(tool_name, tool_args, raw_output)

    if fact_statement:
        # Resolve file paths for hashing (best-effort)
        files_to_hash = []
        if sample_repo_dir:
            # heuristic: any .py filenames mentioned in the output
            import re
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
        print(f"    → Stored new fact #{new_fact['id']}: {fact_statement}\n")
        stats.record_executed(call_label, new_fact)
    else:
        print("    → No extractable fact from this output.\n")
        stats.record_executed(call_label, None)

    return raw_output
