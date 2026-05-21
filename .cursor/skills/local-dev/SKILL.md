---
name: local-dev
description: >-
  Set up wincher-mcp locally: Python venv, dependencies, WINCHER_API_KEY,
  and Claude Desktop (or Cursor) MCP stdio config. Use when installing,
  debugging connection issues, or smoke-testing tools.
---

# Local development (wincher-mcp)

## Prerequisites

- Python **3.10+**
- Wincher account with a **Personal Access Token**
- Claude Desktop or Cursor with MCP support

## Step 1 — Virtual environment

From repo root (`wincher-mcp`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m py_compile wincher_mcp_server.py
```

Use `.venv` or `wincher-mcp-env` consistently; document the path you choose in MCP config.

## Step 2 — API key

```bash
cp .env.example .env
# Edit .env: WINCHER_API_KEY=...
export WINCHER_API_KEY='...'   # for shell smoke tests
```

Never commit `.env`.

## Step 3 — Claude Desktop config (macOS)

File: `~/Library/Application Support/Claude/claude_desktop_config.json`

Template: [docs/MCP_CONFIG.example.json](../../../docs/MCP_CONFIG.example.json)

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

**Staging (optional):** add `"--use-staging"` to `args` (not `env`). In `env`, set only `WINCHER_API_KEY` and `WINCHER_STAGING_API_HOST` on your machine. Get the host from Wincher internally; do not add it to this repo, docs, or commits.

Use **absolute paths**. Restart Claude Desktop fully after edits.

Windows: `%APPDATA%\Claude\claude_desktop_config.json`

## Step 4 — Cursor MCP

Same `command`, `args`, and `env` as above in Cursor MCP settings for this workspace. Prefer env var for the key rather than hardcoding in tracked files.

## Step 5 — Smoke test

With `WINCHER_API_KEY` set:

```bash
python -c "
import asyncio, os
os.environ.setdefault('WINCHER_API_KEY', os.environ.get('WINCHER_API_KEY',''))
import wincher_mcp_server as s
async def t():
    r = await s.make_wincher_request('/v1/websites')
    print('sites:', len(r.get('data', [])))
asyncio.run(t())
"
```

If this fails with 401, fix the key before debugging MCP wiring.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| MCP server not listed | Paths absolute? Claude restarted? |
| `WINCHER_API_KEY not set` | `env` block in MCP config |
| Empty website list | Wincher account has tracked sites |
| HTTP 4xx on tools | Token permissions, correct `website_id` |

## References

- [docs/SETUP.md](../../../docs/SETUP.md)
- [README.md](../../../README.md)
- [AGENTS.md](../../../AGENTS.md)
