---
name: ship-release
description: >-
  Ship a wincher-mcp fork release: verify Python, bump version notes,
  git tag, and GitHub release. Use when the user asks to release,
  tag vX.Y.Z, or create a GitHub release for vmandic/wincher-mcp.
---

# Ship release (wincher-mcp)

Conservative workflow for **vmandic/wincher-mcp** only. There is **no npm/PyPI publish** in this repo unless the user adds it later.

## Hard rules

- **Never** `git push --force` to `main` or delete tags without explicit user approval.
- **Never** commit secrets or `.env`.
- **Never** create a tag or GitHub release if `python -m py_compile wincher_mcp_server.py` fails.
- **Never** tag from a dirty tree unless the user accepts including those changes.

## Before you start

Confirm with the user:

1. Target semver (`v0.1.1`, etc.).
2. Whether to push `main` and create the GitHub release in this session.
3. Whether to note upstream sync from `chris-tutt/wincher-mcp-server` in release notes.

Optional: add or update `CHANGELOG.md` (Keep a Changelog style).

## Step 1 — Verify

```bash
git status
source .venv/bin/activate
pip install -r requirements.txt
python -m py_compile wincher_mcp_server.py
```

## Step 2 — Release commit (if needed)

- Update `CHANGELOG.md` with `## [X.Y.Z] - YYYY-MM-DD` if the project uses a changelog.
- README version badge or “Releases” line only if user asked.

Commit **only when the user explicitly asked**:

```bash
git commit -m "$(cat <<'EOF'
chore: release vX.Y.Z

EOF
)"
```

## Step 3 — Tag and push

After user approval:

```bash
git pull origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

If `main` should include the release commit first: `git push origin main` (only when asked).

## Step 4 — GitHub release

```bash
gh release create vX.Y.Z \
  --title "vX.Y.Z" \
  --notes "## wincher-mcp vX.Y.Z

- <summary bullets>
- Upstream: optional note if merged from chris-tutt/wincher-mcp-server

**Install:** see [README](https://github.com/vmandic/wincher-mcp/blob/main/README.md) and [docs/SETUP.md](https://github.com/vmandic/wincher-mcp/blob/main/docs/SETUP.md)."
```

Verify: https://github.com/vmandic/wincher-mcp/releases

## Post-release

- [ ] Tag exists and points at intended commit
- [ ] Release notes have no secrets
- [ ] README setup paths still valid

## References

- [releasing.mdc](../../rules/releasing.mdc)
- [AGENTS.md](../../../AGENTS.md)
