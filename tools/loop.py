#!/usr/bin/env python3
"""Create integrity-checked engineering-loop records and evidence-backed reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from .common import git, load_json, repository_root, utc_now, write_json
except ImportError:  # Direct script execution.
    from common import git, load_json, repository_root, utc_now, write_json


RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CRITERION_ID = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
CHECK_STATUSES = ("passed", "failed", "skipped", "not-run")
VERDICTS = ("approve", "revise", "reject")
RELEASE_IMPACTS = ("none", "patch", "minor", "major")
FINAL_STATES = ("reported", "blocked", "abandoned")
RUN_SCHEMA_VERSION = "1.2"
RESUME_HANDOFF_SCHEMA_VERSION = "1.0"
DEFAULT_MAXIMUM_CONSECUTIVE_FAILURES = 3


def git_text(root: Path, *args: str) -> str:
    result = git(root, *args, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def current_commit(root: Path) -> str:
    return git_text(root, "rev-parse", "HEAD") or "UNBORN"


def make_run_id(root: Path) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    revision = current_commit(root)
    suffix = revision[:8] if revision != "UNBORN" else "unborn"
    base = f"{timestamp}-{suffix}"
    candidate = base
    index = 2
    while (root / ".harness/runs" / candidate).exists():
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def run_path(root: Path, run_id: str) -> Path:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError(f"invalid run ID: {run_id}")
    return root / ".harness/runs" / run_id / "run.json"


def load_run(root: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    path = run_path(root, run_id)
    return path, load_json(path)


def normalize_repository_path(value: str, *, kind: str) -> str:
    raw = value.strip().replace("\\", "/")
    while raw.endswith("/"):
        raw = raw[:-1]
    path = Path(raw)
    if not raw or raw == "." or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"invalid declared {kind}: {value}")
    normalized = path.as_posix()
    if normalized == ".git" or normalized.startswith(".git/"):
        raise ValueError("declared write scope cannot include .git")
    return normalized


def make_write_set(exact_paths: Iterable[str], prefixes: Iterable[str]) -> list[dict[str, str]]:
    entries = [
        {"mode": "exact", "path": normalize_repository_path(path, kind="path")}
        for path in exact_paths
    ]
    entries.extend(
        {"mode": "prefix", "path": normalize_repository_path(path, kind="prefix")}
        for path in prefixes
    )
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        key = (entry["mode"], entry["path"])
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return unique


def parse_criteria(values: Iterable[str]) -> list[dict[str, Any]]:
    criteria: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        identifier, separator, text = value.partition("=")
        identifier = identifier.strip()
        text = text.strip()
        if not separator or not CRITERION_ID.fullmatch(identifier) or not text:
            raise ValueError(f"criterion must be ID=TEXT with a valid ID: {value}")
        if identifier in seen:
            raise ValueError(f"duplicate acceptance criterion: {identifier}")
        seen.add(identifier)
        criteria.append({"id": identifier, "text": text, "waiver": None})
    if not criteria:
        raise ValueError("at least one acceptance criterion is required")
    return criteria


def path_fingerprint(path: Path) -> tuple[str, str | None]:
    try:
        stat_result = path.lstat()
    except FileNotFoundError:
        return "absent", None
    if path.is_symlink():
        target = os.readlink(path)
        return "symlink", hashlib.sha256(target.encode("utf-8", "surrogateescape")).hexdigest()
    if path.is_file():
        digest = hashlib.sha256()
        digest.update(f"mode:{stat_result.st_mode & 0o7777}\0".encode("ascii"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return "file", digest.hexdigest()
    if path.is_dir():
        return "directory", None
    metadata = f"{stat_result.st_mode}:{stat_result.st_size}:{stat_result.st_mtime_ns}"
    return "other", hashlib.sha256(metadata.encode("ascii")).hexdigest()


def index_fingerprint(root: Path, relative: str) -> list[dict[str, str]]:
    result = git(root, "ls-files", "--stage", "-z", "--", relative, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"could not inspect index entry for {relative}")
    entries: list[dict[str, str]] = []
    for token in result.stdout.split("\0"):
        if not token:
            continue
        metadata, separator, path = token.partition("\t")
        parts = metadata.split()
        if not separator or len(parts) != 3:
            raise ValueError(f"unexpected Git index entry: {token!r}")
        mode, object_id, stage = parts
        entries.append({"mode": mode, "object_id": object_id, "stage": stage, "path": path})
    return entries


def nested_repository_digest(root: Path) -> str:
    head = git_text(root, "rev-parse", "HEAD")
    if not head:
        raise RuntimeError(f"dirty gitlink is not an inspectable repository: {root}")
    full_index = git(root, "ls-files", "--stage", "-z", check=False)
    if full_index.returncode != 0:
        raise RuntimeError(full_index.stderr.strip() or f"could not inspect nested index: {root}")
    payload = {
        "head": head,
        "index": full_index.stdout,
        "dirty": capture_worktree_snapshot(root),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def is_repository_root(path: Path) -> bool:
    result = git(path, "rev-parse", "--show-toplevel", check=False)
    if result.returncode != 0:
        return False
    try:
        return Path(result.stdout.strip()).resolve() == path.resolve()
    except OSError:
        return False


def hidden_index_paths(root: Path) -> dict[str, list[str]]:
    flags: dict[str, set[str]] = {}
    for option, label, predicate in (
        ("-v", "assume-unchanged", lambda tag: tag.islower()),
        ("-t", "skip-worktree", lambda tag: tag == "S"),
    ):
        result = git(root, "ls-files", option, "-z", check=False)
        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip() or f"could not inspect index flags with {option}"
            )
        for token in result.stdout.split("\0"):
            if not token:
                continue
            tag, separator, path = token.partition(" ")
            if not separator or len(tag) != 1:
                raise ValueError(f"unexpected Git index flag entry: {token!r}")
            if predicate(tag):
                flags.setdefault(path, set()).add(label)
    return {path: sorted(values) for path, values in flags.items()}


def snapshot_entry(
    root: Path,
    relative: str,
    status: str,
    *,
    index_flags: Iterable[str] = (),
) -> dict[str, Any]:
    index = index_fingerprint(root, relative)
    target = root / relative
    if any(item["mode"] == "160000" for item in index):
        kind, digest = "gitlink", nested_repository_digest(target)
    elif target.is_symlink():
        kind, digest = path_fingerprint(target)
    elif target.is_dir():
        if not is_repository_root(target):
            raise RuntimeError(f"directory status entry cannot be fingerprinted safely: {relative}")
        kind, digest = "nested-repository", nested_repository_digest(target)
    else:
        kind, digest = path_fingerprint(target)
    return {
        "path": relative,
        "status": status,
        "kind": kind,
        "digest": digest,
        "index": index,
        "index_flags": sorted(index_flags),
    }


def _excluded_from_snapshot(path: str, run_id: str | None) -> bool:
    if not run_id:
        return False
    internal = f".harness/runs/{run_id}"
    return path == internal or path.startswith(f"{internal}/")


def capture_worktree_snapshot(root: Path, run_id: str | None = None) -> list[dict[str, Any]]:
    result = git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=none",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "could not capture Git working-tree status")
    tokens = result.stdout.split("\0")
    entries: list[dict[str, Any]] = []
    flags_by_path = hidden_index_paths(root)
    seen_paths: set[str] = set()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        if len(token) < 4 or token[2] != " ":
            raise ValueError(f"unexpected Git porcelain entry: {token!r}")
        status = token[:2]
        path = token[3:].rstrip("/")
        paths = [(path, status)]
        if "R" in status or "C" in status:
            if index >= len(tokens) or not tokens[index]:
                raise ValueError("incomplete Git rename/copy status entry")
            paths.append((tokens[index].rstrip("/"), f"{status}:source"))
            index += 1
        for relative, path_status in paths:
            if _excluded_from_snapshot(relative, run_id):
                continue
            entries.append(
                snapshot_entry(
                    root,
                    relative,
                    path_status,
                    index_flags=flags_by_path.get(relative, []),
                )
            )
            seen_paths.add(relative)
    for relative, index_flags in flags_by_path.items():
        if relative in seen_paths or _excluded_from_snapshot(relative, run_id):
            continue
        entries.append(snapshot_entry(root, relative, "index-hidden", index_flags=index_flags))
    return sorted(entries, key=lambda item: (item["path"], item["status"]))


def snapshot_map(entries: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {entry["path"]: entry for entry in entries}


def worktree_delta(record: dict[str, Any], current: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = snapshot_map(record.get("baseline", {}).get("entries", []))
    now = snapshot_map(current)
    delta: list[dict[str, Any]] = []
    for path in sorted(set(baseline) | set(now)):
        before = baseline.get(path)
        after = now.get(path)
        if before != after:
            delta.append({"path": path, "before": before, "after": after})
    return delta


def committed_paths_since_start(root: Path, start_commit: str) -> list[str]:
    end_commit = current_commit(root)
    if end_commit == start_commit or end_commit == "UNBORN":
        return []
    if start_commit == "UNBORN":
        result = git(root, "ls-files", "-z", check=False)
    else:
        result = git(
            root,
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            start_commit,
            end_commit,
            check=False,
        )
    if result.returncode != 0:
        detail = result.stderr.strip() or "could not inspect committed paths"
        raise RuntimeError(detail)
    return sorted({path for path in result.stdout.split("\0") if path})


def path_is_declared(path: str, write_set: Iterable[dict[str, str]]) -> bool:
    for entry in write_set:
        declared = entry["path"]
        if entry["mode"] == "exact" and path == declared:
            return True
        if entry["mode"] == "prefix" and (path == declared or path.startswith(f"{declared}/")):
            return True
    return False


def scope_evidence(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    current = capture_worktree_snapshot(root, record["run_id"])
    delta = worktree_delta(record, current)
    delta_by_path = {item["path"]: item for item in delta}
    baseline = snapshot_map(record.get("baseline", {}).get("entries", []))
    for path in committed_paths_since_start(root, record["start_commit"]):
        if _excluded_from_snapshot(path, record["run_id"]):
            continue
        if path in delta_by_path:
            delta_by_path[path]["committed_since_start"] = True
            continue
        after = snapshot_entry(root, path, "committed")
        item = {
            "path": path,
            "before": baseline.get(path),
            "after": after,
            "committed_since_start": True,
        }
        delta.append(item)
        delta_by_path[path] = item
    delta.sort(key=lambda item: item["path"])
    violations = [
        item["path"]
        for item in delta
        if not path_is_declared(item["path"], record.get("declared_write_set", []))
    ]
    return {
        "baseline": record.get("baseline", {}).get("entries", []),
        "current": current,
        "delta": delta,
        "violations": violations,
    }


def candidate_identity(root: Path, record: dict[str, Any]) -> dict[str, str]:
    scope = scope_evidence(root, record)
    payload = {
        "run_id": record["run_id"],
        "revision": record["revision"],
        "attempt_id": record["attempt_id"],
        "commit": current_commit(root),
        "delta": scope["delta"],
        "release_impact": record.get("release_impact"),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    impact = json.dumps(payload["release_impact"], sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {
        "commit": payload["commit"],
        "tree_digest": f"sha256:{hashlib.sha256(serialized).hexdigest()}",
        "release_impact_digest": f"sha256:{hashlib.sha256(impact).hexdigest()}",
    }


def start_run(
    root: Path,
    objective: str,
    issue: str | None,
    run_id: str | None = None,
    *,
    acceptance_criteria: list[dict[str, Any]] | None = None,
    declared_write_set: list[dict[str, str]] | None = None,
    implementers: list[str] | None = None,
) -> dict[str, Any]:
    if not objective.strip():
        raise ValueError("objective is required")
    identifier = run_id or make_run_id(root)
    path = run_path(root, identifier)
    if path.exists():
        raise ValueError(f"run already exists: {identifier}")
    criteria = acceptance_criteria or []
    if not criteria:
        raise ValueError("at least one acceptance criterion is required")
    ids = [item.get("id") for item in criteria]
    if len(ids) != len(set(ids)) or any(
        not isinstance(item, str) or not CRITERION_ID.fullmatch(item) for item in ids
    ):
        raise ValueError("acceptance criteria require unique, valid IDs")
    authors = [item.strip() for item in (implementers or []) if item.strip()]
    if not authors:
        raise ValueError("at least one implementer identity is required")
    if len(authors) != len(set(authors)):
        raise ValueError("implementer identities must be unique")
    branch = git_text(root, "branch", "--show-current") or "DETACHED_OR_UNBORN"
    record: dict[str, Any] = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": identifier,
        "revision": 1,
        "attempt_id": 1,
        "objective_seed": objective,
        "objective": objective,
        "issue": issue,
        "acceptance_criteria": criteria,
        "declared_write_set": declared_write_set or [],
        "implementers": authors,
        "baseline": {
            "captured_at": utc_now(),
            "entries": capture_worktree_snapshot(root, identifier),
        },
        "started_at": utc_now(),
        "finished_at": None,
        "start_commit": current_commit(root),
        "end_commit": None,
        "branch": branch,
        "state": "intake",
        "checks": [],
        "verdicts": [],
        "release_impact": None,
        "revision_history": [],
        "attempt_history": [],
        "retry_policy": {
            "maximum_consecutive_failures": configured_retry_limit(root),
            "on_exhaustion": "stop-and-escalate",
        },
        "agent_handoffs": [],
        "decisions": [],
        "risks": [],
        "telemetry": {},
    }
    write_json(path, record)
    return record


def criterion_ids(record: dict[str, Any]) -> set[str]:
    return {item["id"] for item in record.get("acceptance_criteria", [])}


def active_criterion_ids(record: dict[str, Any]) -> set[str]:
    return {
        item["id"]
        for item in record.get("acceptance_criteria", [])
        if not item.get("waiver") or item["waiver"].get("revision") != record.get("revision")
    }


def current_passed_criteria(record: dict[str, Any]) -> set[str]:
    passed: set[str] = set()
    for check in record.get("checks", []):
        if (
            check.get("status") == "passed"
            and check.get("revision") == record.get("revision")
            and check.get("attempt_id") == record.get("attempt_id")
        ):
            passed.update(check.get("criterion_ids", []))
    return passed


def record_check(
    root: Path,
    run_id: str,
    *,
    name: str,
    command: str,
    status: str,
    evidence: str,
    criteria: Iterable[str] = (),
) -> dict[str, Any]:
    if status not in CHECK_STATUSES:
        raise ValueError(f"invalid check status: {status}")
    if not name.strip() or not command.strip() or not evidence.strip():
        raise ValueError("check name, command, and evidence are required")
    path, record = load_run(root, run_id)
    linked = list(dict.fromkeys(criteria))
    unknown = sorted(set(linked) - criterion_ids(record))
    if unknown:
        raise ValueError(f"check references unknown criteria: {', '.join(unknown)}")
    record["checks"].append(
        {
            "check_id": f"check-{len(record['checks']) + 1:03d}",
            "revision": record.get("revision", 0),
            "attempt_id": record.get("attempt_id", 0),
            "criterion_ids": linked,
            "name": name,
            "command": command,
            "status": status,
            "evidence": evidence,
            "recorded_at": utc_now(),
        }
    )
    write_json(path, record)
    return record


def record_release_impact(
    root: Path,
    run_id: str,
    *,
    level: str,
    reason: str,
    public_contract_changes: Iterable[str] = (),
) -> dict[str, Any]:
    if level not in RELEASE_IMPACTS:
        raise ValueError(f"invalid release impact: {level}")
    if not reason.strip():
        raise ValueError("release impact reason is required")
    path, record = load_run(root, run_id)
    record["release_impact"] = {
        "revision": record["revision"],
        "attempt_id": record["attempt_id"],
        "level": level,
        "reason": reason,
        "public_contract_changes": list(dict.fromkeys(public_contract_changes)),
        "recorded_at": utc_now(),
    }
    write_json(path, record)
    return record


def record_verdict(
    root: Path,
    run_id: str,
    *,
    reviewer: str,
    verdict: str,
    criteria: Iterable[str],
    evidence: str,
) -> dict[str, Any]:
    if verdict not in VERDICTS:
        raise ValueError(f"invalid verifier verdict: {verdict}")
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("reviewer identity is required")
    if not evidence.strip():
        raise ValueError("verifier evidence is required")
    path, record = load_run(root, run_id)
    if record.get("schema_version") != RUN_SCHEMA_VERSION:
        raise ValueError(
            f"verifier verdicts require a loop run created with schema {RUN_SCHEMA_VERSION}"
        )
    if reviewer in record.get("implementers", []):
        raise ValueError(f"reviewer {reviewer!r} is recorded as an implementer")
    covered = set(criteria)
    unknown = sorted(covered - criterion_ids(record))
    if unknown:
        raise ValueError(f"verdict references unknown criteria: {', '.join(unknown)}")
    if verdict == "approve":
        active = active_criterion_ids(record)
        missing_coverage = sorted(active - covered)
        if missing_coverage:
            raise ValueError(f"approval omits active criteria: {', '.join(missing_coverage)}")
        missing_evidence = sorted(active - current_passed_criteria(record))
        if missing_evidence:
            raise ValueError(
                f"approval lacks passed check evidence for criteria: {', '.join(missing_evidence)}"
            )
    record["verdicts"].append(
        {
            "verdict_id": f"verdict-{len(record['verdicts']) + 1:03d}",
            "revision": record["revision"],
            "attempt_id": record["attempt_id"],
            "reviewer": reviewer,
            "decision": verdict,
            "criterion_ids": sorted(covered),
            "evidence": evidence,
            "candidate": candidate_identity(root, record),
            "recorded_at": utc_now(),
        }
    )
    write_json(path, record)
    return record


def revise_run(
    root: Path,
    run_id: str,
    *,
    reason: str,
    objective: str | None = None,
    acceptance_criteria: list[dict[str, Any]] | None = None,
    declared_write_set: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("revision reason is required")
    path, record = load_run(root, run_id)
    if record.get("state") == "blocked" and consecutive_failures(record) >= retry_limit(
        root, record
    ):
        raise ValueError("retry-exhausted runs must use reviewed resume instead of revise")
    record["revision_history"].append(
        {
            "revision": record["revision"],
            "objective": record["objective"],
            "acceptance_criteria": record["acceptance_criteria"],
            "declared_write_set": record["declared_write_set"],
            "superseded_at": utc_now(),
            "reason": reason,
        }
    )
    record["revision"] += 1
    record["attempt_id"] = 1
    if objective is not None:
        if not objective.strip():
            raise ValueError("objective is required")
        record["objective"] = objective
    if acceptance_criteria is not None:
        record["acceptance_criteria"] = acceptance_criteria
    else:
        for criterion in record["acceptance_criteria"]:
            criterion["waiver"] = None
    if declared_write_set is not None:
        record["declared_write_set"] = declared_write_set
    write_json(path, record)
    return record


def configured_retry_limit(root: Path) -> int:
    path = root / "harness/loops/engineering-loop.yaml"
    loop = load_json(path) if path.is_file() else {}
    value = loop.get("retry_policy", {}).get(
        "maximum_consecutive_failures", DEFAULT_MAXIMUM_CONSECUTIVE_FAILURES
    )
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("maximum_consecutive_failures must be a positive integer")
    return value


def retry_limit(root: Path, record: dict[str, Any]) -> int:
    value = record.get("retry_policy", {}).get("maximum_consecutive_failures")
    if value is None:
        value = configured_retry_limit(root)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("recorded maximum_consecutive_failures must be a positive integer")
    return value


def consecutive_failures(record: dict[str, Any]) -> int:
    revision = record.get("revision")
    count = 0
    for attempt in reversed(record.get("attempt_history", [])):
        if attempt.get("revision") != revision or attempt.get("outcome") != "failed":
            break
        count += 1
    return count


def new_attempt(root: Path, run_id: str, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("attempt reason is required")
    path, record = load_run(root, run_id)
    if record.get("state") in FINAL_STATES:
        raise ValueError(f"cannot retry a terminal run in state {record.get('state')}")
    record["attempt_history"].append(
        {
            "revision": record["revision"],
            "attempt_id": record["attempt_id"],
            "ended_at": utc_now(),
            "reason": reason,
            "outcome": "failed",
        }
    )
    failures = consecutive_failures(record)
    limit = retry_limit(root, record)
    if failures >= limit:
        record["state"] = "blocked"
        record.setdefault("telemetry", {})["retry_exhaustion"] = {
            "revision": record["revision"],
            "attempt_id": record["attempt_id"],
            "consecutive_failures": failures,
            "limit": limit,
            "recorded_at": utc_now(),
        }
        write_json(path, record)
        raise RuntimeError(
            f"retry ceiling reached after {failures} consecutive failures; "
            "run is blocked and requires an explicit reviewed handoff"
        )
    record["attempt_id"] += 1
    write_json(path, record)
    return record


def validate_resume_handoff(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["resume handoff must be an object"]
    required = ("schema_version", "summary", "failure_boundary", "preserved_paths", "next_action")
    for key in required:
        if key not in data:
            errors.append(f"resume handoff is missing {key}")
    if data.get("schema_version") != RESUME_HANDOFF_SCHEMA_VERSION:
        errors.append(f"resume handoff schema_version must be {RESUME_HANDOFF_SCHEMA_VERSION}")
    for key in ("summary", "failure_boundary", "next_action"):
        if not isinstance(data.get(key), str) or not data.get(key, "").strip():
            errors.append(f"resume handoff {key} must be a non-empty string")
    preserved = data.get("preserved_paths")
    if not isinstance(preserved, list) or not all(
        isinstance(item, str) and item.strip() for item in preserved
    ):
        errors.append("resume handoff preserved_paths must be a string list")
    else:
        if len(preserved) != len(set(preserved)):
            errors.append("resume handoff preserved_paths must be unique")
        for item in preserved:
            try:
                normalize_repository_path(item, kind="preserved path")
            except ValueError as exc:
                errors.append(str(exc))
    forbidden = {"transcript", "prompt", "hidden_reasoning", "secret", "token"}
    if forbidden.intersection(data):
        errors.append("resume handoff contains a forbidden transcript, reasoning, or secret field")
    unexpected = sorted(set(data) - set(required))
    if unexpected:
        errors.append(f"resume handoff contains unexpected fields: {', '.join(unexpected)}")
    return errors


def resume_run(
    root: Path,
    run_id: str,
    *,
    handoff: dict[str, Any],
    authorized_by: str,
) -> dict[str, Any]:
    authorized_by = authorized_by.strip()
    if not authorized_by.startswith("human:") or not authorized_by.removeprefix("human:").strip():
        raise ValueError("retry-exhausted resume requires --by human:IDENTITY")
    errors = validate_resume_handoff(handoff)
    if errors:
        raise ValueError("; ".join(errors))
    path, record = load_run(root, run_id)
    if record.get("state") != "blocked" or consecutive_failures(record) < retry_limit(root, record):
        raise ValueError("only a retry-exhausted blocked run can be resumed")

    record["revision_history"].append(
        {
            "revision": record["revision"],
            "objective": record["objective"],
            "acceptance_criteria": record["acceptance_criteria"],
            "declared_write_set": record["declared_write_set"],
            "superseded_at": utc_now(),
            "reason": f"human-authorized recovery: {handoff['summary'].strip()}",
        }
    )
    record["revision"] += 1
    record["attempt_id"] = 1
    record["state"] = "understand"
    record["finished_at"] = None
    record["end_commit"] = None
    record["agent_handoffs"].append(
        {
            **handoff,
            "authorized_by": authorized_by,
            "recorded_at": utc_now(),
            "resume_revision": record["revision"],
        }
    )
    write_json(path, record)
    return record


def recovery_status(root: Path, run_id: str, integration_ref: str | None = None) -> dict[str, Any]:
    _, record = load_run(root, run_id)
    current = current_commit(root)
    scope = scope_evidence(root, record)
    status: dict[str, Any] = {
        "run_id": run_id,
        "state": record.get("state"),
        "revision": record.get("revision"),
        "attempt_id": record.get("attempt_id"),
        "consecutive_failures": consecutive_failures(record),
        "retry_limit": retry_limit(root, record),
        "baseline_relative_changes_present": bool(scope["delta"]),
        "changed_paths": [item["path"] for item in scope["delta"]],
        "scope_violations": scope["violations"],
        "integration_ref": integration_ref,
        "integration_ref_commit": None,
        "branch_stale": None,
    }
    if integration_ref:
        ref_commit = git_text(root, "rev-parse", "--verify", integration_ref)
        if not ref_commit:
            raise ValueError(f"integration ref does not exist: {integration_ref}")
        ancestry = git(root, "merge-base", "--is-ancestor", ref_commit, current, check=False)
        if ancestry.returncode not in (0, 1):
            raise RuntimeError(ancestry.stderr.strip() or "could not compare integration ancestry")
        status["integration_ref_commit"] = ref_commit
        status["branch_stale"] = ancestry.returncode == 1
    return status


def waive_criterion(
    root: Path, run_id: str, criterion_id: str, *, waived_by: str, reason: str
) -> dict[str, Any]:
    waived_by = waived_by.strip()
    if not waived_by.startswith("human:") or not waived_by.removeprefix("human:").strip():
        raise ValueError("criterion waivers require --by human:IDENTITY")
    if not reason.strip():
        raise ValueError("criterion waiver reason is required")
    path, record = load_run(root, run_id)
    for criterion in record.get("acceptance_criteria", []):
        if criterion["id"] == criterion_id:
            criterion["waiver"] = {
                "by": waived_by,
                "reason": reason,
                "revision": record["revision"],
                "recorded_at": utc_now(),
            }
            write_json(path, record)
            return record
    raise ValueError(f"unknown acceptance criterion: {criterion_id}")


def add_item(root: Path, run_id: str, collection: str, value: Any) -> dict[str, Any]:
    path, record = load_run(root, run_id)
    record[collection].append(value)
    write_json(path, record)
    return record


def set_state(root: Path, run_id: str, state: str) -> dict[str, Any]:
    loop = load_json(root / "harness/loops/engineering-loop.yaml")
    valid = {item["id"] for item in loop["states"]} | set(loop["terminal_states"])
    if state not in valid:
        raise ValueError(f"unknown loop state: {state}")
    path, record = load_run(root, run_id)
    if record.get("state") in FINAL_STATES and state != record.get("state"):
        raise ValueError(
            f"cannot leave terminal state {record.get('state')} with set-state; use reviewed recovery"
        )
    record["state"] = state
    write_json(path, record)
    return record


def collect_git_evidence(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    end_commit = current_commit(root)
    status = git_text(root, "status", "--short")
    scope = scope_evidence(root, record)
    evidence: dict[str, Any] = {
        "start_commit": record["start_commit"],
        "end_commit": end_commit,
        "branch": git_text(root, "branch", "--show-current") or "DETACHED_OR_UNBORN",
        "working_tree_status": status.splitlines() if status else [],
        "commits": [],
        "diff_stat": "",
        "changed_paths": [item["path"] for item in scope["delta"]],
        "scope": scope,
    }
    if record["start_commit"] != "UNBORN":
        commit_log = git_text(
            root, "log", "--format=%H%x09%s", f"{record['start_commit']}..{end_commit}"
        )
        evidence["commits"] = commit_log.splitlines() if commit_log else []
        evidence["diff_stat"] = git_text(root, "diff", "--stat", record["start_commit"])
    return evidence


def completion_errors(root: Path, record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    project_path = root / "harness/project.yaml"
    if project_path.is_file():
        project = load_json(project_path).get("project", {})
        if project.get("lifecycle") == "adopt" and project.get("status") != "active":
            errors.append(
                "harness project is provisional; resolve adoption gaps and essential intake "
                "context before reported completion"
            )
    criteria = record.get("acceptance_criteria", [])
    if not criteria:
        errors.append("run has no acceptance criteria")
    active = active_criterion_ids(record)
    missing_checks = sorted(active - current_passed_criteria(record))
    if missing_checks:
        errors.append(f"criteria lack current passed checks: {', '.join(missing_checks)}")
    scope = scope_evidence(root, record)
    if scope["violations"]:
        errors.append(f"writes outside declared scope: {', '.join(scope['violations'])}")
    release_impact = record.get("release_impact")
    if not release_impact:
        errors.append("product release impact is not assessed")
    elif release_impact.get("revision") != record.get("revision") or release_impact.get(
        "attempt_id"
    ) != record.get("attempt_id"):
        errors.append("product release impact is stale for the current revision and attempt")
    current_verdicts = [
        item
        for item in record.get("verdicts", [])
        if item.get("revision") == record.get("revision")
        and item.get("attempt_id") == record.get("attempt_id")
    ]
    if not current_verdicts:
        errors.append("no verifier verdict exists for the current revision and attempt")
    else:
        latest = current_verdicts[-1]
        if latest.get("decision") != "approve":
            errors.append(f"latest verifier verdict is {latest.get('decision')}, not approve")
        missing_coverage = sorted(active - set(latest.get("criterion_ids", [])))
        if missing_coverage:
            errors.append(f"verifier verdict omits criteria: {', '.join(missing_coverage)}")
        if latest.get("candidate") != candidate_identity(root, record):
            errors.append("verifier verdict is stale for the current commit or working tree")
    return errors


def markdown_report(record: dict[str, Any], evidence: dict[str, Any]) -> str:
    checks = record.get("checks", [])
    passed = sum(item.get("status") == "passed" for item in checks)
    failed = sum(item.get("status") == "failed" for item in checks)
    changed = evidence.get("changed_paths", [])
    status = evidence.get("working_tree_status", [])
    current_passed = current_passed_criteria(record)

    def list_or_none(values: list[Any], formatter: Callable[[Any], str] = str) -> str:
        if not values:
            return "- None recorded."
        return "\n".join(f"- {formatter(value)}" for value in values)

    check_rows = (
        "\n".join(
            f"| {item.get('check_id', '')} | {item.get('name', '')} | {item.get('status', '')} | "
            f"{', '.join(item.get('criterion_ids', [])) or 'None'} | {item.get('command', '')} | "
            f"{item.get('evidence', '')} |"
            for item in checks
        )
        or "| None | None recorded | not-run | None |  | No check boundary recorded |"
    )
    criterion_rows = (
        "\n".join(
            f"| {item['id']} | "
            f"{'waived' if item.get('waiver') and item['waiver'].get('revision') == record.get('revision') else ('check-passed' if item['id'] in current_passed else 'missing')} | "
            f"{item['text']} | "
            f"{item.get('waiver', {}).get('reason', '') if item.get('waiver') else ''} |"
            for item in record.get("acceptance_criteria", [])
        )
        or "| None | missing | No acceptance criteria recorded | |"
    )
    latest_verdict = record.get("verdicts", [])[-1] if record.get("verdicts") else None
    verdict_text = (
        f"{latest_verdict['decision']} by {latest_verdict['reviewer']} "
        f"for revision {latest_verdict['revision']}, attempt {latest_verdict['attempt_id']}, "
        f"candidate `{latest_verdict['candidate']['commit']}` / "
        f"`{latest_verdict['candidate']['tree_digest']}` / "
        f"impact `{latest_verdict['candidate']['release_impact_digest']}`"
        if latest_verdict
        else "None recorded"
    )
    handoffs = list_or_none(
        record.get("agent_handoffs", []),
        lambda item: json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item),
    )
    risks = list_or_none(record.get("risks", []))
    decisions = list_or_none(record.get("decisions", []))
    changed_text = list_or_none(changed)
    dirty_text = list_or_none(status)
    violation_text = list_or_none(evidence.get("scope", {}).get("violations", []))
    declared_scope_text = list_or_none(
        record.get("declared_write_set", []),
        lambda item: f"{item['mode']}: {item['path']}",
    )
    issue = record.get("issue") or "None"
    release_impact = record.get("release_impact")
    release_impact_text = (
        f"{release_impact['level']}: {release_impact['reason']}"
        if release_impact
        else "not assessed"
    )
    contract_changes = list_or_none(
        release_impact.get("public_contract_changes", []) if release_impact else []
    )

    return f"""# Engineering loop report: {record["run_id"]}

## Outcome and why it matters

- VERIFIED: Collected repository evidence from `{evidence["start_commit"]}` to `{evidence["end_commit"]}`.
- REPORTED: Objective was: {record["objective"]}
- VERIFIED: {len(changed)} baseline-relative changed paths, {passed} passed checks, and {failed} failed checks were recorded.

## Planned versus completed

- REPORTED: Governing Issue: {issue}.
- VERIFIED: Final loop state: {record["state"]}.
- VERIFIED: Run revision {record.get("revision", "legacy")}, attempt {record.get("attempt_id", "legacy")}.
- INFERRED: Completion is limited to the repository and check boundaries listed below.

## Acceptance evidence matrix

| Criterion | Status | Accepted boundary | Waiver reason |
|---|---|---|---|
{criterion_rows}

## User-visible and semantic changes

No user-visible claim is generated automatically. Add one only after inspecting the changed behavior and acceptance evidence.

- VERIFIED: Recommended product release impact: {release_impact_text}

Declared public-contract changes:

{contract_changes}

## Architecture, schema, dependency, data, and interface changes

Review the exact baseline-relative changed paths below; no architecture impact is inferred from filenames alone.

{changed_text}

## Verification evidence

Latest verifier verdict: {verdict_text}.

| Check ID | Check | Result | Criteria | Exact command | Boundary proven |
|---|---|---|---|---|---|
{check_rows}

## GitHub and release state

- REPORTED: Governing Issue: {issue}.
- INFERRED: No live GitHub, deployment, or release state is claimed unless separately recorded in a handoff.

## Risks, limitations, and unverified claims

{risks}

Writes outside the declared scope:

{violation_text}

Working-tree state at report time:

{dirty_text}

## Decisions and authorization needed

{decisions}

## Recommended next loop

Review failed or missing criteria, stale or absent verification, scope violations, residual risks, and the governing Issue before selecting the next bounded slice.

## Exact revision and scope

- Start commit: `{evidence["start_commit"]}`
- End commit: `{evidence["end_commit"]}`
- Branch: `{evidence["branch"]}`
- Dirty-baseline entries: {len(evidence.get("scope", {}).get("baseline", []))}

Declared write set:

{declared_scope_text}

```text
{evidence.get("diff_stat") or "No tracked diff statistics available."}
```

## Agent handoffs

{handoffs}
"""


def finish_run(root: Path, run_id: str, state: str) -> tuple[Path, Path, dict[str, Any]]:
    path, record = load_run(root, run_id)
    if state == "reported":
        errors = completion_errors(root, record)
        if errors:
            raise ValueError("completion gate failed: " + "; ".join(errors))
    evidence = collect_git_evidence(root, record)
    record["state"] = state
    record["finished_at"] = utc_now()
    record["end_commit"] = evidence["end_commit"]
    write_json(path, record)
    run_dir = path.parent
    evidence_path = run_dir / "evidence.json"
    report_path = run_dir / "report.md"
    write_json(
        evidence_path,
        {
            "schema_version": record.get("schema_version", RUN_SCHEMA_VERSION),
            "run_id": run_id,
            "revision": record.get("revision"),
            "attempt_id": record.get("attempt_id"),
            "boundary": evidence,
            "acceptance_criteria": record.get("acceptance_criteria", []),
            "claims": [
                {
                    "status": "verified",
                    "claim": "Repository boundary collected",
                    "evidence": str(evidence_path),
                }
            ],
            "checks": record["checks"],
            "verdicts": record.get("verdicts", []),
            "release_impact": record.get("release_impact"),
            "risks": record["risks"],
        },
    )
    report_path.write_text(markdown_report(record, evidence), encoding="utf-8")
    return report_path, evidence_path, record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    subparsers = parser.add_subparsers(dest="action", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--objective", required=True)
    start.add_argument("--issue")
    start.add_argument("--run-id")
    start.add_argument("--criterion", action="append", required=True, metavar="ID=TEXT")
    start.add_argument("--write-path", action="append", default=[])
    start.add_argument("--write-prefix", action="append", default=[])
    start.add_argument("--implementer", action="append", required=True)

    check = subparsers.add_parser("record-check")
    check.add_argument("--run", required=True)
    check.add_argument("--name", required=True)
    check.add_argument("--command", dest="command_text", required=True)
    check.add_argument("--status", choices=CHECK_STATUSES, required=True)
    check.add_argument("--evidence", required=True)
    check.add_argument("--criterion", action="append", default=[])

    release_impact = subparsers.add_parser("record-release-impact")
    release_impact.add_argument("--run", required=True)
    release_impact.add_argument("--level", choices=RELEASE_IMPACTS, required=True)
    release_impact.add_argument("--reason", required=True)
    release_impact.add_argument("--public-contract-change", action="append", default=[])

    verdict = subparsers.add_parser("record-verdict")
    verdict.add_argument("--run", required=True)
    verdict.add_argument("--reviewer", required=True)
    verdict.add_argument("--verdict", choices=VERDICTS, required=True)
    verdict.add_argument("--criterion", action="append", default=[])
    verdict.add_argument("--evidence", required=True)

    revise = subparsers.add_parser("revise")
    revise.add_argument("--run", required=True)
    revise.add_argument("--reason", required=True)
    revise.add_argument("--objective")
    revise.add_argument("--criterion", action="append")
    revise.add_argument("--write-path", action="append")
    revise.add_argument("--write-prefix", action="append")

    attempt = subparsers.add_parser("new-attempt")
    attempt.add_argument("--run", required=True)
    attempt.add_argument("--reason", required=True)

    resume = subparsers.add_parser("resume")
    resume.add_argument("--run", required=True)
    resume.add_argument("--handoff", type=Path, required=True)
    resume.add_argument("--by", required=True)

    recovery = subparsers.add_parser("recovery-status")
    recovery.add_argument("--run", required=True)
    recovery.add_argument("--integration-ref")

    waiver = subparsers.add_parser("waive-criterion")
    waiver.add_argument("--run", required=True)
    waiver.add_argument("--criterion", required=True)
    waiver.add_argument("--by", required=True)
    waiver.add_argument("--reason", required=True)

    handoff = subparsers.add_parser("record-handoff")
    handoff.add_argument("--run", required=True)
    handoff.add_argument("--file", type=Path, required=True)

    for name in ("record-risk", "record-decision"):
        item = subparsers.add_parser(name)
        item.add_argument("--run", required=True)
        item.add_argument("--text", required=True)

    state_parser = subparsers.add_parser("set-state")
    state_parser.add_argument("--run", required=True)
    state_parser.add_argument("--state", required=True)

    finish = subparsers.add_parser("finish")
    finish.add_argument("--run", required=True)
    finish.add_argument("--state", choices=FINAL_STATES, default="reported")

    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    try:
        if args.action == "start":
            record = start_run(
                root,
                args.objective,
                args.issue,
                args.run_id,
                acceptance_criteria=parse_criteria(args.criterion),
                declared_write_set=make_write_set(args.write_path, args.write_prefix),
                implementers=args.implementer,
            )
            print(record["run_id"])
        elif args.action == "record-check":
            record_check(
                root,
                args.run,
                name=args.name,
                command=args.command_text,
                status=args.status,
                evidence=args.evidence,
                criteria=args.criterion,
            )
            print(f"recorded check for {args.run}")
        elif args.action == "record-release-impact":
            record_release_impact(
                root,
                args.run,
                level=args.level,
                reason=args.reason,
                public_contract_changes=args.public_contract_change,
            )
            print(f"recorded release impact for {args.run}")
        elif args.action == "record-verdict":
            record_verdict(
                root,
                args.run,
                reviewer=args.reviewer,
                verdict=args.verdict,
                criteria=args.criterion,
                evidence=args.evidence,
            )
            print(f"recorded verifier verdict for {args.run}")
        elif args.action == "revise":
            criteria = parse_criteria(args.criterion) if args.criterion is not None else None
            write_set = None
            if args.write_path is not None or args.write_prefix is not None:
                write_set = make_write_set(args.write_path or [], args.write_prefix or [])
            record = revise_run(
                root,
                args.run,
                reason=args.reason,
                objective=args.objective,
                acceptance_criteria=criteria,
                declared_write_set=write_set,
            )
            print(f"revised {args.run} to revision {record['revision']}")
        elif args.action == "new-attempt":
            record = new_attempt(root, args.run, args.reason)
            print(f"started attempt {record['attempt_id']} for {args.run}")
        elif args.action == "resume":
            record = resume_run(
                root,
                args.run,
                handoff=load_json(args.handoff),
                authorized_by=args.by,
            )
            print(f"resumed {args.run} at revision {record['revision']}")
        elif args.action == "recovery-status":
            print(json.dumps(recovery_status(root, args.run, args.integration_ref), indent=2))
        elif args.action == "waive-criterion":
            waive_criterion(
                root,
                args.run,
                args.criterion,
                waived_by=args.by,
                reason=args.reason,
            )
            print(f"waived {args.criterion} for {args.run}")
        elif args.action == "record-handoff":
            add_item(root, args.run, "agent_handoffs", load_json(args.file))
            print(f"recorded handoff for {args.run}")
        elif args.action == "record-risk":
            add_item(root, args.run, "risks", args.text)
            print(f"recorded risk for {args.run}")
        elif args.action == "record-decision":
            add_item(root, args.run, "decisions", args.text)
            print(f"recorded decision for {args.run}")
        elif args.action == "set-state":
            set_state(root, args.run, args.state)
            print(f"set {args.run} to {args.state}")
        elif args.action == "finish":
            report, evidence, _ = finish_run(root, args.run, args.state)
            print(f"report: {report}")
            print(f"evidence: {evidence}")
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
