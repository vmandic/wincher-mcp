"""Tests for scripts/publish_pypi_lib.py (RED → GREEN)."""

from __future__ import annotations

import sys
from pathlib import Path
from subprocess import CompletedProcess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from publish_pypi_lib import (  # noqa: E402
    PublishCommands,
    PublishOptions,
    PublishPaths,
    RecordingRunner,
    assert_git_clean,
    dist_artifacts,
    publish,
    read_version,
    resolve_pypi_token,
    run_build,
    run_twine_upload,
    write_version,
)


@pytest.fixture
def version_file(tmp_path: Path) -> Path:
    pkg = tmp_path / "src" / "wincher_mcp"
    pkg.mkdir(parents=True)
    init_py = pkg / "__init__.py"
    init_py.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    return init_py


@pytest.fixture
def paths(tmp_path: Path, version_file: Path) -> PublishPaths:
    return PublishPaths(root=tmp_path)


class TestVersionIO:
    def test_read_version(self, version_file: Path) -> None:
        assert read_version(version_file) == "1.2.3"

    def test_write_version(self, version_file: Path) -> None:
        write_version(version_file, "2.0.0")
        assert read_version(version_file) == "2.0.0"

    def test_write_rejects_invalid_semver(self, version_file: Path) -> None:
        with pytest.raises(ValueError, match="semver"):
            write_version(version_file, "not-a-version")


class TestGitClean:
    def test_assert_git_clean_passes(self, paths: PublishPaths) -> None:
        runner = RecordingRunner()
        runner.git_status = ""
        assert_git_clean(runner, paths.root)

    def test_assert_git_clean_fails(self, paths: PublishPaths) -> None:
        runner = RecordingRunner()
        runner.git_status = " M README.md"
        with pytest.raises(RuntimeError, match="not clean"):
            assert_git_clean(runner, paths.root)


class TestDistArtifacts:
    def test_finds_wheel_and_sdist(self, tmp_path: Path) -> None:
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "wincher_mcp-1.2.3-py3-none-any.whl").write_text("whl")
        (dist / "wincher_mcp-1.2.3.tar.gz").write_text("sdist")
        names = [p.name for p in dist_artifacts(dist, "1.2.3")]
        assert "wincher_mcp-1.2.3-py3-none-any.whl" in names
        assert "wincher_mcp-1.2.3.tar.gz" in names

    def test_missing_dist_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            dist_artifacts(tmp_path / "dist", "1.2.3")


class TestTwineUpload:
    def test_twine_uses_token_env_not_stdout(self, paths: PublishPaths, tmp_path: Path) -> None:
        dist = paths.root / "dist"
        dist.mkdir()
        (dist / "wincher_mcp-1.2.3-py3-none-any.whl").write_text("x")
        runner = RecordingRunner()
        cmds = PublishCommands(twine="twine")
        run_twine_upload(
            runner,
            paths.root,
            version="1.2.3",
            commands=cmds,
            testpypi=False,
            token="pypi-secret-token",
        )
        assert len(runner.calls) == 1
        cmd, _cwd, env = runner.calls[0]
        assert cmd[0] == "twine"
        assert "upload" in cmd
        assert env is not None
        assert env["TWINE_USERNAME"] == "__token__"
        assert env["TWINE_PASSWORD"] == "pypi-secret-token"
        assert "pypi-secret-token" not in " ".join(cmd)


class TestResolvePypiToken:
    def test_requires_pypi_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PYPI_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="PYPI_TOKEN"):
            resolve_pypi_token(testpypi=False)

    def test_testpypi_accepts_test_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PYPI_TOKEN", raising=False)
        monkeypatch.setenv("TEST_PYPI_TOKEN", "test-only")
        assert resolve_pypi_token(testpypi=True) == "test-only"


class TestPublishPipeline:
    def test_dry_run_does_not_invoke_twine(self, paths: PublishPaths, version_file: Path) -> None:
        runner = RecordingRunner()
        runner.git_status = ""
        version = publish(
            paths,
            PublishOptions(dry_run=True, version="9.9.9"),
            runner,
            commands=PublishCommands(
                python="python",
                pytest="pytest",
                build_module="build",
                twine="twine",
                git="git",
                gh="gh",
            ),
        )
        assert version == "9.9.9"
        assert read_version(version_file) == "9.9.9"
        assert not any(c[0][0] == "twine" for c in runner.calls)

    def test_full_pipeline_mocked(
        self,
        paths: PublishPaths,
        version_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class BuildSeedingRunner(RecordingRunner):
            def __init__(self, seed_version: str) -> None:
                super().__init__()
                self.seed_version = seed_version

            def run(self, cmd, *, cwd, env=None, check=True):
                self.calls.append((cmd, cwd, env))
                if len(cmd) >= 3 and cmd[1] == "-m" and cmd[2] == "build":
                    dist = cwd / "dist"
                    dist.mkdir(exist_ok=True)
                    prefix = f"wincher_mcp-{self.seed_version}"
                    (dist / f"{prefix}-py3-none-any.whl").write_text("w")
                    (dist / f"{prefix}.tar.gz").write_text("s")
                    return CompletedProcess(cmd, 0, "", "")
                return super().run(cmd, cwd=cwd, env=env, check=check)

        runner = BuildSeedingRunner("4.5.6")
        runner.git_status = ""
        monkeypatch.setenv("PYPI_TOKEN", "fake-pypi-token")

        version = publish(
            paths,
            PublishOptions(version="4.5.6", skip_github=True),
            runner,
            commands=PublishCommands(
                python="py",
                pytest="pytest",
                build_module="build",
                twine="twine",
                git="git",
                gh="gh",
            ),
        )

        assert version == "4.5.6"
        joined = " ".join(" ".join(c[0]) for c in runner.calls)
        assert "pytest" in joined or "py" in joined
        assert "twine upload" in joined
        assert "git tag" in joined

    def test_dirty_tree_blocked_on_real_publish(self, paths: PublishPaths) -> None:
        runner = RecordingRunner()
        runner.git_status = "?? foo.txt"
        with pytest.raises(RuntimeError, match="not clean"):
            publish(paths, PublishOptions(dry_run=False, skip_tests=True), runner)

    def test_dry_run_allows_dirty_tree(self, paths: PublishPaths) -> None:
        runner = RecordingRunner()
        runner.git_status = "?? foo.txt"
        version = publish(
            paths,
            PublishOptions(dry_run=True, version="3.1.4"),
            runner,
        )
        assert version == "3.1.4"
