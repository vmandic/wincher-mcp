"""TOON output format tests for wincher_mcp_server."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / "wincher_mcp_server.py"


def load_server_module(*, argv_extra: list[str] | None = None):
    import sys

    saved = sys.argv[:]
    try:
        sys.argv = ["wincher_mcp_server.py", *(argv_extra or [])]
        spec = importlib.util.spec_from_file_location("wincher_mcp_server", SERVER_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.argv = saved


@pytest.fixture
def w():
    return load_server_module()


@pytest.fixture
def w_toon():
    return load_server_module(argv_extra=["--use-toon"])


class TestResolveOutputFormat:
    def test_default_text(self, w):
        assert w._resolve_output_format({}) == "text"

    def test_global_toon_flag(self, w_toon):
        assert w_toon._resolve_output_format({}) == "toon"

    def test_per_call_toon(self, w):
        assert w._resolve_output_format({"output_format": "toon"}) == "toon"

    def test_per_call_text_overrides_global(self, w_toon):
        assert w_toon._resolve_output_format({"output_format": "text"}) == "text"

    def test_rejects_invalid(self, w):
        with pytest.raises(ValueError, match="output_format"):
            w._resolve_output_format({"output_format": "yaml"})


class TestRenderToolOutput:
    def test_text_mode_unchanged_style(self, w):
        out = w._render_tool_output(
            output_format="text",
            title="Title:\n\n",
            items=[{"id": 1}],
            text_formatter=lambda item: f"ID: {item['id']}\n",
            label="items",
            meta={"tool": "get_websites"},
        )
        assert out.startswith("Title:")
        assert "ID: 1" in out
        assert "Format: TOON" not in out

    def test_toon_mode_includes_preamble_and_tabular_body(self, w):
        items = [
            {"id": 1, "keyword": "alpha", "position": 3},
            {"id": 2, "keyword": "beta", "position": 8},
        ]
        out = w._render_tool_output(
            output_format="toon",
            title="Keywords:\n\n",
            items=items,
            text_formatter=lambda _: "",
            label="keywords",
            meta={"tool": "get_keywords", "website_id": 9},
        )
        assert w._TOON_PREAMBLE.splitlines()[0] in out
        assert "meta:" in out or "tool: get_keywords" in out
        assert "data[2" in out or "data[2,]" in out
        assert "alpha" in out

    def test_toon_truncation_meta(self, w):
        items = list(range(w.MAX_FORMAT_ROWS + 5))
        out = w._render_tool_output(
            output_format="toon",
            title="Items:\n\n",
            items=items,
            text_formatter=lambda n: f"{n}\n",
            label="items",
            meta={"tool": "test"},
        )
        assert "truncated: true" in out
        assert f"total: {w.MAX_FORMAT_ROWS + 5}" in out
