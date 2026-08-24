"""Read-only Git identity with repository-controlled helpers neutralized."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from pathlib import Path, PurePosixPath

from .errors import AssessmentError
from .model import Target


FILTER_KEY = re.compile(r"^filter\.(.+)\.(?:clean|smudge|process|required)$", re.IGNORECASE)
MAX_WORKTREE_FILE_BYTES = 32 * 1024 * 1024
MAX_WORKTREE_TOTAL_BYTES = 256 * 1024 * 1024


def _environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
    )
    return environment


def _fingerprint_worktree(root: Path, paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    total = 0
    for relative in paths:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise AssessmentError(f"unsafe repository path: {relative!r}")
        cursor = root
        metadata: os.stat_result | None = None
        for index, part in enumerate(pure.parts):
            cursor /= part
            try:
                metadata = cursor.lstat()
            except FileNotFoundError:
                metadata = None
                break
            except OSError as exc:
                raise AssessmentError(
                    f"cannot fingerprint repository path {relative}: {exc}"
                ) from exc
            if stat.S_ISLNK(metadata.st_mode):
                raise AssessmentError(f"repository path is a symlink: {relative}")
            if index < len(pure.parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
                raise AssessmentError(f"repository path has non-directory ancestor: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        if metadata is None:
            digest.update(b"absent\0")
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise AssessmentError(f"repository path is not a regular file: {relative}")
        if metadata.st_size > MAX_WORKTREE_FILE_BYTES:
            raise AssessmentError(f"repository file exceeds 32 MiB identity bound: {relative}")
        total += metadata.st_size
        if total > MAX_WORKTREE_TOTAL_BYTES:
            raise AssessmentError("repository exceeds 256 MiB worktree identity bound")
        digest.update(f"mode:{stat.S_IMODE(metadata.st_mode):o}:size:{metadata.st_size}".encode())
        digest.update(b"\0")
        try:
            with cursor.open("rb") as stream:
                for chunk in iter(lambda: stream.read(131072), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise AssessmentError(f"cannot fingerprint repository file {relative}: {exc}") from exc
        digest.update(b"\0")
    return digest.hexdigest()


def _run(
    root: Path,
    args: tuple[str, ...],
    filters: tuple[str, ...] = (),
    allowed: tuple[int, ...] = (0,),
) -> str:
    command = [
        "git",
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-C",
        str(root),
    ]
    for name in filters:
        command.extend(
            [
                "-c",
                f"filter.{name}.clean=",
                "-c",
                f"filter.{name}.smudge=",
                "-c",
                f"filter.{name}.process=",
                "-c",
                f"filter.{name}.required=false",
            ]
        )
    command.extend(args)
    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_environment(),
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AssessmentError(f"cannot inspect Git repository safely: {exc}") from exc
    if result.returncode not in allowed:
        detail = result.stderr.decode("utf-8", "replace").strip() or "Git command failed"
        raise AssessmentError(detail)
    try:
        return result.stdout.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise AssessmentError("Git output is not valid UTF-8") from exc


def _filter_names(root: Path) -> tuple[str, ...]:
    includes = _run(
        root,
        (
            "config",
            "--local",
            "--no-includes",
            "--null",
            "--name-only",
            "--get-regexp",
            r"^include(if)?\.",
        ),
        allowed=(0, 1),
    )
    if includes:
        raise AssessmentError(
            "repository-local Git config includes are unsupported by the v0.1 safety boundary"
        )
    command = (
        "config",
        "--local",
        "--no-includes",
        "--null",
        "--name-only",
        "--get-regexp",
        r"^filter\..*\.(clean|smudge|process|required)$",
    )
    output = _run(root, command, allowed=(0, 1))
    names: set[str] = set()
    for key in output.split("\0"):
        if not key:
            continue
        match = FILTER_KEY.fullmatch(key)
        if match is None:
            raise AssessmentError(f"unexpected Git filter key: {key!r}")
        names.add(match.group(1))
    return tuple(sorted(names))


def git_output(root: Path, *args: str) -> str:
    return _run(root, tuple(args), _filter_names(root))


def target_identity(target: Path) -> tuple[Path, Target, tuple[str, ...]]:
    lexical = target.absolute()
    for candidate in (lexical, *lexical.parents):
        try:
            if stat.S_ISLNK(candidate.lstat().st_mode):
                raise AssessmentError(f"target path traverses a symlink: {candidate}")
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise AssessmentError(f"cannot inspect target path: {exc}") from exc
    try:
        root = Path(git_output(target, "rev-parse", "--show-toplevel").rstrip("\r\n")).resolve(
            strict=True
        )
        requested = target.resolve(strict=True)
    except OSError as exc:
        raise AssessmentError(f"cannot resolve target: {exc}") from exc
    if root != requested:
        raise AssessmentError("target must be the exact Git repository root")
    revision = git_output(root, "rev-parse", "HEAD").strip()
    branch = (
        _run(
            root,
            ("symbolic-ref", "--quiet", "--short", "HEAD"),
            _filter_names(root),
            allowed=(0, 1),
        ).strip()
        or "(detached)"
    )
    status = git_output(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=all"
    )
    index = git_output(root, "ls-files", "--stage", "-z")
    if any(item.startswith("160000 ") for item in index.split("\0") if item):
        raise AssessmentError("submodules are unsupported by the v0.1 exact-state boundary")
    flags = git_output(root, "ls-files", "-v", "-z")
    listed = git_output(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    paths = tuple(sorted(item for item in listed.split("\0") if item))
    if any(item.endswith("/") for item in paths):
        raise AssessmentError(
            "embedded Git repositories are unsupported by the v0.1 exact-state boundary"
        )
    worktree = _fingerprint_worktree(root, paths)
    state = hashlib.sha256()
    for value in (revision, branch, status, index, flags, worktree):
        state.update(value.encode("utf-8"))
        state.update(b"\0")
    return (
        root,
        Target(root.name, revision, branch, bool(status), f"sha256:{state.hexdigest()}"),
        paths,
    )
