# ============================================================
# dashboard/server.py  — Person C's file (Hour 4-7)
#
# FastAPI dashboard backend.
# Exposes /api/stats and /api/facts for the HTML frontend.
#
# HOUR 0-1: Not needed yet — stub file so Person C can start it later.
# HOUR 4-7: Implement the endpoints and run with:
#            uvicorn dashboard.server:app --reload --port 8000
# ============================================================

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

import firewall.stats as stats
from firewall.store import get_all_facts

app = FastAPI(title="Work Firewall Dashboard")

# Serve the static HTML dashboard
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    """Serve the dashboard HTML."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/stats")
def get_stats():
    """Return session statistics: total calls, avoided, executed, avoidance rate."""
    return stats.get_summary()


@app.get("/api/facts")
def get_facts():
    """Return all stored facts with their provenance."""
    facts = get_all_facts()
    # Don't send raw_output to the frontend — keep it light
    return [
        {
            "id": f["id"],
            "statement": f["statement"],
            "files": f["files"],
            "source_tool_call": f["source_tool_call"],
            "created_at": f["created_at"],
        }
        for f in facts
    ]


@app.delete("/api/facts/{fact_id}")
def invalidate_fact(fact_id: int):
    """
    Manually invalidate a fact (e.g., if the human inspector spots a wrong fact).
    TODO (Person C, Hour 4-7): implement manual deletion in store.py.
    """
    return {"status": "not_implemented_yet", "fact_id": fact_id}


# TODO (Person C, Hour 4-7):
# - Add POST /api/reset to reset the session stats (useful between demo runs)
# - Add the manual invalidation endpoint above
# - Run with: uvicorn dashboard.server:app --reload --port 8000
