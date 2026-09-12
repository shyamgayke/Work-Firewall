# ============================================================
# firewall/matcher.py  — Person B/C shared file
#
# HOUR 0-1: Logic lives inside proxy.py directly.
# HOUR 1-4: Person C moves and refines the matcher here.
#            Person B can tune prompts and add scoring.
# ============================================================

import os
from firewall.llm import get_llm_config

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


def format_facts(facts: list[dict]) -> str:
    if not facts:
        return "(none)"
    return "\n".join(
        f"[{f['id']}] {f['statement']}  (source: {f['source_tool_call']})"
        for f in facts
    )


def find_matching_fact(
    tool_name: str,
    tool_args: dict,
    question: str,
    valid_facts: list[dict],
) -> dict | None:
    """
    Ask the LLM if any stored fact already answers this tool call.
    Returns the matching fact dict, or None if no match.

    Person B/C: tune the prompt, model, and temperature here.
    Test against at least 4-5 question pairs before Hour 4.
    """
    if not valid_facts:
        return None

    client, model_name = get_llm_config()

    if client is None:
        # Fallback offline heuristic if no API key is set
        q_lower = (question or "").lower()
        pattern = str(tool_args.get("pattern", "")).lower()
        for f in valid_facts:
            stmt = f["statement"].lower()
            if (pattern and pattern in stmt) or (
                ("jwt" in q_lower or "token" in q_lower) and ("jwt" in stmt or "token" in stmt)
            ):
                return f
        return None

    prompt = MATCHER_PROMPT.format(
        facts_block=format_facts(valid_facts),
        tool_name=tool_name,
        tool_args=tool_args,
        question=question or "(not specified)",
    )

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=30,
        )

        decision = response.choices[0].message.content.strip()

        if decision.startswith("MATCH:"):
            try:
                fact_id = int(decision.split(":")[1].strip())
                return next((f for f in valid_facts if f["id"] == fact_id), None)
            except (ValueError, IndexError):
                return None
    except Exception as e:
        print(f"    [Matcher warning] LLM call failed: {e}")
        return None

    return None
