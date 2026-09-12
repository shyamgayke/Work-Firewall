#!/usr/bin/env python3
"""
agent/demo_agent.py — Work Firewall Demo Agent

Modes:
  python -m agent.demo_agent --mode=baseline  → firewall OFF, every call executes
  python -m agent.demo_agent --mode=firewall  → firewall ON, shows avoidance in action
  python -m agent.demo_agent --mode=compare   → runs both and prints comparison table
  python -m agent.demo_agent                  → interactive mode selector

Usage for demo:
  Step 1: python -m agent.demo_agent --mode=baseline
  Step 2: python -m agent.demo_agent --mode=firewall
  Note the dramatic difference in ✅ AVOIDED vs 🔧 EXECUTING counts.
"""

import sys
import os
import time
import argparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firewall.proxy import intercept
from firewall.store import clear_facts
import firewall.stats as stats

SAMPLE_REPO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_repo")

# ---------------------------------------------------------------------------
# Investigation scenarios
# ---------------------------------------------------------------------------
# Each task has:
#   - name:     short display label
#   - tool:     real tool name
#   - args:     tool arguments
#   - question: natural-language question (helps matcher)
#
# IMPORTANT: "baseline" and "firewall" have equivalent intent but different phrasing
#   so the LLM matcher must use semantic understanding, not exact string match.

BASELINE_TASKS = [
    {
        "name": "1. Where is JWT validated?",
        "tool": "grep_search",
        "args": {"pattern": "jwt", "directory": SAMPLE_REPO},
        "question": "Where is JWT validation implemented?",
    },
    {
        "name": "2. What does auth.py contain?",
        "tool": "read_file",
        "args": {"filepath": os.path.join(SAMPLE_REPO, "auth.py")},
        "question": "What is in the authentication module?",
    },
    {
        "name": "3. What files exist in the repo?",
        "tool": "list_files",
        "args": {"directory": SAMPLE_REPO},
        "question": "What files make up this codebase?",
    },
    {
        "name": "4. Where is password hashing done?",
        "tool": "grep_search",
        "args": {"pattern": "bcrypt|hash_password|hashpw", "directory": SAMPLE_REPO},
        "question": "Where is password hashing implemented?",
    },
    {
        "name": "5. What database operations exist?",
        "tool": "grep_search",
        "args": {"pattern": "sqlite|database|db", "directory": SAMPLE_REPO},
        "question": "What database-related code exists?",
    },
    {
        "name": "6. How is auth.py structured?",
        "tool": "read_file",
        "args": {"filepath": os.path.join(SAMPLE_REPO, "auth.py")},
        "question": "Show me the structure of the auth module.",
    },
]

# Firewall tasks — same intent, differently phrased → should be AVOIDED
FIREWALL_TASKS = [
    {
        "name": "1. Token validation location?",
        "tool": "grep_search",
        "args": {"pattern": "jwt", "directory": SAMPLE_REPO},
        "question": "Where in the code is the token signature verified?",
    },
    {
        "name": "2. Read the authentication file",
        "tool": "read_file",
        "args": {"filepath": os.path.join(SAMPLE_REPO, "auth.py")},
        "question": "I need to understand the authentication implementation.",
    },
    {
        "name": "3. List project source files",
        "tool": "list_files",
        "args": {"directory": SAMPLE_REPO},
        "question": "Give me an overview of the repository structure.",
    },
    {
        "name": "4. Password security implementation?",
        "tool": "grep_search",
        "args": {"pattern": "bcrypt|hash_password|hashpw", "directory": SAMPLE_REPO},
        "question": "How is the system securing stored passwords?",
    },
    {
        "name": "5. Any SQL or database usage?",
        "tool": "grep_search",
        "args": {"pattern": "sqlite|database|db", "directory": SAMPLE_REPO},
        "question": "Does this codebase use a database?",
    },
    {
        "name": "6. Inspect auth module functions",
        "tool": "read_file",
        "args": {"filepath": os.path.join(SAMPLE_REPO, "auth.py")},
        "question": "What functions are defined in the authentication module?",
    },
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def header(title: str):
    line = "═" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}\n")


def run_scenario(
    tasks: list[dict],
    firewall_enabled: bool,
    mode_label: str,
    reset_store: bool = False,
) -> dict:
    stats.reset()
    if reset_store:
        clear_facts()   # fresh store for demo

    header(f"Work Firewall Demo — {mode_label}")
    t0 = time.time()

    for task in tasks:
        print(f"  ─ {task['name']}")
        intercept(
            tool_name=task["tool"],
            tool_args=task["args"],
            question=task["question"],
            sample_repo_dir=SAMPLE_REPO,
            firewall_enabled=firewall_enabled,
        )
        time.sleep(0.1)  # slight pause for readability

    elapsed = time.time() - t0
    summary = stats.get_summary()
    summary["wall_seconds"] = round(elapsed, 2)
    return summary


def print_summary(s: dict, label: str):
    print(f"\n  📊 {label} Summary")
    print(f"     Total calls : {s['total_calls']}")
    print(f"     Executed    : {s['executed']}")
    print(f"     Avoided     : {s['avoided']}")
    print(f"     Avoidance   : {s['avoidance_rate']}%")
    print(f"     Latency svd : {s['latency_saved_s']}s")
    print(f"     Cost saved  : ${s['cost_saved_usd']:.4f}")
    print(f"     Wall time   : {s['wall_seconds']}s")


def print_comparison(base: dict, fw: dict):
    header("🏆 COMPARISON — Baseline vs Work Firewall")
    items = [
        ("Total calls",      base["total_calls"],      fw["total_calls"]),
        ("Executed",         base["executed"],          fw["executed"]),
        ("Avoided",          base["avoided"],           fw["avoided"]),
        ("Avoidance rate",   f"{base['avoidance_rate']}%",  f"{fw['avoidance_rate']}%"),
        ("Latency saved",    f"{base['latency_saved_s']}s", f"{fw['latency_saved_s']}s"),
        ("Cost saved",       f"${base['cost_saved_usd']:.4f}", f"${fw['cost_saved_usd']:.4f}"),
        ("Wall time",        f"{base['wall_seconds']}s",      f"{fw['wall_seconds']}s"),
    ]
    col = 20
    print(f"  {'Metric':<{col}} {'Baseline':>12}  {'Firewall':>12}")
    print(f"  {'─'*col} {'─'*12}  {'─'*12}")
    for name, bv, fv in items:
        print(f"  {name:<{col}} {str(bv):>12}  {str(fv):>12}")

    if fw["avoided"] > 0:
        print(f"\n  ✅ Work Firewall avoided {fw['avoided']}/{fw['total_calls']} tool calls")
        print(f"     That's {fw['avoidance_rate']}% fewer redundant investigations!")
    print()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Work Firewall Demo Agent")
    parser.add_argument(
        "--mode",
        choices=["baseline", "firewall", "compare", "interactive"],
        default="interactive",
        help="Demo mode",
    )
    args = parser.parse_args()

    mode = args.mode
    if mode == "interactive":
        print("\nWork Firewall Demo Agent")
        print("  1. baseline  — firewall OFF (all calls execute)")
        print("  2. firewall  — firewall ON  (shows avoidance)")
        print("  3. compare   — runs both, shows comparison table")
        choice = input("\nSelect mode [1/2/3]: ").strip()
        mode = {"1": "baseline", "2": "firewall", "3": "compare"}.get(choice, "firewall")

    if mode == "baseline":
        s = run_scenario(BASELINE_TASKS, firewall_enabled=False, mode_label="BASELINE (No Firewall)", reset_store=True)
        print_summary(s, "Baseline")

    elif mode == "firewall":
        clear_facts()
        # Pre-populate with one baseline run so matcher has facts to work with
        print("  [Pre-run: seeding fact store with baseline investigation…]")
        run_scenario(BASELINE_TASKS, firewall_enabled=True, mode_label="BASELINE SEED (building memory)", reset_store=False)
        print("\n  [Now running firewall scenario with differently-worded questions…]")
        time.sleep(0.5)
        s = run_scenario(FIREWALL_TASKS, firewall_enabled=True, mode_label="FIREWALL ACTIVE", reset_store=False)
        print_summary(s, "Firewall")

    elif mode == "compare":
        base = run_scenario(BASELINE_TASKS, firewall_enabled=False, mode_label="BASELINE", reset_store=True)
        clear_facts()
        # Seed the store, then run firewall scenario
        seed = run_scenario(BASELINE_TASKS, firewall_enabled=True, mode_label="SEED (building memory)", reset_store=False)
        fw = run_scenario(FIREWALL_TASKS, firewall_enabled=True, mode_label="FIREWALL", reset_store=False)
        print_comparison(base, fw)


if __name__ == "__main__":
    main()
