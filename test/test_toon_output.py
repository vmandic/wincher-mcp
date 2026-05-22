"""TOON output format tests for wincher_mcp."""

from __future__ import annotations

import pytest


class TestResolveOutputFormat:
    def test_default_text(self, server_module):
        w = server_module
        assert w._resolve_output_format({}) == "text"

    def test_global_toon_flag(self, server_module_toon):
        w = server_module_toon
        assert w._resolve_output_format({}) == "toon"

    def test_per_call_toon(self, server_module):
        w = server_module
        assert w._resolve_output_format({"output_format": "toon"}) == "toon"

    def test_per_call_text_overrides_global(self, server_module_toon):
        w = server_module_toon
        assert w._resolve_output_format({"output_format": "text"}) == "text"

    def test_rejects_invalid(self, server_module):
        w = server_module
        with pytest.raises(ValueError, match="output_format"):
            w._resolve_output_format({"output_format": "yaml"})


class TestRenderToolOutput:
    def test_text_mode_unchanged_style(self, server_module):
        w = server_module
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

    def test_toon_mode_includes_preamble_and_tabular_body(self, server_module):
        w = server_module
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

    def test_toon_truncation_meta(self, server_module):
        w = server_module
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
