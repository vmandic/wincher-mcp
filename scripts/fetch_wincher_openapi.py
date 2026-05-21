#!/usr/bin/env python3
"""Fetch the Wincher OpenAPI spec embedded in https://www.wincher.com/docs/api."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DOCS_PAGE = "https://www.wincher.com/docs/api"
CHUNK_PATTERN = re.compile(r"pages/docs/api-[a-f0-9]+\.js")
USER_AGENT = "wincher-mcp-spec-fetch/1.0 (+https://github.com/vmandic/wincher-mcp)"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "docs" / "api"
SPEC_PATH = OUT_DIR / "wincher-openapi.json"
META_PATH = OUT_DIR / "META.json"


def http_get(url: str, timeout: float = 60.0) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def discover_chunk_url(html: str) -> str:
    match = CHUNK_PATTERN.search(html)
    if not match:
        raise RuntimeError(
            "Could not find pages/docs/api-*.js chunk in docs page HTML. "
            "Wincher may have changed their docs build."
        )
    return f"https://www.wincher.com/_next/static/chunks/{match.group(0)}"


def unescape_js_single_quoted(raw: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch != "\\" or i + 1 >= len(raw):
            out.append(ch)
            i += 1
            continue
        nxt = raw[i + 1]
        if nxt == "n":
            out.append("\n")
        elif nxt == "t":
            out.append("\t")
        elif nxt == "r":
            out.append("\r")
        elif nxt in ("\\", "'", '"'):
            out.append(nxt)
        elif nxt == "u" and i + 5 < len(raw):
            out.append(chr(int(raw[i + 2 : i + 6], 16)))
            i += 5
        else:
            out.append(nxt)
        i += 2
    return "".join(out)


def _repair_string(text: str) -> str:
    """Fix lone surrogates from split \\uXXXX sequences in the docs bundle."""
    try:
        return text.encode("utf-16", "surrogatepass").decode("utf-16")
    except UnicodeDecodeError:
        return text.encode("utf-8", "surrogatepass").decode("utf-8", "replace")


def _repair_obj(value):
    if isinstance(value, str):
        return _repair_string(value)
    if isinstance(value, list):
        return [_repair_obj(item) for item in value]
    if isinstance(value, dict):
        return {k: _repair_obj(v) for k, v in value.items()}
    return value


def extract_openapi_from_chunk(js: str) -> dict:
    marker = "JSON.parse('"
    idx = js.find(marker)
    if idx < 0:
        raise RuntimeError("OpenAPI JSON.parse('...') block not found in docs chunk.")
    start = idx + len(marker)
    i = start
    escaped = False
    while i < len(js):
        ch = js[i]
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "'":
            break
        i += 1
    else:
        raise RuntimeError("Unterminated JSON.parse string in docs chunk.")
    spec = json.loads(unescape_js_single_quoted(js[start:i]))
    return _repair_obj(spec)


def sha256_hex(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_existing_meta() -> dict | None:
    if not META_PATH.exists():
        return None
    return json.loads(META_PATH.read_text(encoding="utf-8"))


def write_outputs(spec: dict, chunk_url: str, chunk_sha256: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SPEC_PATH.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_page": DOCS_PAGE,
        "source_chunk": chunk_url,
        "source_chunk_sha256": chunk_sha256,
        "openapi_version": spec.get("openapi"),
        "api_title": (spec.get("info") or {}).get("title"),
        "path_count": len(spec.get("paths") or {}),
        "production_server": "https://api.wincher.com/v1",
    }
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def fetch_live() -> tuple[dict, str, str, str]:
    html = http_get(DOCS_PAGE)
    chunk_url = discover_chunk_url(html)
    js = http_get(chunk_url)
    chunk_hash = sha256_hex(js)
    spec = extract_openapi_from_chunk(js)
    return spec, chunk_url, chunk_hash


def check_chunk_unchanged() -> int:
    """Exit 0 if live docs chunk hash matches vendored META.json."""
    previous = load_existing_meta()
    if not previous or not previous.get("source_chunk_sha256"):
        print(
            "error: META.json missing source_chunk_sha256; run fetch without --check",
            file=sys.stderr,
        )
        return 1
    try:
        _, _, live_hash = fetch_live()
    except (HTTPError, URLError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    expected = previous["source_chunk_sha256"]
    if live_hash != expected:
        print(
            "chunk changed: live docs bundle differs from vendored META.json\n"
            f"  expected: {expected}\n"
            f"  live:     {live_hash}\n"
            "  run: python3 scripts/fetch_wincher_openapi.py",
            file=sys.stderr,
        )
        return 1

    print("chunk unchanged (source_chunk_sha256 matches)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify live docs chunk SHA-256 matches META.json (no write)",
    )
    args = parser.parse_args()

    if args.check:
        return check_chunk_unchanged()

    try:
        spec, chunk_url, chunk_hash = fetch_live()
        previous = load_existing_meta()
        if previous and previous.get("source_chunk_sha256") and previous["source_chunk_sha256"] != chunk_hash:
            print(
                f"note: docs chunk changed ({previous['source_chunk_sha256'][:12]}… -> {chunk_hash[:12]}…)",
                file=sys.stderr,
            )
        write_outputs(spec, chunk_url, chunk_hash)
    except (HTTPError, URLError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {SPEC_PATH.relative_to(REPO_ROOT)}")
    print(f"wrote {META_PATH.relative_to(REPO_ROOT)}")
    with META_PATH.open(encoding="utf-8") as f:
        meta = json.load(f)
    print(
        f"fetched_at={meta['fetched_at']} paths={meta['path_count']} "
        f"chunk_sha256={meta['source_chunk_sha256'][:12]}…"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
