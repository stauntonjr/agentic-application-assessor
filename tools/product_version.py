#!/usr/bin/env python3
"""Resolve and validate the product version independently from the harness version."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root
except ImportError:  # Direct script execution.
    from common import load_json, repository_root


def nested_value(data: Any, dotted_key: str) -> Any:
    value = data
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"version source key does not exist: {dotted_key}")
        value = value[part]
    return value


def split_locator(locator: str) -> tuple[str, str | None]:
    path, separator, key = locator.partition(":")
    if not path or (separator and not key):
        raise ValueError(f"invalid product version source: {locator}")
    return path, key if separator else None


def resolve_source(root: Path, locator: str) -> str:
    relative, key = split_locator(locator)
    source = (root / relative).resolve()
    try:
        source.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("product version source must stay inside the repository") from exc
    if not source.is_file():
        raise ValueError(f"product version source does not exist: {relative}")
    if key is None:
        return source.read_text(encoding="utf-8").strip()
    if source.suffix == ".toml":
        data = tomllib.loads(source.read_text(encoding="utf-8"))
    elif source.suffix in {".json", ".yaml", ".yml"}:
        data = load_json(source)
    else:
        raise ValueError("keyed product version sources must be JSON-compatible or TOML")
    value = nested_value(data, key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("resolved product version must be a non-empty string")
    return value.strip()


def product_version_status(root: Path, tag: str | None = None) -> dict[str, Any]:
    project = load_json(root / "harness/project.yaml")
    contract = project.get("engineering", {}).get("versioning", {})
    strategy = contract.get("strategy")
    if project.get("template_mode") or strategy in {"TBD", "none"}:
        return {
            "ok": True,
            "configured": False,
            "strategy": strategy,
            "reason": "template or no-version project",
        }
    declared = contract.get("current", "")
    source = contract.get("source", "")
    resolved = resolve_source(root, source)
    expected_tag = f"{contract.get('tag_prefix', '')}{declared}"
    errors: list[str] = []
    if resolved != declared:
        errors.append(f"declared product version {declared} differs from source {resolved}")
    if tag is not None and tag != expected_tag:
        errors.append(f"product tag {tag} must equal {expected_tag}")
    return {
        "ok": not errors,
        "configured": True,
        "strategy": strategy,
        "declared": declared,
        "source": source,
        "resolved": resolved,
        "expected_tag": expected_tag,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--tag", help="Optional product release tag to validate")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    try:
        status = product_version_status(root, args.tag)
    except (OSError, ValueError) as exc:
        status = {"ok": False, "configured": True, "errors": [str(exc)]}
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print(f"product version: {'ok' if status['ok'] else 'failed'}")
        for error in status.get("errors", []):
            print(f"  error: {error}")
        if status.get("configured") and status.get("ok"):
            print(f"  {status['declared']} from {status['source']}")
        elif not status.get("configured"):
            print(f"  not configured: {status['reason']}")
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
