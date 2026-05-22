"""Shared fixtures for wincher_mcp tests."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator

import pytest


@pytest.fixture()
def server_module() -> Iterator:
    """Import server with a clean sys.argv (no --use-staging / --use-toon)."""
    saved = sys.argv[:]
    try:
        sys.argv = ["wincher-mcp"]
        import wincher_mcp.server as mod

        yield importlib.reload(mod)
    finally:
        sys.argv = saved


@pytest.fixture()
def server_module_toon() -> Iterator:
    """Import server with --use-toon enabled at module load."""
    saved = sys.argv[:]
    try:
        sys.argv = ["wincher-mcp", "--use-toon"]
        import wincher_mcp.server as mod

        yield importlib.reload(mod)
    finally:
        sys.argv = saved
