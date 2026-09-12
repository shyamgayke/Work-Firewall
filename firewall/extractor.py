# ============================================================
# firewall/extractor.py  — Person B's file
# Turns raw tool output into a structured fact statement.
# ============================================================

import os
from firewall.llm import get_llm_config

EXTRACTION_PROMPT = """You are a code-knowledge extractor for an AI tool-call firewall.

Given the output of a tool call, extract a single concise factual statement that captures
the key insight discovered. This statement will be stored and reused to avoid re-running
the same investigation later.

Rules:
- Be specific: include file names, line numbers, function names if present in the output.
- Be self-contained: the statement must make sense without the raw output.
- One sentence only. No bullet points.
- If the output is empty or uninformative, return exactly: NO_FACT

Tool called: {tool_name}
Tool arguments: {tool_args}
Tool output:
---
{tool_output}
---

Extracted fact (one sentence):"""


def extract_fact(tool_name: str, tool_args: dict, tool_output: str) -> str | None:
    """
    Ask the LLM to extract a structured fact from a tool's raw output.
    Returns the fact string, or None if no meaningful fact could be extracted.
    Person B: tune the prompt and model as needed.
    """
    client, model_name = get_llm_config()

    if client is None:
        # Fallback offline extraction heuristic if no API key is provided
        lines = [line.strip() for line in tool_output.strip().split("\n") if line.strip()]
        if not lines or "No matches found" in tool_output:
            return None
        return f"{tool_name} with {tool_args} discovered: {lines[0]}"

    prompt = EXTRACTION_PROMPT.format(
        tool_name=tool_name,
        tool_args=tool_args,
        tool_output=tool_output[:3000],  # cap to avoid token blowout
    )

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=120,
        )

        result = response.choices[0].message.content.strip()
        if result == "NO_FACT" or not result:
            return None
        return result
    except Exception as e:
        print(f"    [Extractor warning] LLM call failed: {e}")
        # Graceful fallback to avoid halting demo
        lines = [l.strip() for l in tool_output.split("\n") if l.strip()]
        return f"{tool_name} found: {lines[0]}" if lines else None
