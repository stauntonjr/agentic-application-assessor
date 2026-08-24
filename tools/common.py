"""Shared dependency-free helpers for the agentic project harness."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def repository_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "harness" / "project.yaml").is_file():
            return candidate
    raise RuntimeError("Could not find harness/project.yaml from the current directory")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON-compatible YAML in {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(payload)
        temp_name = handle.name
    os.replace(temp_name, path)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(
    argv: Iterable[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(argv),
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        command = " ".join(argv)
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"command failed ({result.returncode}): {command}\n{detail}")
    return result


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=root, check=check)


def get_nested(mapping: dict[str, Any], dotted_key: str, default: Any = None) -> Any:
    value: Any = mapping
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def set_nested(mapping: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    target = mapping
    for part in parts[:-1]:
        child = target.get(part)
        if not isinstance(child, dict):
            child = {}
            target[part] = child
        target = child
    target[parts[-1]] = value
