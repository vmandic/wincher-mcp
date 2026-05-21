---
name: update-api-spec
description: >-
  Refresh the vendored Wincher OpenAPI spec from wincher.com/docs/api. Use when
  API docs changed, adding MCP tools, or the user asks to update/sync the API spec.
---

# Update Wincher API spec

Refreshes `docs/api/wincher-openapi.json` and `docs/api/META.json` from the live docs page.

## Run

From repo root:

```bash
python3 scripts/fetch_wincher_openapi.py
```

Check for upstream docs changes (no write):

```bash
python3 scripts/fetch_wincher_openapi.py --check
```

Requires network access. Uses only the Python standard library.

## After fetch

1. Read `docs/api/META.json` for `fetched_at`, `source_chunk_sha256`, and `path_count`.
2. `git diff docs/api/` — confirm changes are expected.
3. If MCP tools were added, cross-check paths in `wincher_mcp_server.py` against `docs/api/wincher-openapi.json`.
4. Commit only when the user asked (include `META.json` timestamp in commit message).

## Source

- Page: https://www.wincher.com/docs/api
- Spec is embedded in the Next.js chunk `pages/docs/api-*.js` (URL discovered automatically).

## Do not

- Commit staging API hosts or tokens.
- Hand-edit `wincher-openapi.json` except for local experiments (prefer re-fetch).

## References

- [docs/api/README.md](../../../docs/api/README.md)
- [architecture.mdc](../../rules/architecture.mdc)
