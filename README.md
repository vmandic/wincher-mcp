# Wincher MCP

[![CI](https://github.com/vmandic/wincher-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/vmandic/wincher-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-6366f1)](https://modelcontextprotocol.io)

**Read-only [Wincher](https://www.wincher.com) SEO data for AI coding agents.**  
Connect Cursor, Claude Code, or any MCP client to your tracked websites: keyword rankings, competitors, SERPs, and groups, without leaving the editor.

- **Read-only by design** — GET-style Wincher API usage only; no writes to your account
- **Stdio MCP** — local process spawned by the client; no HTTP listener
- **Nine focused tools** — websites, keywords, rankings, competitors, SERPs, groups, bulk history, annotations
- **Hardened defaults** — input limits, response caps, safe errors, optional staging host validation
- **Optional TOON output** — compact [Token-Oriented Object Notation](https://github.com/toon-format/toon) responses to cut LLM token use on large keyword and ranking lists

Maintained fork of [chris-tutt/wincher-mcp-server](https://github.com/chris-tutt/wincher-mcp-server) with agent docs, CI, vendored OpenAPI, and security hardening.

---

## Table of contents

- [Why use this](#why-use-this)
- [Features](#features)
- [Quick start](#quick-start)
- [Requirements](#requirements)
- [Installation](#installation)
- [Authentication](#authentication)
- [Connect your MCP client](#connect-your-mcp-client)
- [Tools reference](#tools-reference)
- [Example prompts for agents](#example-prompts-for-agents)
- [Security](#security)
- [API reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Upstream and license](#upstream-and-license)

---

## Why use this

Wincher holds the keyword and competitor data SEO workflows depend on. This server exposes that data through the [Model Context Protocol](https://modelcontextprotocol.io) so agents can answer questions in chat instead of exporting CSVs or clicking through dashboards.

Use it when you want:

- Website and keyword lists inside an agent session
- Competitor and SERP context for a target query
- A **small, auditable** tool surface (nine read-only tools)

---

## Features

| Capability | MCP tool |
|------------|----------|
| List tracked websites | `get_websites` |
| Keywords and current rankings | `get_keywords` |
| Historical ranking series | `get_keyword_rankings` |
| Competitor summary metrics | `get_competitor_ranking_summaries` |
| Competitor positions per keyword | `get_competitor_keyword_positions` |
| SERP snapshot and features | `get_serps` |
| Keyword group aggregates | `get_keyword_groups` |
| Bulk ranking history | `get_bulk_ranking_history` |
| SEO annotations / notes | `get_annotations` |

**Input validation** — Positive integer IDs, bounded bulk lists, validated date strings where applicable.

**Clear errors** — HTTP failures return endpoint and status without leaking full URLs, tokens, or raw API bodies.

---

## Quick start

### Agentic install prompt

Paste into **Cursor, Claude Code, or Copilot** and ask the agent to run setup on your machine.

**Assumptions (confirm before changing anything):**

| Assumption | Why it matters |
|------------|----------------|
| **Python 3.10+** | Required to run `wincher_mcp_server.py` |
| **Wincher account** | Personal Access Token from Wincher settings |
| **Stdio MCP** | Config uses `command` + `args`; no HTTP transport |
| **Absolute paths** | MCP config must point at real `.venv/bin/python` and `wincher_mcp_server.py` |
| **Secrets off-repo** | `WINCHER_API_KEY` in MCP `env` or `~/.zsh_secrets`, never committed |

```
Set up the wincher-mcp MCP server from https://github.com/vmandic/wincher-mcp on this machine end-to-end.

Before you change anything, confirm with me:
1) Which MCP client I use (Cursor, Claude Code, or VS Code Copilot).
2) Where to clone the repo (default: ~/source/vmandic/wincher-mcp).

Then:

A) Prerequisites — Python 3.10+, no secrets in git.
B) Clone, venv, test — git clone, python3 -m venv .venv, pip install -r requirements.txt -r requirements-dev.txt, pytest -q, py_compile wincher_mcp_server.py.
C) Wincher token — I create a Personal Access Token in Wincher; add WINCHER_API_KEY to MCP env (or ~/.zsh_secrets if using a wrapper script).
D) MCP config — stdio: command = ABSOLUTE_PATH/.venv/bin/python, args = [ABSOLUTE_PATH/wincher_mcp_server.py], env = { WINCHER_API_KEY }. See docs/MCP_CONFIG.example.json. Do not commit real keys or staging hosts.
E) Verify — restart MCP client, call get_websites, report results or auth errors.

Summarize: clone path, config file edited, and exact JSON used.
```

### Manual setup

**1. Clone and install**

```bash
git clone https://github.com/vmandic/wincher-mcp.git
cd wincher-mcp
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. API key** — Wincher → Settings → [Personal Access Tokens](https://www.wincher.com). Copy the token once; store it only in env or a local secrets file.

**3. MCP client** — example for **Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "wincher-mcp": {
      "command": "/absolute/path/to/wincher-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/wincher-mcp/wincher_mcp_server.py"],
      "env": {
        "WINCHER_API_KEY": "YOUR_KEY_HERE"
      }
    }
  }
}
```

See [docs/MCP_CONFIG.example.json](docs/MCP_CONFIG.example.json) for production, optional staging, and TOON entries.

**4. Restart the client**, then ask: *“List my Wincher websites”* (`get_websites`).

Full walkthrough: [docs/SETUP.md](docs/SETUP.md). More prompts: [docs/EXAMPLES.md](docs/EXAMPLES.md).

---

## Requirements

| Requirement | Notes |
|-------------|--------|
| **Python** | 3.10 or newer (CI tests 3.10–3.12) |
| **Wincher account** | With API access and tracked sites/keywords |
| **API token** | Personal Access Token; env var `WINCHER_API_KEY` |
| **MCP client** | Cursor, Claude Code, or any stdio MCP host |

---

## Installation

### From PyPI (recommended)

```bash
pipx install wincher-mcp
# or: pip install wincher-mcp
```

MCP config then uses the console script (no clone path):

```json
{
  "mcpServers": {
    "wincher": {
      "command": "wincher-mcp",
      "args": [],
      "env": { "WINCHER_API_KEY": "YOUR_KEY_HERE" }
    }
  }
}
```

Find the binary path if needed: `pipx which wincher-mcp`.

Package: [pypi.org/project/wincher-mcp](https://pypi.org/project/wincher-mcp/). **Publishing:** [docs/PYPI.md](docs/PYPI.md).

### From a clone (development)

```bash
git clone https://github.com/vmandic/wincher-mcp.git
cd wincher-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Legacy launcher `wincher_mcp_server.py` at repo root still works for existing MCP JSON paths.

### Virtual environment name

Use `.venv` (as in CI) or **pipx** for MCP hosts. Update MCP config `command` accordingly.

---

## Authentication

The server never stores tokens on disk. It reads **`WINCHER_API_KEY`** from the process environment (set in MCP `env` or exported in the shell).

| What | Purpose |
|------|---------|
| **Personal Access Token** | Bearer auth to `https://api.wincher.com` (production) |
| **Optional staging** | MCP arg `"--use-staging"` plus env `WINCHER_STAGING_API_HOST` on your machine only |

Production API host is **hardcoded** in the server. The staging host must **never** be committed to this repository.

Obtain staging URLs from your Wincher team; wire them only in private MCP config. See [docs/MCP_CONFIG.example.json](docs/MCP_CONFIG.example.json) (`wincher-staging` has no host in the example).

### Optional TOON responses (lower token use)

[TOON](https://github.com/toon-format/toon) is a compact encoding for structured data sent to LLMs. Tabular Wincher payloads (keywords, competitors, bulk history) often use **30–60% fewer tokens** than the default human-readable text layout.

| Mode | How |
|------|-----|
| **Server default TOON** | Add `"--use-toon"` to the MCP server `args` array (see `wincher-toon` in [docs/MCP_CONFIG.example.json](docs/MCP_CONFIG.example.json)) |
| **Per call** | Pass `"output_format": "toon"` on any tool (or `"text"` to force readable text when `--use-toon` is on) |

Responses include a short preamble and TOON body. Decode in Python with `python-toon`:

```python
from toon import decode
```

Default remains human-readable **text** when `--use-toon` is not set.

**Wrapper pattern (optional):** a shell script can `source ~/.zsh_secrets` then `exec .venv/bin/python wincher_mcp_server.py` so Cursor opened from the Dock still gets the key. Do not commit that script with secrets inside.

Copy [`.env.example`](.env.example) to `.env` for local shell use only; `.env` is gitignored.

---

## Connect your MCP client

| Client | Config location | Config key |
|--------|-----------------|------------|
| Cursor | `~/.cursor/mcp.json` or project `.cursor/mcp.json` | `mcpServers` |
| Claude Code | `~/.claude.json` or project `.mcp.json` | `mcpServers` |
| VS Code Copilot | `.vscode/mcp.json` | `servers` (stdio) |

The Claude desktop app (if you use it) uses `claude_desktop_config.json` on macOS/Windows with the same `mcpServers` shape; see [docs/SETUP.md](docs/SETUP.md).

All examples use **stdio**: the client spawns Python and talks JSON-RPC over stdin/stdout. Logs and errors go to stderr.

**Project-level MCP:** some repos commit `.cursor/mcp.json` with a `command` pointing at a **local wrapper** (no secrets in JSON). Global user config can hold the same server for all workspaces.

---

## Tools reference

All tools are **read-only**. Parameters use Wincher website/keyword IDs from `get_websites` / `get_keywords`.

| Tool | Main inputs |
|------|-------------|
| `get_websites` | — |
| `get_keywords` | `website_id` |
| `get_keyword_rankings` | `website_id`, `keyword_id`, date range |
| `get_competitor_ranking_summaries` | `website_id` |
| `get_competitor_keyword_positions` | `website_id`, competitor filters |
| `get_serps` | `website_id`, `keyword_id` |
| `get_keyword_groups` | `website_id` |
| `get_bulk_ranking_history` | `website_id`, keyword id list (capped) |
| `get_annotations` | `website_id` |

Field-level detail: vendored [docs/api/wincher-openapi.json](docs/api/wincher-openapi.json) and [Wincher API docs](https://www.wincher.com/docs/api).

---

## Example prompts for agents

- *“List all websites in my Wincher account.”*
- *“For website ID 12345, show keywords in the top 10.”*
- *“Compare our rankings vs competitor X for this site.”*
- *“Show the SERP for keyword ID 67890.”*
- *“Which keyword group has the best average position?”*

---

## Security

This server calls **your** Wincher account using **your** API token. Treat it like any local tool with outbound HTTPS.

### What we enforce in code

| Control | Detail |
|---------|--------|
| **Read-only tools** | No create/update/delete Wincher resources |
| **Stdio only** | No network listener in the server |
| **Production host fixed** | `https://api.wincher.com` in source |
| **Staging URL validation** | HTTPS only; blocks localhost/private/metadata hosts |
| **No redirect following** | `follow_redirects=False` on HTTP client |
| **Bounded inputs/outputs** | ID validation, bulk caps, row limits in formatted responses |
| **Error redaction** | Tool errors avoid tokens and full response bodies |

### What you should do

1. **Never commit** `.env`, real MCP JSON with keys, or `WINCHER_STAGING_API_HOST` values.
2. **Prefer project gitignore** for `.cursor/mcp.json` if it might hold local paths tied to secrets workflow.
3. **Review** [security_best_practices_report.md](security_best_practices_report.md) for the full audit and residual risks (including SSRF if staging env is mis-set).

### Threat model (short)

| Mode | Who can call tools? |
|------|---------------------|
| **stdio** | The MCP client that started the Python process (your IDE / agent host) |

---

## API reference

OpenAPI is vendored from [wincher.com/docs/api](https://www.wincher.com/docs/api):

| File | Role |
|------|------|
| [docs/api/wincher-openapi.json](docs/api/wincher-openapi.json) | Spec snapshot |
| [docs/api/META.json](docs/api/META.json) | `fetched_at`, `source_chunk_sha256` |
| [docs/api/README.md](docs/api/README.md) | Refresh instructions |

Refresh locally:

```bash
python3 scripts/fetch_wincher_openapi.py
```

CI runs a weekly drift check (`scripts/fetch_wincher_openapi.py --check`) against `META.json`.

---

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| **MCP server not listed** | Restart client; check absolute paths to `.venv/bin/python` and `wincher_mcp_server.py`. |
| **`WINCHER_API_KEY` not set** | Add token to MCP `env` or wrapper that sources your secrets file. |
| **HTTP 401** | Regenerate token in Wincher; update env; restart client. |
| **Empty or partial data** | Confirm sites/keywords exist in Wincher UI; check website/keyword IDs. |
| **Staging errors** | Ensure `--use-staging` in `args` and `WINCHER_STAGING_API_HOST` set in `env` (host not in repo). |

Test API key manually:

```bash
curl -sS -H "Authorization: Bearer YOUR_KEY" https://api.wincher.com/v1/websites
```

---

## Development

Every push and pull request to `main` runs [CI](.github/workflows/ci.yml):

| Job | What it does |
|-----|----------------|
| **test** | Python 3.10 / 3.11 / 3.12 — `pip install`, `py_compile`, `pytest`, `pip-audit` |
| **api-spec-check** | Weekly (and on schedule) — verify Wincher docs chunk hash vs `docs/api/META.json` |

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
pip-audit -r requirements.txt -r requirements-dev.txt
python3 scripts/fetch_wincher_openapi.py          # refresh spec
python3 scripts/fetch_wincher_openapi.py --check  # drift check
```

Layout:

```
wincher_mcp_server.py   # MCP entry (stdio)
scripts/                # OpenAPI fetch
docs/api/               # Vendored spec + META
test/                   # pytest (security, fetch script)
.cursor/                # Agent rules and skills
AGENTS.md               # Pointer for coding agents
```

Agents: start with [AGENTS.md](AGENTS.md) and [.cursor/rules/](.cursor/rules/README.md).

Dependabot: [.github/dependabot.yml](.github/dependabot.yml) (pip + GitHub Actions).

---

## Upstream and license

| Item | Link |
|------|------|
| **This fork** | [github.com/vmandic/wincher-mcp](https://github.com/vmandic/wincher-mcp) |
| **Upstream** | [github.com/chris-tutt/wincher-mcp-server](https://github.com/chris-tutt/wincher-mcp-server) |
| **Wincher API** | [wincher.com/docs/api](https://www.wincher.com/docs/api) |
| **MCP SDK** | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) |

[MIT](LICENSE) — see upstream copyright in LICENSE; fork maintenance by [Vedran Mandić](https://github.com/vmandic) and contributors.

Contributions welcome via issues and pull requests. Run `pytest` and `pip-audit` before opening a PR.
