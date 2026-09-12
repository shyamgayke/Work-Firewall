#!/usr/bin/env python3
"""
run_all.py — Work Firewall Master Launcher

Starts:
1. Maxim AI Bifrost Gateway (http://localhost:8080)
2. Work Firewall Dashboard Server (http://localhost:8000)
3. Runs the Demo Agent comparison (optional or interactive)

Usage:
  python run_all.py          → launch services and start demo
  python run_all.py --server → launch services only
  python run_all.py --demo   → run comparison demo directly
"""

import sys
import os
import time
import subprocess
import urllib.request
import argparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BIFROST_URL = "http://localhost:8080"
DASHBOARD_URL = "http://localhost:8000"


def is_service_ready(url: str, path: str = "/") -> bool:
    try:
        req = urllib.request.urlopen(f"{url.rstrip('/')}{path}", timeout=1)
        return req.getcode() in [200, 404]
    except Exception:
        return False


def start_bifrost():
    if is_service_ready(BIFROST_URL, "/health"):
        print("  [✓] Maxim AI Bifrost Gateway is already running on http://localhost:8080")
        return None

    print("  [⏳] Starting Maxim AI Bifrost Gateway on port 8080...")
    proc = subprocess.Popen(
        ["npx", "-y", "@maximhq/bifrost", "-port", "8080"],
        cwd=ROOT_DIR,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(15):
        time.sleep(1)
        if is_service_ready(BIFROST_URL, "/health"):
            print("  [✓] Maxim AI Bifrost Gateway started on http://localhost:8080")
            return proc
    print("  [!] Bifrost startup timeout; continuing with fallback backends.")
    return proc


def start_dashboard():
    if is_service_ready(DASHBOARD_URL, "/api/stats"):
        print("  [✓] Work Firewall Dashboard is already running on http://localhost:8000")
        return None

    print("  [⏳] Starting Work Firewall Dashboard on port 8000...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "dashboard.server:app", "--port", "8000"],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(10):
        time.sleep(0.8)
        if is_service_ready(DASHBOARD_URL, "/api/stats"):
            print("  [✓] Work Firewall Dashboard started on http://localhost:8000")
            return proc
    print("  [!] Dashboard server startup timeout.")
    return proc


def main():
    parser = argparse.ArgumentParser(description="Work Firewall Master Launcher")
    parser.add_argument("--server", action="store_true", help="Launch servers only")
    parser.add_argument("--demo", action="store_true", help="Run comparison demo directly")
    args = parser.parse_args()

    print("\n" + "═" * 65)
    print("  🛡️  WORK FIREWALL — AI Coding Agent Intelligence Middleware")
    print("  Integrated with Maxim AI Bifrost Gateway & VS Code Extension")
    print("═" * 65 + "\n")

    bifrost_proc = start_bifrost()
    dash_proc = start_dashboard()

    print("\n  📍 System Endpoints:")
    print(f"     • Web Dashboard  : {DASHBOARD_URL}")
    print(f"     • Bifrost Gateway: {BIFROST_URL}")
    print("     • MCP Server     : python mcp_server/server.py")
    print("     • VS Code Ext    : vscode-extension/work-firewall-1.0.0.vsix")

    if args.server:
        print("\n  Servers running in background. Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            if bifrost_proc:
                bifrost_proc.terminate()
            if dash_proc:
                dash_proc.terminate()
        return

    print("\n  🚀 Running Comparison Demo: Baseline vs Work Firewall...\n")
    from agent.demo_agent import BASELINE_TASKS, FIREWALL_TASKS, run_scenario, print_comparison
    from firewall.store import clear_facts

    base = run_scenario(BASELINE_TASKS, firewall_enabled=False, mode_label="BASELINE", reset_store=True)
    clear_facts()
    seed = run_scenario(BASELINE_TASKS, firewall_enabled=True, mode_label="SEED (building institutional memory)", reset_store=False)
    fw = run_scenario(FIREWALL_TASKS, firewall_enabled=True, mode_label="FIREWALL ACTIVE", reset_store=False)
    print_comparison(base, fw)

    print("  🎉 Demo finished! Open the Dashboard at http://localhost:8000 to inspect facts and metrics.")


if __name__ == "__main__":
    main()
