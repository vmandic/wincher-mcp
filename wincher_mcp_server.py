"""Backward-compatible launcher for MCP configs that reference wincher_mcp_server.py.

Prefer the PyPI console script: wincher-mcp
Or: python -m wincher_mcp
"""

from wincher_mcp.server import cli

if __name__ == "__main__":
    cli()
