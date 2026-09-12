# ============================================================
# firewall/stats.py — Session statistics + cost estimation
# ============================================================

import time

_session_start = time.time()
_avoided: list[dict] = []
_executed: list[dict] = []

# Rough cost estimate: $0.0001 per avoided tool call (1 LLM call saved)
COST_PER_TOOL_CALL_USD = 0.0001
# Rough latency saved per avoided call (median tool call time)
LATENCY_SAVED_PER_CALL_S = 1.2


def record_avoided(call_label: str, fact: dict, latency_saved_s: float = LATENCY_SAVED_PER_CALL_S):
    _avoided.append({
        "call": call_label,
        "fact_id": fact["id"],
        "fact_statement": fact["statement"],
        "ts": time.time(),
        "latency_saved_s": latency_saved_s,
    })


def record_executed(call_label: str, new_fact: dict | None, tool_latency_s: float = 0.0):
    _executed.append({
        "call": call_label,
        "new_fact_id": new_fact["id"] if new_fact else None,
        "ts": time.time(),
        "tool_latency_s": tool_latency_s,
    })


def get_summary() -> dict:
    total = len(_avoided) + len(_executed)
    total_latency_saved = sum(e.get("latency_saved_s", 0) for e in _avoided)
    total_cost_saved = len(_avoided) * COST_PER_TOOL_CALL_USD

    return {
        "total_calls": total,
        "avoided": len(_avoided),
        "executed": len(_executed),
        "avoidance_rate": round(len(_avoided) / total * 100, 1) if total > 0 else 0.0,
        "latency_saved_s": round(total_latency_saved, 2),
        "cost_saved_usd": round(total_cost_saved, 4),
        "session_seconds": round(time.time() - _session_start, 1),
        "avoided_log": _avoided[-20:],    # last 20 for dashboard
        "executed_log": _executed[-20:],
    }


def reset():
    global _session_start
    _session_start = time.time()
    _avoided.clear()
    _executed.clear()
