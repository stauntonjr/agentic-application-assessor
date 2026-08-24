"""Validate immutable and least-privilege GitHub Actions workflow references."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ACTION_USE = re.compile(
    r"^\s*(?:-\s+)?(?:uses|\"uses\"|'uses')\s*:\s*"
    r"(?:\"([^\"]+)\"|'([^']+)'|([^\s#]+))",
    re.MULTILINE,
)
FULL_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
DOCKER_DIGEST = re.compile(r"^docker://[^\s@]+@sha256:[0-9a-f]{64}$")
PERMISSIONS_KEY = re.compile(r"^(\s*)(?:permissions|\"permissions\"|'permissions')\s*:\s*(.*)$")
PERMISSION_ENTRY = re.compile(
    r"^\s+(?:([a-z-]+)|\"([a-z-]+)\"|'([a-z-]+)')\s*:\s*"
    r"([\"']?)(read|write|none)\4\s*(?:#.*)?$"
)


def action_references(text: str) -> list[str]:
    return [next(value for value in match if value) for match in ACTION_USE.findall(text)]


def write_permissions(text: str) -> set[str]:
    lines = text.splitlines()
    permissions: set[str] = set()
    for index, line in enumerate(lines):
        match = PERMISSIONS_KEY.match(line)
        if not match:
            continue
        indentation = len(match.group(1))
        inline = match.group(2).strip()
        if inline and inline != "{}":
            if inline == "write-all":
                permissions.add("*")
            else:
                permissions.add("unparsed-inline-permissions")
            continue
        for child in lines[index + 1 :]:
            child_indent = len(child) - len(child.lstrip())
            if child.strip() and child_indent <= indentation:
                break
            permission = PERMISSION_ENTRY.match(child)
            if permission and permission.group(5) == "write":
                permissions.add(next(value for value in permission.groups()[:3] if value))
    return permissions


def check_workflows(root: Path) -> list[str]:
    errors: list[str] = []
    workflow_root = root / ".github/workflows"
    allowlist_path = root / ".github/actions-allowlist.json"
    allowed: dict[str, list[str]] = {}
    if allowlist_path.is_file():
        allowed = json.loads(allowlist_path.read_text(encoding="utf-8")).get(
            "write_permissions", {}
        )
    for path in sorted((*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml"))):
        relative = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        if allowlist_path.is_file() and path.name not in allowed:
            errors.append(f"{relative}: workflow is missing from the write-permission allowlist")
        if not re.search(
            r"^(?:permissions|\"permissions\"|'permissions')\s*:\s*(?:$|\{)",
            text,
            re.MULTILINE,
        ):
            errors.append(f"{relative}: missing explicit top-level permissions")
        actual_writes = write_permissions(text)
        expected_writes = set(allowed.get(path.name, []))
        unexpected = sorted(actual_writes - expected_writes)
        missing = sorted(expected_writes - actual_writes)
        if unexpected:
            errors.append(
                f"{relative}: write permissions are not allowlisted: {', '.join(unexpected)}"
            )
        if missing:
            errors.append(f"{relative}: stale write-permission allowlist: {', '.join(missing)}")
        if re.search(r"^\s*pull_request_target:\s*$", text, re.MULTILINE):
            errors.append(f"{relative}: pull_request_target requires a separate threat review")
        for reference in action_references(text):
            if reference.startswith("./"):
                continue
            if reference.startswith("docker://"):
                if not DOCKER_DIGEST.fullmatch(reference):
                    errors.append(
                        f"{relative}: Docker action must use a sha256 image digest: {reference}"
                    )
                continue
            action, separator, revision = reference.rpartition("@")
            if not separator or not action or not FULL_COMMIT_SHA.fullmatch(revision):
                errors.append(
                    f"{relative}: external action must use a full 40-character commit SHA: "
                    f"{reference}"
                )
    unknown_workflows = sorted(set(allowed) - {path.name for path in workflow_root.glob("*.y*ml")})
    if unknown_workflows:
        errors.append(
            "actions allowlist references missing workflows: " + ", ".join(unknown_workflows)
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else Path(__file__).resolve().parents[2]
    errors = check_workflows(root)
    if errors:
        print("GitHub Actions supply-chain check: failed")
        for error in errors:
            print(f"  error: {error}")
        return 1
    print("GitHub Actions supply-chain check: ok")
    return 0
