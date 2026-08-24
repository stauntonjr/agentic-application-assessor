#!/usr/bin/env python3
"""Manage provenance-locked, ownership-aware upgrades for derived harness repositories."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root, utc_now, write_json
except ImportError:  # Direct script execution.
    from common import load_json, repository_root, utc_now, write_json


ALLOWED_ACTIONS = {"add", "replace", "remove", "manual"}
OWNERSHIP_CLASSES = {"upstream-owned", "project-owned", "merge-required"}
RESOLUTIONS = {"keep-local", "use-upstream", "merged"}
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
IGNORED_PARTS = {
    ".git",
    ".harness",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
IGNORED_NAMES = {".coverage", "harness.lock"}


def sha256(path: Path) -> str | None:
    if not path.is_file() or path.is_symlink():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_relative(value: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or str(path) in {".", ""}:
        raise ValueError(f"path must stay inside the repository: {value}")
    return path


def safe_path(root: Path, value: str) -> Path:
    relative = safe_relative(value)
    candidate = root / relative
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"refusing path through symlink: {value}")
    if candidate.is_symlink():
        raise ValueError(f"refusing symlink target: {value}")
    return candidate


def validate_repository(value: str) -> str:
    if not REPOSITORY.fullmatch(value):
        raise ValueError(f"invalid GitHub repository: {value}")
    return value


def validate_ref(value: str) -> str:
    if not SAFE_REF.fullmatch(value) or ".." in value.split("/"):
        raise ValueError(f"invalid release ref: {value}")
    return value


def ownership_for(path: str, policy: dict[str, Any]) -> str:
    for rule in policy.get("rules", []):
        if fnmatch.fnmatchcase(path, rule["pattern"]):
            return rule["ownership"]
    return policy.get("default_ownership", "project-owned")


def validate_ownership_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if policy.get("default_ownership") not in OWNERSHIP_CLASSES:
        errors.append("ownership policy has invalid default_ownership")
    for index, rule in enumerate(policy.get("rules", [])):
        if not rule.get("pattern"):
            errors.append(f"ownership rule {index}: pattern is required")
        if rule.get("ownership") not in OWNERSHIP_CLASSES:
            errors.append(f"ownership rule {index}: invalid ownership")
    return errors


def iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in relative.parts):
            continue
        if path.name in IGNORED_NAMES or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"template source contains a symlink: {relative}")
        if path.is_file():
            files.append(path)
    return sorted(files)


def create_lock(
    source_root: Path,
    *,
    repository: str,
    release: str,
    commit: str,
) -> dict[str, Any]:
    policy = load_json(source_root / "harness/ownership.json")
    errors = validate_ownership_policy(policy)
    if errors:
        raise ValueError("; ".join(errors))
    version = load_json(source_root / "harness/version.json")
    files: dict[str, Any] = {}
    for path in iter_source_files(source_root):
        relative = path.relative_to(source_root).as_posix()
        digest = sha256(path)
        if digest is None:
            raise ValueError(f"unable to hash source file: {relative}")
        files[relative] = {
            "sha256": digest,
            "ownership": ownership_for(relative, policy),
        }
    return {
        "schema_version": "1.0",
        "harness_version": version["current"],
        "upstream": {
            "repository": validate_repository(repository),
            "release": validate_ref(release),
            "commit": commit,
        },
        "files": files,
    }


def validate_lock(lock: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "harness_version", "upstream", "files"):
        if key not in lock:
            errors.append(f"lock missing {key}")
    upstream = lock.get("upstream", {})
    try:
        validate_repository(upstream.get("repository", ""))
        validate_ref(upstream.get("release", ""))
    except ValueError as exc:
        errors.append(str(exc))
    if not upstream.get("commit"):
        errors.append("lock upstream.commit is required")
    for path, entry in lock.get("files", {}).items():
        try:
            safe_relative(path)
        except ValueError as exc:
            errors.append(str(exc))
        digest = entry.get("sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"lock has invalid sha256 for {path}")
        if entry.get("ownership") not in OWNERSHIP_CLASSES:
            errors.append(f"lock has invalid ownership for {path}")
    return errors


def inspect_lock_state(root: Path, lock: dict[str, Any]) -> dict[str, list[str]]:
    state = {"matching": [], "modified": [], "missing": []}
    for relative, entry in sorted(lock.get("files", {}).items()):
        current = sha256(safe_path(root, relative))
        if current is None:
            state["missing"].append(relative)
        elif current == entry["sha256"]:
            state["matching"].append(relative)
        else:
            state["modified"].append(relative)
    return state


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "from_version", "to_version", "operations"):
        if key not in manifest:
            errors.append(f"migration missing {key}")
    for index, operation in enumerate(manifest.get("operations", [])):
        action = operation.get("action")
        path = operation.get("path")
        if action not in ALLOWED_ACTIONS:
            errors.append(f"operation {index}: unsupported action {action}")
        try:
            safe_relative(path if isinstance(path, str) else "")
        except ValueError:
            errors.append(f"operation {index}: path must stay inside the repository")
        if not operation.get("reason"):
            errors.append(f"operation {index}: reason is required")
        if action in {"add", "replace"} and not operation.get("source"):
            errors.append(f"operation {index}: {action} requires source")
        ownership = operation.get("ownership")
        if ownership is not None and ownership not in OWNERSHIP_CLASSES:
            errors.append(f"operation {index}: invalid ownership")
    return errors


def build_plan(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Render the legacy manifest plan without mutating the repository."""
    current = load_json(root / "harness/project.yaml")["harness_version"]
    items = []
    for operation in manifest.get("operations", []):
        target = safe_path(root, operation["path"])
        ownership = operation.get("ownership", "merge-required")
        items.append(
            {
                **operation,
                "ownership": ownership,
                "target_exists": target.exists(),
                "current_sha256": sha256(target),
                "requires_explicit_review": (
                    operation["action"] in {"replace", "remove", "manual"}
                    or ownership != "upstream-owned"
                ),
            }
        )
    return {
        "ok": current == manifest.get("from_version"),
        "current_version": current,
        "from_version": manifest.get("from_version"),
        "to_version": manifest.get("to_version"),
        "dry_run": True,
        "operations": items,
        "note": "legacy manifest plan; use --source-root for three-way planning",
    }


def _operation(
    *,
    path: str,
    action: str,
    ownership: str,
    base: str | None,
    local: str | None,
    upstream: str | None,
    disposition: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "path": path,
        "action": action,
        "ownership": ownership,
        "base_sha256": base,
        "local_sha256": local,
        "upstream_sha256": upstream,
        "disposition": disposition,
        "reason": reason,
        "requires_explicit_review": disposition == "manual",
    }


def build_release_plan(root: Path, source_root: Path) -> dict[str, Any]:
    current_lock = load_json(root / "harness.lock")
    source_lock = load_json(source_root / "harness.lock")
    errors = validate_lock(current_lock) + validate_lock(source_lock)
    if errors:
        raise ValueError("; ".join(errors))
    if current_lock["upstream"]["repository"] != source_lock["upstream"]["repository"]:
        raise ValueError("source release belongs to a different upstream repository")
    for relative, entry in source_lock["files"].items():
        actual = sha256(safe_path(source_root, relative))
        if actual != entry["sha256"]:
            raise ValueError(f"source lock mismatch for {relative}")

    operations: list[dict[str, Any]] = []
    all_paths = sorted(set(current_lock["files"]) | set(source_lock["files"]))
    for relative in all_paths:
        old = current_lock["files"].get(relative)
        new = source_lock["files"].get(relative)
        base = old.get("sha256") if old else None
        upstream = new.get("sha256") if new else None
        local = sha256(safe_path(root, relative))
        ownership = (new or old)["ownership"]
        ownership_changed = bool(old and new and old["ownership"] != new["ownership"])

        if old and new and base == upstream and not ownership_changed:
            continue
        if not old and new:
            if local is None:
                disposition, reason = "ready", "new upstream file does not collide locally"
            elif local == upstream:
                disposition, reason = "current", "local file already matches the release"
            else:
                disposition, reason = "manual", "new upstream file collides with a local file"
            operations.append(
                _operation(
                    path=relative,
                    action="add",
                    ownership=ownership,
                    base=base,
                    local=local,
                    upstream=upstream,
                    disposition=disposition,
                    reason=reason,
                )
            )
            continue
        if old and not new:
            if local is None:
                disposition, reason = "current", "file is already absent"
            elif ownership == "upstream-owned" and local == base:
                disposition, reason = "ready", "unchanged upstream-owned file was removed upstream"
            else:
                disposition, reason = (
                    "manual",
                    "removal could discard local or project-owned content",
                )
            operations.append(
                _operation(
                    path=relative,
                    action="remove",
                    ownership=ownership,
                    base=base,
                    local=local,
                    upstream=None,
                    disposition=disposition,
                    reason=reason,
                )
            )
            continue

        if ownership_changed:
            disposition, reason = "manual", "ownership classification changed"
        elif local == upstream:
            disposition, reason = "current", "local file already matches the release"
        elif ownership == "upstream-owned" and local == base:
            disposition, reason = "ready", "unmodified upstream-owned file can advance safely"
        elif ownership == "project-owned":
            disposition, reason = "manual", "project-owned files are never replaced silently"
        elif ownership == "merge-required":
            disposition, reason = "manual", "repository policy requires a reviewed merge"
        else:
            disposition, reason = "manual", "upstream-owned file has local modifications"
        operations.append(
            _operation(
                path=relative,
                action="replace",
                ownership=ownership,
                base=base,
                local=local,
                upstream=upstream,
                disposition=disposition,
                reason=reason,
            )
        )

    from_version = current_lock["harness_version"]
    to_version = source_lock["harness_version"]
    counts = {
        key: sum(operation["disposition"] == key for operation in operations)
        for key in ("ready", "manual", "current")
    }
    return {
        "schema_version": "1.0",
        "plan_id": f"{from_version}-to-{to_version}",
        "from_version": from_version,
        "to_version": to_version,
        "source": source_lock["upstream"],
        "dry_run": True,
        "ok": from_version != to_version,
        "counts": counts,
        "operations": operations,
        "note": "ready operations are safe to automate; every manual operation requires a named resolution",
    }


def parse_resolutions(values: list[str]) -> dict[str, str]:
    resolutions: dict[str, str] = {}
    for value in values:
        path, separator, decision = value.rpartition("=")
        if not separator or decision not in RESOLUTIONS:
            raise ValueError(f"resolution must be PATH=keep-local|use-upstream|merged: {value}")
        safe_relative(path)
        resolutions[path] = decision
    return resolutions


def _copy_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.harness-upgrade.tmp")
    shutil.copy2(source, temporary)
    temporary.replace(target)


def _backup(root: Path, backup_root: Path, relative: str) -> dict[str, Any]:
    target = safe_path(root, relative)
    before = sha256(target)
    record = {"path": relative, "existed": target.is_file(), "before_sha256": before}
    if target.is_file():
        backup = safe_path(backup_root, relative)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        record["backup"] = relative
    return record


def apply_release_plan(
    root: Path,
    source_root: Path,
    plan: dict[str, Any],
    resolutions: dict[str, str],
    *,
    receipt_root: Path | None = None,
) -> Path:
    current_lock = load_json(root / "harness.lock")
    source_lock = load_json(source_root / "harness.lock")
    errors = validate_lock(current_lock) + validate_lock(source_lock)
    if errors:
        raise ValueError("; ".join(errors))
    if not plan.get("ok"):
        raise ValueError("plan does not describe a newer or different release")
    if current_lock["harness_version"] != plan.get("from_version"):
        raise ValueError("plan is stale: current lock version changed")
    if source_lock["harness_version"] != plan.get("to_version"):
        raise ValueError("plan source version does not match source lock")
    if source_lock["upstream"] != plan.get("source"):
        raise ValueError("plan source provenance does not match source lock")
    if current_lock["upstream"]["repository"] != source_lock["upstream"]["repository"]:
        raise ValueError("source release belongs to a different upstream repository")

    manual_paths = {
        item["path"] for item in plan.get("operations", []) if item["disposition"] == "manual"
    }
    unresolved = sorted(manual_paths - resolutions.keys())
    unknown = sorted(resolutions.keys() - manual_paths)
    if unresolved:
        raise ValueError(f"manual operations require resolutions: {', '.join(unresolved)}")
    if unknown:
        raise ValueError(f"resolutions do not match manual operations: {', '.join(unknown)}")

    decisions: dict[str, str] = {}
    for item in plan.get("operations", []):
        disposition = item["disposition"]
        if disposition == "current":
            decisions[item["path"]] = "already-current"
            continue
        decision = "use-upstream" if disposition == "ready" else resolutions[item["path"]]
        decisions[item["path"]] = decision
        current = sha256(safe_path(root, item["path"]))
        if decision != "merged" and current != item.get("local_sha256"):
            raise ValueError(f"plan is stale: local file changed: {item['path']}")
        if decision == "use-upstream" and item["action"] != "remove":
            source = safe_path(source_root, item["path"])
            if sha256(source) != item.get("upstream_sha256"):
                raise ValueError(f"source changed after planning: {item['path']}")

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    receipt_dir = receipt_root or root / ".harness/upgrades" / plan["plan_id"] / stamp
    receipt_dir.mkdir(parents=True, exist_ok=False)
    backup_root = receipt_dir / "backup"
    pre_state: dict[str, dict[str, Any]] = {}

    def preserve(relative: str) -> None:
        if relative not in pre_state:
            pre_state[relative] = _backup(root, backup_root, relative)

    preserve("harness.lock")
    preserve("harness/project.yaml")
    applied: list[dict[str, Any]] = []
    try:
        for item in plan.get("operations", []):
            decision = decisions[item["path"]]
            if decision == "already-current":
                applied.append({"path": item["path"], "decision": decision, "changed": False})
                continue
            target = safe_path(root, item["path"])
            current = sha256(target)
            changed = False
            if decision == "use-upstream":
                preserve(item["path"])
                if item["action"] == "remove":
                    if target.is_file():
                        target.unlink()
                        changed = True
                else:
                    source = safe_path(source_root, item["path"])
                    _copy_atomic(source, target)
                    changed = current != item.get("upstream_sha256")
            applied.append({"path": item["path"], "decision": decision, "changed": changed})

        _copy_atomic(source_root / "harness.lock", root / "harness.lock")
        project = load_json(root / "harness/project.yaml")
        project["harness_version"] = plan["to_version"]
        write_json(root / "harness/project.yaml", project)

        for relative, record in pre_state.items():
            record["after_sha256"] = sha256(safe_path(root, relative))
        receipt = {
            "schema_version": "1.0",
            "plan_id": plan["plan_id"],
            "from_version": plan["from_version"],
            "to_version": plan["to_version"],
            "applied_at": utc_now(),
            "rolled_back_at": None,
            "pre_state": list(pre_state.values()),
            "decisions": applied,
        }
        receipt_path = receipt_dir / "receipt.json"
        write_json(receipt_path, receipt)
        return receipt_path
    except Exception:
        for record in reversed(list(pre_state.values())):
            target = safe_path(root, record["path"])
            if record["existed"]:
                source = safe_path(backup_root, record["backup"])
                _copy_atomic(source, target)
            elif target.is_file():
                target.unlink()
        raise


def rollback_receipt(root: Path, receipt_path: Path) -> dict[str, Any]:
    receipt = load_json(receipt_path)
    if receipt.get("rolled_back_at"):
        raise ValueError("receipt has already been rolled back")
    backup_root = receipt_path.parent / "backup"
    for record in receipt.get("pre_state", []):
        target = safe_path(root, record["path"])
        if sha256(target) != record.get("after_sha256"):
            raise ValueError(f"refusing rollback over later changes: {record['path']}")
        if record["existed"]:
            source = safe_path(backup_root, record["backup"])
            if sha256(source) != record.get("before_sha256"):
                raise ValueError(f"rollback backup is missing or corrupt: {record['path']}")
    for record in reversed(receipt.get("pre_state", [])):
        target = safe_path(root, record["path"])
        if record["existed"]:
            source = safe_path(backup_root, record["backup"])
            _copy_atomic(source, target)
        elif target.is_file():
            target.unlink()
    receipt["rolled_back_at"] = utc_now()
    write_json(receipt_path, receipt)
    return receipt


def latest_release(repository: str) -> dict[str, Any]:
    repository = validate_repository(repository)
    result = subprocess.run(
        ["gh", "api", f"repos/{repository}/releases/latest"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "unable to query latest release")
    payload = json.loads(result.stdout)
    return {
        "repository": repository,
        "tag": payload.get("tag_name"),
        "target": payload.get("target_commitish"),
        "published_at": payload.get("published_at"),
        "url": payload.get("html_url"),
    }


def fetch_release(root: Path, repository: str, ref: str, destination: Path | None = None) -> Path:
    repository = validate_repository(repository)
    ref = validate_ref(ref)
    source_root = root / ".harness/upgrades/sources"
    source_root.mkdir(parents=True, exist_ok=True)
    target = (destination or source_root / ref.replace("/", "-")).resolve()
    try:
        target.relative_to(source_root.resolve())
    except ValueError as exc:
        raise ValueError("release destination must stay under .harness/upgrades/sources") from exc
    if target.exists():
        raise ValueError(f"release destination already exists: {target}")
    result = subprocess.run(
        ["gh", "repo", "clone", repository, str(target), "--", "--branch", ref, "--depth", "1"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "unable to fetch release")
    asset_root = root / ".harness/upgrades/assets" / ref.replace("/", "-")
    asset_root.mkdir(parents=True, exist_ok=True)
    asset = asset_root / "harness.release.lock"
    if asset.exists():
        raise ValueError(f"release lock asset already exists: {asset}")
    download = subprocess.run(
        [
            "gh",
            "release",
            "download",
            ref,
            "--repo",
            repository,
            "--pattern",
            "harness.release.lock",
            "--dir",
            str(asset_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if download.returncode != 0 or not asset.is_file():
        raise RuntimeError(download.stderr.strip() or "release is missing harness.release.lock")
    release_lock = load_json(asset)
    errors = validate_lock(release_lock)
    if errors:
        raise ValueError("invalid release lock: " + "; ".join(errors))
    if release_lock["upstream"]["repository"] != repository:
        raise ValueError("release lock repository does not match requested repository")
    if release_lock["upstream"]["release"] != ref:
        raise ValueError("release lock tag does not match requested ref")
    _copy_atomic(asset, target / "harness.lock")
    return target


def write_output(payload: dict[str, Any], output: Path | None) -> None:
    if output:
        write_json(output, payload)
        print(output)
    else:
        print(json.dumps(payload, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--source-root", type=Path)
    latest = subparsers.add_parser("latest")
    latest.add_argument("--repository")
    fetch = subparsers.add_parser("fetch")
    fetch.add_argument("--repository")
    fetch.add_argument("--ref", required=True)
    fetch.add_argument("--destination", type=Path)
    fetch.add_argument("--yes", action="store_true")
    lock = subparsers.add_parser("lock")
    lock.add_argument("--source-root", type=Path)
    lock.add_argument("--repository")
    lock.add_argument("--release")
    lock.add_argument("--commit", default="UNPUBLISHED")
    lock.add_argument("--output", type=Path)
    lock.add_argument("--yes", action="store_true")
    plan = subparsers.add_parser("plan")
    plan.add_argument("--manifest", type=Path)
    plan.add_argument("--source-root", type=Path)
    plan.add_argument("--output", type=Path)
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--source-root", type=Path, required=True)
    apply_parser.add_argument("--resolve", action="append", default=[])
    apply_parser.add_argument("--yes", action="store_true")
    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("--receipt", type=Path, required=True)
    rollback.add_argument("--yes", action="store_true")

    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    try:
        if args.command == "status":
            lock_data = load_json(root / "harness.lock")
            errors = validate_lock(lock_data)
            project = load_json(root / "harness/project.yaml")
            payload: dict[str, Any] = {
                "ok": not errors and project["harness_version"] == lock_data["harness_version"],
                "project_version": project["harness_version"],
                "locked_version": lock_data["harness_version"],
                "upstream": lock_data["upstream"],
                "files": inspect_lock_state(root, lock_data),
                "errors": errors,
            }
            if args.source_root:
                payload["upgrade_plan"] = build_release_plan(root, args.source_root.resolve())
            write_output(payload, None)
            return 0 if payload["ok"] else 1

        lock_data = load_json(root / "harness.lock") if (root / "harness.lock").is_file() else None
        if args.command == "latest":
            if args.repository:
                repository = args.repository
            elif lock_data is not None:
                repository = lock_data["upstream"]["repository"]
            else:
                raise ValueError("latest requires --repository when harness.lock is absent")
            write_output(latest_release(repository), None)
        elif args.command == "fetch":
            if not args.yes:
                raise ValueError("fetch requires --yes because it writes a release checkout")
            if args.repository:
                repository = args.repository
            elif lock_data is not None:
                repository = lock_data["upstream"]["repository"]
            else:
                raise ValueError("fetch requires --repository when harness.lock is absent")
            print(fetch_release(root, repository, args.ref, args.destination))
        elif args.command == "lock":
            if not args.yes:
                raise ValueError("lock generation requires --yes")
            source_root = args.source_root.resolve() if args.source_root else root
            version = load_json(source_root / "harness/version.json")
            existing = (
                load_json(source_root / "harness.lock")
                if (source_root / "harness.lock").is_file()
                else {}
            )
            repository = (
                args.repository
                or existing.get("upstream", {}).get("repository")
                or version["upstream_repository"]
            )
            release = args.release or f"v{version['current']}"
            payload = create_lock(
                source_root, repository=repository, release=release, commit=args.commit
            )
            output = args.output.resolve() if args.output else source_root / "harness.lock"
            write_json(output, payload)
            print(output)
        elif args.command == "plan":
            if bool(args.manifest) == bool(args.source_root):
                raise ValueError("plan requires exactly one of --manifest or --source-root")
            if args.manifest:
                manifest = load_json(args.manifest)
                errors = validate_manifest(manifest)
                if errors:
                    raise ValueError("; ".join(errors))
                payload = build_plan(root, manifest)
            else:
                payload = build_release_plan(root, args.source_root.resolve())
            write_output(payload, args.output)
        elif args.command == "apply":
            if not args.yes:
                raise ValueError("apply requires --yes")
            receipt = apply_release_plan(
                root,
                args.source_root.resolve(),
                load_json(args.plan),
                parse_resolutions(args.resolve),
            )
            print(receipt)
        elif args.command == "rollback":
            if not args.yes:
                raise ValueError("rollback requires --yes")
            rollback_receipt(root, args.receipt.resolve())
            print(f"rolled back: {args.receipt}")
        return 0
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
