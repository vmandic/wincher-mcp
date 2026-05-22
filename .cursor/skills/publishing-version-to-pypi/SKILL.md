---
name: publishing-version-to-pypi
description: Use when publishing a new wincher-mcp version to PyPI, bumping __version__, or the user mentions twine upload, pipx release, or PYPI_TOKEN — run the publish script instead of improvising shell steps.
---

# Publishing version to PyPI (wincher-mcp)

## Overview

**Do not** paste long manual checklists into the chat. Run **`scripts/publish_pypi.py`** — it bumps version, tests, builds, uploads, tags, and creates a GitHub release.

## When to use

- User asks to publish/release to PyPI
- Bump `src/wincher_mcp/__init__.py` and upload a new version
- User has `PYPI_TOKEN` in `~/.zsh_secrets`

**When NOT:** Documentation-only changes with no release. **Never** commit tokens.

## Agent workflow (minimal tokens)

```bash
cd /path/to/wincher-mcp
source .venv/bin/activate
pip install -e ".[dev]" build twine   # once per venv

# Preview bump only
python scripts/publish_pypi.py --dry-run --version X.Y.Z

# TestPyPI first (optional)
python scripts/publish_pypi.py --testpypi --version X.Y.Z

# Production PyPI (after clean main + user approval)
python scripts/publish_pypi.py --version X.Y.Z
```

Script loads `~/.zsh_secrets` for `PYPI_TOKEN` if not already exported.

## Flags

| Flag | Effect |
|------|--------|
| `--version X.Y.Z` | Write `__version__` before publish |
| `--dry-run` | Bump only; no test/build/upload/tag |
| `--testpypi` | Upload to TestPyPI |
| `--skip-tests` | Skip pytest |
| `--skip-tag` | No `git tag` / push |
| `--skip-github` | No `gh release create` |
| `--allow-dirty` | Allow dirty tree (avoid unless user insists) |

Override binaries via env: `PUBLISH_PYTHON`, `PUBLISH_PYTEST`, `PUBLISH_TWINE`, `PUBLISH_GIT`, `PUBLISH_GH`.

## Hard rules

| Rule | Why |
|------|-----|
| **Run the script** | Same steps every time; fewer tokens than re-deriving twine/git |
| **Never print `PYPI_TOKEN`** | Secrets stay in env |
| **Never upload without user approval** | Publishing is irreversible on PyPI |
| **Commit version bump before publish** | Script requires clean tree (except `--dry-run`) |
| **Do not force-push `main`** | [releasing.mdc](../../rules/releasing.mdc) |

## RED baseline (why this skill exists)

Without the script, agents often:

| Failure | Reality |
|---------|---------|
| Skip `__version__` bump | PyPI rejects duplicate version |
| Run `twine` without `TWINE_USERNAME=__token__` | Upload auth fails |
| Print token in chat or commit `.pypirc` | Secret leak |
| Tag before tests pass | Broken release on PyPI |
| Re-type 20-step README | Wastes tokens; drifts from repo |

## After publish

- Confirm https://pypi.org/project/wincher-mcp/X.Y.Z/
- User may run `pipx upgrade wincher-mcp`
- Optional: commit version bump if not already on `main`

## Red flags — stop

- Manually running five different twine/git commands instead of the script
- Publishing from a dirty tree without `--allow-dirty`
- Inventing a new version not agreed with the user
- Uploading when `pytest` was not run (unless `--skip-tests` and user approved)

## References

- [docs/PYPI.md](../../../docs/PYPI.md) — human-oriented detail
- [ship-release](../ship-release/SKILL.md) — git tag / GitHub release policy
- Tests: `test/test_publish_pypi.py`
