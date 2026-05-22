# Publishing to PyPI

This project is packaged for **[PyPI](https://pypi.org)** (Python’s default package index). Users install with **`pip`** or **`pipx`**.

Package name: **`wincher-mcp`**  
Console command after install: **`wincher-mcp`**

## One-time setup (your machine)

### 1. PyPI account

1. Create an account at [pypi.org](https://pypi.org/account/register/).
2. Enable **2FA** (recommended).
3. Create an **API token**:
   - Account settings → API tokens → “Add API token”
   - Scope: project **`wincher-mcp`** (or entire account for first upload)
   - Copy the token (`pypi-...`) — shown once.

Store the token locally (never commit it):

```bash
# ~/.pypirc (chmod 600) — optional; twine reads this
[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...

[testpypi]
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZwC...
```

Or pass credentials only at upload time (see below).

### 2. Build tools

```bash
cd ~/source/vmandic/wincher-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install build twine
```

## Version bumps

Single source of truth:

1. Edit **`src/wincher_mcp/__init__.py`** → `__version__ = "x.y.z"`
2. Hatch reads the same value via `[tool.hatch.version]` in `pyproject.toml`.

Tag releases on git when you publish: `git tag v0.2.0 && git push origin v0.2.0`.

## Dry run (local)

```bash
source .venv/bin/activate
pytest -q
python -m build
ls -la dist/
```

You should see `wincher_mcp-0.2.0-py3-none-any.whl` and `.tar.gz`.

Test install from the wheel in a fresh venv:

```bash
python -m venv /tmp/wincher-mcp-test
/tmp/wincher-mcp-test/bin/pip install dist/wincher_mcp-*.whl
/tmp/wincher-mcp-test/bin/wincher-mcp --help 2>&1 | head -1 || true
# MCP has no --help; verify the command exists:
which wincher-mcp || ls /tmp/wincher-mcp-test/bin/wincher-mcp
```

## TestPyPI (recommended first upload)

[TestPyPI](https://test.pypi.org) is a sandbox. Package names can overlap; use it to verify metadata and install flow.

```bash
python -m build
twine upload --repository testpypi dist/*
```

Install from TestPyPI:

```bash
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ wincher-mcp==0.2.0
```

(`--extra-index-url` pulls normal dependencies like `mcp` from production PyPI.)

## Production PyPI

When TestPyPI looks good:

```bash
python -m build
twine upload dist/*
# Or: TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-... twine upload dist/*
```

Verify: https://pypi.org/project/wincher-mcp/

## End-user install

**pipx** (isolated CLI, good for MCP):

```bash
pipx install wincher-mcp
```

**pip** (into current venv):

```bash
pip install wincher-mcp
```

**Cursor / Claude MCP config** (after pipx):

```json
{
  "mcpServers": {
    "wincher": {
      "command": "wincher-mcp",
      "args": ["--use-toon"],
      "env": {
        "WINCHER_API_KEY": "YOUR_KEY"
      }
    }
  }
}
```

Optional flags in `args`: `--use-staging` (requires `WINCHER_STAGING_API_HOST`), `--use-toon`.

Legacy path still works if you clone the repo:

```json
"command": "/path/to/.venv/bin/python",
"args": ["/path/to/wincher-mcp/wincher_mcp_server.py"]
```

## Checklist before each release

- [ ] `pytest -q` passes
- [ ] Version bumped in `src/wincher_mcp/__init__.py`
- [ ] `CHANGELOG.md` updated (if you keep one)
- [ ] `python -m build` succeeds
- [ ] Upload to TestPyPI first (optional but wise)
- [ ] `twine upload` to PyPI
- [ ] Git tag `vX.Y.Z` and GitHub release (see [ship-release skill](../.cursor/skills/ship-release/SKILL.md))

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `File already exists` on upload | Bump version; PyPI names are immutable per version |
| `Invalid distribution` | Run `python -m build` again; upload only `dist/*` from latest build |
| `wincher-mcp` not on PATH after pipx | `pipx ensurepath`; restart shell |
| MCP client cannot find command | Use full path: `pipx which wincher-mcp` |

## Security

- Never commit API tokens, `.pypirc` with passwords, or `WINCHER_API_KEY` in package metadata.
- Use a **project-scoped** PyPI token for `wincher-mcp` only.
