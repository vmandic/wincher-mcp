#!/usr/bin/env python3
"""Publish wincher-mcp to PyPI (scripted; minimal LLM steps).

Usage:
  python scripts/publish_pypi.py --dry-run --version 0.2.1
  python scripts/publish_pypi.py
  python scripts/publish_pypi.py --testpypi

Requires PYPI_TOKEN in the environment (e.g. ~/.zsh_secrets).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from publish_pypi_lib import (
    PublishCommands,
    PublishOptions,
    PublishPaths,
    SubprocessRunner,
    publish,
    read_version,
)


def _load_secrets() -> None:
    secrets = Path.home() / ".zsh_secrets"
    if not secrets.is_file():
        return
    # Minimal parse: export VAR=value lines only (no eval).
    for line in secrets.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish wincher-mcp to PyPI")
    parser.add_argument(
        "--version",
        help="Set src/wincher_mcp/__init__.py __version__ before publish (X.Y.Z)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Bump version only (if --version); do not test/build/upload/tag",
    )
    parser.add_argument(
        "--testpypi",
        action="store_true",
        help="Upload to TestPyPI (uses TEST_PYPI_TOKEN or PYPI_TOKEN)",
    )
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-tag", action="store_true")
    parser.add_argument("--skip-github", action="store_true")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow non-clean git tree (not recommended)",
    )
    parser.add_argument(
        "--github-repo",
        default="vmandic/wincher-mcp",
        help="owner/repo for gh release create",
    )
    parser.add_argument(
        "--python",
        default=os.environ.get("PUBLISH_PYTHON", "python"),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root",
    )
    args = parser.parse_args(argv)

    _load_secrets()

    paths = PublishPaths(root=args.root)
    options = PublishOptions(
        version=args.version,
        dry_run=args.dry_run,
        testpypi=args.testpypi,
        skip_tests=args.skip_tests,
        skip_tag=args.skip_tag,
        skip_github=args.skip_github,
        allow_dirty=args.allow_dirty,
        github_repo=args.github_repo,
    )
    commands = PublishCommands(
        python=args.python,
        pytest=os.environ.get("PUBLISH_PYTEST", "pytest"),
        build_module=os.environ.get("PUBLISH_BUILD", "build"),
        twine=os.environ.get("PUBLISH_TWINE", "twine"),
        git=os.environ.get("PUBLISH_GIT", "git"),
        gh=os.environ.get("PUBLISH_GH", "gh"),
    )

    try:
        version = publish(paths, options, SubprocessRunner(), commands=commands)
    except Exception as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        return 1

    if options.dry_run:
        print(f"dry-run OK: version={version} (no upload)")
    else:
        index = "testpypi" if options.testpypi else "pypi"
        print(f"published wincher-mcp {version} to {index}")
        print(f"https://pypi.org/project/wincher-mcp/{version}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
