# Agent guide — wincher-mcp

Coding agents: start with **Cursor rules** (below). End users: [README.md](README.md).

## Cursor rules (primary)

Conventions are split by topic in [`.cursor/rules/`](.cursor/rules/README.md):

- **`core.mdc`** — always on: identity, commands, rule index
- **`coding-guidelines.mdc`** — `wincher_mcp_server.py`: Python, MCP stdio, tool handlers
- **`architecture.mdc`** — layout, Wincher API mapping, extension points
- **`testing.mdc`** — verification before claiming done (`pytest -q`, `pip-audit`; see CI)
- **`security.mdc`** — API keys, HTTP, error redaction
- **`git-commit.mdc`** — commit/push gates
- **`releasing.mdc`** — tags and GitHub releases (fork maintenance)

Do not duplicate rule content here; update the relevant `.mdc` when conventions change.

## Cursor skills

| Skill | When |
|-------|------|
| [update-api-spec](.cursor/skills/update-api-spec/SKILL.md) | Refresh vendored OpenAPI from wincher.com/docs/api |
| [ship-release](.cursor/skills/ship-release/SKILL.md) | Version bump, git tag, GitHub release |
| [local-dev](.cursor/skills/local-dev/SKILL.md) | venv, deps, Claude Desktop MCP config, smoke test |

Index: [.cursor/skills/README.md](.cursor/skills/README.md).

## Quick reference

| Item | Value |
|------|--------|
| Entry | `wincher_mcp_server.py` (stdio MCP) |
| Python | 3.10+ |
| Deps | `pip install -r requirements.txt` (`mcp`, `httpx`); dev: `requirements-dev.txt` |
| Test | `pytest -q`; audit: `pip-audit -r requirements.txt -r requirements-dev.txt` |
| Secret | `WINCHER_API_KEY` (env only; never commit) |
| Staging | MCP arg `--use-staging` + env `WINCHER_STAGING_API_HOST` (host never in repo) |
| MCP example | [docs/MCP_CONFIG.example.json](docs/MCP_CONFIG.example.json) |
| API spec | [docs/api/wincher-openapi.json](docs/api/wincher-openapi.json) (`META.json` has `fetched_at`) |
| Security report | [security_best_practices_report.md](security_best_practices_report.md) |
| Upstream | https://github.com/chris-tutt/wincher-mcp-server |
| Fork | https://github.com/vmandic/wincher-mcp |
| License | MIT |

## Ask before doing

- New MCP tools or Wincher API endpoints beyond current read-only set
- Refactoring into a package layout without an explicit request
- Committing, pushing, tagging, or opening releases without explicit request
- Broad refactors or dependency major bumps
