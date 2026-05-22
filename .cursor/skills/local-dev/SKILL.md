---
name: local-dev
description: >-
  Set up wincher-mcp locally: Python venv, dependencies, WINCHER_API_KEY,
  and MCP stdio config (Cursor or Claude Code). Use when installing,
  debugging connection issues, or smoke-testing tools.
---

# Local development (wincher-mcp)

## Prerequisites

- Python **3.10+**
- Wincher account with a **Personal Access Token**
- **Cursor**, **Claude Code**, or another MCP-capable client

## Step 1 — Virtual environment

From repo root (`wincher-mcp`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

End users can skip the clone: `pipx install wincher-mcp` (see [docs/PYPI.md](../../../docs/PYPI.md)).

## Step 2 — API key

```bash
cp .env.example .env
# Edit .env: WINCHER_API_KEY=...
export WINCHER_API_KEY='...'   # for shell smoke tests
```

Never commit `.env`.

## Step 3 — MCP client config

Template: [docs/MCP_CONFIG.example.json](../../../docs/MCP_CONFIG.example.json)

### PyPI / pipx (recommended)

```json
{
  "mcpServers": {
    "wincher": {
      "command": "wincher-mcp",
      "args": [],
      "env": {
        "WINCHER_API_KEY": "paste_key_here"
      }
    }
  }
}
```

### From a clone (development)

```json
{
  "mcpServers": {
    "wincher": {
      "command": "/ABSOLUTE/PATH/TO/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/wincher-mcp/wincher_mcp_server.py"],
      "env": {
        "WINCHER_API_KEY": "paste_key_here"
      }
    }
  }
}
```

**Where to put it:**

| Client | Config file |
|--------|-------------|
| **Cursor** | `~/.cursor/mcp.json` or project `.cursor/mcp.json` |
| **Claude Code** | `~/.claude.json` or project `.mcp.json` |

**Staging (optional):** add `"--use-staging"` to `args`. In `env`, set `WINCHER_API_KEY` and `WINCHER_STAGING_API_HOST` on your machine only (never commit the host).

**TOON (optional):** add `"--use-toon"` to `args` for compact responses.

Use **absolute paths** for clone-based installs. Restart the MCP client fully after edits.

**Claude desktop app (optional):** same JSON under `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows).

## Step 4 — Cursor MCP

Same JSON as above in Cursor MCP settings for this workspace. Prefer env var for the key rather than hardcoding in tracked files.

## Step 5 — Smoke test

With `WINCHER_API_KEY` set:

```bash
python -c "
import asyncio, os
os.environ.setdefault('WINCHER_API_KEY', os.environ.get('WINCHER_API_KEY',''))
from wincher_mcp.server import make_wincher_request
async def t():
    r = await make_wincher_request('/v1/websites')
    print('sites:', len(r.get('data', [])))
asyncio.run(t())
"
```

If this fails with 401, fix the key before debugging MCP wiring.

In the client chat: *"List my Wincher websites"* (`get_websites`).

## Troubleshooting

| Symptom | Check |
|---------|--------|
| MCP server not listed | Paths absolute (clone)? `wincher-mcp` on PATH (pipx)? Client restarted? |
| `WINCHER_API_KEY not set` | `env` block in MCP config |
| Empty website list | Wincher account has tracked sites |
| HTTP 4xx on tools | Token permissions, correct `website_id` |

## References

- [docs/SETUP.md](../../../docs/SETUP.md)
- [README.md](../../../README.md)
- [AGENTS.md](../../../AGENTS.md)
