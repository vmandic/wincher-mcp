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
- **`releasing.mdc`** — tags, GitHub releases, and PyPI

Do not duplicate rule content here; update the relevant `.mdc` when conventions change.

## Cursor skills

| Skill | When |
|-------|------|
| [update-api-spec](.cursor/skills/update-api-spec/SKILL.md) | Refresh vendored OpenAPI from wincher.com/docs/api |
| [ship-release](.cursor/skills/ship-release/SKILL.md) | Version bump, git tag, GitHub release |
| [local-dev](.cursor/skills/local-dev/SKILL.md) | venv, deps, MCP client config (Cursor / Claude Code), smoke test |

Index: [.cursor/skills/README.md](.cursor/skills/README.md).

## Quick reference

| Item | Value |
|------|--------|
| Entry | `wincher-mcp` CLI or `python -m wincher_mcp` (stdio MCP); shim `wincher_mcp_server.py` |
| Python | 3.10+ |
| Deps | `pip install -e ".[dev]"` or PyPI `wincher-mcp` (`mcp`, `httpx`, `python-toon`) |
| Test | `pytest -q`; audit: `pip-audit` after editable install |
| PyPI | [publishing-version-to-pypi](.cursor/skills/publishing-version-to-pypi/SKILL.md) + `scripts/publish_pypi.py`; version in `src/wincher_mcp/__init__.py` |
| Secret | `WINCHER_API_KEY` (env only; never commit) |
| Staging | MCP arg `--use-staging` + env `WINCHER_STAGING_API_HOST` (host never in repo) |
| MCP example | [docs/MCP_CONFIG.example.json](docs/MCP_CONFIG.example.json) |
| API spec | [docs/api/wincher-openapi.json](docs/api/wincher-openapi.json) (`META.json` has `fetched_at`) |
| Security report | [security_best_practices_report.md](security_best_practices_report.md) |
| Repository | https://github.com/vmandic/wincher-mcp |
| PyPI | https://pypi.org/project/wincher-mcp/ |
| Early prototype | https://github.com/chris-tutt/wincher-mcp-server |
| License | MIT |

## Ask before doing

- New MCP tools or Wincher API endpoints beyond current read-only set
- Refactoring into a package layout without an explicit request
- Committing, pushing, tagging, or opening releases without explicit request
- Broad refactors or dependency major bumps
