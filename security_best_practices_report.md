# Security best practices report — wincher-mcp

**Date:** 2026-05-21  
**Scope:** Python MCP stdio server (`wincher_mcp_server.py`), fetch script, docs, dependencies  
**Stack:** Python 3.10+, MCP SDK, httpx (no web server)

## Executive summary

The project has a small attack surface: stdio MCP, outbound HTTPS to Wincher only, secrets in env. The main risks are **SSRF via `WINCHER_STAGING_API_HOST`**, **unbounded tool inputs/outputs** (rate limits and context exhaustion), and **generic error messages** leaking internals. Secret handling and TLS for production are already sound. This report lists findings by severity; fixes marked **implemented** are applied in the same change set.

---

## Critical

None identified for production-only use with trusted MCP config.

---

## High

### SEC-001 — SSRF via staging API host (environment)

| Field | Detail |
|-------|--------|
| **Location** | `wincher_mcp_server.py` — `base_url()` lines 30–38, `wincher_request()` line 73 |
| **Evidence** | `WINCHER_STAGING_API_HOST` is passed directly into `httpx` without scheme/host validation. |
| **Impact** | A malicious or mistaken MCP `env` could point the server at `http://127.0.0.1`, metadata IPs, or internal services. |
| **Fix** | **implemented** — Require HTTPS; block loopback/private/link-local IPs and known metadata hosts; disable HTTP redirects on the client. |

---

## Medium

### SEC-002 — Unbounded `keyword_ids` on bulk history

| Field | Detail |
|-------|--------|
| **Location** | `wincher_mcp_server.py` — `get_bulk_ranking_history` lines 414–427 |
| **Evidence** | No limit on `keyword_ids` array size before POST. |
| **Impact** | Large arrays can exhaust API rate limits (5000/hour per Wincher docs) or produce huge responses. |
| **Fix** | **implemented** — Cap list length (aligned with OpenAPI `maxItems: 1000` elsewhere in spec). |

### SEC-003 — Unbounded formatted API responses to the LLM

| Field | Detail |
|-------|--------|
| **Location** | `wincher_mcp_server.py` — all `call_tool` formatters (e.g. lines 249–272, 282–290) |
| **Evidence** | Full `data` arrays rendered with no row cap. |
| **Impact** | Memory pressure and accidental exfiltration of very large result sets into chat context. |
| **Fix** | **implemented** — `MAX_FORMAT_ROWS` cap with truncation notice. |

### SEC-004 — MCP tool arguments not validated before path construction

| Field | Detail |
|-------|--------|
| **Location** | `wincher_mcp_server.py` — e.g. lines 277, 295–296, 415–418 |
| **Evidence** | `arguments["website_id"]` used without type/range checks; non-integer values produce odd paths. |
| **Impact** | Unexpected API errors; harder to reason about authorization boundaries. |
| **Fix** | **implemented** — `_positive_int()` / `_positive_int_list()` helpers. |

### SEC-005 — Generic exceptions returned to the host

| Field | Detail |
|-------|--------|
| **Location** | `wincher_mcp_server.py` lines 465–466 |
| **Evidence** | `f"Error: {str(e)}"` may include stack-related or environment-specific text. |
| **Impact** | Information disclosure to the LLM session. |
| **Fix** | **implemented** — `ValueError` messages kept; other exceptions return type name only. |

---

## Low

### SEC-006 — Dependency version ranges not upper-bounded

| Field | Detail |
|-------|--------|
| **Location** | `requirements.txt` |
| **Evidence** | `mcp>=1.0.0`, `httpx>=0.27.0` without upper bounds. |
| **Impact** | Future major releases could introduce breaking or unwanted behavior on fresh install. |
| **Fix** | **implemented** — Add compatible upper bounds. |

### SEC-007 — HTTP redirects followed by default

| Field | Detail |
|-------|--------|
| **Location** | `wincher_mcp_server.py` — `httpx.AsyncClient()` |
| **Evidence** | Default `follow_redirects=True` can turn an allowed URL into an internal redirect target. |
| **Impact** | Redirect-based SSRF if staging host is compromised or misconfigured. |
| **Fix** | **implemented** — `follow_redirects=False` on the API client. |

### SEC-008 — Fetch script downloads executable JS from the web

| Field | Detail |
|-------|--------|
| **Location** | `scripts/fetch_wincher_openapi.py` |
| **Evidence** | Pulls and parses Next.js chunk from wincher.com. |
| **Impact** | Supply-chain risk if CDN or page is tampered with; mitigated by reviewing diff on update. |
| **Fix** | Documented; run only on maintainer request; optional future: checksum pin of chunk hash in `META.json`. |

---

## Positive controls already in place

- Production API host hardcoded to `https://api.wincher.com`.
- Staging host not stored in the repository.
- `.env` and `claude_desktop_config.json` gitignored.
- HTTP errors omit full request URL (staging host not leaked).
- API error bodies truncated to 200 characters.
- Stdio-only MCP (no network listener).
- Read-only tools (no mutating Wincher API calls in MCP layer).

---

## Follow-ups (implemented 2026-05-21)

| ID | Item | Status |
|----|------|--------|
| SEC-009 | `test/test_security.py` — validators, caps, HTTP error shape | **Done** |
| SEC-010 | CI: `pytest`, `pip-audit`; Dependabot pip + actions | **Done** |
| SEC-011 | `source_chunk_sha256` in `META.json`; `fetch_wincher_openapi.py --check` | **Done** |
