"""Tests for scripts/fetch_wincher_openapi.py (no network)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FETCH_SCRIPT = REPO_ROOT / "scripts" / "fetch_wincher_openapi.py"
META_PATH = REPO_ROOT / "docs" / "api" / "META.json"


def load_fetch_module():
    spec = importlib.util.spec_from_file_location("fetch_wincher_openapi", FETCH_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def fetch():
    return load_fetch_module()


SAMPLE_HTML = """
<script src="/_next/static/chunks/pages/docs/api-deadbeef12345678.js"></script>
"""


class TestDiscoverChunk:
    def test_finds_chunk_path(self, fetch):
        url = fetch.discover_chunk_url(SAMPLE_HTML)
        assert url.endswith("pages/docs/api-deadbeef12345678.js")

    def test_missing_chunk_raises(self, fetch):
        with pytest.raises(RuntimeError, match="Could not find"):
            fetch.discover_chunk_url("<html></html>")


class TestChunkSha256:
    def test_hash_stable(self, fetch):
        content = "sample-chunk-content"
        digest = fetch.sha256_hex(content)
        assert digest == hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert len(digest) == 64


class TestVendoredMeta:
    def test_meta_has_chunk_sha256(self):
        if not META_PATH.exists():
            pytest.skip("META.json not generated yet")
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        assert meta.get("source_chunk_sha256")
        assert len(meta["source_chunk_sha256"]) == 64
