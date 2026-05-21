# Cursor rules (wincher-mcp)

Rules are `.mdc` files. **`core`** uses `alwaysApply: true`. Others activate when matching paths are in context (`alwaysApply: false` + `globs`).

| File | `alwaysApply` | Globs |
|------|---------------|--------|
| [core.mdc](core.mdc) | yes | — |
| [coding-guidelines.mdc](coding-guidelines.mdc) | no | `wincher_mcp_server.py`, `**/*.py` |
| [architecture.mdc](architecture.mdc) | no | `wincher_mcp_server.py`, `**/*.py`, `docs/**` |
| [testing.mdc](testing.mdc) | no | `wincher_mcp_server.py`, `test/**`, `requirements.txt` |
| [security.mdc](security.mdc) | no | `wincher_mcp_server.py`, `.env*`, `requirements.txt` |
| [git-commit.mdc](git-commit.mdc) | no | `**/*` |
| [releasing.mdc](releasing.mdc) | no | `**/*` |

Skills: [../skills/README.md](../skills/README.md). Human-facing docs: [../../README.md](../../README.md).
