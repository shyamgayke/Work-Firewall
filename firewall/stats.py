# ============================================================
# firewall/stats.py  — shared stats module
# Tracks avoided vs executed calls. Dashboard reads this.
# ============================================================

import time

_session_start = time.time()

_avoided: list[dict] = []
_executed: list[dict] = []


def record_avoided(call_label: str, fact: dict):
    _avoided.append({"call": call_label, "fact_id": fact["id"], "ts": time.time()})


def record_executed(call_label: str, new_fact: dict | None):
    _executed.append(
        {
            "call": call_label,
            "new_fact_id": new_fact["id"] if new_fact else None,
            "ts": time.time(),
        }
    )


def get_summary() -> dict:
    return {
        "total_calls": len(_avoided) + len(_executed),
        "avoided": len(_avoided),
        "executed": len(_executed),
        "avoidance_rate": (
            round(len(_avoided) / (len(_avoided) + len(_executed)) * 100, 1)
            if (_avoided or _executed)
            else 0.0
        ),
        "session_seconds": round(time.time() - _session_start, 1),
        "avoided_log": _avoided,
        "executed_log": _executed,
    }


def reset():
    _avoided.clear()
    _executed.clear()
