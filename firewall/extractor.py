# ============================================================
# firewall/extractor.py — Tool output → structured fact
# ============================================================

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from firewall.llm import llm_chat

EXTRACTION_PROMPT = """You are a code-knowledge extractor for an AI tool-call firewall.

Given the output of a tool call, extract a SINGLE concise factual statement that captures
the key insight discovered. This statement will be stored and reused to avoid re-running
the same investigation later.

Rules:
- Be specific: include file names, line numbers, function names if visible in the output.
- Be self-contained: the statement must make sense without seeing the raw output.
- One sentence only. No bullet points, no markdown.
- If the output is empty, "no results", or clearly uninformative, return exactly: NO_FACT

Tool: {tool_name}
Args: {tool_args}
Output:
---
{tool_output}
---

Extracted fact (one sentence):"""


def extract_fact(tool_name: str, tool_args: dict, tool_output: str) -> str | None:
    """
    Ask the LLM to extract a structured fact from a tool's raw output.
    Returns the fact string, or None if no meaningful fact found.
    """
    if not tool_output or "No matches found" in tool_output or "File not found" in tool_output:
        return None

    prompt = EXTRACTION_PROMPT.format(
        tool_name=tool_name,
        tool_args=tool_args,
        tool_output=tool_output[:3000],
    )

    result = llm_chat(prompt, max_tokens=500)

    if result is None:
        # Offline fallback heuristic
        lines = [l.strip() for l in tool_output.split("\n") if l.strip()]
        return f"{tool_name} with {tool_args} discovered: {lines[0]}" if lines else None

    if result.strip().upper() == "NO_FACT" or not result.strip():
        return None

    return result.strip()
