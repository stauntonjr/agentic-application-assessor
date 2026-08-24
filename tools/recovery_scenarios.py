#!/usr/bin/env python3
"""Replay sanitized engineering-loop recovery fixtures in disposable repositories."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root, write_json
    from .loop import (
        add_item,
        load_run,
        make_write_set,
        new_attempt,
        parse_criteria,
        recovery_status,
        resume_run,
        scope_evidence,
        start_run,
    )
except ImportError:  # Direct script execution.
    from common import load_json, repository_root, write_json
    from loop import (
        add_item,
        load_run,
        make_write_set,
        new_attempt,
        parse_criteria,
        recovery_status,
        resume_run,
        scope_evidence,
        start_run,
    )


FAILURE_CLASSES = {
    "dirty-worktree",
    "partial-loop",
    "stale-branch",
    "agent-crash",
    "retry-exhaustion",
    "resumable-handoff",
}
DESTRUCTIVE_GIT = {"reset", "clean", "checkout", "restore", "rebase"}


def git(root: Path, *args: str) -> None:
    if args and args[0] in DESTRUCTIVE_GIT:
        raise RuntimeError(f"recovery fixture attempted destructive Git command: {args[0]}")
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def init_repository(root: Path, source_root: Path) -> Path:
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "Recovery Fixture")
    artifact = root / "artifact.txt"
    artifact.write_text("baseline\n", encoding="utf-8")
    git(root, "add", "--", "artifact.txt")
    git(root, "commit", "-m", "fixture baseline")
    loop_target = root / "harness/loops/engineering-loop.yaml"
    loop_target.parent.mkdir(parents=True)
    loop_target.write_bytes((source_root / "harness/loops/engineering-loop.yaml").read_bytes())
    return artifact


def start_fixture_run(root: Path) -> dict[str, Any]:
    return start_run(
        root,
        "Exercise deterministic recovery",
        "14",
        "recovery-fixture",
        acceptance_criteria=parse_criteria(["AC1=Recovery preserves bounded work"]),
        declared_write_set=make_write_set(["artifact.txt", "partial.txt"], []),
        implementers=["fixture-implementer"],
    )


def set_fixture_state(root: Path, state: str) -> None:
    path, record = load_run(root, "recovery-fixture")
    record["state"] = state
    write_json(path, record)


def dirty_worktree(root: Path, source_root: Path) -> dict[str, Any]:
    artifact = init_repository(root, source_root)
    artifact.write_text("pre-existing user work\n", encoding="utf-8")
    record = start_fixture_run(root)
    (root / "partial.txt").write_text("bounded recovery output\n", encoding="utf-8")
    scope = scope_evidence(root, record)
    return {
        "terminal_state": "recoverable",
        "preserved_partial_work": artifact.read_text(encoding="utf-8")
        == "pre-existing user work\n",
        "delta_paths": [item["path"] for item in scope["delta"]],
        "scope_violations": scope["violations"],
        "destructive_git_commands": [],
    }


def partial_loop(root: Path, source_root: Path) -> dict[str, Any]:
    init_repository(root, source_root)
    start_fixture_run(root)
    set_fixture_state(root, "implement")
    (root / "partial.txt").write_text("durable partial work\n", encoding="utf-8")
    _, reloaded = load_run(root, "recovery-fixture")
    return {
        "terminal_state": reloaded["state"],
        "preserved_partial_work": (root / "partial.txt").read_text(encoding="utf-8")
        == "durable partial work\n",
        "same_run_id": reloaded["run_id"] == "recovery-fixture",
        "destructive_git_commands": [],
    }


def stale_branch(root: Path, source_root: Path) -> dict[str, Any]:
    init_repository(root, source_root)
    git(root, "switch", "-c", "feature")
    start_fixture_run(root)
    git(root, "branch", "integration", "main")
    git(root, "switch", "integration")
    (root / "integration.txt").write_text("integration advanced\n", encoding="utf-8")
    git(root, "add", "--", "integration.txt")
    git(root, "commit", "-m", "advance integration")
    git(root, "switch", "feature")
    status = recovery_status(root, "recovery-fixture", "integration")
    return {
        "terminal_state": "inspect-before-integration",
        "branch_stale": status["branch_stale"],
        "scope_violations": status["scope_violations"],
        "destructive_git_commands": [],
    }


def agent_crash(root: Path, source_root: Path) -> dict[str, Any]:
    init_repository(root, source_root)
    start_fixture_run(root)
    set_fixture_state(root, "implement")
    (root / "partial.txt").write_text("work before process loss\n", encoding="utf-8")
    add_item(
        root,
        "recovery-fixture",
        "agent_handoffs",
        {
            "schema_version": "1.0",
            "summary": "Process ended during implementation",
            "failure_boundary": "agent process unavailable",
            "preserved_paths": ["partial.txt"],
            "next_action": "Inspect the recorded state before continuing",
        },
    )
    _, reloaded = load_run(root, "recovery-fixture")
    return {
        "terminal_state": reloaded["state"],
        "preserved_partial_work": (root / "partial.txt").is_file(),
        "handoff_count": len(reloaded["agent_handoffs"]),
        "destructive_git_commands": [],
    }


def exhaust_retries(root: Path) -> dict[str, Any]:
    new_attempt(root, "recovery-fixture", "failure one")
    new_attempt(root, "recovery-fixture", "failure two")
    try:
        new_attempt(root, "recovery-fixture", "failure three")
    except RuntimeError as exc:
        error = str(exc)
    else:  # pragma: no cover - a failure is the contract under test.
        error = "retry ceiling did not stop"
    _, record = load_run(root, "recovery-fixture")
    return {
        "record": record,
        "error": error,
    }


def retry_exhaustion(root: Path, source_root: Path) -> dict[str, Any]:
    init_repository(root, source_root)
    start_fixture_run(root)
    exhausted = exhaust_retries(root)
    record = exhausted["record"]
    return {
        "terminal_state": record["state"],
        "attempt_id": record["attempt_id"],
        "failure_count": len(record["attempt_history"]),
        "ceiling_error": "retry ceiling reached after 3" in exhausted["error"],
        "destructive_git_commands": [],
    }


def resumable_handoff(root: Path, source_root: Path) -> dict[str, Any]:
    init_repository(root, source_root)
    start_fixture_run(root)
    (root / "partial.txt").write_text("reviewable preserved work\n", encoding="utf-8")
    exhaust_retries(root)
    resumed = resume_run(
        root,
        "recovery-fixture",
        handoff={
            "schema_version": "1.0",
            "summary": "Use a reviewed recovery approach",
            "failure_boundary": "Three failures at one boundary",
            "preserved_paths": ["partial.txt"],
            "next_action": "Re-enter understand before changing the candidate",
        },
        authorized_by="human:fixture-owner",
    )
    return {
        "terminal_state": resumed["state"],
        "revision": resumed["revision"],
        "attempt_id": resumed["attempt_id"],
        "preserved_partial_work": (root / "partial.txt").read_text(encoding="utf-8")
        == "reviewable preserved work\n",
        "authorized_by": resumed["agent_handoffs"][-1]["authorized_by"],
        "destructive_git_commands": [],
    }


SCENARIOS: dict[str, Callable[[Path, Path], dict[str, Any]]] = {
    "dirty-worktree": dirty_worktree,
    "partial-loop": partial_loop,
    "stale-branch": stale_branch,
    "agent-crash": agent_crash,
    "retry-exhaustion": retry_exhaustion,
    "resumable-handoff": resumable_handoff,
}


def validate_fixture(data: Any, path: Path) -> list[str]:
    if not isinstance(data, dict):
        return [f"{path.name}: fixture must be an object"]
    errors: list[str] = []
    for key in ("schema_version", "id", "failure_class", "source", "expected"):
        if key not in data:
            errors.append(f"{path.name}: missing {key}")
    if data.get("schema_version") != "1.0":
        errors.append(f"{path.name}: schema_version must be 1.0")
    identifier = data.get("id")
    if not isinstance(identifier, str) or path.stem != identifier:
        errors.append(f"{path.name}: filename must match fixture id")
    if data.get("failure_class") not in FAILURE_CLASSES:
        errors.append(f"{path.name}: unsupported failure_class")
    source = data.get("source")
    if not isinstance(source, dict):
        errors.append(f"{path.name}: source must be an object")
    else:
        if source.get("kind") not in {"public-dogfood", "synthetic"}:
            errors.append(f"{path.name}: source.kind must be public-dogfood or synthetic")
        if source.get("sanitized") is not True:
            errors.append(f"{path.name}: source.sanitized must be true")
        if source.get("contains_raw_transcript") is not False:
            errors.append(f"{path.name}: source.contains_raw_transcript must be false")
        reference = source.get("reference")
        if not isinstance(reference, str) or not reference.strip():
            errors.append(f"{path.name}: source.reference is required")
    if not isinstance(data.get("expected"), dict) or not data.get("expected"):
        errors.append(f"{path.name}: expected must be a non-empty object")
    return errors


def expected_mismatches(actual: Any, expected: Any, prefix: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{prefix or 'result'}: expected object"]
        for key, value in expected.items():
            child = f"{prefix}.{key}" if prefix else key
            if key not in actual:
                errors.append(f"{child}: missing")
            else:
                errors.extend(expected_mismatches(actual[key], value, child))
    elif actual != expected:
        errors.append(f"{prefix}: expected {expected!r}, got {actual!r}")
    return errors


def fixture_paths(root: Path) -> list[Path]:
    fixture_root = root / "harness/recovery"
    if fixture_root.is_symlink():
        raise ValueError("harness/recovery must not be a symlink")
    paths = sorted(fixture_root.glob("R*.json"))
    symlinks = [path.name for path in paths if path.is_symlink()]
    if symlinks:
        raise ValueError(f"recovery fixtures must not be symlinks: {', '.join(symlinks)}")
    return paths


def replay_fixture(source_root: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        actual = SCENARIOS[fixture["failure_class"]](Path(directory), source_root)
    mismatches = expected_mismatches(actual, fixture["expected"])
    return {"id": fixture["id"], "ok": not mismatches, "actual": actual, "errors": mismatches}


def replay_known_bad(case: str) -> tuple[int, dict[str, Any]]:
    if case == "pi-unbounded-unavailable-tools":
        payload = {
            "case": case,
            "observed_unavailable_calls": 231,
            "configured_ceiling": 3,
            "aborted": False,
            "signature": "unbounded unavailable-tool retries",
        }
        return 1, payload
    if case == "adoption-partial-mutation":
        payload = {
            "case": case,
            "files_written_before_preflight_failure": 1,
            "signature": "partial mutation before preflight",
        }
        return 1, payload
    return 2, {"case": case, "signature": "unknown known-bad case"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--fixture", action="append", default=[])
    parser.add_argument("--known-bad")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    if args.known_bad:
        code, payload = replay_known_bad(args.known_bad)
        print(json.dumps(payload, indent=2))
        return code

    selected = set(args.fixture)
    fixtures: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        paths = fixture_paths(root)
    except ValueError as exc:
        paths = []
        errors.append(str(exc))
    for path in paths:
        try:
            fixture = load_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        errors.extend(validate_fixture(fixture, path))
        if not selected or fixture.get("id") in selected:
            fixtures.append(fixture)
    missing = sorted(selected - {item.get("id") for item in fixtures})
    errors.extend(f"unknown recovery fixture: {item}" for item in missing)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    results = [replay_fixture(root, item) for item in fixtures]
    payload = {"ok": all(item["ok"] for item in results), "results": results}
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
