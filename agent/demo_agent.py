# ============================================================
# agent/demo_agent.py  — Person A's file
# A minimal agent loop that uses Work Firewall intercept().
# Person A: expand this with more questions and scenarios.
# ============================================================

import os
import sys

# Ensure utf-8 stdout on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Make sure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from firewall.proxy import intercept
from firewall.store import clear_facts
import firewall.stats as stats

SAMPLE_REPO_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "sample_repo")
)

# ---------------------------------------------------------------------------
# Demo scenario: two questions that overlap — second should be AVOIDED
# ---------------------------------------------------------------------------
def run_demo():
    clear_facts()
    stats.reset()

    print("=" * 60)
    print("  Work Firewall — Demo Run")
    print("=" * 60)

    # Question 1: first time — should EXECUTE and store a fact
    print("\n[Agent] Q1: Where is JWT validation happening?")
    result1 = intercept(
        tool_name="grep_search",
        tool_args={"pattern": "jwt"},
        question="Where is JWT validation happening?",
        sample_repo_dir=SAMPLE_REPO_DIR,
    )
    print(f"  Output: {result1[:200]}...\n" if len(result1) > 200 else f"  Output: {result1}\n")

    # Question 2: differently worded — should AVOID and reuse fact
    print("\n[Agent] Q2: Which file handles JSON web token verification?")
    result2 = intercept(
        tool_name="grep_search",
        tool_args={"pattern": "verify_token"},
        question="Which file handles JSON web token verification?",
        sample_repo_dir=SAMPLE_REPO_DIR,
    )
    print(f"  Output: {result2[:200]}...\n" if len(result2) > 200 else f"  Output: {result2}\n")

    # Question 3: new topic — should EXECUTE
    print("\n[Agent] Q3: How is the database connection established?")
    result3 = intercept(
        tool_name="grep_search",
        tool_args={"pattern": "database|db_connect|sqlite"},
        question="How is the database connection established?",
        sample_repo_dir=SAMPLE_REPO_DIR,
    )
    print(f"  Output: {result3[:200]}...\n" if len(result3) > 200 else f"  Output: {result3}\n")

    # ── Final stats ─────────────────────────────────────────────────────────
    summary = stats.get_summary()
    print("\n" + "=" * 60)
    print("  SESSION SUMMARY")
    print("=" * 60)
    print(f"  Total tool calls intercepted : {summary['total_calls']}")
    print(f"  ✅ Avoided (fact reused)      : {summary['avoided']}")
    print(f"  🔧 Executed (real tool ran)   : {summary['executed']}")
    print(f"  Avoidance rate               : {summary['avoidance_rate']}%")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
