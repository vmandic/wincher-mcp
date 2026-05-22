"""PyPI publish workflow (testable; invoked by scripts/publish_pypi.py)."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from typing import Callable, Protocol

VERSION_PATTERN = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$', re.M)
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class CommandRunner(Protocol):
    def run(
        self,
        cmd: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> CompletedProcess[str]: ...


@dataclass
class PublishPaths:
    root: Path
    version_file: Path = field(init=False)
    dist_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.version_file = self.root / "src" / "wincher_mcp" / "__init__.py"
        self.dist_dir = self.root / "dist"


@dataclass
class PublishOptions:
    version: str | None = None
    dry_run: bool = False
    testpypi: bool = False
    skip_tests: bool = False
    skip_tag: bool = False
    skip_github: bool = False
    allow_dirty: bool = False
    github_repo: str = "vmandic/wincher-mcp"


@dataclass
class PublishCommands:
    python: str = "python"
    pytest: str = "pytest"
    build_module: str = "build"
    twine: str = "twine"
    git: str = "git"
    gh: str = "gh"


def read_version(version_file: Path) -> str:
    text = version_file.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(text)
    if not match:
        raise ValueError(f"__version__ not found in {version_file}")
    return match.group(1)


def write_version(version_file: Path, version: str) -> None:
    if not SEMVER_PATTERN.match(version):
        raise ValueError(f"Invalid semver: {version!r} (expected X.Y.Z)")
    text = version_file.read_text(encoding="utf-8")
    if not VERSION_PATTERN.search(text):
        raise ValueError(f"__version__ not found in {version_file}")
    updated = VERSION_PATTERN.sub(f'__version__ = "{version}"', text, count=1)
    version_file.write_text(updated, encoding="utf-8")


def git_status_porcelain(runner: CommandRunner, root: Path) -> str:
    result = runner.run([PublishCommands.git, "status", "--porcelain"], cwd=root, check=True)
    return (result.stdout or "").strip()


def assert_git_clean(runner: CommandRunner, root: Path) -> None:
    status = git_status_porcelain(runner, root)
    if status:
        raise RuntimeError(
            "Working tree is not clean. Commit or stash changes before publishing.\n"
            + status
        )


def run_pytest(runner: CommandRunner, root: Path, *, commands: PublishCommands) -> None:
    runner.run([commands.python, "-m", commands.pytest, "-q"], cwd=root, check=True)


def run_build(runner: CommandRunner, root: Path, *, commands: PublishCommands) -> None:
    if root.joinpath("dist").exists():
        shutil.rmtree(root / "dist")
    runner.run([commands.python, "-m", commands.build_module], cwd=root, check=True)


def dist_artifacts(dist_dir: Path, version: str) -> list[Path]:
    if not dist_dir.is_dir():
        raise FileNotFoundError(f"Missing dist directory: {dist_dir}")
    expected_prefix = f"wincher_mcp-{version}"
    artifacts = sorted(
        p for p in dist_dir.iterdir() if p.name.startswith(expected_prefix) and p.is_file()
    )
    if not artifacts:
        raise FileNotFoundError(
            f"No dist artifacts for {expected_prefix} in {dist_dir}"
        )
    return artifacts


def twine_repository(testpypi: bool) -> str:
    return "testpypi" if testpypi else "pypi"


def run_twine_upload(
    runner: CommandRunner,
    root: Path,
    *,
    version: str,
    commands: PublishCommands,
    testpypi: bool,
    token: str,
) -> None:
    artifacts = dist_artifacts(root / "dist", version)
    env = os.environ.copy()
    env["TWINE_USERNAME"] = "__token__"
    env["TWINE_PASSWORD"] = token
    cmd = [commands.twine, "upload", "--repository", twine_repository(testpypi)]
    cmd.extend(str(p) for p in artifacts)
    runner.run(cmd, cwd=root, env=env, check=True)


def run_git_tag_push(
    runner: CommandRunner,
    root: Path,
    version: str,
    *,
    commands: PublishCommands,
) -> None:
    tag = f"v{version}"
    runner.run([commands.git, "tag", tag], cwd=root, check=True)
    runner.run([commands.git, "push", "origin", tag], cwd=root, check=True)


def run_gh_release(
    runner: CommandRunner,
    root: Path,
    version: str,
    *,
    commands: PublishCommands,
    github_repo: str,
) -> None:
    tag = f"v{version}"
    notes = (
        f"## wincher-mcp {tag}\n\n"
        f"PyPI: https://pypi.org/project/wincher-mcp/{version}/\n"
    )
    runner.run(
        [
            commands.gh,
            "release",
            "create",
            tag,
            "--repo",
            github_repo,
            "--title",
            tag,
            "--notes",
            notes,
        ],
        cwd=root,
        check=True,
    )


def resolve_pypi_token(testpypi: bool) -> str:
    if testpypi:
        token = os.environ.get("TEST_PYPI_TOKEN") or os.environ.get("PYPI_TOKEN", "")
    else:
        token = os.environ.get("PYPI_TOKEN", "")
    if not token:
        var = "TEST_PYPI_TOKEN or PYPI_TOKEN" if testpypi else "PYPI_TOKEN"
        raise RuntimeError(f"{var} is not set (e.g. in ~/.zsh_secrets)")
    return token


def publish(
    paths: PublishPaths,
    options: PublishOptions,
    runner: CommandRunner,
    *,
    commands: PublishCommands | None = None,
) -> str:
    """Run the publish pipeline. Returns the version published."""
    cmds = commands or PublishCommands()

    if not options.allow_dirty and not options.dry_run:
        assert_git_clean(runner, paths.root)

    version = options.version or read_version(paths.version_file)
    if options.version:
        write_version(paths.version_file, options.version)

    if options.dry_run:
        return version

    if not options.skip_tests:
        run_pytest(runner, paths.root, commands=cmds)

    run_build(runner, paths.root, commands=cmds)
    dist_artifacts(paths.dist_dir, version)

    token = resolve_pypi_token(options.testpypi)
    run_twine_upload(
        runner,
        paths.root,
        version=version,
        commands=cmds,
        testpypi=options.testpypi,
        token=token,
    )

    if not options.skip_tag:
        run_git_tag_push(runner, paths.root, version, commands=cmds)

    if not options.skip_github:
        run_gh_release(
            runner,
            paths.root,
            version,
            commands=cmds,
            github_repo=options.github_repo,
        )

    return version


class SubprocessRunner:
    """Default runner: real subprocess."""

    def run(
        self,
        cmd: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> CompletedProcess[str]:
        import subprocess

        return subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            check=check,
            text=True,
            capture_output=True,
        )


class RecordingRunner:
    """Test double: record calls and return configured exit codes."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path, dict[str, str] | None]] = []
        self.results: dict[str, tuple[int, str, str]] = {}
        self.git_status: str = ""

    def set_result(self, executable: str, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.results[executable] = (returncode, stdout, stderr)

    def run(
        self,
        cmd: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> CompletedProcess[str]:
        self.calls.append((cmd, cwd, env))
        key = Path(cmd[0]).name if cmd else ""
        if key == "git" and len(cmd) > 1 and cmd[1] == "status":
            return CompletedProcess(cmd, 0, self.git_status, "")
        rc, stdout, stderr = self.results.get(key, (0, "", ""))
        if check and rc != 0:
            raise CalledProcessError(rc, cmd, output=stdout, stderr=stderr)
        return CompletedProcess(cmd, rc, stdout, stderr)
