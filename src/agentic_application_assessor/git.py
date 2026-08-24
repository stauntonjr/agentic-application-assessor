"""Read-only Git identity with repository-controlled helpers neutralized."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from pathlib import Path

from .errors import AssessmentError
from .model import Target


FILTER_KEY = re.compile(r"^filter\.(.+)\.(?:clean|smudge|process|required)$", re.IGNORECASE)


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
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
    command = (
        "config",
        "--local",
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
    if any(item.endswith("/") for item in listed.split("\0") if item):
        raise AssessmentError(
            "embedded Git repositories are unsupported by the v0.1 exact-state boundary"
        )
    state = hashlib.sha256()
    for value in (revision, branch, status, index, flags):
        state.update(value.encode("utf-8"))
        state.update(b"\0")
    return (
        root,
        Target(root.name, revision, branch, bool(status), f"sha256:{state.hexdigest()}"),
        tuple(sorted(item for item in listed.split("\0") if item)),
    )
