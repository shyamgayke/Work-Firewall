"""
dashboard/server.py — Work Firewall FastAPI dashboard backend

Endpoints:
  GET  /               → serve dashboard HTML
  GET  /api/stats      → session statistics + cost/latency savings
  GET  /api/facts      → all stored facts with validity status
  GET  /api/activity   → last 50 activity events (newest first)
  POST /api/facts/{id}/invalidate → manually delete a fact
  POST /api/reset      → reset session stats + clear all facts
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

import firewall.stats as stats
from firewall.store import get_all_facts, delete_fact, clear_facts, get_activity_log
from firewall.validator import is_fact_valid

app = FastAPI(title="Work Firewall Dashboard", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, encoding="utf-8") as f:
        return f.read()


@app.get("/api/stats")
async def get_stats():
    return stats.get_summary()


@app.get("/api/facts")
async def get_facts():
    all_facts = get_all_facts()
    result = []
    for f in all_facts:
        entry = dict(f)
        entry["is_valid"] = is_fact_valid(f)
        result.append(entry)
    return {"facts": result, "total": len(result)}


@app.get("/api/activity")
async def get_activity():
    return {"events": get_activity_log()}


@app.post("/api/facts/{fact_id}/invalidate")
async def invalidate_fact(fact_id: int):
    deleted = delete_fact(fact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Fact {fact_id} not found")
    return {"success": True, "deleted_id": fact_id}


from pydantic import BaseModel
from firewall.proxy import query_firewall

class QueryRequest(BaseModel):
    prompt: str = ""
    question: str = ""

@app.post("/api/query")
async def handle_query(req: QueryRequest):
    p = req.prompt or req.question
    if not p:
        raise HTTPException(status_code=400, detail="Missing prompt or question")
    return query_firewall(p)

@app.post("/api/reset")
async def reset_session():
    clear_facts()
    stats.reset()
    return {"success": True, "message": "Session reset: all facts cleared, stats zeroed"}
