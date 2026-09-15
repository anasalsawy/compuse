"""Safe, in-place updates for the Tasker source installation.

Tasker is commonly installed editable from a Windows project directory.  That
means pip can reinstall the launcher while leaving the source files unchanged.
This module makes the source installation self-updating: on startup it checks
the public ``main`` commit, overlays a staged GitHub archive when the source
is not a Git checkout, and restarts the process on the new code.

Updates never remove user files.  Existing files are replaced atomically and
the previous contents are kept in a temporary rollback area until the update
finishes.  Network or update failures are reported and the current program is
allowed to continue.
"""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler
import zipfile


REPOSITORY = "anasalsawy/compuse"
BRANCH = "main"
REVISION_MARKER = ".tasker-source-revision"
RESTART_ENV = "TASKER_UPDATE_RESTARTED"
DEFAULT_TIMEOUT = 8.0


class UpdateError(RuntimeError):
    """An update could not be safely completed."""


@dataclass(frozen=True)
class UpdateResult:
    """Outcome of one automatic update check."""

    state: str
    revision: str | None = None
    detail: str = ""
    exit_code: int | None = None


def source_root() -> Path:
    """Find the editable project root containing ``pyproject.toml``."""

    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "compuse").is_dir():
            return parent
    return module_path.parents[2]


def _http_get(url: str, *, timeout: float) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Tasker-auto-updater",
        },
    )
    errors: list[str] = []
    # Try direct access first so inherited broken proxy variables do not block
    # updates.  Fall back to the normal opener for networks that require one.
    for opener in (build_opener(ProxyHandler({})), build_opener()):
        try:
            with opener.open(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors.append(str(exc))
    raise UpdateError(f"GitHub request failed: {'; '.join(errors)}")


def remote_revision(*, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Return the current commit SHA for the configured update branch."""

    url = f"https://api.github.com/repos/{REPOSITORY}/commits/{BRANCH}"
    try:
        payload = json.loads(_http_get(url, timeout=timeout).decode("utf-8"))
        revision = str(payload["sha"]).strip()
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise UpdateError(f"GitHub returned an invalid commit response: {exc}") from exc
    if len(revision) < 20 or any(char not in "0123456789abcdef" for char in revision.lower()):
        raise UpdateError("GitHub returned an invalid commit SHA")
    return revision


def _git_revision(root: Path) -> str | None:
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _known_revision(root: Path) -> str | None:
    revision = _git_revision(root)
    if revision:
        return revision
    marker = root / REVISION_MARKER
    try:
        return marker.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _git_pull(root: Path, expected_revision: str) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "pull", "--ff-only", "origin", BRANCH],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(f"Git update could not run: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().replace("\n", " ")
        raise UpdateError(f"Git update failed: {detail or 'unknown git error'}")
    actual = _git_revision(root)
    if actual != expected_revision:
        raise UpdateError("Git update completed but the local revision is not the requested main revision")


def _safe_relative_name(name: str, archive_root: str) -> Path | None:
    path = PurePosixPath(name)
    parts = path.parts
    if len(parts) < 2 or parts[0] != archive_root:
        return None
    relative = parts[1:]
    if any(part in {"", ".", ".."} for part in relative):
        raise UpdateError(f"Unsafe path in update archive: {name}")
    if relative[0] == ".git":
        return None
    return Path(*relative)


def _stage_archive(data: bytes, staging_root: Path) -> list[tuple[Path, Path]]:
    archive_path = staging_root / "source.zip"
    archive_path.write_bytes(data)
    staged_root = staging_root / "staged"
    staged_root.mkdir()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = [info.filename for info in archive.infolist() if info.filename.strip("/")]
            if not names:
                raise UpdateError("GitHub update archive was empty")
            archive_root = PurePosixPath(names[0]).parts[0]
            staged_files: list[tuple[Path, Path]] = []
            for info in archive.infolist():
                relative = _safe_relative_name(info.filename, archive_root)
                if relative is None or info.is_dir():
                    continue
                destination = staged_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(info))
                staged_files.append((relative, destination))
    except zipfile.BadZipFile as exc:
        raise UpdateError(f"GitHub update was not a valid ZIP archive: {exc}") from exc
    if not staged_files:
        raise UpdateError("GitHub update archive contained no project files")
    return staged_files


def _write_revision_marker(root: Path, revision: str) -> None:
    marker = root / REVISION_MARKER
    temporary = root / f"{REVISION_MARKER}.tmp"
    temporary.write_text(f"{revision}\n", encoding="ascii")
    os.replace(temporary, marker)


def _install_staged(root: Path, files: Iterable[tuple[Path, Path]], revision: str, staging_root: Path) -> None:
    backup_root = staging_root / "rollback"
    backups: list[tuple[Path, Path]] = []
    created: list[Path] = []
    try:
        for relative, source in files:
            target = root / relative
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise UpdateError(f"Cannot safely update non-file target: {target}")
            if target.exists():
                backup = backup_root / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                backups.append((target, backup))
            else:
                created.append(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.tasker-update")
            shutil.copy2(source, temporary)
            os.replace(temporary, target)
        _write_revision_marker(root, revision)
    except Exception:
        for target in created:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
        for target, backup in reversed(backups):
            try:
                shutil.copy2(backup, target)
            except OSError:
                pass
        raise


def _archive_update(root: Path, revision: str, *, timeout: float) -> None:
    url = f"https://github.com/{REPOSITORY}/archive/{revision}.zip"
    data = _http_get(url, timeout=max(timeout, 30.0))
    with tempfile.TemporaryDirectory(prefix="tasker-update-") as temporary:
        staging_root = Path(temporary)
        files = _stage_archive(data, staging_root)
        _install_staged(root, files, revision, staging_root)


def maybe_auto_update(
    *,
    root: Path | None = None,
    argv: Sequence[str] = (),
    timeout: float = DEFAULT_TIMEOUT,
    restart: bool = True,
) -> UpdateResult:
    """Check ``main`` and update/restart when a newer revision exists."""

    if os.environ.get("TASKER_AUTO_UPDATE", "1").strip().lower() in {"0", "false", "off", "no"}:
        return UpdateResult("disabled", detail="automatic updates disabled")
    if os.environ.get(RESTART_ENV) == "1":
        return UpdateResult("restarted", detail="running after automatic update")

    project_root = (root or source_root()).resolve()
    latest = remote_revision(timeout=timeout)
    current = _known_revision(project_root)
    if current == latest:
        return UpdateResult("current", revision=latest)

    try:
        if _git_revision(project_root):
            _git_pull(project_root, latest)
        else:
            _archive_update(project_root, latest, timeout=timeout)
    except UpdateError:
        raise
    except (OSError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        raise UpdateError(f"update could not be applied safely: {exc}") from exc

    if not restart:
        return UpdateResult("updated", revision=latest)

    environment = os.environ.copy()
    environment[RESTART_ENV] = "1"
    command = [sys.executable, "-m", "compuse.app.tasker_cli", *argv]
    print(f"[Tasker] updated from {current or 'unknown'} to {latest}; restarting...")
    # subprocess receives an argv list and therefore preserves executable
    # paths such as ``C:\\Program Files\\Python314\\python.exe`` on Windows.
    try:
        child = subprocess.run(
            command,
            cwd=str(project_root),
            env=environment,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise UpdateError(f"updated successfully but restart failed: {exc}") from exc
    return UpdateResult("restarted", revision=latest, exit_code=child.returncode)
