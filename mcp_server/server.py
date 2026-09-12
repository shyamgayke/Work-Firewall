#!/usr/bin/env python3
# ============================================================
# mcp_server/server.py — Work Firewall MCP Server (MCP 2.x)
#
# A Model Context Protocol server that wraps Work Firewall's
# interception layer. VS Code Copilot and Claude Desktop
# connect to this server and call search_code / read_file / list_files
# — all of which pass through proxy.intercept() first!
# ============================================================

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.mcpserver import MCPServer
from firewall.proxy import intercept
from firewall import stats

REPO_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_repo")

app = MCPServer("work-firewall")


@app.tool(
    name="search_code",
    description="Search for a pattern across source files. Work Firewall intercepts and reuses facts.",
)
def search_code(pattern: str, directory: str = "", question: str = "") -> str:
    search_dir = directory if directory else REPO_ROOT
    tool_args = {"pattern": pattern, "directory": search_dir}
    return intercept(
        "grep_search",
        tool_args,
        question=question,
        sample_repo_dir=REPO_ROOT,
    )


@app.tool(
    name="read_file",
    description="Read the contents of a source file. Work Firewall intercepts and reuses facts.",
)
def read_file(filepath: str, question: str = "") -> str:
    target_path = filepath if os.path.isabs(filepath) else os.path.join(REPO_ROOT, filepath)
    tool_args = {"filepath": target_path}
    return intercept(
        "read_file",
        tool_args,
        question=question,
        sample_repo_dir=REPO_ROOT,
    )


@app.tool(
    name="list_files",
    description="List files in a directory. Work Firewall intercepts and reuses facts.",
)
def list_files(directory: str = "", question: str = "") -> str:
    target_dir = directory if directory else REPO_ROOT
    tool_args = {"directory": target_dir}
    return intercept(
        "list_files",
        tool_args,
        question=question,
        sample_repo_dir=REPO_ROOT,
    )


@app.tool(
    name="get_firewall_stats",
    description="Get Work Firewall statistics: calls avoided, cost saved, avoidance rate.",
)
def get_firewall_stats() -> str:
    summary = stats.get_summary()
    return json.dumps(summary, indent=2)


if __name__ == "__main__":
    app.run(transport="stdio")
