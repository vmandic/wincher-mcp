# Wincher API spec (vendored)

Offline copy of the official OpenAPI document shown at [wincher.com/docs/api](https://www.wincher.com/docs/api).

| File | Purpose |
|------|---------|
| `wincher-openapi.json` | OpenAPI 3.0 spec (paths, schemas, operations) |
| `META.json` | `fetched_at`, `source_chunk_sha256`, and fetch provenance |

Production base URL in the spec: `https://api.wincher.com/v1`. Staging hosts are not stored in this repo.

## Refresh

```bash
python3 scripts/fetch_wincher_openapi.py
```

Check whether live docs changed without writing files:

```bash
python3 scripts/fetch_wincher_openapi.py --check
```

Or use the Cursor skill [.cursor/skills/update-api-spec/SKILL.md](../../.cursor/skills/update-api-spec/SKILL.md).

CI runs `pytest` and `pip-audit` on every push/PR; a weekly job runs `--check` to detect upstream docs drift.

After updating, review the git diff and commit if the spec changed.
